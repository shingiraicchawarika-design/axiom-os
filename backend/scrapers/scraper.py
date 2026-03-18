"""
Axiom OS — Real scraper layer using Playwright + httpx
Scrapes: Google, care directories, forums, Bark, LinkedIn, NHS/LA, Facebook, social
"""
import asyncio
import random
import re
from typing import List, Optional
from datetime import datetime
from playwright.async_api import async_playwright, Browser, Page
from bs4 import BeautifulSoup
import httpx
from fake_useragent import UserAgent

from core.config import (
    COMPANY_LOCATIONS, SERVICE_KEYWORDS, INTENT_PHRASES,
    SCRAPING_DELAY_MS, HEADLESS
)
from models.schemas import RawLead, ScraperSource


ua = UserAgent()

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

async def human_delay(min_ms: int = 1500, max_ms: int = 4000):
    await asyncio.sleep(random.randint(min_ms, max_ms) / 1000)


class BaseScraper:
    def __init__(self, browser: Browser):
        self.browser = browser

    async def new_page(self) -> Page:
        context = await self.browser.new_context(
            user_agent=ua.random,
            viewport={"width": 1280, "height": 800},
            locale="en-GB",
            timezone_id="Europe/London",
        )
        page = await context.new_page()
        await page.set_extra_http_headers({**HEADERS, "User-Agent": ua.random})
        return page

    async def safe_goto(self, page: Page, url: str, wait: int = 3000) -> bool:
        try:
            await page.goto(url, timeout=15000, wait_until="domcontentloaded")
            await asyncio.sleep(wait / 1000)
            return True
        except Exception as e:
            print(f"[Scraper] Failed to load {url}: {e}")
            return False


# ── Google Search Scraper ─────────────────────────────────────────────────────
class GoogleScraper(BaseScraper):
    """Scrapes Google search results for care intent queries"""

    BASE_URL = "https://www.google.co.uk/search"

    async def search(self, query: str, num: int = 10) -> List[RawLead]:
        leads = []
        page = await self.new_page()
        try:
            url = f"{self.BASE_URL}?q={query.replace(' ', '+')}&num={num}&gl=uk&hl=en"
            ok = await self.safe_goto(page, url, wait=2000)
            if not ok:
                return leads

            # Accept cookies if present
            try:
                cookie_btn = page.locator("button:has-text('Accept all')")
                if await cookie_btn.count() > 0:
                    await cookie_btn.first.click()
                    await asyncio.sleep(1)
            except:
                pass

            # Extract organic results
            results = await page.query_selector_all("div.g")
            for result in results[:num]:
                try:
                    title_el = await result.query_selector("h3")
                    link_el = await result.query_selector("a")
                    snippet_el = await result.query_selector("div[data-sncf], .VwiC3b, .yXK7lf")

                    title = await title_el.inner_text() if title_el else ""
                    url_href = await link_el.get_attribute("href") if link_el else ""
                    snippet = await snippet_el.inner_text() if snippet_el else ""

                    if snippet and len(snippet) > 30:
                        location = self._extract_location(snippet + " " + title)
                        leads.append(RawLead(
                            source=ScraperSource.GOOGLE,
                            source_url=url_href,
                            title=title,
                            snippet=snippet[:500],
                            location=location,
                            scraped_at=datetime.now(),
                            raw_data={"query": query}
                        ))
                except:
                    continue
        except Exception as e:
            print(f"[GoogleScraper] Error: {e}")
        finally:
            await page.close()
        return leads

    def _extract_location(self, text: str) -> Optional[str]:
        for loc in COMPANY_LOCATIONS:
            if loc.lower() in text.lower():
                return loc
        return None

    async def scrape_intent_queries(self, locations: List[str], max_per_query: int = 5) -> List[RawLead]:
        all_leads = []
        queries = []
        for phrase in INTENT_PHRASES[:8]:
            for loc in locations[:3]:
                queries.append(f"{phrase} {loc}")
        for keyword in SERVICE_KEYWORDS[:5]:
            for loc in locations[:2]:
                queries.append(f"{keyword} {loc}")

        for query in queries[:15]:  # Limit to avoid rate limiting
            leads = await self.search(query, num=max_per_query)
            all_leads.extend(leads)
            await human_delay(2000, 5000)

        return all_leads


# ── Care Directories Scraper ──────────────────────────────────────────────────
class CareDirectoriesScraper(BaseScraper):
    """Scrapes homecare.co.uk and carehome.co.uk for providers and leads"""

    async def scrape_homecare_uk(self, location: str) -> List[RawLead]:
        leads = []
        page = await self.new_page()
        try:
            url = f"https://www.homecare.co.uk/homecareservices/search/?term={location.replace(' ', '+')}"
            ok = await self.safe_goto(page, url)
            if not ok:
                return leads

            providers = await page.query_selector_all(".provider-listing, .search-result, article.provider")
            for provider in providers[:10]:
                try:
                    name_el = await provider.query_selector("h2, h3, .provider-name")
                    desc_el = await provider.query_selector("p, .description, .summary")
                    link_el = await provider.query_selector("a")

                    name = await name_el.inner_text() if name_el else ""
                    desc = await desc_el.inner_text() if desc_el else ""
                    href = await link_el.get_attribute("href") if link_el else ""
                    full_url = f"https://www.homecare.co.uk{href}" if href and not href.startswith("http") else href

                    if name:
                        leads.append(RawLead(
                            source=ScraperSource.CARE_DIRECTORIES,
                            source_url=full_url,
                            title=name.strip(),
                            snippet=desc.strip()[:400] if desc else f"Homecare provider in {location}",
                            location=location,
                            scraped_at=datetime.now(),
                            raw_data={"directory": "homecare.co.uk", "location": location}
                        ))
                except:
                    continue
        except Exception as e:
            print(f"[CareDirectories] homecare.co.uk error: {e}")
        finally:
            await page.close()
        return leads

    async def scrape_bark_care(self, location: str, service: str = "home care") -> List[RawLead]:
        leads = []
        page = await self.new_page()
        try:
            url = f"https://www.bark.com/en/gb/near/{service.replace(' ', '-')}/{location.lower().replace(' ', '-')}/"
            ok = await self.safe_goto(page, url)
            if not ok:
                return leads

            # Bark listings
            items = await page.query_selector_all(".profile-card, .provider-card, [data-testid='profile']")
            for item in items[:8]:
                try:
                    name_el = await item.query_selector("h3, h2, .name")
                    desc_el = await item.query_selector("p, .description")
                    name = await name_el.inner_text() if name_el else ""
                    desc = await desc_el.inner_text() if desc_el else ""
                    if name:
                        leads.append(RawLead(
                            source=ScraperSource.BARK,
                            source_url=url,
                            title=name.strip(),
                            snippet=desc.strip()[:400] if desc else f"Care provider on Bark in {location}",
                            location=location,
                            scraped_at=datetime.now(),
                            raw_data={"directory": "bark.com", "service": service}
                        ))
                except:
                    continue
        except Exception as e:
            print(f"[CareDirectories] Bark error: {e}")
        finally:
            await page.close()
        return leads

    async def scrape_all(self, locations: List[str]) -> List[RawLead]:
        all_leads = []
        for loc in locations[:4]:
            leads = await self.scrape_homecare_uk(loc)
            all_leads.extend(leads)
            await human_delay(1500, 3000)
            bark_leads = await self.scrape_bark_care(loc)
            all_leads.extend(bark_leads)
            await human_delay(2000, 4000)
        return all_leads


# ── Forum Scraper ─────────────────────────────────────────────────────────────
class ForumScraper(BaseScraper):
    """Scrapes Mumsnet, Reddit for care intent posts"""

    async def scrape_mumsnet(self, keywords: List[str]) -> List[RawLead]:
        leads = []
        page = await self.new_page()
        try:
            for keyword in keywords[:3]:
                url = f"https://www.mumsnet.com/search?q={keyword.replace(' ', '+')}&type=threads"
                ok = await self.safe_goto(page, url, wait=2000)
                if not ok:
                    continue

                threads = await page.query_selector_all("article, .thread-listing, .search-result")
                for thread in threads[:8]:
                    try:
                        title_el = await thread.query_selector("h3, h2, a.thread-title, .title")
                        snippet_el = await thread.query_selector("p, .excerpt, .snippet")
                        link_el = await thread.query_selector("a")

                        title = await title_el.inner_text() if title_el else ""
                        snippet = await snippet_el.inner_text() if snippet_el else ""
                        href = await link_el.get_attribute("href") if link_el else ""
                        full_url = f"https://www.mumsnet.com{href}" if href and not href.startswith("http") else href

                        if title and self._is_care_relevant(title + " " + snippet):
                            location = self._extract_location(title + " " + snippet)
                            leads.append(RawLead(
                                source=ScraperSource.FORUMS,
                                source_url=full_url,
                                title=title.strip(),
                                snippet=snippet.strip()[:500] if snippet else title,
                                location=location,
                                scraped_at=datetime.now(),
                                raw_data={"forum": "mumsnet", "keyword": keyword}
                            ))
                    except:
                        continue
                await human_delay(2000, 4000)
        except Exception as e:
            print(f"[ForumScraper] Mumsnet error: {e}")
        finally:
            await page.close()
        return leads

    async def scrape_reddit(self, subreddits: List[str] = None) -> List[RawLead]:
        leads = []
        if not subreddits:
            subreddits = ["eldercare", "AgingParents", "CaregiverSupport", "dementia", "caregiver"]

        async with httpx.AsyncClient(headers={**HEADERS, "User-Agent": ua.random}) as client:
            for sub in subreddits[:3]:
                try:
                    url = f"https://www.reddit.com/r/{sub}/search.json?q=care+uk&restrict_sr=1&sort=new&limit=15"
                    resp = await client.get(url, timeout=10)
                    if resp.status_code == 200:
                        data = resp.json()
                        posts = data.get("data", {}).get("children", [])
                        for post in posts:
                            pd = post.get("data", {})
                            title = pd.get("title", "")
                            selftext = pd.get("selftext", "")
                            permalink = pd.get("permalink", "")

                            if self._is_care_relevant(title + " " + selftext):
                                location = self._extract_location(title + " " + selftext)
                                leads.append(RawLead(
                                    source=ScraperSource.FORUMS,
                                    source_url=f"https://reddit.com{permalink}",
                                    title=title,
                                    snippet=(selftext[:400] if selftext else title),
                                    location=location,
                                    scraped_at=datetime.now(),
                                    raw_data={"forum": "reddit", "subreddit": sub}
                                ))
                    await human_delay(1000, 2000)
                except Exception as e:
                    print(f"[ForumScraper] Reddit r/{sub} error: {e}")
        return leads

    def _is_care_relevant(self, text: str) -> bool:
        text_lower = text.lower()
        return any(kw.lower() in text_lower for kw in SERVICE_KEYWORDS + INTENT_PHRASES[:5])

    def _extract_location(self, text: str) -> Optional[str]:
        for loc in COMPANY_LOCATIONS:
            if loc.lower() in text.lower():
                return loc
        uk_patterns = r'\b([A-Z][a-z]+(?:shire|ampton|ford|bury|ster|field))\b'
        matches = re.findall(uk_patterns, text)
        return matches[0] if matches else None


# ── LinkedIn Scraper ──────────────────────────────────────────────────────────
class LinkedInScraper(BaseScraper):
    """Scrapes LinkedIn public pages for commissioners and case managers"""

    async def search_companies(self, keywords: List[str], locations: List[str]) -> List[RawLead]:
        leads = []
        page = await self.new_page()
        try:
            for keyword in keywords[:2]:
                for loc in locations[:2]:
                    query = f"site:linkedin.com/company {keyword} {loc} care"
                    url = f"https://www.google.co.uk/search?q={query.replace(' ', '+')}&num=5&gl=uk"
                    ok = await self.safe_goto(page, url, wait=2000)
                    if not ok:
                        continue

                    results = await page.query_selector_all("div.g")
                    for result in results[:5]:
                        try:
                            title_el = await result.query_selector("h3")
                            link_el = await result.query_selector("a")
                            snippet_el = await result.query_selector(".VwiC3b, .yXK7lf")
                            title = await title_el.inner_text() if title_el else ""
                            href = await link_el.get_attribute("href") if link_el else ""
                            snippet = await snippet_el.inner_text() if snippet_el else ""

                            if "linkedin.com" in (href or "") and title:
                                leads.append(RawLead(
                                    source=ScraperSource.LINKEDIN,
                                    source_url=href,
                                    title=title.strip(),
                                    snippet=snippet.strip()[:400],
                                    location=loc,
                                    scraped_at=datetime.now(),
                                    raw_data={"keyword": keyword, "search": "linkedin_company"}
                                ))
                        except:
                            continue
                    await human_delay(3000, 6000)
        except Exception as e:
            print(f"[LinkedInScraper] Error: {e}")
        finally:
            await page.close()
        return leads


# ── NHS/LA Commissioner Scraper ───────────────────────────────────────────────
class NHSLAScraper(BaseScraper):
    """Scrapes NHS and Local Authority sites for commissioner contacts"""

    NHS_SOURCES = [
        ("https://www.nhs.uk/service-search/find-a-community-service", "NHS Community Services"),
        ("https://www.cqc.org.uk/search/run-search?query=domiciliary+care", "CQC Providers"),
    ]

    LA_SOURCES = [
        "https://www.northnorthants.gov.uk/adult-care",
        "https://www.luton.gov.uk/Health_and_social_care/Pages/Adult-social-care.aspx",
        "https://www.buckinghamshire.gov.uk/adult-social-care",
        "https://www.milton-keynes.gov.uk/adult-social-care",
        "https://www.bedford.gov.uk/health-and-social-care/adult-social-care",
    ]

    async def scrape_cqc_providers(self, location: str) -> List[RawLead]:
        leads = []
        page = await self.new_page()
        try:
            url = f"https://www.cqc.org.uk/search/run-search?query=homecare+{location.replace(' ', '+')}&resultcount=20&categoryId=ASC-RC"
            ok = await self.safe_goto(page, url, wait=3000)
            if not ok:
                return leads

            providers = await page.query_selector_all(".result-item, .provider-result, article")
            for provider in providers[:10]:
                try:
                    name_el = await provider.query_selector("h2, h3, .name")
                    desc_el = await provider.query_selector("p, .description")
                    link_el = await provider.query_selector("a")
                    name = await name_el.inner_text() if name_el else ""
                    desc = await desc_el.inner_text() if desc_el else ""
                    href = await link_el.get_attribute("href") if link_el else ""
                    full_url = f"https://www.cqc.org.uk{href}" if href and not href.startswith("http") else href

                    if name:
                        leads.append(RawLead(
                            source=ScraperSource.NHS_LA,
                            source_url=full_url,
                            title=name.strip(),
                            snippet=desc.strip()[:400] if desc else f"CQC registered provider in {location}",
                            location=location,
                            scraped_at=datetime.now(),
                            raw_data={"registry": "CQC", "location": location}
                        ))
                except:
                    continue
        except Exception as e:
            print(f"[NHSLAScraper] CQC error: {e}")
        finally:
            await page.close()
        return leads

    async def scrape_all(self, locations: List[str]) -> List[RawLead]:
        all_leads = []
        for loc in locations[:3]:
            leads = await self.scrape_cqc_providers(loc)
            all_leads.extend(leads)
            await human_delay(2000, 4000)
        return all_leads


# ── Facebook / Social Scraper ─────────────────────────────────────────────────
class SocialScraper(BaseScraper):
    """Scrapes public Facebook pages and social media via Google indexing"""

    async def scrape_facebook_public(self, keywords: List[str], locations: List[str]) -> List[RawLead]:
        """Uses Google to find public Facebook posts (avoids login requirement)"""
        leads = []
        page = await self.new_page()
        try:
            for keyword in keywords[:3]:
                for loc in locations[:2]:
                    query = f'site:facebook.com "{keyword}" "{loc}" care'
                    url = f"https://www.google.co.uk/search?q={query.replace(' ', '+')}&num=5&gl=uk"
                    ok = await self.safe_goto(page, url, wait=2000)
                    if not ok:
                        continue

                    results = await page.query_selector_all("div.g")
                    for result in results[:5]:
                        try:
                            title_el = await result.query_selector("h3")
                            link_el = await result.query_selector("a")
                            snippet_el = await result.query_selector(".VwiC3b")
                            title = await title_el.inner_text() if title_el else ""
                            href = await link_el.get_attribute("href") if link_el else ""
                            snippet = await snippet_el.inner_text() if snippet_el else ""

                            if "facebook.com" in (href or "") and snippet:
                                leads.append(RawLead(
                                    source=ScraperSource.FACEBOOK,
                                    source_url=href,
                                    title=title.strip(),
                                    snippet=snippet.strip()[:400],
                                    location=loc,
                                    scraped_at=datetime.now(),
                                    raw_data={"platform": "facebook", "keyword": keyword}
                                ))
                        except:
                            continue
                    await human_delay(2500, 5000)
        except Exception as e:
            print(f"[SocialScraper] Facebook error: {e}")
        finally:
            await page.close()
        return leads


# ── Master Scraper Orchestrator ───────────────────────────────────────────────
class ScraperOrchestrator:
    """Coordinates all scrapers and returns unified RawLead list"""

    async def run(
        self,
        sources: List[str],
        keywords: List[str],
        locations: List[str],
        max_results: int = 30,
    ) -> List[RawLead]:
        all_leads: List[RawLead] = []

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=HEADLESS)
            try:
                tasks = []

                if "google" in sources:
                    scraper = GoogleScraper(browser)
                    tasks.append(scraper.scrape_intent_queries(locations))

                if "care_directories" in sources or "bark" in sources:
                    scraper = CareDirectoriesScraper(browser)
                    tasks.append(scraper.scrape_all(locations))

                if "forums" in sources:
                    scraper = ForumScraper(browser)
                    tasks.append(scraper.scrape_mumsnet(keywords))
                    tasks.append(scraper.scrape_reddit())

                if "linkedin" in sources:
                    scraper = LinkedInScraper(browser)
                    tasks.append(scraper.search_companies(
                        ["commissioner", "case manager", "CHC", "discharge"],
                        locations
                    ))

                if "nhs_la" in sources:
                    scraper = NHSLAScraper(browser)
                    tasks.append(scraper.scrape_all(locations))

                if "facebook" in sources or "social" in sources:
                    scraper = SocialScraper(browser)
                    tasks.append(scraper.scrape_facebook_public(keywords[:3], locations[:3]))

                # Run with controlled concurrency
                for i in range(0, len(tasks), 2):
                    batch = tasks[i:i+2]
                    results = await asyncio.gather(*batch, return_exceptions=True)
                    for result in results:
                        if isinstance(result, list):
                            all_leads.extend(result)
                        elif isinstance(result, Exception):
                            print(f"[Orchestrator] Task failed: {result}")

                # Deduplicate by snippet similarity
                all_leads = self._deduplicate(all_leads)
                return all_leads[:max_results]

            finally:
                await browser.close()

    def _deduplicate(self, leads: List[RawLead]) -> List[RawLead]:
        seen_snippets = set()
        unique = []
        for lead in leads:
            key = lead.snippet[:80].lower().strip()
            if key not in seen_snippets:
                seen_snippets.add(key)
                unique.append(lead)
        return unique

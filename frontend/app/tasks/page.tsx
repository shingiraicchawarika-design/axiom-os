export default function Page() {
  return (
    <div style={{ minHeight: '100vh', background: 'var(--ax-void)', fontFamily: 'var(--font-ui)', display: 'flex' }}>
      <aside style={{ width: 200, flexShrink: 0, background: 'var(--ax-depth)', borderRight: '1px solid var(--ax-border)', padding: '24px 10px' }}>
        <a href="/" style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px', marginBottom: 16, textDecoration: 'none' }}>
          <div style={{ width: 30, height: 30, borderRadius: 8, background: 'linear-gradient(135deg,#6366f1,#4338ca)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 800, fontSize: 15 }}>A</div>
          <span style={{ fontFamily: 'var(--font-display)', fontStyle: 'italic', fontSize: 16, color: 'var(--ax-text-primary)' }}>Axiom</span>
        </a>
        {([['/', 'Agent Hub'], ['/leads', 'Leads CRM'], ['/relationships', 'Relationships'], ['/scraper', 'Scraper'], ['/outreach', 'Outreach'], ['/tasks', 'Tasks'], ['/staff', 'Staff & Rota']] as [string, string][]).map(([href, label]) => (
          <a key={href} href={href} style={{ display: 'flex', alignItems: 'center', gap: 9, padding: '8px 12px', borderRadius: 10, textDecoration: 'none', fontSize: 13, color: 'var(--ax-text-secondary)', marginBottom: 2 }}>{label}</a>
        ))}
      </aside>
      <main style={{ flex: 1, padding: '36px 40px' }}>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 36, fontWeight: 400, fontStyle: 'italic', margin: '0 0 8px', color: 'var(--ax-text-primary)' }}>Module</h1>
        <p style={{ color: 'var(--ax-text-muted)', fontSize: 13 }}>Connected to FastAPI backend. Run the pipeline from Agent Hub to populate data.</p>
        <div style={{ marginTop: 24, background: 'var(--ax-card)', border: '1px solid var(--ax-border)', borderRadius: 14, padding: 48, textAlign: 'center' }}>
          <div style={{ color: 'var(--ax-text-secondary)', fontSize: 14, marginBottom: 6 }}>No data yet</div>
          <div style={{ color: 'var(--ax-text-muted)', fontSize: 12, marginBottom: 16 }}>Start a pipeline run from Agent Hub to populate this module</div>
          <a href="/" style={{ display: 'inline-block', padding: '10px 24px', borderRadius: 10, background: 'linear-gradient(135deg,#6366f1,#4338ca)', color: '#fff', fontWeight: 700, fontSize: 13, textDecoration: 'none' }}>Go to Agent Hub</a>
        </div>
      </main>
    </div>
  )
}

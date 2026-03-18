'use client'
import { usePathname } from 'next/navigation'

const NAV = [
  { href:'/', label:'Agent Hub', icon:'◈' },
  { href:'/leads', label:'Leads CRM', icon:'◈' },
  { href:'/relationships', label:'Relationships', icon:'⬡' },
  { href:'/scraper', label:'Scraper', icon:'⊕' },
  { href:'/outreach', label:'Outreach', icon:'◻' },
  { href:'/tasks', label:'Tasks', icon:'◇' },
  { href:'/staff', label:'Staff & Rota', icon:'⬟' },
]

export default function MiniSidebar() {
  const pathname = usePathname()
  return (
    <aside style={{ width:200, flexShrink:0, background:'var(--ax-depth)', borderRight:'1px solid var(--ax-border)', padding:'24px 10px', display:'flex', flexDirection:'column', gap:2, height:'100vh', position:'sticky', top:0 }}>
      <a href="/" style={{ display:'flex', alignItems:'center', gap:8, padding:'8px 12px', marginBottom:16, textDecoration:'none' }}>
        <div style={{ width:30, height:30, borderRadius:8, background:'linear-gradient(135deg,#6366f1,#4338ca)', display:'flex', alignItems:'center', justifyContent:'center', color:'#fff', fontWeight:800, fontSize:15 }}>A</div>
        <span style={{ fontFamily:'var(--font-display)', fontStyle:'italic', fontSize:16, color:'var(--ax-text-primary)' }}>Axiom</span>
      </a>
      {NAV.map(item => {
        const active = pathname === item.href
        return (
          <a key={item.href} href={item.href} style={{
            display:'flex', alignItems:'center', gap:9, padding:'8px 12px', borderRadius:10,
            textDecoration:'none', fontWeight:active?600:400, fontSize:13,
            background:active?'var(--ax-indigo-dim)':'transparent',
            color:active?'var(--ax-indigo-bright)':'var(--ax-text-secondary)',
            borderLeft:active?'2px solid var(--ax-indigo)':'2px solid transparent',
          }}>
            <span style={{ opacity:active?1:0.5, fontSize:13 }}>{item.icon}</span>{item.label}
          </a>
        )
      })}
    </aside>
  )
}

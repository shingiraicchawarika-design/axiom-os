'use client'
import { useState, useEffect } from 'react'
import { client } from '@/lib/api'

const STAGES = ['New Lead','Contacted','Engaged','Assessment Booked','Care Package Designed','Converted']
const STAGE_COLOR: Record<string,string> = {
  'New Lead':'#0ea5e9','Contacted':'#6366f1','Engaged':'#8b5cf6',
  'Assessment Booked':'#f59e0b','Care Package Designed':'#f97316','Converted':'#10b981'
}
const URG_COLOR: Record<string,string> = { high:'#f43f5e', medium:'#f59e0b', low:'#10b981' }

function Card({ children, style, onClick }: any) {
  return <div onClick={onClick} style={{ background:'var(--ax-card)', border:'1px solid var(--ax-border)', borderRadius:14, cursor:onClick?'pointer':undefined, ...style }}>{children}</div>
}

export default function LeadsPage() {
  const [leads, setLeads] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [view, setView] = useState<'pipeline'|'list'>('pipeline')
  const [selected, setSelected] = useState<any>(null)
  const [addOpen, setAddOpen] = useState(false)
  const [form, setForm] = useState({ name:'', service_type:'', location:'', urgency:'medium', stage:'New Lead', lead_score:50, pipeline_value:0, notes:'', source:'' })

  useEffect(() => {
    client.getLeads().then(r => { setLeads(r.leads || []); setLoading(false) }).catch(() => {
      // Fallback demo data
      setLeads([
        { id:'1', name:'HPFT NHS Trust', service_type:'Mental health support', stage:'New Lead', urgency:'high', lead_score:82, location:'Aylesbury', pipeline_value:3200, source:'NHS Directory' },
        { id:'2', name:'Margaret Thornton', service_type:'Dementia care', stage:'Engaged', urgency:'high', lead_score:91, location:'Milton Keynes', pipeline_value:2600, source:'Mumsnet' },
        { id:'3', name:'Robert Ellis', service_type:'Post-discharge support', stage:'Assessment Booked', urgency:'high', lead_score:88, location:'Aylesbury', pipeline_value:3400, source:'Bark' },
        { id:'4', name:'Patricia Walsh', service_type:'Live-in care', stage:'Care Package Designed', urgency:'medium', lead_score:79, location:'Northampton', pipeline_value:4200, source:'Google Ads' },
        { id:'5', name:'James Okoye', service_type:'Complex care', stage:'Converted', urgency:'low', lead_score:95, location:'Northampton', pipeline_value:5100, source:'Commissioner' },
        { id:'6', name:'Care & Carers Ltd', service_type:'Visiting care', stage:'Contacted', urgency:'medium', lead_score:65, location:'Luton', pipeline_value:1800, source:'Google' },
      ])
      setLoading(false)
    })
  }, [])

  async function updateStage(id: string, stage: string) {
    setLeads(p => p.map(l => l.id === id ? { ...l, stage } : l))
    setSelected((p: any) => p?.id === id ? { ...p, stage } : p)
    try { await client.updateLead(id, { stage }) } catch {}
  }

  async function addLead() {
    const lead = { ...form }
    try {
      const res = await client.createLead(lead)
      setLeads(p => [res, ...p])
    } catch {
      setLeads(p => [{ ...lead, id: String(Date.now()) }, ...p])
    }
    setAddOpen(false)
    setForm({ name:'', service_type:'', location:'', urgency:'medium', stage:'New Lead', lead_score:50, pipeline_value:0, notes:'', source:'' })
  }

  const totalValue = leads.reduce((s, l) => s + (l.pipeline_value || 0), 0)

  return (
    <div style={{ minHeight:'100vh', background:'var(--ax-void)', fontFamily:'var(--font-ui)', display:'flex' }}>
      {/* Mini sidebar */}
      <aside style={{ width:200, flexShrink:0, background:'var(--ax-depth)', borderRight:'1px solid var(--ax-border)', padding:'24px 12px', display:'flex', flexDirection:'column', gap:2 }}>
        <a href="/" style={{ display:'flex', alignItems:'center', gap:8, padding:'8px 12px', marginBottom:16, textDecoration:'none' }}>
          <div style={{ width:30, height:30, borderRadius:8, background:'linear-gradient(135deg,#6366f1,#4338ca)', display:'flex', alignItems:'center', justifyContent:'center', color:'#fff', fontWeight:800, fontSize:15 }}>A</div>
          <span style={{ fontFamily:'var(--font-display)', fontStyle:'italic', fontSize:16, color:'var(--ax-text-primary)' }}>Axiom</span>
        </a>
        {[
          { href:'/', label:'Agent Hub', icon:'◈' },
          { href:'/leads', label:'Leads CRM', icon:'◈', active:true },
          { href:'/relationships', label:'Relationships', icon:'⬡' },
          { href:'/scraper', label:'Scraper', icon:'⊕' },
          { href:'/outreach', label:'Outreach', icon:'◻' },
          { href:'/tasks', label:'Tasks', icon:'◇' },
          { href:'/staff', label:'Staff & Rota', icon:'⬟' },
        ].map(item => (
          <a key={item.href} href={item.href} style={{
            display:'flex', alignItems:'center', gap:9, padding:'8px 12px', borderRadius:10,
            textDecoration:'none', fontWeight:item.active ? 600 : 400, fontSize:13,
            background:item.active ? 'var(--ax-indigo-dim)' : 'transparent',
            color:item.active ? 'var(--ax-indigo-bright)' : 'var(--ax-text-secondary)',
            borderLeft:item.active ? '2px solid var(--ax-indigo)' : '2px solid transparent',
          }}>
            <span style={{ opacity:item.active?1:0.5 }}>{item.icon}</span>{item.label}
          </a>
        ))}
      </aside>

      <main style={{ flex:1, padding:'36px 40px', minWidth:0 }}>
        <div className="fade-up" style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:28 }}>
          <div>
            <h1 style={{ margin:0, fontFamily:'var(--font-display)', fontSize:36, fontWeight:400, fontStyle:'italic' }}>Leads CRM</h1>
            <p style={{ margin:'6px 0 0', fontSize:13, color:'var(--ax-text-muted)' }}>{leads.length} leads · £{totalValue.toLocaleString()} pipeline</p>
          </div>
          <div style={{ display:'flex', gap:10 }}>
            <div style={{ display:'flex', background:'var(--ax-surface)', borderRadius:10, padding:4, gap:2 }}>
              {(['pipeline','list'] as const).map(v => (
                <button key={v} onClick={() => setView(v)} style={{ padding:'6px 14px', borderRadius:7, border:'none', cursor:'pointer', background:view===v?'var(--ax-raised)':'transparent', color:view===v?'var(--ax-text-primary)':'var(--ax-text-muted)', fontSize:12, fontWeight:view===v?600:400, fontFamily:'var(--font-ui)' }}>
                  {v === 'pipeline' ? '⬡ Pipeline' : '≡ List'}
                </button>
              ))}
            </div>
            <button onClick={() => setAddOpen(true)} style={{ padding:'9px 20px', borderRadius:10, border:'none', background:'linear-gradient(135deg,#6366f1,#4338ca)', color:'#fff', fontWeight:700, fontSize:13, cursor:'pointer', fontFamily:'var(--font-ui)' }}>+ Add Lead</button>
          </div>
        </div>

        {loading ? (
          <div style={{ textAlign:'center', padding:'80px 0', color:'var(--ax-text-muted)' }}>Loading leads…</div>
        ) : view === 'pipeline' ? (
          <div className="fade-up-1" style={{ display:'grid', gridTemplateColumns:`repeat(${STAGES.length},minmax(180px,1fr))`, gap:14, overflowX:'auto' }}>
            {STAGES.map(stage => {
              const stageLeads = leads.filter(l => l.stage === stage)
              const color = STAGE_COLOR[stage]
              return (
                <div key={stage}>
                  <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:10, padding:'0 2px' }}>
                    <div style={{ display:'flex', alignItems:'center', gap:5 }}>
                      <div style={{ width:7, height:7, borderRadius:2, background:color }} />
                      <span style={{ fontSize:10, fontWeight:700, textTransform:'uppercase', letterSpacing:'0.07em', color:'var(--ax-text-muted)' }}>{stage}</span>
                    </div>
                    <span style={{ fontSize:11, fontFamily:'var(--font-mono)', color, fontWeight:700 }}>{stageLeads.length}</span>
                  </div>
                  <div style={{ display:'flex', flexDirection:'column', gap:8, minHeight:80 }}>
                    {stageLeads.length === 0 && (
                      <div style={{ border:`1px dashed ${color}30`, borderRadius:10, height:70, display:'flex', alignItems:'center', justifyContent:'center' }}>
                        <span style={{ fontSize:10, color:'var(--ax-text-muted)' }}>Empty</span>
                      </div>
                    )}
                    {stageLeads.map(lead => (
                      <Card key={lead.id} onClick={() => setSelected(lead)} style={{ padding:16, borderLeft:`3px solid ${color}` }}>
                        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:8 }}>
                          <div style={{ width:7, height:7, borderRadius:'50%', background:URG_COLOR[lead.urgency]||'#fff', marginTop:3, ...(lead.urgency==='high'?{animation:'pulse-dot 1.2s infinite',boxShadow:`0 0 5px ${URG_COLOR.high}`}:{}) }} />
                          <span style={{ fontSize:15, fontWeight:800, color:lead.lead_score>=80?'var(--ax-emerald)':lead.lead_score>=60?'var(--ax-amber)':'var(--ax-rose)', fontFamily:'var(--font-mono)' }}>{lead.lead_score}</span>
                        </div>
                        <div style={{ fontSize:12, fontWeight:700, color:'var(--ax-text-primary)', marginBottom:4, lineHeight:1.3 }}>{lead.name}</div>
                        <div style={{ fontSize:10, color:'var(--ax-text-muted)', marginBottom:8 }}>{lead.service_type}</div>
                        <div style={{ display:'flex', justifyContent:'space-between', fontSize:10 }}>
                          <span style={{ color:'var(--ax-text-muted)' }}>{lead.location}</span>
                          <span style={{ color:'var(--ax-emerald)', fontWeight:700, fontFamily:'var(--font-mono)' }}>£{(lead.pipeline_value||0).toLocaleString()}</span>
                        </div>
                      </Card>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <div className="fade-up-1" style={{ display:'flex', flexDirection:'column', gap:8 }}>
            <div style={{ display:'grid', gridTemplateColumns:'2fr 1.5fr 1fr 1fr 80px 80px', gap:12, padding:'6px 16px', fontSize:9, fontWeight:700, textTransform:'uppercase', letterSpacing:'0.08em', color:'var(--ax-text-muted)' }}>
              <span>Name</span><span>Service</span><span>Stage</span><span>Location</span><span>Score</span><span>Value</span>
            </div>
            {leads.map(lead => (
              <Card key={lead.id} onClick={() => setSelected(lead)} style={{ padding:'13px 16px', display:'grid', gridTemplateColumns:'2fr 1.5fr 1fr 1fr 80px 80px', gap:12, alignItems:'center' }}>
                <div style={{ display:'flex', alignItems:'center', gap:8 }}>
                  <div style={{ width:7, height:7, borderRadius:'50%', background:URG_COLOR[lead.urgency], flexShrink:0 }} />
                  <span style={{ fontSize:13, fontWeight:600, color:'var(--ax-text-primary)' }}>{lead.name}</span>
                </div>
                <span style={{ fontSize:12, color:'var(--ax-text-secondary)' }}>{lead.service_type}</span>
                <span style={{ fontSize:10, fontWeight:700, padding:'2px 8px', borderRadius:5, background:`${STAGE_COLOR[lead.stage]}18`, color:STAGE_COLOR[lead.stage], textTransform:'uppercase', letterSpacing:'0.05em' }}>{lead.stage}</span>
                <span style={{ fontSize:11, color:'var(--ax-text-muted)' }}>{lead.location}</span>
                <span style={{ fontSize:14, fontWeight:700, color:'var(--ax-indigo)', fontFamily:'var(--font-mono)' }}>{lead.lead_score}</span>
                <span style={{ fontSize:12, fontWeight:600, color:'var(--ax-emerald)', fontFamily:'var(--font-mono)' }}>£{(lead.pipeline_value||0).toLocaleString()}</span>
              </Card>
            ))}
          </div>
        )}

        {/* Lead detail modal */}
        {selected && (
          <div onClick={() => setSelected(null)} style={{ position:'fixed', inset:0, background:'rgba(0,0,0,0.75)', zIndex:100, display:'flex', alignItems:'center', justifyContent:'center', padding:24 }}>
            <div onClick={e => e.stopPropagation()} style={{ background:'var(--ax-surface)', border:'1px solid var(--ax-border)', borderRadius:20, maxWidth:580, width:'100%', maxHeight:'88vh', overflowY:'auto', padding:30 }}>
              <div style={{ display:'flex', justifyContent:'space-between', marginBottom:20 }}>
                <h2 style={{ margin:0, fontFamily:'var(--font-display)', fontStyle:'italic', fontSize:22 }}>{selected.name}</h2>
                <button onClick={() => setSelected(null)} style={{ background:'none', border:'none', color:'var(--ax-text-muted)', cursor:'pointer', fontSize:20 }}>×</button>
              </div>
              <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:12, marginBottom:20 }}>
                {[
                  { label:'Service', value:selected.service_type },
                  { label:'Location', value:selected.location },
                  { label:'Source', value:selected.source },
                  { label:'Urgency', value:selected.urgency },
                ].map(({ label, value }) => value && (
                  <div key={label} style={{ background:'var(--ax-raised)', borderRadius:10, padding:'12px 16px' }}>
                    <div style={{ fontSize:9, textTransform:'uppercase', letterSpacing:'0.08em', color:'var(--ax-text-muted)', marginBottom:4 }}>{label}</div>
                    <div style={{ fontSize:13, color:'var(--ax-text-primary)' }}>{value}</div>
                  </div>
                ))}
              </div>
              {selected.snippet && <div style={{ background:'var(--ax-raised)', borderRadius:10, padding:'14px 16px', marginBottom:20, fontSize:12, color:'var(--ax-text-secondary)', lineHeight:1.7, fontStyle:'italic' }}>"{selected.snippet}"</div>}
              {selected.ai_analysis && <div style={{ background:'var(--ax-indigo-dim)', border:'1px solid var(--ax-indigo-mid)', borderRadius:10, padding:'12px 16px', marginBottom:20, fontSize:12, color:'var(--ax-text-secondary)' }}><strong style={{ color:'var(--ax-indigo-bright)' }}>AI Analysis:</strong> {selected.ai_analysis}</div>}
              <div style={{ marginBottom:20 }}>
                <div style={{ fontSize:10, textTransform:'uppercase', letterSpacing:'0.08em', color:'var(--ax-text-muted)', marginBottom:10 }}>Move Stage</div>
                <div style={{ display:'flex', gap:6, flexWrap:'wrap' }}>
                  {STAGES.map(stage => (
                    <button key={stage} onClick={() => updateStage(selected.id, stage)} style={{
                      padding:'6px 14px', borderRadius:8, border:`1px solid ${STAGE_COLOR[stage]}40`,
                      background:selected.stage===stage?`${STAGE_COLOR[stage]}20`:'transparent',
                      color:selected.stage===stage?STAGE_COLOR[stage]:'var(--ax-text-muted)',
                      fontSize:11, fontWeight:selected.stage===stage?700:400, cursor:'pointer', fontFamily:'var(--font-ui)',
                    }}>{stage}</button>
                  ))}
                </div>
              </div>
              <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:12 }}>
                <div style={{ background:'var(--ax-indigo-dim)', border:'1px solid var(--ax-indigo-mid)', borderRadius:10, padding:'14px 16px', textAlign:'center' }}>
                  <div style={{ fontSize:10, color:'var(--ax-text-muted)', textTransform:'uppercase', marginBottom:4 }}>Lead Score</div>
                  <div style={{ fontSize:28, fontWeight:800, color:'var(--ax-indigo-bright)', fontFamily:'var(--font-mono)' }}>{selected.lead_score}</div>
                </div>
                <div style={{ background:'var(--ax-emerald-dim)', border:'1px solid var(--ax-emerald)30', borderRadius:10, padding:'14px 16px', textAlign:'center' }}>
                  <div style={{ fontSize:10, color:'var(--ax-text-muted)', textTransform:'uppercase', marginBottom:4 }}>Pipeline Value</div>
                  <div style={{ fontSize:28, fontWeight:800, color:'var(--ax-emerald)', fontFamily:'var(--font-mono)' }}>£{(selected.pipeline_value||0).toLocaleString()}</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Add Lead modal */}
        {addOpen && (
          <div onClick={() => setAddOpen(false)} style={{ position:'fixed', inset:0, background:'rgba(0,0,0,0.75)', zIndex:100, display:'flex', alignItems:'center', justifyContent:'center', padding:24 }}>
            <div onClick={e => e.stopPropagation()} style={{ background:'var(--ax-surface)', border:'1px solid var(--ax-border)', borderRadius:20, maxWidth:520, width:'100%', padding:28 }}>
              <h2 style={{ margin:'0 0 20px', fontFamily:'var(--font-display)', fontStyle:'italic', fontSize:22 }}>Add Lead</h2>
              <div style={{ display:'flex', flexDirection:'column', gap:14 }}>
                {[
                  { label:'Name', key:'name', type:'text', placeholder:'Person or organisation' },
                  { label:'Service Type', key:'service_type', type:'text', placeholder:'e.g. Dementia care at home' },
                  { label:'Location', key:'location', type:'text', placeholder:'e.g. Aylesbury, Buckinghamshire' },
                  { label:'Source', key:'source', type:'text', placeholder:'e.g. Mumsnet, Google, Bark' },
                ].map(f => (
                  <div key={f.key}>
                    <label style={{ fontSize:11, fontWeight:600, color:'var(--ax-text-muted)', textTransform:'uppercase', letterSpacing:'0.06em', display:'block', marginBottom:5 }}>{f.label}</label>
                    <input type={f.type} placeholder={f.placeholder} value={(form as any)[f.key]} onChange={e => setForm(p => ({ ...p, [f.key]: e.target.value }))}
                      style={{ width:'100%', background:'var(--ax-raised)', border:'1px solid var(--ax-border)', borderRadius:8, padding:'10px 14px', fontSize:13, color:'var(--ax-text-primary)', fontFamily:'var(--font-ui)', outline:'none' }} />
                  </div>
                ))}
                <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:12 }}>
                  <div>
                    <label style={{ fontSize:11, fontWeight:600, color:'var(--ax-text-muted)', textTransform:'uppercase', letterSpacing:'0.06em', display:'block', marginBottom:5 }}>Urgency</label>
                    <select value={form.urgency} onChange={e => setForm(p => ({ ...p, urgency:e.target.value }))} style={{ width:'100%', background:'var(--ax-raised)', border:'1px solid var(--ax-border)', borderRadius:8, padding:'10px 14px', fontSize:13, color:'var(--ax-text-primary)', fontFamily:'var(--font-ui)', outline:'none' }}>
                      <option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option>
                    </select>
                  </div>
                  <div>
                    <label style={{ fontSize:11, fontWeight:600, color:'var(--ax-text-muted)', textTransform:'uppercase', letterSpacing:'0.06em', display:'block', marginBottom:5 }}>Score</label>
                    <input type="number" min={0} max={100} value={form.lead_score} onChange={e => setForm(p => ({ ...p, lead_score:Number(e.target.value) }))} style={{ width:'100%', background:'var(--ax-raised)', border:'1px solid var(--ax-border)', borderRadius:8, padding:'10px 14px', fontSize:13, color:'var(--ax-text-primary)', fontFamily:'var(--font-ui)', outline:'none' }} />
                  </div>
                  <div>
                    <label style={{ fontSize:11, fontWeight:600, color:'var(--ax-text-muted)', textTransform:'uppercase', letterSpacing:'0.06em', display:'block', marginBottom:5 }}>Value (£)</label>
                    <input type="number" value={form.pipeline_value} onChange={e => setForm(p => ({ ...p, pipeline_value:Number(e.target.value) }))} style={{ width:'100%', background:'var(--ax-raised)', border:'1px solid var(--ax-border)', borderRadius:8, padding:'10px 14px', fontSize:13, color:'var(--ax-text-primary)', fontFamily:'var(--font-ui)', outline:'none' }} />
                  </div>
                </div>
                <div style={{ display:'flex', gap:10 }}>
                  <button onClick={addLead} disabled={!form.name} style={{ flex:1, padding:'11px 0', borderRadius:10, border:'none', background:'linear-gradient(135deg,#6366f1,#4338ca)', color:'#fff', fontWeight:700, fontSize:13, cursor:'pointer', fontFamily:'var(--font-ui)' }}>Add Lead</button>
                  <button onClick={() => setAddOpen(false)} style={{ flex:1, padding:'11px 0', borderRadius:10, border:'1px solid var(--ax-border)', background:'transparent', color:'var(--ax-text-secondary)', fontWeight:600, fontSize:13, cursor:'pointer', fontFamily:'var(--font-ui)' }}>Cancel</button>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

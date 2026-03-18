'use client'
import { useState, useEffect } from 'react'
import { client, streamPipeline } from '@/lib/api'

const AGENTS = [
  { id: 'lead_scraper', name: 'Lead Scraper', icon: '⊕', color: '#0ea5e9' },
  { id: 'lead_intelligence', name: 'Intelligence', icon: '◉', color: '#10b981' },
  { id: 'lead_enrichment', name: 'Enrichment', icon: '⬡', color: '#34d399' },
  { id: 'urgency_detection', name: 'Urgency', icon: '⚡', color: '#f43f5e' },
  { id: 'outreach', name: 'Outreach', icon: '◻', color: '#f59e0b' },
  { id: 'nurture', name: 'Nurture', icon: '◇', color: '#8b5cf6' },
  { id: 'booking', name: 'Booking', icon: '⬟', color: '#f97316' },
  { id: 'crm_manager', name: 'CRM', icon: '⬡', color: '#06b6d4' },
  { id: 'referral_agent', name: 'Referral', icon: '⬡', color: '#a78bfa' },
  { id: 'ceo', name: 'CEO', icon: '◈', color: '#6366f1' },
]
const SOURCES = [
  { id: 'google', label: 'Google Search' },
  { id: 'care_directories', label: 'Care Directories' },
  { id: 'forums', label: 'Forums (Mumsnet/Reddit)' },
  { id: 'bark', label: 'Bark / Marketplaces' },
  { id: 'linkedin', label: 'LinkedIn' },
  { id: 'nhs_la', label: 'NHS / LA Databases' },
  { id: 'facebook', label: 'Facebook Public' },
  { id: 'social', label: 'Other Social' },
]
const LOCATIONS = ['Aylesbury','Buckinghamshire','Bedfordshire','Luton','Milton Keynes','Northampton']
const KEYWORDS = ['homecare','live-in care','domiciliary care','dementia care','overnight care','care at home']

function Card({ children, style }: any) {
  return <div style={{ background:'var(--ax-card)', border:'1px solid var(--ax-border)', borderRadius:14, ...style }}>{children}</div>
}
function Dot({ color, pulse }: any) {
  return <div style={{ width:8, height:8, borderRadius:'50%', background:color, flexShrink:0, ...(pulse?{animation:'pulse-dot 1.2s infinite',boxShadow:`0 0 6px ${color}`}:{}) }} />
}
function Btn({ children, onClick, variant='secondary', disabled, loading, style }: any) {
  return (
    <button onClick={onClick} disabled={disabled||loading} style={{
      display:'inline-flex', alignItems:'center', gap:7, padding:'9px 20px', borderRadius:10,
      border: variant==='ghost'?'1px solid var(--ax-border)':'none',
      background: variant==='primary'?'linear-gradient(135deg,var(--ax-indigo),#4338ca)': variant==='ghost'?'transparent':'var(--ax-raised)',
      color: variant==='primary'?'#fff':'var(--ax-text-secondary)',
      fontFamily:'var(--font-ui)', fontWeight:600, fontSize:13,
      cursor:disabled||loading?'not-allowed':'pointer', opacity:disabled?0.5:1, ...style
    }}>
      {loading && <span style={{display:'inline-block',width:12,height:12,border:'2px solid #ffffff40',borderTopColor:'#fff',borderRadius:'50%',animation:'spin 0.7s linear infinite'}} />}
      {children}
    </button>
  )
}

export default function AxiomOS() {
  const [tab, setTab] = useState<'overview'|'leads'|'outreach'|'config'|'logs'>('overview')
  const [runId, setRunId] = useState<string|null>(null)
  const [pipelineStatus, setPipelineStatus] = useState<any>(null)
  const [logs, setLogs] = useState<any[]>([])
  const [running, setRunning] = useState(false)
  const [stats, setStats] = useState<any>(null)
  const [leads, setLeads] = useState<any[]>([])
  const [outreachQueue, setOutreachQueue] = useState<any[]>([])
  const [agentResults, setAgentResults] = useState<Record<string,any>>({})
  const [selectedSources, setSelectedSources] = useState(new Set(['google','forums','care_directories','bark']))
  const [selectedLocations, setSelectedLocations] = useState(new Set(LOCATIONS.slice(0,4)))

  const STAGE_COLORS: Record<string,string> = {
    'New Lead':'#0ea5e9','Contacted':'#6366f1','Engaged':'#8b5cf6',
    'Assessment Booked':'#f59e0b','Care Package Designed':'#f97316','Converted':'#10b981'
  }

  useEffect(() => {
    client.stats().then(setStats).catch(()=>setStats({total_leads:0,conversion_rate:0,pipeline_value:0,high_urgency:0,outreach_pending:0,stage_counts:{}}))
    client.getLeads().then(r=>setLeads(r.leads||[])).catch(()=>{})
    client.getOutreach('draft').then(r=>setOutreachQueue(r.outreach||[])).catch(()=>{})
  }, [])

  useEffect(() => {
    if (!runId||!running) return
    const iv = setInterval(async()=>{
      try {
        const logData = await client.pipelineLogs(runId)
        if (Array.isArray(logData)) setLogs(logData)
        const status = await client.pipelineStatus(runId)
        setPipelineStatus(status)
        if (status.status==='completed'||status.status==='failed') {
          setRunning(false)
          client.stats().then(setStats).catch(()=>{})
          client.getLeads().then(r=>setLeads(r.leads||[])).catch(()=>{})
          client.getOutreach('draft').then(r=>setOutreachQueue(r.outreach||[])).catch(()=>{})
        }
      } catch {}
    }, 2000)
    return ()=>clearInterval(iv)
  }, [runId, running])

  async function startPipeline() {
    setRunning(true); setLogs([]); setPipelineStatus(null)
    try {
      const res = await client.runPipeline({ sources:Array.from(selectedSources), keywords:KEYWORDS, locations:Array.from(selectedLocations), max_results:25 })
      setRunId(res.run_id)
    } catch { setRunning(false); alert('Backend not reachable. Start the FastAPI server first.') }
  }

  async function runSingleAgent(agentId: string) {
    try {
      const res = await client.runAgent(agentId, {})
      setAgentResults(prev=>({...prev,[agentId]:res.result}))
    } catch(e) { setAgentResults(prev=>({...prev,[agentId]:{error:'Agent failed — check backend'}})) }
  }

  function agentStatus(id: string) {
    if (!pipelineStatus) return 'idle'
    if (pipelineStatus.agents_running?.includes(id)) return 'running'
    if (pipelineStatus.agents_completed?.includes(id)) return 'done'
    return 'idle'
  }

  const navItems = [
    { key:'overview', label:'Overview', icon:'◈' },
    { key:'leads', label:'Leads CRM', icon:'◉', badge: leads.length },
    { key:'outreach', label:'Outreach Queue', icon:'◻', badge: outreachQueue.length },
    { key:'config', label:'Configure', icon:'⊕' },
    { key:'logs', label:'Logs', icon:'◇', badge: logs.length },
  ]

  return (
    <div style={{minHeight:'100vh',background:'var(--ax-void)',display:'flex',fontFamily:'var(--font-ui)'}}>
      {/* Sidebar */}
      <aside style={{width:220,flexShrink:0,background:'var(--ax-depth)',borderRight:'1px solid var(--ax-border)',display:'flex',flexDirection:'column',height:'100vh',position:'sticky',top:0}}>
        <div style={{padding:'24px 20px 18px',borderBottom:'1px solid var(--ax-border)'}}>
          <div style={{display:'flex',alignItems:'center',gap:10}}>
            <div style={{width:34,height:34,borderRadius:10,background:'linear-gradient(135deg,var(--ax-indigo),#4338ca)',display:'flex',alignItems:'center',justifyContent:'center',fontSize:16,color:'#fff',fontWeight:700,boxShadow:'0 0 16px #6366f130'}}>A</div>
            <div>
              <div style={{fontFamily:'var(--font-display)',fontStyle:'italic',fontSize:17,color:'var(--ax-text-primary)'}}>Axiom</div>
              <div style={{fontSize:10,color:'var(--ax-text-muted)',fontFamily:'var(--font-mono)',letterSpacing:'0.08em'}}>LEAD GEN OS</div>
            </div>
          </div>
        </div>
        <nav style={{flex:1,padding:'14px 10px',display:'flex',flexDirection:'column',gap:2}}>
          {navItems.map(item=>(
            <button key={item.key} onClick={()=>setTab(item.key as any)} style={{
              display:'flex',alignItems:'center',gap:10,padding:'9px 12px',borderRadius:10,
              border:'none',cursor:'pointer',width:'100%',textAlign:'left',
              background:tab===item.key?'var(--ax-indigo-dim)':'transparent',
              color:tab===item.key?'var(--ax-indigo-bright)':'var(--ax-text-secondary)',
              fontSize:13,fontFamily:'var(--font-ui)',fontWeight:tab===item.key?600:400,
              borderLeft:tab===item.key?'2px solid var(--ax-indigo)':'2px solid transparent',
            }}>
              <span style={{fontSize:14,opacity:tab===item.key?1:0.6}}>{item.icon}</span>
              {item.label}
              {(item as any).badge>0 && <span style={{marginLeft:'auto',background:'var(--ax-rose)',color:'#fff',borderRadius:10,padding:'0 6px',fontSize:10,fontWeight:700}}>{(item as any).badge}</span>}
            </button>
          ))}
        </nav>
        <div style={{padding:'14px 16px 20px',borderTop:'1px solid var(--ax-border)'}}>
          <div style={{display:'flex',alignItems:'center',gap:6,marginBottom:8}}>
            <Dot color={running?'#10b981':'#3d5578'} pulse={running} />
            <span style={{fontSize:10,color:'var(--ax-text-muted)',fontFamily:'var(--font-mono)'}}>{running?'Pipeline active':'Agents idle'}</span>
          </div>
          <Btn variant="primary" style={{width:'100%',justifyContent:'center',padding:'8px 0',fontSize:12}} onClick={startPipeline} loading={running} disabled={running}>
            {running?'Running…':'▶ Run Pipeline'}
          </Btn>
        </div>
      </aside>

      {/* Main */}
      <main style={{flex:1,padding:'32px 36px',minWidth:0,maxWidth:1300}}>

        {/* OVERVIEW */}
        {tab==='overview' && (
          <div>
            <div className="fade-up" style={{marginBottom:28}}>
              <div style={{display:'flex',alignItems:'center',gap:10,marginBottom:6}}>
                <Dot color="#10b981" pulse />
                <span style={{fontSize:11,fontWeight:600,letterSpacing:'0.1em',textTransform:'uppercase',color:'var(--ax-text-muted)',fontFamily:'var(--font-mono)'}}>
                  {new Date().toLocaleDateString('en-GB',{weekday:'long',day:'numeric',month:'long'})}
                </span>
              </div>
              <h1 style={{margin:0,fontFamily:'var(--font-display)',fontSize:38,fontWeight:400,fontStyle:'italic'}}>Agent Hub</h1>
              <p style={{margin:'6px 0 0',fontSize:13,color:'var(--ax-text-muted)'}}>10 AI agents · Hybrid mode — auto scrape & score, approval gate for outreach</p>
            </div>

            {/* KPIs */}
            <div className="fade-up-1" style={{display:'grid',gridTemplateColumns:'repeat(5,1fr)',gap:14,marginBottom:28}}>
              {[
                {label:'Total Leads',value:stats?.total_leads??'—',color:'var(--ax-indigo)'},
                {label:'Conversion',value:stats?`${stats.conversion_rate}%`:'—',color:'var(--ax-emerald)'},
                {label:'Pipeline',value:stats?`£${((stats.pipeline_value||0)/1000).toFixed(1)}k`:'—',color:'var(--ax-amber)'},
                {label:'Urgent',value:stats?.high_urgency??'—',color:'var(--ax-rose)'},
                {label:'Pending Approval',value:outreachQueue.length,color:'var(--ax-sky)'},
              ].map(({label,value,color})=>(
                <Card key={label} style={{padding:'18px 20px'}}>
                  <div style={{fontSize:28,fontWeight:800,color,fontFamily:'var(--font-mono)',marginBottom:4}}>{value}</div>
                  <div style={{fontSize:10,color:'var(--ax-text-muted)',textTransform:'uppercase',letterSpacing:'0.07em'}}>{label}</div>
                </Card>
              ))}
            </div>

            {/* Pipeline progress */}
            {(running||pipelineStatus) && (
              <div className="fade-up-2" style={{marginBottom:24}}>
                <Card style={{padding:22}}>
                  <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:14}}>
                    <div style={{fontFamily:'var(--font-display)',fontStyle:'italic',fontSize:17}}>
                      Run <span style={{fontFamily:'var(--font-mono)',fontSize:13,color:'var(--ax-indigo-bright)'}}>{runId}</span>
                      {' '}<span style={{fontSize:12,color:running?'var(--ax-amber)':'var(--ax-emerald)',marginLeft:8}}>{running?'● Running':'✓ Complete'}</span>
                    </div>
                    <div style={{display:'flex',gap:16,fontSize:12,color:'var(--ax-text-secondary)'}}>
                      <span>Found <strong style={{color:'var(--ax-sky)'}}>{pipelineStatus?.leads_found??0}</strong></span>
                      <span>Qualified <strong style={{color:'var(--ax-emerald)'}}>{pipelineStatus?.leads_qualified??0}</strong></span>
                      <span>Drafts <strong style={{color:'var(--ax-amber)'}}>{pipelineStatus?.outreach_drafted??0}</strong></span>
                    </div>
                  </div>
                  <div style={{display:'flex',gap:8,flexWrap:'wrap'}}>
                    {AGENTS.map(agent=>{
                      const s=agentStatus(agent.id)
                      return (
                        <div key={agent.id} style={{display:'flex',alignItems:'center',gap:6,padding:'5px 12px',background:s==='idle'?'var(--ax-surface)':`${agent.color}15`,border:`1px solid ${s!=='idle'?`${agent.color}40`:'var(--ax-border)'}`,borderRadius:8,fontSize:11,fontWeight:600,color:s!=='idle'?agent.color:'var(--ax-text-muted)'}}>
                          <Dot color={s==='done'?agent.color:s==='running'?agent.color:'#3d5578'} pulse={s==='running'} />
                          {agent.name}
                          {s==='done'&&<span style={{fontSize:9}}>✓</span>}
                        </div>
                      )
                    })}
                  </div>
                </Card>
              </div>
            )}

            {/* Agent cards */}
            <div className="fade-up-3" style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(260px,1fr))',gap:14}}>
              {AGENTS.map(agent=>{
                const result=agentResults[agent.id]
                const s=agentStatus(agent.id)
                return (
                  <Card key={agent.id} style={{padding:18}}>
                    <div style={{display:'flex',justifyContent:'space-between',alignItems:'flex-start',marginBottom:10}}>
                      <div style={{display:'flex',alignItems:'center',gap:10}}>
                        <div style={{width:34,height:34,borderRadius:9,background:`${agent.color}18`,border:`1px solid ${agent.color}30`,display:'flex',alignItems:'center',justifyContent:'center',fontSize:15,color:agent.color}}>{agent.icon}</div>
                        <div>
                          <div style={{fontSize:12,fontWeight:700,color:'var(--ax-text-primary)'}}>{agent.name}</div>
                          <div style={{fontSize:9,textTransform:'uppercase',letterSpacing:'0.08em',color:'var(--ax-text-muted)'}}>{s==='running'?'Running…':s==='done'?'Complete':'Idle'}</div>
                        </div>
                      </div>
                      <Dot color={s==='done'?'#10b981':s==='running'?agent.color:'#3d5578'} pulse={s==='running'} />
                    </div>
                    {result&&(
                      <div style={{background:'var(--ax-surface)',borderRadius:7,padding:'8px 10px',marginBottom:8,fontSize:10,color:'var(--ax-text-secondary)',lineHeight:1.5,borderLeft:`2px solid ${agent.color}`,maxHeight:60,overflow:'hidden'}}>
                        {typeof result==='string'?result.slice(0,100):result.briefing?.slice(0,100)||JSON.stringify(result).slice(0,100)}
                      </div>
                    )}
                    <button onClick={()=>runSingleAgent(agent.id)} style={{width:'100%',padding:'7px 0',borderRadius:7,border:`1px solid ${agent.color}40`,background:'transparent',color:agent.color,fontSize:11,fontWeight:600,cursor:'pointer',fontFamily:'var(--font-ui)'}}>
                      ▶ Run
                    </button>
                  </Card>
                )
              })}
            </div>
          </div>
        )}

        {/* LEADS */}
        {tab==='leads' && (
          <div>
            <div className="fade-up" style={{marginBottom:24}}>
              <h1 style={{margin:0,fontFamily:'var(--font-display)',fontSize:36,fontWeight:400,fontStyle:'italic'}}>Leads CRM</h1>
              <p style={{margin:'6px 0 0',fontSize:13,color:'var(--ax-text-muted)'}}>{leads.length} leads in pipeline</p>
            </div>
            {leads.length===0?(
              <Card style={{padding:48,textAlign:'center'}}>
                <div style={{fontSize:24,marginBottom:12}}>◈</div>
                <div style={{color:'var(--ax-text-secondary)',fontSize:14,marginBottom:6}}>No leads yet</div>
                <div style={{color:'var(--ax-text-muted)',fontSize:12,marginBottom:20}}>Run the pipeline to scrape and qualify leads automatically</div>
                <Btn variant="primary" onClick={()=>{setTab('overview');startPipeline()}}>▶ Run Pipeline</Btn>
              </Card>
            ):(
              <>
                {/* Pipeline kanban */}
                <div className="fade-up-1" style={{display:'grid',gridTemplateColumns:'repeat(6,minmax(180px,1fr))',gap:12,overflowX:'auto',marginBottom:24}}>
                  {Object.entries(STAGE_COLORS).map(([stage,color])=>{
                    const stageLeads=leads.filter((l:any)=>l.stage===stage)
                    return (
                      <div key={stage}>
                        <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:10,padding:'0 2px'}}>
                          <div style={{display:'flex',alignItems:'center',gap:5}}>
                            <div style={{width:7,height:7,borderRadius:2,background:color}} />
                            <span style={{fontSize:10,fontWeight:700,textTransform:'uppercase',letterSpacing:'0.06em',color:'var(--ax-text-muted)'}}>{stage.replace(' Lead','')}</span>
                          </div>
                          <span style={{fontSize:11,fontFamily:'var(--font-mono)',color,fontWeight:700}}>{stageLeads.length}</span>
                        </div>
                        <div style={{display:'flex',flexDirection:'column',gap:8}}>
                          {stageLeads.slice(0,3).map((lead:any)=>(
                            <div key={lead.id} style={{background:'var(--ax-card)',border:`1px solid var(--ax-border)`,borderLeft:`3px solid ${color}`,borderRadius:10,padding:14,cursor:'pointer'}}>
                              <div style={{fontSize:12,fontWeight:700,color:'var(--ax-text-primary)',marginBottom:4,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{lead.name}</div>
                              <div style={{fontSize:10,color:'var(--ax-text-muted)',marginBottom:8}}>{lead.service_type?.slice(0,30)}</div>
                              <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
                                <span style={{fontSize:10,color:lead.urgency==='high'?'var(--ax-rose)':lead.urgency==='medium'?'var(--ax-amber)':'var(--ax-emerald)',fontWeight:700}}>{lead.urgency}</span>
                                <span style={{fontSize:11,fontWeight:700,color:'var(--ax-emerald)',fontFamily:'var(--font-mono)'}}>{lead.lead_score}</span>
                              </div>
                            </div>
                          ))}
                          {stageLeads.length>3&&<div style={{fontSize:10,color:'var(--ax-text-muted)',textAlign:'center',padding:'4px 0'}}>+{stageLeads.length-3} more</div>}
                        </div>
                      </div>
                    )
                  })}
                </div>
                {/* Lead list */}
                <div className="fade-up-2" style={{display:'flex',flexDirection:'column',gap:8}}>
                  {leads.slice(0,15).map((lead:any)=>(
                    <Card key={lead.id} style={{padding:'14px 18px',display:'grid',gridTemplateColumns:'2fr 1.5fr 1fr 100px 80px 80px',gap:12,alignItems:'center'}}>
                      <div style={{display:'flex',alignItems:'center',gap:8}}>
                        <div style={{width:6,height:6,borderRadius:'50%',background:lead.urgency==='high'?'var(--ax-rose)':lead.urgency==='medium'?'var(--ax-amber)':'var(--ax-emerald)',flexShrink:0}} />
                        <div>
                          <div style={{fontSize:13,fontWeight:600,color:'var(--ax-text-primary)',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap',maxWidth:220}}>{lead.name}</div>
                          {lead.organisation&&<div style={{fontSize:10,color:'var(--ax-text-muted)'}}>{lead.organisation}</div>}
                        </div>
                      </div>
                      <div style={{fontSize:11,color:'var(--ax-text-secondary)',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{lead.service_type}</div>
                      <div style={{fontSize:11,color:'var(--ax-text-muted)'}}>{lead.location}</div>
                      <div style={{display:'flex',alignItems:'center',gap:5}}>
                        <div style={{width:6,height:6,borderRadius:1,background:STAGE_COLORS[lead.stage]||'#3d5578'}} />
                        <span style={{fontSize:10,color:STAGE_COLORS[lead.stage]||'var(--ax-text-muted)',fontWeight:600,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{lead.stage}</span>
                      </div>
                      <div style={{fontSize:14,fontWeight:700,color:'var(--ax-indigo-bright)',fontFamily:'var(--font-mono)',textAlign:'center'}}>{lead.lead_score}</div>
                      <div style={{fontSize:12,fontWeight:600,color:'var(--ax-emerald)',fontFamily:'var(--font-mono)',textAlign:'right'}}>£{(lead.pipeline_value||0).toLocaleString()}</div>
                    </Card>
                  ))}
                </div>
              </>
            )}
          </div>
        )}

        {/* OUTREACH */}
        {tab==='outreach' && (
          <div>
            <div className="fade-up" style={{marginBottom:24}}>
              <h1 style={{margin:0,fontFamily:'var(--font-display)',fontSize:36,fontWeight:400,fontStyle:'italic'}}>Outreach Queue</h1>
              <p style={{margin:'6px 0 0',fontSize:13,color:'var(--ax-text-muted)'}}>AI-drafted messages — review and approve before sending</p>
            </div>
            <div style={{background:'var(--ax-indigo-dim)',border:'1px solid var(--ax-indigo-mid)',borderRadius:12,padding:'14px 18px',marginBottom:24,display:'flex',alignItems:'center',gap:12}}>
              <span style={{fontSize:16,color:'var(--ax-indigo-bright)'}}>⬟</span>
              <div>
                <div style={{fontSize:13,fontWeight:600,color:'var(--ax-indigo-bright)'}}>Hybrid Mode — Approval Gate Active</div>
                <div style={{fontSize:12,color:'var(--ax-text-muted)',marginTop:2}}>The Outreach Agent drafts every message. Nothing sends without your explicit approval. GDPR-compliant basis documented per draft.</div>
              </div>
            </div>
            {outreachQueue.length===0?(
              <Card style={{padding:48,textAlign:'center'}}>
                <div style={{fontSize:32,marginBottom:12,color:'var(--ax-text-muted)'}}>◻</div>
                <div style={{color:'var(--ax-text-secondary)',fontSize:14,marginBottom:4}}>No outreach pending</div>
                <div style={{color:'var(--ax-text-muted)',fontSize:12}}>Run the pipeline to generate AI-drafted outreach for qualifying leads</div>
              </Card>
            ):(
              <div className="fade-up-1" style={{display:'flex',flexDirection:'column',gap:16}}>
                {outreachQueue.map((item:any)=>(
                  <Card key={item.id} style={{padding:24}}>
                    <div style={{display:'flex',justifyContent:'space-between',gap:20}}>
                      <div style={{flex:1,minWidth:0}}>
                        <div style={{display:'flex',gap:8,marginBottom:10,flexWrap:'wrap',alignItems:'center'}}>
                          <span style={{fontSize:10,fontWeight:700,padding:'2px 8px',borderRadius:5,background:'var(--ax-amber-dim)',color:'var(--ax-amber)',textTransform:'uppercase',letterSpacing:'0.06em'}}>Pending Approval</span>
                          <span style={{fontSize:12,color:'var(--ax-text-secondary)',fontWeight:600}}>{item.to_name}</span>
                          {item.to_email&&<span style={{fontSize:11,color:'var(--ax-text-muted)'}}>{item.to_email}</span>}
                        </div>
                        <div style={{fontSize:15,fontWeight:700,color:'var(--ax-text-primary)',marginBottom:10}}>{item.subject}</div>
                        <div style={{background:'var(--ax-surface)',borderRadius:8,padding:'12px 16px',fontSize:12,color:'var(--ax-text-secondary)',lineHeight:1.75,whiteSpace:'pre-line',maxHeight:180,overflow:'hidden',borderLeft:'2px solid var(--ax-indigo)'}}>
                          {(item.body||'').slice(0,500)}{item.body?.length>500?'…':''}
                        </div>
                        {item.talking_points?.length>0&&(
                          <div style={{marginTop:10}}>
                            <div style={{fontSize:10,textTransform:'uppercase',letterSpacing:'0.08em',color:'var(--ax-text-muted)',marginBottom:6}}>Talking Points</div>
                            {item.talking_points.map((pt:string,i:number)=>(
                              <div key={i} style={{display:'flex',gap:8,marginBottom:5,fontSize:11,color:'var(--ax-text-secondary)'}}>
                                <span style={{color:'var(--ax-indigo)',fontWeight:700,fontFamily:'var(--font-mono)'}}>0{i+1}</span>{pt}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                      <div style={{display:'flex',flexDirection:'column',gap:8,flexShrink:0,paddingTop:4}}>
                        <Btn variant="primary" style={{fontSize:12,padding:'8px 18px',justifyContent:'center'}}
                          onClick={async()=>{
                            await client.approveOutreach(item.id)
                            setOutreachQueue(prev=>prev.filter((o:any)=>o.id!==item.id))
                            if(stats) setStats({...stats,outreach_pending:Math.max(0,(stats.outreach_pending||1)-1)})
                          }}>✓ Approve</Btn>
                        <Btn variant="ghost" style={{fontSize:12,padding:'8px 18px',justifyContent:'center',color:'var(--ax-rose)',borderColor:'var(--ax-rose)30'}}
                          onClick={()=>setOutreachQueue(prev=>prev.filter((o:any)=>o.id!==item.id))}>✕ Reject</Btn>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </div>
        )}

        {/* CONFIG */}
        {tab==='config' && (
          <div>
            <div className="fade-up" style={{marginBottom:24}}>
              <h1 style={{margin:0,fontFamily:'var(--font-display)',fontSize:36,fontWeight:400,fontStyle:'italic'}}>Configure Run</h1>
              <p style={{margin:'6px 0 0',fontSize:13,color:'var(--ax-text-muted)'}}>Select sources and locations for the next pipeline run</p>
            </div>
            <div className="fade-up-1" style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:20,marginBottom:20}}>
              <Card style={{padding:24}}>
                <div style={{fontSize:14,fontWeight:700,color:'var(--ax-text-primary)',marginBottom:16}}>Scraping Sources</div>
                {SOURCES.map(src=>{
                  const active=selectedSources.has(src.id)
                  return (
                    <div key={src.id} onClick={()=>setSelectedSources(prev=>{const s=new Set(prev);active?s.delete(src.id):s.add(src.id);return s})}
                      style={{display:'flex',alignItems:'center',gap:10,padding:'10px 14px',background:active?'var(--ax-indigo-dim)':'var(--ax-surface)',border:`1px solid ${active?'var(--ax-indigo)40':'var(--ax-border)'}`,borderRadius:10,cursor:'pointer',marginBottom:8,transition:'all 0.15s'}}>
                      <div style={{width:18,height:18,borderRadius:4,border:`2px solid ${active?'var(--ax-indigo)':'var(--ax-border-light)'}`,background:active?'var(--ax-indigo)':'transparent',display:'flex',alignItems:'center',justifyContent:'center',flexShrink:0}}>
                        {active&&<span style={{fontSize:10,color:'#fff'}}>✓</span>}
                      </div>
                      <span style={{fontSize:12,color:active?'var(--ax-text-primary)':'var(--ax-text-secondary)',fontWeight:active?600:400}}>{src.label}</span>
                    </div>
                  )
                })}
              </Card>
              <div style={{display:'flex',flexDirection:'column',gap:20}}>
                <Card style={{padding:24}}>
                  <div style={{fontSize:14,fontWeight:700,color:'var(--ax-text-primary)',marginBottom:14}}>Target Locations</div>
                  <div style={{display:'flex',flexWrap:'wrap',gap:8}}>
                    {LOCATIONS.map(loc=>{
                      const active=selectedLocations.has(loc)
                      return (
                        <div key={loc} onClick={()=>setSelectedLocations(prev=>{const s=new Set(prev);active?s.delete(loc):s.add(loc);return s})}
                          style={{padding:'7px 14px',borderRadius:8,background:active?'var(--ax-indigo-dim)':'var(--ax-surface)',border:`1px solid ${active?'var(--ax-indigo)50':'var(--ax-border)'}`,color:active?'var(--ax-indigo-bright)':'var(--ax-text-secondary)',fontSize:12,fontWeight:active?700:400,cursor:'pointer'}}>
                          📍 {loc}
                        </div>
                      )
                    })}
                  </div>
                </Card>
                <Card style={{padding:20}}>
                  <div style={{fontSize:13,color:'var(--ax-text-secondary)',marginBottom:14}}>
                    <strong style={{color:'var(--ax-indigo-bright)'}}>{selectedSources.size}</strong> sources · <strong style={{color:'var(--ax-indigo-bright)'}}>{selectedLocations.size}</strong> locations · <strong style={{color:'var(--ax-indigo-bright)'}}>{KEYWORDS.length}</strong> keywords
                  </div>
                  <div style={{background:'var(--ax-surface)',borderRadius:8,padding:'10px 14px',marginBottom:14,fontSize:11,color:'var(--ax-text-muted)',lineHeight:1.6}}>
                    <strong style={{color:'var(--ax-amber)'}}>Hybrid mode:</strong> Scraping + scoring runs fully autonomously. Outreach drafts require your approval before any email is sent.
                  </div>
                  <Btn variant="primary" style={{width:'100%',justifyContent:'center'}} onClick={()=>{setTab('overview');startPipeline()}} loading={running} disabled={running}>
                    ▶ Start Pipeline Run
                  </Btn>
                </Card>
              </div>
            </div>
          </div>
        )}

        {/* LOGS */}
        {tab==='logs' && (
          <div>
            <div className="fade-up" style={{marginBottom:24}}>
              <h1 style={{margin:0,fontFamily:'var(--font-display)',fontSize:36,fontWeight:400,fontStyle:'italic'}}>Activity Logs</h1>
              <p style={{margin:'6px 0 0',fontSize:13,color:'var(--ax-text-muted)'}}>Real-time agent activity — run {runId||'none'}</p>
            </div>
            <Card style={{padding:24}}>
              {logs.length===0?(
                <div style={{textAlign:'center',padding:'40px 0',color:'var(--ax-text-muted)',fontSize:13}}>No logs yet — start a pipeline run</div>
              ):(
                <div style={{display:'flex',flexDirection:'column',gap:5}}>
                  {[...logs].reverse().map((log:any,i)=>(
                    <div key={i} style={{display:'flex',gap:14,padding:'8px 12px',background:'var(--ax-surface)',borderRadius:7,alignItems:'flex-start',fontSize:11}}>
                      <span style={{fontFamily:'var(--font-mono)',color:'var(--ax-text-muted)',flexShrink:0,width:75}}>{(log.ts||'').slice(11,19)}</span>
                      <span style={{fontWeight:700,color:'var(--ax-indigo-bright)',flexShrink:0,width:120,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{log.agent}</span>
                      <span style={{color:'var(--ax-text-secondary)',lineHeight:1.4}}>{log.event}</span>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>
        )}
      </main>
    </div>
  )
}

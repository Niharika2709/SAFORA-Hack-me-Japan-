import React,{useCallback,useEffect,useMemo,useState} from 'react';
import axios from 'axios';
import { useTranslation } from "react-i18next";
import {Activity,ArrowUpRight,BarChart3,Music2,BookOpen,CalendarDays,Check,ChevronLeft,ChevronRight,CircleHelp,Compass,Download,FileUp,Filter,Flame,Gauge,Home,Layers3,Lightbulb,Menu,RefreshCw,Search,Settings2,Sparkles,TrendingUp,Users,X,Zap} from 'lucide-react';import {Area,AreaChart,Bar,BarChart,CartesianGrid,Cell,Legend,Line,LineChart,Pie,PieChart,ResponsiveContainer,Tooltip,XAxis,YAxis} from 'recharts';
const API='http://127.0.0.1:8000';
const COLORS=['#8062B2','#C9A9E7','#E7B5C8','#A6C5B2','#E7CF98'];
const fmt=v=>new Intl.NumberFormat('en-IN',{maximumFractionDigits:1}).format(v??0);
const dateLabel=(v,lang='en')=>v?new Date(`${String(v).slice(0,10)}T00:00:00`).toLocaleDateString(lang==='ja'?'ja-JP':lang==='hi'?'hi-IN':'en-IN',{month:'short',year:'2-digit'}):'';
function App(){
const { t, i18n } = useTranslation();
 const [data,setData]=useState(null),[opts,setOpts]=useState(null),[page,setPage]=useState('Dashboard'),[sidebar,setSidebar]=useState(true),[mobile,setMobile]=useState(false);
 const [demographics, setDemographics] = useState(null);
const [demographicsError, setDemographicsError] = useState('');
 const [cats,setCats]=useState([]),[from,setFrom]=useState(''),[to,setTo]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState(''),[filename,setFilename]=useState('');
 const [title,setTitle]=useState(''),[horizon,setHorizon]=useState(3),[forecast,setForecast]=useState(null),[search,setSearch]=useState(''),[sort,setSort]=useState('potential_score'),[compare,setCompare]=useState([]);
 const loadOptions=useCallback(async()=>{const r=await axios.get(`${API}/api/options`);setOpts(r.data);setCats(r.data.categories);setFrom(r.data.min_date);setTo(r.data.max_date);},[]);
 const loadDashboard=useCallback(async(override={})=>{setBusy(true);setError('');try{const r=await axios.post(`${API}/api/dashboard`,{categories:override.categories??cats,start_date:override.start_date??from,end_date:override.end_date??to});setData(r.data);setCompare(old=>old.length?old.filter(t=>r.data.raw_titles.includes(t)):r.data.raw_titles.slice(0,4));setTitle(old=>r.data.raw_titles.includes(old)?old:(r.data.raw_titles[0]||''));}catch(e){setError(e.response?.data?.detail||'Cannot connect to the API. Start the backend on port 8000.');}finally{setBusy(false);}},[cats,from,to]);
 useEffect(()=>{loadOptions().catch(()=>setError('Backend not connected. Follow the README to start the FastAPI server.'));},[loadOptions]);
 useEffect(()=>{if(opts&&from&&to)loadDashboard({categories:opts.categories,start_date:opts.min_date,end_date:opts.max_date});},[opts?.min_date]);
useEffect(() => {
  axios.get(`${API}/api/audience-demographics`)
    .then(response => {
      setDemographics(response.data);
      setDemographicsError('');
 
    })
    .catch(error => {
      setDemographicsError(
        error.response?.data?.detail ||
        'Could not load audience demographics.'
      );
    });
}, []);
 const apply=()=>loadDashboard();
 const reset=async()=>{setBusy(true);try{await axios.post(`${API}/api/reset-demo`);const r=await axios.get(`${API}/api/options`);setOpts(r.data);setCats(r.data.categories);setFrom(r.data.min_date);setTo(r.data.max_date);setFilename('');setNotice('Demo data restored.');await loadDashboard({categories:r.data.categories,start_date:r.data.min_date,end_date:r.data.max_date});}catch(e){setError(e.response?.data?.detail||'Could not reset demo data.');}finally{setBusy(false);}};
 const upload=async e=>{const f=e.target.files?.[0];if(!f)return;setBusy(true);setError('');try{const form=new FormData();form.append('file',f);const r=await axios.post(`${API}/api/upload-csv`,form);setFilename(f.name);const o=await axios.get(`${API}/api/options`);setOpts(o.data);setCats(o.data.categories);setFrom(o.data.min_date);setTo(o.data.max_date);setNotice(`${f.name} loaded · ${r.data.rows} rows · ${r.data.titles} titles`);await loadDashboard({categories:o.data.categories,start_date:o.data.min_date,end_date:o.data.max_date});}catch(err){setError(err.response?.data?.detail||'CSV upload failed. Check required columns.');}finally{setBusy(false);e.target.value='';}};
 const runForecast=async()=>{setBusy(true);setError('');try{const r=await axios.post(`${API}/api/forecast`,{title,horizon});setForecast(r.data);}catch(e){setError(e.response?.data?.detail||'Could not create forecast.');}finally{setBusy(false);}};
 const ranking=useMemo(()=>!data?[]:data.ranking.filter(r=>`${r.title} ${r.category} ${r.potential}`.toLowerCase().includes(search.toLowerCase())).sort((a,b)=>sort==='title'?a.title.localeCompare(b.title):(b[sort]??0)-(a[sort]??0)),[data,search,sort]);
 const trend=useMemo(()=>data?.monthly_trend.map(x=>({...x,label:dateLabel(x.month)}))||[],[data]);
 const comparison=useMemo(()=>data?.ranking.filter(r=>compare.includes(r.title)).map(r=>({title:r.title,interest:r.avg_search,latest:r.latest_search}))||[],[data,compare]);
 const exportCsv=()=>{if(!ranking.length)return;const keys=Object.keys(ranking[0]);const csv=[keys.join(','),...ranking.map(r=>keys.map(k=>`"${String(r[k]??'').replaceAll('"','""')}"`).join(','))].join('\n');const url=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));const a=document.createElement('a');a.href=url;a.download='safora_content_ranking.csv';a.click();URL.revokeObjectURL(url);};
const nav=[
  ['Dashboard',Home,'WORKSPACE'],
  ['Content Ranking',BarChart3],
  ['Audience Trends',Activity],
  ['Music Intelligence',Music2],
  ['Prediction Studio',TrendingUp],
  ['Methodology',BookOpen,'INSIGHTS']
];
 const kpis=data?[['Titles explored',fmt(data.kpis.titles_explored),'Unique titles in this view',Layers3,'lavender'],['Average interest',`${data.kpis.average_interest}/100`,'Search-interest index',Gauge,'pink'],['High-potential titles',fmt(data.kpis.high_potential),'Weighted screening score',Sparkles,'mint'],['Top opportunity',data.kpis.top_opportunity,'Highest weighted score',Flame,'butter']]:[];
 const pageTitle=t({'Dashboard':'Market overview','Content Ranking':'Content opportunity ranking','Audience Trends':'Audience trends','Prediction Studio':'Prediction studio','Methodology':'Methodology & trust','Music Intelligence':'J-Pop Music Intelligence',}[page]);
 return <div className={`app-shell ${sidebar?'':'sidebar-collapsed'}`}>
  {mobile&&<button className="scrim" onClick={()=>setMobile(false)} aria-label="Close navigation"/>}
  <aside className={`sidebar ${sidebar?'':'sidebar-hidden'} ${mobile?'mobile-open':''}`}>
   <div className="brand-card"><div className="brand-topline">✿ JAPAN × INDIA</div><div className="brand-name">SAFORA <span>✧</span></div><p>{t("Japanese Media Intelligence")}</p><div className="brand-foot">{t("DISCOVER · ANALYZE · GROW")}</div></div>
   <div className="group-label">{t("WORKSPACE")}</div><nav className="nav-list">{nav.map(([label,Icon,section])=><React.Fragment key={label}>{section==='INSIGHTS'&&<div className="group-label insight-label">{t("INSIGHTS")}</div>}<button className={`nav-item ${page===label?'active':''}`} onClick={()=>{setPage(label);setMobile(false)}}><Icon size={17}/><span>{t(label)}</span>{page===label&&<i/>}</button></React.Fragment>)}</nav>
   <div className="divider"/><div className="filter-title"><Filter size={14}/> DATA CONTROLS</div>
   <div className="filter-block"><label>{t("Content categories")}</label><div className="pills">{(opts?.categories||[]).map(c=><button key={c} className={cats.includes(c)?'pill selected':'pill'} onClick={()=>setCats(old=>old.includes(c)?old.filter(x=>x!==c):[...old,c])}>{c}{cats.includes(c)&&<Check size={11}/>}</button>)}</div></div>
   <div className="filter-block"><label>{t("Analysis period")}</label><div className="dates"><div><small>{t("FROM")}</small><input type="date" value={from} min={opts?.min_date} max={to||opts?.max_date} onChange={e=>setFrom(e.target.value)}/></div><div><small>{t("TO")}</small><input type="date" value={to} min={from||opts?.min_date} max={opts?.max_date} onChange={e=>setTo(e.target.value)}/></div></div></div>
   <button className="primary apply" disabled={busy} onClick={apply}><Filter size={14}/> Apply filters</button><div className="divider"/><div className="filter-title"><Layers3 size={14}/> DATA SOURCE</div>
   <label className="upload"><FileUp size={15}/> Upload CSV<input type="file" accept=".csv,text/csv" onChange={upload}/></label>{filename&&<div className="filename">{filename}</div>}<button className="reset" onClick={reset} disabled={busy}><RefreshCw size={13}/> Reset to demo data</button>
   <div className="status"><i className={opts?.synthetic_demo?'demo':'live'}/>{opts?.synthetic_demo?'Synthetic demo dataset':'Uploaded dataset active'}</div><div className="side-foot"><span>{t("SAFORA · PROTOTYPE")}</span><span>v1.0</span></div>
  </aside>
  <main className="main-area"><header className="topbar"><div className="top-left"><button className="icon-btn" onClick={()=>window.innerWidth<=820?setMobile(true):setSidebar(v=>!v)} aria-label={t('Toggle sidebar')}>{sidebar?<ChevronLeft size={18}/>:<Menu size={18}/>}</button><div className="crumb"><b>SAFORA</b><ChevronRight size={13}/><span>{t(page)}</span></div></div><div className="top-right"><div className="language-switcher"><select value={i18n.resolvedLanguage?.split('-')[0]||'en'} onChange={e=>{const lang=e.target.value;i18n.changeLanguage(lang);localStorage.setItem('safora-language',lang);}} aria-label={t('Website language')}><option value="en">🇬🇧 English</option><option value="hi">🇮🇳 हिन्दी</option><option value="ja">🇯🇵 日本語</option></select></div><span className="local-dot"><i/> {t('LOCAL WORKSPACE')}</span><button className="icon-btn" onClick={()=>loadDashboard()} title={t('Refresh')}><RefreshCw size={16}/></button><div className="avatar">S</div></div></header>
   <div className="content"><section className="welcome"><div><div className="eyebrow"><Sparkles size={13}/> JAPAN × INDIA · MEDIA INTELLIGENCE</div><h1>{pageTitle}<span>✿</span></h1><p>{t("Understand audience signals, spot emerging titles, and explore content opportunities.")}</p></div><div className="date-chip"><CalendarDays size={14}/>{dateLabel(from,i18n.resolvedLanguage)} — {dateLabel(to,i18n.resolvedLanguage)}</div></section>
    {error&&<div className="alert error"><CircleHelp size={17}/><div><b>{t("Something needs attention")}</b><span>{error}</span></div><button onClick={()=>setError('')}><X size={15}/></button></div>}{notice&&<div className="alert success"><Check size={17}/><span>{notice}</span><button onClick={()=>setNotice('')}><X size={15}/></button></div>}
    {opts?.synthetic_demo&&<div className="demo-note"><div className="note-icon"><Lightbulb size={17}/></div><div><b>{t("Demo workspace")}</b><p>{t("Sample data is synthetic and demonstrates the interface only. It is not verified Japanese market research.")}</p></div><span>{t("DEMO DATA")}</span></div>}{busy&&<div className="loading"><i/> Updating insights…</div>}
    {data&&page==='Dashboard'&&<><section className="kpi-grid">{kpis.map(([label,value,sub,Icon,tone])=><article className={`kpi ${tone}`} key={label}><div className="kpi-top"><span>{t(label)}</span><i><Icon size={17}/></i></div><strong className={label==='Top opportunity'?'top-title':''}>{value}</strong><small>{sub}</small></article>)}</section>
      <section className="charts-grid"><article className="panel"><PanelHeading icon={<TrendingUp size={16}/>} title="Audience interest through time" subtitle="Average search-interest signal · 0–100"/><div className="chart trend"><ResponsiveContainer width="100%" height="100%"><AreaChart data={trend} margin={{top:8,right:8,left:-18,bottom:0}}><defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#9272C5" stopOpacity={.27}/><stop offset="95%" stopColor="#9272C5" stopOpacity={.01}/></linearGradient></defs><CartesianGrid stroke="#EEE5F0" strokeDasharray="4 5" vertical={false}/><XAxis dataKey="label" tick={{fill:'#91849E',fontSize:10}} axisLine={false} tickLine={false} minTickGap={24}/><YAxis domain={[0,100]} tick={{fill:'#91849E',fontSize:10}} axisLine={false} tickLine={false}/><Tooltip content={<Tip/>}/><Area type="monotone" dataKey="search_interest" name="Search interest" stroke="#8062B2" strokeWidth={3} fill="url(#area)" activeDot={{r:5,fill:'#E7AFC5',stroke:'#FFFDF8',strokeWidth:2}}/></AreaChart></ResponsiveContainer></div><div className="chart-foot"><span><i/> Monthly average</span><span>{t("Current filter selection")}</span></div></article>
      <article className="panel"><PanelHeading icon={<Sparkles size={16}/>} title="Opportunity mix" subtitle="Titles grouped by screening score"/><div className="donut-box"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={data.opportunity_mix} dataKey="value" nameKey="name" innerRadius="60%" outerRadius="81%" paddingAngle={4} cornerRadius={5} stroke="none">{data.opportunity_mix.map((x,i)=><Cell key={x.name} fill={({High:'#8062B2',Medium:'#C9A9E7',Low:'#E7B5C8'})[x.name]||COLORS[i]}/>)}</Pie><Tooltip content={<Tip/>}/><Legend verticalAlign="bottom" iconType="circle" iconSize={8} formatter={v=><span className="legend-label">{v}</span>}/></PieChart></ResponsiveContainer><div className="donut-center"><b>{data.kpis.titles_explored}</b><span>{t("titles")}</span></div></div><div className="mix-summary">{data.opportunity_mix.map(x=><div key={x.name}><i className={x.name.toLowerCase()}/><span>{x.name}</span><b>{x.value}</b></div>)}</div></article></section>
      <section className="panel ranking-preview"><PanelHeading icon={<Flame size={16}/>} title="Recommended titles to investigate" subtitle="Highest weighted opportunity scores" action={<button className="text-action" onClick={()=>setPage('Content Ranking')}>View full ranking <ChevronRight size={14}/></button>}/><RankingTable rows={data.ranking.slice(0,6)}/></section>
      <section className="lower-grid"><article className="panel"><PanelHeading icon={<ArrowUpRight size={16}/>} title="Rising Stars" subtitle="Recent 3-month average vs previous 3 months"/>{data.rising_stars.length?<div className="rising-list">{data.rising_stars.slice(0,4).map((r,i)=><div className="rising-row" key={r.title}><div className="rank-num">{String(i+1).padStart(2,'0')}</div><div className="rising-info"><b>{r.title}</b><span>{Number(r.recent_interest).toFixed(1)} recent interest</span></div><div className="growth"><ArrowUpRight size={13}/> +{r.change_points}</div></div>)}</div>:<Empty text="At least six months of comparable data are needed."/>}</article><article className="panel"><PanelHeading icon={<Compass size={16}/>} title="Audience signals" subtitle="Average search interest by language"/><div className="chart signal"><ResponsiveContainer width="100%" height="100%"><BarChart data={data.language_signals.slice(0,5)} layout="vertical" margin={{top:0,right:8,left:4,bottom:0}}><CartesianGrid stroke="#EEE5F0" strokeDasharray="3 4" horizontal={false}/><XAxis type="number" domain={[0,100]} hide/><YAxis type="category" dataKey="language" width={74} tick={{fill:'#82758F',fontSize:10}} axisLine={false} tickLine={false}/><Tooltip content={<Tip/>}/><Bar dataKey="search_interest" name="Interest" radius={[0,7,7,0]} barSize={14}>{data.language_signals.slice(0,5).map((x,i)=><Cell key={x.language} fill={COLORS[i%COLORS.length]}/>)}</Bar></BarChart></ResponsiveContainer></div></article></section></>}
    {data&&page==='Content Ranking'&&<section className="panel full"><PanelHeading icon={<BarChart3 size={16}/>} title="Content opportunity leaderboard" subtitle="Search, compare, and export titles" action={<button className="primary compact" onClick={exportCsv}><Download size={14}/> Export CSV</button>}/><div className="table-tools"><div className="search"><Search size={15}/><input placeholder={t("Search title, category, potential…")} value={search} onChange={e=>setSearch(e.target.value)}/></div><select value={sort} onChange={e=>setSort(e.target.value)}><option value="potential_score">{t("Opportunity score")}</option><option value="avg_search">{t("Average interest")}</option><option value="latest_search">{t("Latest interest")}</option><option value="rating">{t("Rating")}</option><option value="reviews">{t("Reviews")}</option><option value="title">{t("Title A–Z")}</option></select></div><RankingTable rows={ranking}/><p className="table-note">The score is a prioritization heuristic, not a forecast of revenue or guaranteed success.</p></section>}

{data && page === 'Audience Trends' && (
  <>
    <section className="panel full">
      <PanelHeading
        icon={<Activity size={16} />}
        title="Compare audience-interest signals"
        subtitle="Select titles to compare average and latest interest"
      />

      <div className="compare-pills">
        {data.raw_titles.slice(0, 30).map(item => (
          <button
            key={item}
            className={compare.includes(item) ? 'compare selected' : 'compare'}
            onClick={() =>
              setCompare(old =>
                old.includes(item)
                  ? old.filter(x => x !== item)
                  : [...old, item]
              )
            }
          >
            {item}
          </button>
        ))}
      </div>

      <div className="chart big">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={comparison}
            margin={{ top: 12, right: 12, left: 0, bottom: 45 }}
          >
            <CartesianGrid stroke="#EEE5F0" strokeDasharray="4 5" vertical={false} />
            <XAxis
              dataKey="title"
              angle={-24}
              textAnchor="end"
              interval={0}
              height={80}
              tick={{ fill: '#82758F', fontSize: 10 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis domain={[0, 100]} />
            <Tooltip content={<Tip />} />
            <Legend />
            <Bar dataKey="interest" name="Average interest" fill="#C9A9E7" radius={[6, 6, 0, 0]} />
            <Bar dataKey="latest" name="Latest interest" fill="#8062B2" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>

    <section className="lower-grid">
      <SignalPanel
        title="Google Trends language signals"
        subtitle="Search interest by language, when available"
        data={data.language_signals}
        keyName="language"
      />

      <SignalPanel
        title="Regional indicators"
        subtitle="Relative Google Trends interest by region"
        data={data.region_signals}
        keyName="region"
      />
    </section>

    {demographics && (
      <>
        <div className="demo-note">
          <div className="note-icon">
            <Lightbulb size={17} />
          </div>
          <div>
            <b>Sample audience demographics</b>
            <p>{demographics.note}</p>
          </div>
          <span>SYNTHETIC DATA</span>
        </div>

        <section className="kpi-grid">
          <article className="kpi lavender">
            <div className="kpi-top">
              <span>Sample profiles</span>
              <i><Users size={17} /></i>
            </div>
            <strong>{fmt(demographics.sample_size)}</strong>
            <small>Profiles in the source dataset</small>
          </article>
        </section>

        <section className="lower-grid">
          <DemographicPanel
            title="Preferred language"
            subtitle="Distribution across sample profiles"
            rows={demographics.language}
          />
          <DemographicPanel
            title="Age distribution"
            subtitle="Percentage of sample profiles by age group"
            rows={demographics.age}
          />
          <DemographicPanel
            title="Gender distribution"
            subtitle="Reported gender categories in sample profiles"
            rows={demographics.gender}
          />
        </section>
      </>
    )}

    {demographicsError && (
      <div className="alert error">
        <CircleHelp size={17} />
        <span>{demographicsError}</span>
      </div>
    )}

    <p className="table-note">
      Google Trends values represent relative search interest.
      Demographic percentages represent synthetic sample profiles,
      not verified population statistics.
    </p>
  </>
)}
    
    {data&&page==='Prediction Studio'&&<section className="panel full"><PanelHeading icon={<TrendingUp size={16}/>} title="Baseline trend forecast" subtitle="Linear-regression baseline with chronological holdout evaluation"/><div className="forecast-controls"><div><label>{t("Choose a title")}</label><select value={title} onChange={e=>{setTitle(e.target.value);setForecast(null)}}>{data.raw_titles.map(t=><option key={t}>{t}</option>)}</select></div><div><label>{t("Forecast horizon")}</label><select value={horizon} onChange={e=>setHorizon(Number(e.target.value))}>{[1,2,3,4,5,6,9,12].map(n=><option key={n} value={n}>{n} month{n>1?'s':''}</option>)}</select></div><button className="primary" disabled={busy} onClick={runForecast}><Zap size={15}/> Generate forecast</button></div>{forecast?<><div className="forecast-kpis"><Metric label="Mean interest" value={`${forecast.mean_interest}/100`}/><Metric label="Latest interest" value={`${forecast.latest_interest}/100`}/><Metric label="Holdout MAE" value={forecast.mae??'N/A'}/><Metric label="Holdout RMSE" value={forecast.rmse??'N/A'}/></div><div className="chart forecast"><ResponsiveContainer width="100%" height="100%"><LineChart data={[...forecast.history.map(x=>({...x,label:dateLabel(x.month)})),...forecast.forecast.map(x=>({...x,label:dateLabel(x.month)}))]} margin={{top:12,right:14,left:-12,bottom:0}}><CartesianGrid stroke="#EEE5F0" strokeDasharray="4 5" vertical={false}/><XAxis dataKey="label" tick={{fill:'#82758F',fontSize:10}} axisLine={false} tickLine={false}/><YAxis domain={[0,100]} tick={{fill:'#82758F',fontSize:10}} axisLine={false} tickLine={false}/><Tooltip content={<Tip/>}/><Line type="monotone" dataKey="search_interest" name="Interest" stroke="#8062B2" strokeWidth={3} dot={{r:3}}/></LineChart></ResponsiveContainer></div><div className="demo-note"><Lightbulb size={17}/><div><b>{t("Interpret with care")}</b><p>{forecast.note} Demo data is synthetic and is not verified market demand.</p></div></div></>:<Empty text="Choose a title and generate a baseline forecast to view its history, error metrics, and forward trend."/>}</section>}
    {data&&page==='Methodology'&&<><section className="method-hero"><div className="method-icon"><BookOpen size={23}/></div><div><div className="eyebrow">{t("TRANSPARENCY FIRST")}</div><h2>{t("Useful signals, honest limitations.")}</h2><p>{t("SAFORA helps prioritize what to investigate. It does not claim to prove market success.")}</p></div></section><section className="method-grid"><Method n="01" title="Collect signals" text="Bring search-interest observations and content indicators into one consistent dataset."/><Method n="02" title="Clean and filter" text="Normalize common column names, parse dates, validate numeric fields, and filter the analysis window."/><Method n="03" title="Rank opportunities" text="Combine average interest, latest interest, ratings, reviews, and engagement using explicit weights."/><Method n="04" title="Spot momentum" text="Compare the latest three-month average with the preceding three-month average to flag rising titles."/><Method n="05" title="Evaluate a baseline" text="Fit a linear regression on earlier observations and report MAE/RMSE on a later holdout slice."/><Method n="06" title="Validate before decisions" text="Replace synthetic data with documented sources, check representativeness, and compare against sensible baselines."/></section><section className="panel weights"><PanelHeading icon={<Settings2 size={16}/>} title="Opportunity score weights" subtitle="Weighted screening score · total weight 100%"/>{[['Average search interest',35,'#8062B2'],['Latest search interest',25,'#C9A9E7'],['Rating',15,'#E7B5C8'],['Reviews',15,'#A6C5B2'],['Engagement',10,'#E7CF98']].map(([l,v,c])=><div className="weight" key={l}><div><span>{l}</span><b>{v}%</b></div><i><span style={{width:`${v}%`,background:c}}/></i></div>)}</section><div className="demo-note"><CircleHelp size={17}/><div><b>{t("Data integrity note")}</b><p>Demo data is synthetic. Search interest is not the same as views, market share, revenue, or confirmed purchase intent.</p></div></div></>}
    <MusicPage active={page === 'Music Intelligence'} />
    <footer className="footer"><b>SAFORA <span>✿</span></b><span>Japanese Media Intelligence · Local prototype</span><span>{t("Built for exploration, designed for clarity.")}</span></footer>
   </div>
  </main>{busy&&<div className="busy"><i/> Working</div>}</div>
}

function MusicPage({ active }) {
  const [stats, setStats] = useState(null);
  const [tracks, setTracks] = useState([]);
  const [topTracks, setTopTracks] = useState([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [musicError, setMusicError] = useState('');

  useEffect(() => {
    if (!active) return;

    let cancelled = false;

    async function loadMusic() {
      setLoading(true);
      setMusicError('');

      try {
        const [statsResponse, tracksResponse, topResponse] =
          await Promise.all([
            axios.get(`${API}/api/music/stats`),
            axios.get(`${API}/api/music`, {
              params: { search: query || undefined, limit: 50 }
            }),
            axios.get(`${API}/api/music/top`, {
              params: { limit: 5 }
            })
          ]);

        if (!cancelled) {
          setStats(statsResponse.data);
          setTracks(tracksResponse.data.tracks || []);
          setTopTracks(topResponse.data.tracks || []);
        }
      } catch (err) {
        if (!cancelled) {
          setMusicError(
            err.response?.data?.detail ||
            'Could not load music data. Check that the backend is running.'
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadMusic();

    return () => {
      cancelled = true;
    };
  }, [active, query]);

  if (!active) return null;

  return (
    <section className="music-page">
      <div className="music-intro">
        <span className="music-eyebrow">JAPANESE MUSIC DISCOVERY</span>
        <h2>J-Pop Intelligence</h2>
        <p>
          Explore tracks, artists, albums and dataset-reported play counts.
        </p>
      </div>

      {musicError && (
        <div className="alert error">
          <span>{musicError}</span>
        </div>
      )}

      {loading && <p className="music-muted">Loading music data...</p>}

      <div className="music-kpis">
        <article className="music-stat">
          <span>Total tracks</span>
          <strong>{stats ? fmt(stats.total_tracks) : '—'}</strong>
        </article>

        <article className="music-stat">
          <span>Unique artists</span>
          <strong>{stats ? fmt(stats.unique_artists) : '—'}</strong>
        </article>

        <article className="music-stat">
          <span>Unique albums</span>
          <strong>{stats ? fmt(stats.unique_albums) : '—'}</strong>
        </article>

        <article className="music-stat">
          <span>Average popularity</span>
          <strong>
            {stats?.average_popularity != null
              ? Number(stats.average_popularity).toFixed(1)
              : '—'}
          </strong>
        </article>
      </div>

      <section className="panel music-panel">
        <PanelHeading
          icon={<Music2 size={16} />}
          title="Top tracks"
          subtitle="Ranked by play_count reported in this dataset"
        />

        {topTracks.length > 0 ? (
          <div className="music-track-list">
            {topTracks.map((track, index) => (
              <article
                className="music-track"
                key={track.track_id || `${track.name}-${index}`}
              >
                <span className="music-rank">
                  {String(index + 1).padStart(2, '0')}
                </span>

                <div className="music-track-info">
                  <strong>{track.name || 'Unknown track'}</strong>
                  <span>{track.artist || 'Unknown artist'}</span>
                  <small>
                    {track.album || 'Album unavailable'}
                    {track.release_year
                      ? ` · ${track.release_year}`
                      : ''}
                  </small>
                </div>

                <span className="music-plays">
                  {fmt(track.play_count)} plays
                </span>
              </article>
            ))}
          </div>
        ) : (
          !loading && <Empty text="No ranked tracks are available." />
        )}
      </section>

      <section className="panel music-panel">
        <PanelHeading
          icon={<Search size={16} />}
          title="Explore the catalogue"
          subtitle="Search song titles, artists or albums"
        />

        <div className="search music-search">
          <Search size={16} />
          <input
            type="search"
            placeholder="Try a song or artist name..."
            value={query}
            onChange={event => setQuery(event.target.value)}
          />
          {query && (
            <button
              className="music-clear"
              onClick={() => setQuery('')}
            >
              Clear
            </button>
          )}
        </div>

        <p className="music-muted">
          {tracks.length} tracks shown
          {query ? ` for "${query}"` : ' from the catalogue'}
          {' · '}up to 50 results per search
        </p>

        <div className="table-scroll">
          <table className="ranking-table">
            <thead>
              <tr>
                <th>Track</th>
                <th>Artist</th>
                <th>Album</th>
                <th>Year</th>
                <th>Popularity</th>
              </tr>
            </thead>

            <tbody>
              {tracks.map((track, index) => (
                <tr
                  key={track.track_id || `${track.name}-${index}`}
                >
                  <td>
                    <strong>{track.name || '—'}</strong>
                  </td>
                  <td>{track.artist || '—'}</td>
                  <td>{track.album || '—'}</td>
                  <td>{track.release_year || '—'}</td>
                  <td>{track.popularity ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {!loading && tracks.length === 0 && (
          <Empty text="No tracks match your search." />
        )}
      </section>

      <p className="music-disclaimer">
        Source: Hugging Face — sdy623/JPOP-Sampled-Spotify.
        Popularity and play counts are dataset-level metrics, not verified
        Indian audience statistics or current live Spotify rankings.
      </p>
    </section>
  );
}

function PanelHeading({icon,title,subtitle,action}){const {t}=useTranslation();return <div className="panel-heading"><div className="panel-icon">{icon}</div><div className="panel-heading-text"><h2>{t(title)}</h2>{subtitle&&<p>{t(subtitle)}</p>}</div>{action&&<div className="panel-action">{action}</div>}</div>}
function Tip({active,payload,label}){if(!active||!payload?.length)return null;return <div className="tooltip"><b>{label||''}</b>{payload.map((p,i)=><div key={i}><i style={{background:p.color||p.fill||'#8062B2'}}/>{p.name||p.dataKey}<strong>{typeof p.value==='number'?p.value.toFixed(1):p.value}</strong></div>)}</div>}
function RankingTable({rows}){const {t}=useTranslation();if(!rows?.length)return <Empty text="No titles match the current filters."/>;return <div className="table-scroll"><table className="ranking-table"><thead><tr><th>{t('Title')}</th><th>{t('Category')}</th><th>{t("Opportunity score")}</th><th>{t('Potential')}</th><th>{t('Avg. interest')}</th><th>{t('Latest')}</th><th>{t("Rating")}</th></tr></thead><tbody>{rows.map(r=><tr key={`${r.title}-${r.category}`}><td><div className="title-cell"><span>✿</span><b>{r.title}</b></div></td><td><label className="category-label">{r.category}</label></td><td><div className="score"><b>{Number(r.potential_score).toFixed(1)}</b><i><span style={{width:`${Math.max(0,Math.min(100,r.potential_score))}%`}}/></i></div></td><td><label className={`badge ${String(r.potential).toLowerCase()}`}>{r.potential}</label></td><td>{Number(r.avg_search).toFixed(1)}</td><td>{Number(r.latest_search).toFixed(1)}</td><td>{Number(r.rating)>0?`${Number(r.rating).toFixed(1)}/10`:'—'}</td></tr>)}</tbody></table></div>}
function Empty({text}){const {t}=useTranslation();return <div className="empty"><span><Search size={18}/></span><p>{t(text)}</p></div>}
function Metric({label,value}){const {t}=useTranslation();return <div className="metric"><span>{t(label)}</span><b>{value}</b></div>}
function Method({n,title,text}){const {t}=useTranslation();return <article className="method-card"><span>{n}</span><h3>{title}</h3><p>{t(text)}</p></article>}
function SignalPanel({title,subtitle,data,keyName}){return <article className="panel"><PanelHeading icon={<Compass size={16}/>} title={title} subtitle={subtitle}/><div className="signal-bars">{data.map((r,i)=><div className="signal-row" key={r[keyName]}><span>{r[keyName]}</span><i><span style={{width:`${Math.min(100,r.search_interest)}%`,background:COLORS[i%COLORS.length]}}/></i><b>{Number(r.search_interest).toFixed(1)}</b></div>)}</div></article>}
export default App;

function DemographicPanel({ title, subtitle, rows = [] }) {
  return (
    <article className="panel">
      <PanelHeading
        icon={<Users size={16} />}
        title={title}
        subtitle={subtitle}
      />

      {rows.length ? (
        <div className="signal-bars">
          {rows.map((row, index) => (
            <div className="signal-row" key={row.name}>
              <span>{row.name}</span>
              <i>
                <span
                  style={{
                    width: `${Math.min(100, row.percentage)}%`,
                    background: COLORS[index % COLORS.length],
                  }}
                />
              </i>
              <b>{row.percentage.toFixed(1)}%</b>
            </div>
          ))}
        </div>
      ) : (
        <Empty text="No demographic records are available." />
      )}
    </article>
  );
}

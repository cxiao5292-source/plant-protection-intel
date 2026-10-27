let allItems=[],archiveItems=[],category="all",archiveMode=false;
const names={global:"全球动态",plant:"植保科研",visa:"海外签证",jobs:"农化就业"};
const relLabel={high:"高相关",medium:"中相关",low:"低相关"};
const relColor={high:"#16a34a",medium:"#ca8a04",low:"#94a3b8"};
const statusColor={"官方确认开放":"#16a34a","已关闭或已过期":"#dc2626","官方页面存在但开放状态不明":"#ca8a04","只有第三方历史信息":"#94a3b8"};

function safe(s){
  return String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))
}

function relBadge(r){
  if(!r||!relLabel[r]) return "";
  return '<span class="badge" style="background:'+relColor[r]+'20;color:'+relColor[r]+'">'+safe(relLabel[r])+'</span>';
}

function statusBadge(s){
  if(!s) return "";
  var c=statusColor[s]||"#94a3b8";
  return '<span class="badge" style="background:'+c+'20;color:'+c+'">'+safe(s)+'</span>';
}

function jobsExtra(x){
  var h="";
  if(x.official_url) h+='<a href="'+safe(x.official_url)+'" target="_blank" rel="noopener noreferrer">官方链接 ↗</a> ';
  if(x.jobs_verified_date) h+='<span class="vdate">核验: '+safe(x.jobs_verified_date)+'</span>';
  return h;
}

async function loadArchive(){
  try{
    let r=await fetch("data/archive/index.json?ts="+Date.now(),{cache:"no-store"});
    if(!r.ok) return;
    let dates=await r.json();
    if(!dates||!dates.length) return;
    // Load the most recent archive file
    let latest=dates[0];
    let r2=await fetch("data/archive/"+latest+".json?ts="+Date.now(),{cache:"no-store"});
    if(!r2.ok) return;
    let d=await r2.json();
    archiveItems=d.items||[];
  }catch(e){
    console.log("Archive load failed:",e);
  }
}

async function load(){
  try{
    let r=await fetch("data/current.json?ts="+Date.now(),{cache:"no-store"});
    if(!r.ok) throw Error();
    let d=await r.json();
    allItems=d.items||[];
    document.querySelector("#updated").textContent="数据日期："+(d.date||"待更新")+" · 最近刷新："+(d.updated||"自动任务");
    await loadArchive();
    render()
  }catch(e){
    document.querySelector("#updated").textContent="网站已发布；首次自动更新后将显示情报。";
    document.querySelector("#cards").innerHTML='<div class="empty">暂时没有读取到数据。请稍后刷新，或查看项目仓库的 Actions 运行状态。</div>'
  }
}

function render(){
  let q=document.querySelector("#search").value.trim().toLowerCase();
  let source=category==="archive"?archiveItems:allItems;
  let arr=source.filter(x=>(category==="all"||category==="archive"||x.category===category)&&[x.title,x.summary,x.source,x.category].join(" ").toLowerCase().includes(q));
  document.querySelector("#heading").textContent=category==="all"?"今日情报":category==="archive"?"历史归档（最近一次采集）":names[category];
  document.querySelector("#count").textContent=arr.length+" 条线索";
  if(category==="archive"&&!archiveItems.length){
    document.querySelector("#cards").innerHTML='<div class="empty">暂无历史归档数据。归档文件将在自动更新后生成。</div>';
    return;
  }
  document.querySelector("#cards").innerHTML=arr.length?arr.map(x=>{
    var isJobs=x.category==="jobs";
    var meta=x.source||"公开来源";
    if(x.date) meta+=" · "+x.date;
    if(x.source_level) meta+=" · "+x.source_level;
    var badges=relBadge(x.relevance);
    if(isJobs&&x.official_status) badges+=statusBadge(x.official_status);
    var extra="";
    if(isJobs) extra=jobsExtra(x);
    if(x.verification&&x.verification!=="待打开原文核实") extra+=' <span class="vnote">'+safe(x.verification)+'</span>';
    return '<article class="item"><span class="tag">'+safe(names[x.category]||"情报")+'</span>'+badges+'<h3>'+safe(x.title)+'</h3><p>'+safe(x.summary||"打开原文查看详细信息。")+'</p><div class="source">'+safe(meta)+'</div>'+(extra?'<div class="extra">'+extra+'</div>':'')+'<p><a href="'+safe(x.url||"#")+'" target="_blank" rel="noopener noreferrer">阅读原文 ↗</a></p></article>'
  }).join(""):'<div class="empty">没有匹配内容。可换个关键词，或切换栏目。</div>'
}

document.querySelector("#tabs").addEventListener("click",e=>{
  let b=e.target.closest("button[data-cat]");
  if(!b) return;
  category=b.dataset.cat;
  document.querySelectorAll(".tab").forEach(x=>x.classList.toggle("active",x===b));
  render()
});
document.querySelector("#search").addEventListener("input",render);
load();

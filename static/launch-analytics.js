(()=>{
  const allowed=new Set(["buyer_click","seller_click","demo_click","founding_click","language_click","guide_click"]);
  const params=new URLSearchParams(location.search);
  const campaign=(params.get("utm_campaign")||"").replace(/[^A-Za-z0-9._-]/g,"").slice(0,80);
  const trackedPath=/^\/mainnet\/(deal|negotiate)\//.test(location.pathname)?location.pathname.replace(/\/[^/]+$/,"/id"):location.pathname;
  let activeMs=0,visibleStarted=document.visibilityState==="visible"?Date.now():null;
  let session=sessionStorage.getItem("agentsolis_session");
  if(!session){const bytes=new Uint8Array(16);crypto.getRandomValues(bytes);session=Array.from(bytes,b=>b.toString(16).padStart(2,"0")).join("");sessionStorage.setItem("agentsolis_session",session)}
  function send(event,duration=0){
    if(!["page_view","page_exit","heartbeat"].includes(event)&&!allowed.has(event))return;
    const body=JSON.stringify({event,path:trackedPath,language:document.documentElement.lang||"en",campaign,session_id:session,duration_seconds:Math.min(86400,Math.max(0,Math.round(duration)))});
    if(navigator.sendBeacon){navigator.sendBeacon("/internal/analytics/event",new Blob([body],{type:"application/json"}));return;}
    fetch("/internal/analytics/event",{method:"POST",headers:{"Content-Type":"application/json"},body,keepalive:true}).catch(()=>{});
  }
  send("page_view");
  const elapsed=()=>((activeMs+(visibleStarted?Date.now()-visibleStarted:0))/1000);
  const heartbeat=setInterval(()=>{if(document.visibilityState==="visible")send("heartbeat",elapsed())},30000);
  document.addEventListener("visibilitychange",()=>{if(document.visibilityState==="hidden"&&visibleStarted){activeMs+=Date.now()-visibleStarted;visibleStarted=null;send("heartbeat",elapsed())}else if(document.visibilityState==="visible"&&!visibleStarted)visibleStarted=Date.now()});
  addEventListener("pagehide",()=>{if(visibleStarted){activeMs+=Date.now()-visibleStarted;visibleStarted=null}clearInterval(heartbeat);send("page_exit",elapsed())});
  document.addEventListener("click",event=>{
    const link=event.target.closest("a[data-event]");
    if(link)send(link.dataset.event,elapsed());
  });
})();

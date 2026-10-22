(()=>{
  const allowed=new Set(["buyer_click","seller_click","demo_click","founding_click","language_click"]);
  const params=new URLSearchParams(location.search);
  const campaign=(params.get("utm_campaign")||"").replace(/[^A-Za-z0-9._-]/g,"").slice(0,80);
  function send(event){
    if(event!=="landing_view"&&!allowed.has(event))return;
    const body=JSON.stringify({event,path:location.pathname,language:document.documentElement.lang||"en",campaign});
    if(navigator.sendBeacon){navigator.sendBeacon("/internal/analytics/event",new Blob([body],{type:"application/json"}));return;}
    fetch("/internal/analytics/event",{method:"POST",headers:{"Content-Type":"application/json"},body,keepalive:true}).catch(()=>{});
  }
  send("landing_view");
  document.addEventListener("click",event=>{
    const link=event.target.closest("a[data-event]");
    if(link)send(link.dataset.event);
  });
})();

(async()=>{
  const allowed=await fetch('/massive_assistant/api',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({jsonrpc:'2.0',method:'call',id:1,params:{action:'visible',data:{}}})}).then(r=>r.json()).then(r=>({ok:!!r.result?.visible,data:{design:r.result?.design || {}}})).catch(()=>null);
  if(!allowed?.ok || (document.getElementById("mc-extension-host") || document.getElementById("mc-native-host")))return;
  const design=allowed.data?.design || {};
  const host=document.createElement("div");host.id="mc-native-host";
  host.style.cssText="position:fixed;right:20px;bottom:20px;z-index:2147483647;max-width:calc(100vw - 16px);opacity:1;isolation:isolate;";
  const root=host.attachShadow({mode:"closed"});
  const style=document.createElement("style");style.textContent="*{box-sizing:border-box}button{font:600 14px system-ui;cursor:pointer;border:0;border-radius:8px;padding:8px 10px;background:#fff;color:#182740}#mc{border-radius:50%;width:56px;height:56px;background-color:var(--primary,#963c81);background-image:radial-gradient(circle at 30% 20%,#ffffff88 0%,#ffffff00 48%),radial-gradient(circle at 35% 30%,#0000 25%,#0007 100%);color:white;border:1px solid #ffffff70;box-shadow:inset 0 2px 3px #ffffff70,inset 0 -3px 5px #0004,0 5px 18px #0005;opacity:1;touch-action:none;cursor:grab;padding:6px}#mc img{width:100%;height:100%;object-fit:contain;pointer-events:none}section{width:min(var(--width,390px),calc(100vw - 16px));height:min(var(--height,620px),calc(100dvh - 24px));background:white;border:1px solid #ddd;border-radius:16px;box-shadow:0 12px 48px #0004;overflow:hidden;display:flex;flex-direction:column}section[hidden],button[hidden]{display:none}header{display:flex;align-items:center;gap:6px;background:var(--primary,#963c81);padding:10px;color:var(--header-text,#fff);font:600 14px system-ui;touch-action:none;cursor:grab;user-select:none}header span{flex:1}iframe{border:0;flex:1;width:100%;min-height:0}#move{cursor:move}";root.append(style);
  if(/^#[a-f0-9]{6}$/i.test(design.primary||""))host.style.setProperty("--primary",design.primary);
  if(/^#[a-f0-9]{6}$/i.test(design.header_text||""))host.style.setProperty("--header-text",design.header_text);
  for(const key of ["width","height"])if(Number.isInteger(design[key])&&design[key]>=320&&design[key]<=800)host.style.setProperty("--"+key,design[key]+"px");
  const icon=document.createElement("button");icon.id="mc";icon.textContent="MC";icon.setAttribute("aria-label","Abrir Asistente Massive");icon.setAttribute("aria-expanded","false");root.append(icon);
  const logo=document.createElement("img");logo.alt="Massive Connector";logo.src="/massive_assistant/static/description/icon.png";
  if(design.custom_icon_logo===true && /^data:image\/(?:png|jpeg|webp);base64,[A-Za-z0-9+/=]+$/.test(design.logo||"")&&design.logo.length<360000)logo.src=design.logo;
  icon.replaceChildren(logo);
  const panel=document.createElement("section");panel.hidden=true;panel.setAttribute("aria-label","Asistente Massive");
  const header=document.createElement("header"),title=document.createElement("span");title.textContent=typeof design.title==="string"?design.title.slice(0,60):"Asistente Massive";header.append(title);
  function button(text,label,action){const b=document.createElement("button");b.textContent=text;b.setAttribute("aria-label",label);b.onclick=action;header.append(b);return b;}
  const move=button("↔","Mover ventana con flechas o arrastrar",()=>{});move.id="move";
  const home=()=>{host.style.left="";host.style.top="";host.style.right="20px";host.style.bottom="20px";};
  const minimize=()=>{panel.hidden=true;icon.hidden=false;icon.setAttribute("aria-expanded","false");home();icon.focus();};
  button("—","Minimizar conversación",minimize);button("×","Cerrar asistente",()=>host.remove());panel.append(header);
  const frame=document.createElement("iframe");frame.title="Chat privado de Asistente Massive";panel.append(frame);root.append(panel);document.documentElement.append(host);
  let dragged=false;
  icon.onclick=()=>{if(dragged){dragged=false;return;}if(!frame.getAttribute("src"))frame.src="/massive_assistant/panel";icon.hidden=true;panel.hidden=false;icon.setAttribute("aria-expanded","true");const r=host.getBoundingClientRect();position(r.left,r.top);move.focus();};
  window.addEventListener("message",e=>{if(e.source===frame.contentWindow && e.origin===new URL(frame.src).origin && e.data==="mc-minimize")minimize();});
  root.addEventListener("keydown",e=>{if(e.key==="Escape")minimize();});
  function position(left,top){host.style.right="auto";host.style.bottom="auto";host.style.left=Math.max(8,Math.min(left,innerWidth-host.getBoundingClientRect().width-8))+"px";host.style.top=Math.max(8,Math.min(top,innerHeight-host.getBoundingClientRect().height-8))+"px";}
  function draggable(target){let drag;target.addEventListener("pointerdown",e=>{if(e.button!==0 || (target===header && e.target.closest("button")!==move && e.target.closest("button")))return;drag={x:e.clientX,y:e.clientY,left:host.getBoundingClientRect().left,top:host.getBoundingClientRect().top,moved:false};dragged=false;target.setPointerCapture(e.pointerId);});target.addEventListener("pointermove",e=>{if(!drag)return;if(Math.hypot(e.clientX-drag.x,e.clientY-drag.y)>4)drag.moved=true;if(drag.moved)position(drag.left+e.clientX-drag.x,drag.top+e.clientY-drag.y);});target.addEventListener("pointerup",()=>{if(target===icon)dragged=!!drag?.moved;drag=null;});target.addEventListener("pointercancel",()=>{drag=null;dragged=false;});}
  draggable(icon);draggable(header);
  function keyboard(e){const deltas={ArrowLeft:[-20,0],ArrowRight:[20,0],ArrowUp:[0,-20],ArrowDown:[0,20]};if(deltas[e.key]){e.preventDefault();const r=host.getBoundingClientRect();position(r.left+deltas[e.key][0],r.top+deltas[e.key][1]);}}
  move.onkeydown=keyboard;icon.onkeydown=keyboard;
  window.addEventListener("resize",()=>{if(host.isConnected && host.style.left){const r=host.getBoundingClientRect();position(r.left,r.top);}});
})();

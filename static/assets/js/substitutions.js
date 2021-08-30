!function(){"use strict";function i(e,t=null){try{var n=e.name,i=(null==t?void 0:t.message)||e.message,o=e.description,s=e.number,a=(null==t?void 0:t.filename)||e.fileName,r=(null==t?void 0:t.lineno)||e.lineNumber,l=(null==t?void 0:t.colno)||e.columnNumber,d=(null==t?void 0:t.stack)||e.stack;plausible("JavaScript Error",{props:{[(n||"Generic Error")+": "+i]:d+" - "+a+":"+r+":"+l+" "+o+" "+s}})}catch(e){console.error("reporting error failed",e)}}window.addEventListener("error",e=>i(e.error,e)),window.addEventListener("unhandledrejection",e=>i(e.reason));const s=window.location.pathname.split("/",2)[1],a=document.getElementById("selectionInput").value,e=document.getElementById("timetables-block");if(e&&(e.hidden=!1),window.location.hash.startsWith("#timetable:"))try{let[,n,i]=window.location.hash.split(":");i=atob(i);let e=!0,o;if(150!==i.length)console.warn("Timetable in URL has wrong length:",i.length,"instead of",150,i),e=!1;else{o=[];for(let n=0;n<5;n++){let t=[];o.push(t);for(let e=0;e<10;e++){var r=i.substr(10*n*3+3*e,3).trim();t.push(r)}}}if(e){let e;try{e=JSON.parse(window.localStorage.getItem(s+"-timetables")),e=e||{}}catch{e={}}n=n.toUpperCase();let t=n in e?"Die aufgerufene URL enthält einen Stundenplan für "+n+". Soll der aktuell gespeicherte Stundenplan für "+n+" durch diesen ersetzt werden?":"Die aufgerufene URL enthält einen Stundenplan für "+n+". Diesen Stundenplan setzen?";if(a){let e=!1;for(var l of a.split(", "))if(l.toUpperCase()===n){e=!0;break}e||(t+=" Achtung: Der Stundenplan wird erst angewendet, wenn "+n+" auch ausgewählt ist.")}else t+=" Achtung: Der Stundenplan wird erst angewendet, wenn Vertretungen ausgewählt sind.";confirm(t)&&(e[n]=o,window.localStorage.setItem(s+"-timetables",JSON.stringify(e))),window.location.hash="",plausible("Timetable: Set From Link")}}catch(e){console.error("Error while retrieving timetable from URL",e),i(e)}const d=document.getElementsByClassName("date");function c(){const e=new Date;if(0<d.length&&d[0].innerHTML===e.getDate()+"."+(e.getMonth()+1)+"."+e.getFullYear()){var t,n=e.getHours(),i=e.getMinutes();for(t of[["1",8,35],["2",9,25],["3",10,30],["4",11,15],["5",12,20],["6",13,10],["7",14,35],["8",15,25],["9",16,20],["10",17,5]]){if(!(t[1]<n||t[1]===n&&t[2]<=i)){setTimeout(c,new Date(e.getFullYear(),e.getMonth(),e.getDate(),t[1],t[2]).getTime()-e.getTime());break}for(var o of document.getElementsByClassName("lesson"+t[0]))o.classList.add("grey")}}}c(),window.addEventListener("focus",()=>c());let o;var t,n=document.getElementById("status").textContent;try{if(o=JSON.parse(window.localStorage.getItem(s+"-seen-substitutions")),o.status!==n){var u,g,f,m=Date.now();for(u of Object.keys(o.seenSubstitutions))u<=m&&delete o.seenSubstitutions[u];for([g,f]of Object.entries(o.newSubstitutions))g>m&&(g in o.seenSubstitutions?o.seenSubstitutions[g].push(...f):o.seenSubstitutions[g]=f);o.newSubstitutions={},o.status=n}}catch{}o=o||{seenSubstitutions:{},newSubstitutions:{},status:n};for(t of document.getElementsByClassName("substitutions-box")){var h=t.querySelector(".substitutions-table tbody");if(h){const _=t.querySelector(".date").textContent.trim();var p,[,b,w,S]=_.match(/(\d\d?).(\d\d?).(\d\d\d\d)/),v=Date.UTC(S,w-1,b+1);v in o.seenSubstitutions||(o.seenSubstitutions[v]=[]),v in o.newSubstitutions||(o.newSubstitutions[v]=[]);let n;for(p of h.children){let e=p.querySelector(".group-name");null!=e&&(n=e.textContent.trim());let t=n;for(var y of p.children)y.classList.contains(".group-name")||(t+="#"+y.textContent.trim());o.seenSubstitutions[v].includes(t)||(p.classList.add("new-subs"),o.newSubstitutions[v].includes(t)||o.newSubstitutions[v].push(t))}}}window.localStorage.setItem(s+"-seen-substitutions",JSON.stringify(o));const k=document.getElementById("notifications-toggle");function E(e){for(var t of document.getElementsByClassName("notification-state"))t.hidden=!0;document.querySelector(`.notification-state[data-n="${e}"]`).hidden=!1}function L(e){localStorage.setItem(s+"-notification-state-pa",e)}function N(e,t){return e.pushManager.subscribe({userVisibleOnly:!0,applicationServerKey:function(e){e=(e+"=".repeat((4-e.length%4)%4)).replace(/-/g,"+").replace(/_/g,"/");const t=atob(e),n=new Uint8Array(t.length);for(let e=0;e<t.length;++e)n[e]=t.charCodeAt(e);return n}("BDu6tTwQHFlGb36-pLCzwMdgumSlyj_vqMR3I1KahllZd3v2se-LM25vhP3Yv_y0qXYx_KPOVOD2EYTaJaibzo8")}).then(e=>fetch("api/subscribe-push",{method:"post",headers:{"Content-Type":"application/json"},body:JSON.stringify({subscription:e.toJSON(),selection:a,is_active:t})})).then(e=>{if(!e.ok)throw Error(`Got ${e.status} from server`);return e.json()}).then(e=>{if(!e.ok)throw Error("Got ok: False from server")})}let I;function C(t,e){switch("failed"!==(I=e)&&localStorage.setItem(s+"-notification-state",I),L(e),k.checked="granted-and-enabled"===I,k.disabled="denied"===I,I){case"granted-and-enabled":E("subscribing"),N(t,!0).then(()=>E("enabled")).catch(e=>{C(t,"failed"),i(e)});break;case"denied":E("blocked");break;case"failed":E("failed");break;default:case"default":case"granted-and-disabled":E("disabled")}}navigator.serviceWorker.register("/sw.js").catch(e=>i(e)),window.addEventListener("load",()=>{"serviceWorker"in navigator?navigator.serviceWorker.ready.then(e=>{var t;function n(){return!I.startsWith(Notification.permission)&&"failed"!==I&&(console.log(I+" changed to "+Notification.permission),C(t,"granted"===Notification.permission?"granted-and-disabled":Notification.permission),!0)}"Notification"in window?"PushManager"in window?(t=e,document.getElementById("notifications-not-available-alert").hidden=!0,document.getElementById("toggle-notifications-wrapper").hidden=!1,I=window.localStorage.getItem(s+"-notification-state"),k.addEventListener("change",()=>{k.checked?(Notification.requestPermission().then(e=>{C(t,"granted"===e?"granted-and-enabled":e)}),plausible("Push Subscription",{props:{[s]:"Subscribe"}})):("granted-and-enabled"===I&&(E("unsubscribing"),N(t,!1).then(()=>{C(t,"granted-and-disabled")}).catch(e=>{C(t,"failed"),i(e)})),plausible("Push Subscription",{props:{[s]:"Unsubscribe"}}))}),I&&"failed"!==I||(I="default"),n()||C(t,I),window.addEventListener("focus",n)):L("unsupported (PushManager)"):L("unsupported (Notification)")}).catch(e=>i(e)):L("unsupported (Service Worker)")});const O=document.getElementById("online-status");let B=null;function D(){O.textContent="Aktuell",O.classList.add("online"),O.classList.remove("offline","updating")}function T(){O.textContent="Offline",O.classList.add("offline"),O.classList.remove("online","updating")}function J(t=null){B=new WebSocket(("http:"===window.location.protocol?"ws:":"wss:")+"//"+window.location.host+window.location.pathname+"api/wait-for-updates"),B.addEventListener("open",e=>{console.log("WebSocket opened",e),D(),t&&t(e.target)}),B.addEventListener("close",e=>{console.log("WebSocket closed",e),T()}),B.addEventListener("message",e=>{var t=JSON.parse(e.data);console.log("WebSocket message",t),"status"===t.type?(e=t.status)&&(e===document.getElementById("status").textContent?D():window.location.reload()):console.warn("Unknown WebSocket message type",t.type)})}function x(){O.textContent="Aktualisiere...",O.classList.add("updating"),O.classList.remove("online","offline"),B.readyState===B.OPEN?B.send(JSON.stringify({type:"get_status"})):J(e=>e.send(JSON.stringify({type:"get_status"})))}J(),window.addEventListener("focus",()=>{console.log("focus, checking for new substitutions"),x()}),window.addEventListener("online",()=>{console.log("online, checking for new substitutions"),x()}),window.addEventListener("offline",()=>{console.log("offline"),T()}),document.getElementById("themes-block").hidden=!1;const M=document.documentElement,W=document.getElementById("themes-system-default"),A=document.getElementById("themes-light"),U=document.getElementById("themes-dark");function q(e){switch(localStorage.setItem("theme",e),e){case"system-default":M.classList.remove("light","dark");break;case"light":M.classList.add("light"),M.classList.remove("dark");break;case"dark":M.classList.add("dark"),M.classList.remove("light")}}switch(localStorage.getItem("theme")){case"light":A.checked=!0;break;case"dark":U.checked=!0}W.addEventListener("change",()=>q("system-default")),A.addEventListener("change",()=>q("light")),U.addEventListener("change",()=>q("dark"));try{let e=localStorage.getItem("theme");"system-default"!==e&&e||(e="system-"+(window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light")),plausible("Features - "+s,{props:{Selection:a?(a.match(/,/g)||[]).length+1:0,Notifications:localStorage.getItem(s+"-notification-state-pa")||"unknown",Theme:e,Timetables:null}})}catch(e){console.error(e),i(e)}function P(e,t){for(var n of e)n.addEventListener("click",t),n.addEventListener("auxclick",t)}function j(e){e=e.split(",");plausible(JSON.parse(e[0]),e[1]?{props:JSON.parse(e[1])}:null)}P(document.querySelectorAll("a[data-pa]"),function(e){let t=e.target;var n="auxclick"===e.type&&2===e.which,i="click"===e.type;for(;t&&(void 0===t.tagName||"a"!==t.tagName.toLowerCase()||!t.href);)t=t.parentNode;(n||i)&&j(t.getAttribute("data-pa"));t.target||e.ctrlKey||e.metaKey||e.shiftKey||!i||(setTimeout(function(){location.href=t.href},150),e.preventDefault())}),P(document.querySelectorAll("button[data-pa]"),function(e){e.preventDefault(),j(e.target.getAttribute("data-pa")),setTimeout(function(){e.target.form.submit()},150)})}();
//# sourceMappingURL=substitutions.js.map

!function(){"use strict";function c(e,t){const n={n:e,u:self.location.toString(),d:"gawvertretung.florian-raediker.de",r:null};return t&&t.meta&&(n.m=JSON.stringify(t.meta)),t&&t.props&&(n.p=JSON.stringify(t.props)),fetch("https://plausible.io/api/event",{method:"POST",headers:{"Content-Type":"text/plain"},body:JSON.stringify(n)}).catch(e=>console.error("reporting error failed",e))}function t(e,t=null){console.error("reporting error",e,t);try{var n=e.name,o=(null==t?void 0:t.message)||e.message,r=e.description,a=e.number,s=(null==t?void 0:t.filename)||e.fileName,i=(null==t?void 0:t.lineno)||e.lineNumber,l=(null==t?void 0:t.colno)||e.columnNumber;c("JavaScript Error (Service Worker)",{props:{[(n||"Generic Error")+": "+o]:((null==t?void 0:t.stack)||e.stack)+" - "+s+":"+i+":"+l+" "+r+" "+a}})}catch(e){console.error("reporting error failed",e)}}self.addEventListener("error",e=>t(e.error,e)),self.addEventListener("unhandledrejection",e=>t(e.reason));const r="gawvertretung-v1",a=["/students/","/teachers/"],s=["/assets/style/main.css","/assets/js/substitutions.js","/assets/js/timetables.js","/assets/ferien/style.css","/assets/ferien/script.js","/favicon-32x32.png","/android-chrome-192x192.png"];self.addEventListener("install",e=>{e.waitUntil(caches.open(r).then(n=>Promise.all([Promise.all(a.map(t=>fetch(t+"?all&sw").then(e=>n.put(t,e))))])))}),self.addEventListener("activate",e=>{e.waitUntil(caches.open(r).then(n=>{n.keys().then(e=>Promise.all(e.map(e=>{var t=new URL(e.url);if(!s.includes(t.pathname)&&!a.includes(t.pathname))return console.log("cache: delete old",e),n.delete(e)})))}))}),self.addEventListener("fetch",o=>{const n=new URL(o.request.url);console.log("requested",o.request.url,n.pathname),"/"===n.pathname?o.respondWith(Response.redirect("/students/")):a.includes(n.pathname)?o.respondWith(new Promise((e,t)=>{console.log("fetching",o.request),fetch(o.request).then(t=>{console.log("fetch successful",o.request.url),e(t.clone()),caches.open(r).then(e=>e.put(n.pathname,t))},t)}).catch(()=>caches.open(r).then(e=>e.match(n.pathname,{ignoreSearch:!0}).then(e=>e||(console.log("no match for",o.request),Promise.reject("no-match")))))):s.includes(n.pathname)?o.respondWith(new Promise(n=>caches.open(r).then(t=>t.match(o.request).then(e=>e?(console.log("cache has up-to-date response for",o.request.url),void n(e)):void fetch(o.request).then(async e=>{console.log("cache is missing up-to-date response, fetching for",o.request.url),n(e.clone()),await t.delete(o.request,{ignoreSearch:!0,ignoreVary:!0}).then(e=>console.log("deleted",e,o.request.url)),console.log("putting in cache:",o.request.url),await t.put(o.request,e)}).catch(()=>{n(t.match(o.request,{ignoreSearch:!0,ignoreVary:!0}))}))))):console.log("not using SW for request")}),self.addEventListener("push",async e=>{if(e.data){var t=e.data.json();if("generic_message"===t.type)e.waitUntil(self.registration.showNotification(t.title,{body:t.body||"",icon:"android-chrome-512x512.png",badge:"monochrome-96x96.png",lang:"de",data:{type:"generic_message"}}));else{let s=t.plan_id,i=t.affected_groups_by_day;console.log("affectedGroups",i);for(var n of Object.values(i))n.groups=new Set(n.groups);let l=Date.now()/1e3;e.waitUntil(self.registration.getNotifications().then(e=>{for(var n of e)if(n.data&&n.data.plan_id===s){for(let[t,e]of Object.entries(n.data.affected_groups_by_day))console.log("expiryTime, currentTimestamp:",t,l),t>l&&(console.log("add",e.groups),t in i?(console.log("already in affectedGroups"),e.groups.forEach(e=>i[t].groups.add(e))):(console.log("new day",e),i[t]=e));n.close()}for(var t of Object.values(i))t.groups=Array.from(t.groups);let o,r;if(1===Object.keys(i).length){let e=Object.values(i)[0];o=e.name+": Neue Vertretungen",r=e.groups.join(", ")}else{o="Neue Vertretungen",r="";for(var a of Object.values(i))r+=a.name+": "+a.groups.join(", ")+"\n"}e={body:r,icon:"android-chrome-512x512.png",badge:"monochrome-96x96.png",lang:"de",vibrate:[300,100,400],data:{type:"subs_update",plan_id:s,url:new URL("/"+s+"/?source=Notification",self.location.origin).href,affected_groups_by_day:i}};self.registration.showNotification(o,e),c("Notification",{props:{[s]:"Received"}})}))}}else e.waitUntil(Promise.all([self.registration.showNotification("Neue Benachrichtigung",{icon:"android-chrome-512x512.png",badge:"monochrome-96x96.png",lang:"de"}),c("Notification",{props:{other:"Received, but without Payload"}})]))}),self.addEventListener("notificationclick",r=>{r.notification.close(),"subs_update"===r.notification.data.type&&r.waitUntil(Promise.all([self.clients.matchAll().then(function(e){var t,n=new URL(r.notification.data.url);for(t of e){var o=new URL(t.url);if(o.origin+o.pathname===n.origin+n.pathname&&"focus"in t)return t.focus()}if(self.clients.openWindow)return self.clients.openWindow(r.notification.data.url)}),self.registration.getNotifications().then(e=>{e.forEach(e=>{null!=e.data&&e.data.plan_id===r.notification.data.plan_id&&e.close()})}),c("Notification",{props:{[r.notification.data.plan_id]:"Clicked"}})]))})}();
//# sourceMappingURL=sw.js.map

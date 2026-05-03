(function(){let e=document.createElement(`link`).relList;if(e&&e.supports&&e.supports(`modulepreload`))return;for(let e of document.querySelectorAll(`link[rel="modulepreload"]`))n(e);new MutationObserver(e=>{for(let t of e)if(t.type===`childList`)for(let e of t.addedNodes)e.tagName===`LINK`&&e.rel===`modulepreload`&&n(e)}).observe(document,{childList:!0,subtree:!0});function t(e){let t={};return e.integrity&&(t.integrity=e.integrity),e.referrerPolicy&&(t.referrerPolicy=e.referrerPolicy),e.crossOrigin===`use-credentials`?t.credentials=`include`:e.crossOrigin===`anonymous`?t.credentials=`omit`:t.credentials=`same-origin`,t}function n(e){if(e.ep)return;e.ep=!0;let n=t(e);fetch(e.href,n)}})();var e=``,t=`FaceR2026Key`;function n(){return{Authorization:`Bearer ${t}`}}async function r(t,n){let r=await fetch(`${e}/api/v1/auth/login`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({username:t,password:n})});if(!r.ok){let e=await r.json().catch(()=>({detail:`Error de conexión`}));throw Error(e.detail||`Error ${r.status}`)}return r.json()}async function i(t){let r=new FormData;r.append(`file`,t,`capture.jpg`);let i=await fetch(`${e}/api/v1/documents/analyze-capture`,{method:`POST`,headers:n(),body:r});if(!i.ok)throw Error(`Analyze failed: ${i.status} ${await i.text()}`);return i.json()}async function a(t,r,i,a){let o=new FormData;o.append(`user_id`,String(t)),o.append(`country`,String(r)),o.append(`document_type`,String(i)),o.append(`file`,a,`document.jpg`);let s=await fetch(`${e}/api/v1/documents/upload-and-process`,{method:`POST`,headers:n(),body:o});if(!s.ok){let e=await s.text(),t=`Error ${s.status}`;try{t=JSON.parse(e).detail||t}catch{t=e||t}throw Error(t)}return s.json()}async function o(e,t=`environment`){let n={video:{facingMode:t,width:{ideal:1920},height:{ideal:1080}},audio:!1},r=await navigator.mediaDevices.getUserMedia(n);return e.srcObject=r,await e.play(),{video:e,stream:r,stop(){r.getTracks().forEach(e=>e.stop()),e.srcObject=null},capture(t=.92){let n=document.createElement(`canvas`);n.width=e.videoWidth,n.height=e.videoHeight;let r=n.getContext(`2d`);return r?(r.drawImage(e,0,0),s(n.toDataURL(`image/jpeg`,t))):null}}}function s(e){let t=e.split(`,`),n=t[0].match(/:(.*?);/)[1],r=atob(t[1]),i=new Uint8Array(r.length);for(let e=0;e<r.length;e++)i[e]=r.charCodeAt(e);return new Blob([i],{type:n})}async function c(e,t={}){let{maxWidth:n=1600,maxHeight:r=1200,quality:i=.82,maxSizeBytes:a=1.5*1024*1024}=t,o=e.size,s=await l(e),c=s.naturalWidth,d=s.naturalHeight,f=c,p=d;f>n&&(p=Math.round(n/f*p),f=n),p>r&&(f=Math.round(r/p*f),p=r),(f<900||p<600)&&(f=Math.max(f,c),p=Math.max(p,d));let m=document.createElement(`canvas`);m.width=f,m.height=p;let h=m.getContext(`2d`);h.imageSmoothingEnabled=!0,h.imageSmoothingQuality=`high`,h.drawImage(s,0,0,f,p);let g=i,_=await u(m,g);for(;_.size>a&&g>.5;)g-=.08,_=await u(m,g);return{blob:_,originalSize:o,compressedSize:_.size,width:f,height:p,quality:g,compressionRatio:o>0?_.size/o:1}}function l(e){return new Promise((t,n)=>{let r=new Image;r.onload=()=>{URL.revokeObjectURL(r.src),t(r)},r.onerror=()=>{URL.revokeObjectURL(r.src),n(Error(`No se pudo cargar la imagen`))},r.src=URL.createObjectURL(e)})}function u(e,t){return new Promise((n,r)=>{e.toBlob(e=>{e?n(e):r(Error(`No se pudo comprimir la imagen`))},`image/jpeg`,t)})}function d(e){return e<1024?`${e} B`:e<1024*1024?`${(e/1024).toFixed(1)} KB`:`${(e/(1024*1024)).toFixed(2)} MB`}var f={screen:`login`,country:`MX`,documentType:`INE`,userId:1,userName:``,camera:null,capturedBlob:null,capturedUrl:``,compressedBlob:null,compressionInfo:null,analysis:null,results:null,error:``},p=document.getElementById(`app`);function m(){switch(f.screen){case`login`:g();break;case`select`:_();break;case`capture`:v();break;case`review`:y();break;case`processing`:b();break;case`results`:S();break}}function h(e,t){return`
    <div class="text-center mb-8">
      <div class="flex items-center justify-center gap-3 mb-3">
        <div class="w-10 h-10 rounded-lg bg-facer-accent/20 flex items-center justify-center">
          <svg class="w-6 h-6 text-facer-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
          </svg>
        </div>
        <h1 class="text-2xl font-semibold tracking-tight">FaceR</h1>
      </div>
      <h2 class="text-lg font-medium text-facer-text">${e}</h2>
      ${t?`<p class="text-sm text-facer-text-muted mt-1">${t}</p>`:``}
    </div>
  `}function g(){p.innerHTML=`
    <div class="min-h-screen flex items-center justify-center p-4">
      <div class="w-full max-w-sm fade-in">
        <div class="text-center mb-8">
          <div class="flex items-center justify-center gap-3 mb-4">
            <div class="w-14 h-14 rounded-2xl bg-facer-accent/20 flex items-center justify-center">
              <svg class="w-8 h-8 text-facer-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
              </svg>
            </div>
          </div>
          <h1 class="text-2xl font-bold tracking-tight text-facer-text">FaceR</h1>
          <p class="text-sm text-facer-text-muted mt-1">Registro Documental</p>
        </div>
        <div class="bg-facer-surface rounded-2xl p-6 border border-facer-border shadow-xl">
          <form id="login-form" class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-facer-text-muted mb-1.5">Usuario</label>
              <input id="login-user" type="text" autocomplete="username" required
                class="w-full px-4 py-3 rounded-xl bg-facer-card border border-facer-border text-facer-text placeholder-facer-text-muted/50 focus:outline-none focus:border-facer-accent focus:ring-1 focus:ring-facer-accent/30 transition-all text-sm" 
                placeholder="Ingresa tu usuario" />
            </div>
            <div>
              <label class="block text-sm font-medium text-facer-text-muted mb-1.5">Contraseña</label>
              <input id="login-pass" type="password" autocomplete="current-password" required
                class="w-full px-4 py-3 rounded-xl bg-facer-card border border-facer-border text-facer-text placeholder-facer-text-muted/50 focus:outline-none focus:border-facer-accent focus:ring-1 focus:ring-facer-accent/30 transition-all text-sm"
                placeholder="Ingresa tu contraseña" />
            </div>
            <div id="login-error" class="hidden text-sm text-facer-error text-center py-1"></div>
            <button type="submit" id="login-btn" class="btn-primary w-full py-3 rounded-xl text-white font-medium text-sm cursor-pointer border-0 mt-2">
              Iniciar sesión
            </button>
          </form>
        </div>
        <p class="text-center text-xs text-facer-text-muted/50 mt-6">FaceR Registro Documental v2.0</p>
      </div>
    </div>
  `;let e=document.getElementById(`login-form`),t=document.getElementById(`login-error`),n=document.getElementById(`login-btn`);e.addEventListener(`submit`,async e=>{e.preventDefault();let i=document.getElementById(`login-user`).value.trim(),a=document.getElementById(`login-pass`).value;if(!i||!a){t.textContent=`Ingresa usuario y contraseña`,t.classList.remove(`hidden`);return}n.disabled=!0,n.textContent=`Verificando...`,t.classList.add(`hidden`);try{let e=await r(i,a);f.userId=e.user_id,f.userName=e.full_name,f.screen=`select`,m()}catch(e){t.textContent=e.message||`Error de autenticación`,t.classList.remove(`hidden`),n.disabled=!1,n.textContent=`Iniciar sesión`}})}function _(){let e=[{country:`MX`,type:`INE`,label:`INE / IFE`,icon:`🇲🇽`,desc:`Credencial para votar (México)`},{country:`MX`,type:`PASSPORT_MX`,label:`Pasaporte MX`,icon:`🇲🇽`,desc:`Pasaporte mexicano`},{country:`CO`,type:`CEDULA_CO`,label:`Cédula CO`,icon:`🇨🇴`,desc:`Cédula de ciudadanía (Colombia)`},{country:`CO`,type:`PASSPORT_CO`,label:`Pasaporte CO`,icon:`🇨🇴`,desc:`Pasaporte colombiano`}];p.innerHTML=`
    <div class="min-h-screen flex items-center justify-center p-4">
      <div class="w-full max-w-md fade-in">
        ${h(`Registro Documental`,`Hola, ${f.userName}. Selecciona el tipo de documento.`)}
        <div class="space-y-3">
          ${e.map((e,t)=>`
            <button data-idx="${t}" class="doc-type-btn w-full bg-facer-surface hover:bg-facer-card border border-facer-border hover:border-facer-accent/50 rounded-xl p-4 flex items-center gap-4 transition-all cursor-pointer text-left">
              <span class="text-3xl">${e.icon}</span>
              <div class="flex-1 min-w-0">
                <div class="font-medium text-facer-text text-sm">${e.label}</div>
                <div class="text-xs text-facer-text-muted mt-0.5">${e.desc}</div>
              </div>
              <svg class="w-5 h-5 text-facer-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
              </svg>
            </button>
          `).join(``)}
        </div>
        <button id="btn-logout" class="btn-secondary w-full py-2.5 rounded-xl text-facer-text-muted font-medium text-sm cursor-pointer mt-4">
          Cerrar sesión
        </button>
      </div>
    </div>
  `,document.querySelectorAll(`.doc-type-btn`).forEach(t=>{t.addEventListener(`click`,()=>{let n=e[parseInt(t.dataset.idx,10)];f.country=n.country,f.documentType=n.type,f.screen=`capture`,m()})}),document.getElementById(`btn-logout`).addEventListener(`click`,()=>{f.userId=0,f.userName=``,f.screen=`login`,m()})}function v(){p.innerHTML=`
    <div class="min-h-screen flex flex-col items-center justify-center p-4">
      <div class="w-full max-w-lg fade-in">
        ${h(`Captura de Documento`,`Coloca tu ${f.documentType===`INE`?`INE / IFE`:f.documentType===`PASSPORT_MX`?`Pasaporte MX`:f.documentType===`CEDULA_CO`?`Cédula CO`:`Pasaporte CO`} dentro del marco`)}
        <div class="relative bg-black rounded-2xl overflow-hidden shadow-2xl">
          <video id="cam-video" autoplay playsinline muted class="w-full aspect-[4/3] object-cover"></video>
          <!-- Guide overlay -->
          <div class="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div class="guide-overlay relative w-[85%] h-[70%] border-2 border-facer-accent/60 rounded-xl">
              <div class="absolute -top-px -left-px w-6 h-6 border-t-3 border-l-3 border-facer-accent rounded-tl-lg"></div>
              <div class="absolute -top-px -right-px w-6 h-6 border-t-3 border-r-3 border-facer-accent rounded-tr-lg"></div>
              <div class="absolute -bottom-px -left-px w-6 h-6 border-b-3 border-l-3 border-facer-accent rounded-bl-lg"></div>
              <div class="absolute -bottom-px -right-px w-6 h-6 border-b-3 border-r-3 border-facer-accent rounded-br-lg"></div>
            </div>
          </div>
          <!-- Status bar -->
          <div class="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4">
            <p id="cam-hint" class="text-center text-sm text-white/80">Iniciando cámara...</p>
          </div>
        </div>
        <div class="flex gap-3 mt-4">
          <button id="cam-back" class="btn-secondary flex-1 py-3 rounded-xl text-facer-text-muted font-medium text-sm cursor-pointer">
            Cancelar
          </button>
          <button id="cam-capture" disabled class="btn-primary flex-1 py-3 rounded-xl text-white font-medium text-sm cursor-pointer border-0 disabled:opacity-40 disabled:cursor-not-allowed">
            Capturar
          </button>
        </div>
      </div>
    </div>
  `;let e=document.getElementById(`cam-video`),t=document.getElementById(`cam-hint`),n=document.getElementById(`cam-capture`);o(e,`environment`).then(e=>{f.camera=e,t.textContent=`Alinea el documento dentro del marco y presiona Capturar`,n.disabled=!1}).catch(e=>{t.innerHTML=`<span class="text-red-400">Error: ${e.message}</span>`}),n.addEventListener(`click`,()=>{if(!f.camera)return;let e=f.camera.capture(.92);e&&(f.capturedBlob=e,f.capturedUrl=URL.createObjectURL(e),f.camera.stop(),f.camera=null,f.screen=`review`,m())}),document.getElementById(`cam-back`).addEventListener(`click`,()=>{f.camera&&=(f.camera.stop(),null),f.screen=`select`,m()})}function y(){p.innerHTML=`
    <div class="min-h-screen flex items-center justify-center p-4">
      <div class="w-full max-w-lg fade-in">
        ${h(`Revisar Captura`,`Verifica que el documento se vea claro y completo`)}
        <div class="bg-facer-surface rounded-2xl overflow-hidden border border-facer-border shadow-xl">
          <img src="${f.capturedUrl}" alt="Documento capturado" class="w-full aspect-[4/3] object-cover" />
          <div id="quality-info" class="p-4">
            <div class="flex items-center gap-2 text-sm text-facer-text-muted">
              <svg class="w-4 h-4 animate-spin text-facer-accent" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
              </svg>
              Preparando imagen...
            </div>
          </div>
        </div>
        <div class="flex gap-3 mt-4">
          <button id="rev-retake" class="btn-secondary flex-1 py-3 rounded-xl text-facer-text-muted font-medium text-sm cursor-pointer">
            Volver a capturar
          </button>
          <button id="rev-send" disabled class="btn-primary flex-1 py-3 rounded-xl text-white font-medium text-sm cursor-pointer border-0 disabled:opacity-40 disabled:cursor-not-allowed">
            Enviar documento
          </button>
        </div>
      </div>
    </div>
  `;let e=document.getElementById(`quality-info`),t=document.getElementById(`rev-send`);if(f.capturedBlob){let n=i(f.capturedBlob).catch(()=>null),r=c(f.capturedBlob,{maxWidth:1600,maxHeight:1200,quality:.82,maxSizeBytes:1.5*1024*1024});Promise.all([n,r]).then(([n,r])=>{if(f.compressionInfo=r,f.compressedBlob=r.blob,n){f.analysis=n;let t=Math.round(n.quality_score*100);e.innerHTML=`
            <div class="space-y-3">
              <div class="flex items-center justify-between">
                <span class="text-sm text-facer-text-muted">Calidad de imagen</span>
                <span class="flex items-center gap-1.5 text-sm font-medium ${n.meets_minimum?`text-facer-success`:`text-facer-warning`}">
                  ${n.meets_minimum?`<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>`:`<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>`}
                  ${t}%
                </span>
              </div>
              <div class="w-full h-2 bg-facer-card rounded-full overflow-hidden">
                <div class="h-full rounded-full transition-all duration-500 ${n.meets_minimum?`bg-facer-success`:`bg-facer-warning`}" style="width: ${t}%"></div>
              </div>
              <div class="flex items-center justify-between bg-facer-card rounded-lg p-2">
                <span class="text-xs text-facer-text-muted">Compresión</span>
                <span class="text-xs font-medium text-facer-accent">
                  ${d(r.originalSize)} → ${d(r.compressedSize)}
                  (${Math.round((1-r.compressionRatio)*100)}% reducido)
                </span>
              </div>
              ${n.recapture_recommended?`<p class="text-xs text-facer-warning text-center">Se recomienda recapturar para mejores resultados</p>`:``}
            </div>
          `}else e.innerHTML=`
            <div class="space-y-2">
              <div class="flex items-center gap-2 text-sm text-facer-success">
                <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>
                Imagen lista para enviar
              </div>
              <div class="flex items-center justify-between bg-facer-card rounded-lg p-2">
                <span class="text-xs text-facer-text-muted">Tamaño</span>
                <span class="text-xs font-medium text-facer-accent">
                  ${d(r.compressedSize)}
                </span>
              </div>
            </div>
          `;t.disabled=!1}).catch(()=>{e.innerHTML=`<p class="text-sm text-facer-warning">No se pudo preparar la imagen. Puedes enviar de todos modos.</p>`,f.compressedBlob=f.capturedBlob,t.disabled=!1})}document.getElementById(`rev-retake`).addEventListener(`click`,()=>{f.capturedBlob=null,f.capturedUrl=``,f.compressedBlob=null,f.compressionInfo=null,f.analysis=null,f.screen=`capture`,m()}),t.addEventListener(`click`,async()=>{f.capturedBlob&&(t.disabled=!0,t.textContent=`Enviando...`,f.screen=`processing`,m())})}function b(){p.innerHTML=`
    <div class="min-h-screen flex items-center justify-center p-4">
      <div class="w-full max-w-md fade-in text-center">
        ${h(`Procesando Documento`)}
        <div class="bg-facer-surface rounded-2xl p-8 border border-facer-border shadow-xl">
          <div class="mb-6">
            <svg class="w-16 h-16 mx-auto text-facer-accent animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
            </svg>
          </div>
          <div id="proc-steps" class="space-y-3 text-left">
            <div id="step-upload" class="flex items-center gap-3 text-sm">
              <div class="w-6 h-6 rounded-full bg-facer-accent/20 flex items-center justify-center shrink-0">
                <svg class="w-3.5 h-3.5 text-facer-accent animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
              </div>
              <span class="text-facer-text-muted">Enviando imagen${f.compressionInfo?` (${d(f.compressionInfo.compressedSize)})`:``}...</span>
            </div>
            <div id="step-ocr" class="flex items-center gap-3 text-sm opacity-40">
              <div class="w-6 h-6 rounded-full bg-facer-card flex items-center justify-center shrink-0">
                <span class="w-2 h-2 rounded-full bg-facer-text-muted/30"></span>
              </div>
              <span class="text-facer-text-muted">Extrayendo texto (OCR)...</span>
            </div>
            <div id="step-parse" class="flex items-center gap-3 text-sm opacity-40">
              <div class="w-6 h-6 rounded-full bg-facer-card flex items-center justify-center shrink-0">
                <span class="w-2 h-2 rounded-full bg-facer-text-muted/30"></span>
              </div>
              <span class="text-facer-text-muted">Analizando campos...</span>
            </div>
          </div>
          <div id="proc-error" class="hidden mt-4 text-sm text-facer-error"></div>
        </div>
      </div>
    </div>
  `,x()}async function x(){let e=document.getElementById(`step-upload`),t=document.getElementById(`step-ocr`),n=document.getElementById(`step-parse`),r=document.getElementById(`proc-error`),i=`<div class="w-6 h-6 rounded-full bg-facer-success/20 flex items-center justify-center shrink-0"><svg class="w-3.5 h-3.5 text-facer-success" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/></svg></div>`,o=`<div class="w-6 h-6 rounded-full bg-facer-accent/20 flex items-center justify-center shrink-0"><svg class="w-3.5 h-3.5 text-facer-accent animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg></div>`;try{let r=f.compressedBlob||f.capturedBlob;e.innerHTML=`${o}<span class="text-facer-text-muted">Enviando y procesando...</span>`,t.classList.remove(`opacity-40`),t.innerHTML=`${o}<span class="text-facer-text-muted">Extrayendo texto (OCR)...</span>`;let s=await a(f.userId,f.country,f.documentType,r);e.innerHTML=`${i}<span class="text-facer-success">Imagen enviada</span>`,t.innerHTML=`${i}<span class="text-facer-success">Texto extraído</span>`,n.classList.remove(`opacity-40`),n.innerHTML=`${i}<span class="text-facer-success">Campos analizados</span>`,f.results=s,setTimeout(()=>{f.screen=`results`,m()},800)}catch(e){let t=e.message||``,n=`Ocurrió un error al procesar el documento.`;t.includes(`foto más clara`)||t.includes(`OCR`)?n=`No se pudo leer el documento. Intenta con una foto más clara y bien iluminada.`:t.includes(`Usuario no encontrado`)?n=`Tu sesión expiró. Inicia sesión de nuevo.`:t.includes(`País`)||t.includes(`inválido`)?n=`Tipo de documento no válido. Selecciona otro.`:(t.includes(`fetch`)||t.includes(`network`)||t.includes(`Failed`))&&(n=`Error de conexión. Verifica tu internet e intenta de nuevo.`),r.classList.remove(`hidden`),r.innerHTML=`
      <div class="bg-facer-error/10 border border-facer-error/30 rounded-xl p-4 mb-3">
        <div class="flex items-center gap-2 mb-2">
          <svg class="w-5 h-5 text-facer-error shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/>
          </svg>
          <span class="font-medium text-facer-error">Error</span>
        </div>
        <p class="text-sm text-facer-text">${n}</p>
      </div>
      <div class="flex gap-2 justify-center">
        <button id="proc-retry" class="btn-primary px-5 py-2.5 rounded-xl text-white text-sm cursor-pointer border-0">Reintentar</button>
        <button id="proc-back" class="btn-secondary px-5 py-2.5 rounded-xl text-sm cursor-pointer">Volver</button>
      </div>
    `,document.getElementById(`proc-retry`)?.addEventListener(`click`,()=>{f.screen=`processing`,m()}),document.getElementById(`proc-back`)?.addEventListener(`click`,()=>{f.screen=`select`,m()})}}function S(){let e=f.results;if(!e)return;let t=e.extracted_fields||{},n=t.nombre_completo||t.nombre||t.curp?{nombre:`Nombre(s)`,apellido_paterno:`Apellido paterno`,apellido_materno:`Apellido materno`,nombre_completo:`Nombre completo`,nacionalidad:`Nacionalidad`,fecha_nacimiento:`Fecha de nacimiento`,curp:`CURP`,domicilio:`Domicilio`,sexo:`Sexo`,clave_elector:`Clave de elector`,seccion:`Sección`}:{full_name:`Nombre completo`,first_name:`Nombre(s)`,last_name:`Apellido(s)`,birth_date:`Fecha de nacimiento`,sex:`Sexo`,national_id:`Clave de elector`,document_number:`Número de documento`,curp:`CURP`,nationality:`Nacionalidad`,issue_date:`Fecha de emisión`,expiration_date:`Fecha de expiración`},r={valid:`bg-facer-success/20 text-facer-success`,pending:`bg-facer-warning/20 text-facer-warning`,needs_review:`bg-facer-warning/20 text-facer-warning`,invalid:`bg-facer-error/20 text-facer-error`},i={valid:`Válido`,pending:`Pendiente`,needs_review:`Requiere revisión`,invalid:`Inválido`},a=r[e.validation_status]||r.pending,o=i[e.validation_status]||e.validation_status,s=Object.entries(n).filter(([e])=>t[e]!==null&&t[e]!==void 0&&t[e]!==``).map(([e,n])=>`
      <div class="flex justify-between items-start py-2.5 border-b border-facer-border/50 last:border-0">
        <span class="text-sm text-facer-text-muted">${n}</span>
        <span class="text-sm font-medium text-facer-text text-right max-w-[60%]">${t[e]}</span>
      </div>
    `).join(``);p.innerHTML=`
    <div class="min-h-screen flex items-center justify-center p-4">
      <div class="w-full max-w-md fade-in">
        ${h(`Resultados`,`Datos extraídos del documento`)}
        
        <!-- Status badge -->
        <div class="flex gap-2 justify-center mb-4">
          <span class="px-3 py-1 rounded-full text-xs font-medium ${a}">${o}</span>
          ${e.extraction_confidence===null?``:`<span class="px-3 py-1 rounded-full text-xs font-medium bg-facer-accent/20 text-facer-accent">Confianza: ${Math.round(e.extraction_confidence*100)}%</span>`}
        </div>

        <!-- Extracted fields -->
        <div class="bg-facer-surface rounded-2xl border border-facer-border shadow-xl overflow-hidden">
          <div class="p-4 border-b border-facer-border">
            <h3 class="text-sm font-medium text-facer-text">Campos extraídos</h3>
          </div>
          <div class="p-4">
            ${s||`<p class="text-sm text-facer-text-muted text-center py-4">No se extrajeron campos</p>`}
          </div>
        </div>

        <!-- Actions -->
        <div class="flex gap-3 mt-4">
          <button id="res-new" class="btn-primary flex-1 py-3 rounded-xl text-white font-medium text-sm cursor-pointer border-0">
            Nuevo documento
          </button>
        </div>
      </div>
    </div>
  `,document.getElementById(`res-new`).addEventListener(`click`,()=>{f.capturedBlob=null,f.capturedUrl=``,f.compressedBlob=null,f.compressionInfo=null,f.analysis=null,f.results=null,f.screen=`select`,m()})}m();
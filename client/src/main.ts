import "./style.css";
import {
  login,
  analyzeCapture,
  uploadAndProcess,
  type ProcessResponse,
  type CaptureAnalysis,
  type LoginResponse,
} from "./api";
import { startCamera, type CameraInstance } from "./camera";
import { compressImage, formatBytes, type CompressResult } from "./compress";

// ── State ──────────────────────────────────────────────
interface AppState {
  screen: "login" | "select" | "capture" | "review" | "processing" | "results";
  country: string;
  documentType: string;
  userId: number;
  userName: string;
  camera: CameraInstance | null;
  capturedBlob: Blob | null;
  capturedUrl: string;
  compressedBlob: Blob | null;
  compressionInfo: CompressResult | null;
  analysis: CaptureAnalysis | null;
  results: ProcessResponse | null;
  error: string;
}

const state: AppState = {
  screen: "login",
  country: "MX",
  documentType: "INE",
  userId: 1,
  userName: "",
  camera: null,
  capturedBlob: null,
  capturedUrl: "",
  compressedBlob: null,
  compressionInfo: null,
  analysis: null,
  results: null,
  error: "",
};

const app = document.getElementById("app")!;

// ── Render Router ──────────────────────────────────────
function render() {
  switch (state.screen) {
    case "login":
      renderLogin();
      break;
    case "select":
      renderSelect();
      break;
    case "capture":
      renderCapture();
      break;
    case "review":
      renderReview();
      break;
    case "processing":
      renderProcessing();
      break;
    case "results":
      renderResults();
      break;
  }
}

// ── Header Component ───────────────────────────────────
function headerHTML(title: string, subtitle?: string): string {
  return `
    <div class="text-center mb-8">
      <div class="flex items-center justify-center gap-3 mb-3">
        <div class="w-10 h-10 rounded-lg bg-facer-accent/20 flex items-center justify-center">
          <svg class="w-6 h-6 text-facer-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
          </svg>
        </div>
        <h1 class="text-2xl font-semibold tracking-tight">FaceR</h1>
      </div>
      <h2 class="text-lg font-medium text-facer-text">${title}</h2>
      ${subtitle ? `<p class="text-sm text-facer-text-muted mt-1">${subtitle}</p>` : ""}
    </div>
  `;
}

// ── Screen: Login ─────────────────────────────────────
function renderLogin() {
  app.innerHTML = `
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
  `;

  const form = document.getElementById("login-form") as HTMLFormElement;
  const errorEl = document.getElementById("login-error")!;
  const btn = document.getElementById("login-btn") as HTMLButtonElement;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const username = (document.getElementById("login-user") as HTMLInputElement).value.trim();
    const password = (document.getElementById("login-pass") as HTMLInputElement).value;

    if (!username || !password) {
      errorEl.textContent = "Ingresa usuario y contraseña";
      errorEl.classList.remove("hidden");
      return;
    }

    btn.disabled = true;
    btn.textContent = "Verificando...";
    errorEl.classList.add("hidden");

    try {
      const response: LoginResponse = await login(username, password);
      state.userId = response.user_id;
      state.userName = response.full_name;
      state.screen = "select";
      render();
    } catch (err: any) {
      errorEl.textContent = err.message || "Error de autenticación";
      errorEl.classList.remove("hidden");
      btn.disabled = false;
      btn.textContent = "Iniciar sesión";
    }
  });
}

// ── Screen: Select Document Type ───────────────────────
function renderSelect() {
  const docTypes: { country: string; type: string; label: string; icon: string; desc: string }[] = [
    { country: "MX", type: "INE", label: "INE / IFE", icon: "🇲🇽", desc: "Credencial para votar (México)" },
    { country: "MX", type: "PASSPORT_MX", label: "Pasaporte MX", icon: "🇲🇽", desc: "Pasaporte mexicano" },
    { country: "CO", type: "CEDULA_CO", label: "Cédula CO", icon: "🇨🇴", desc: "Cédula de ciudadanía (Colombia)" },
    { country: "CO", type: "PASSPORT_CO", label: "Pasaporte CO", icon: "🇨🇴", desc: "Pasaporte colombiano" },
  ];

  app.innerHTML = `
    <div class="min-h-screen flex items-center justify-center p-4">
      <div class="w-full max-w-md fade-in">
        ${headerHTML("Registro Documental", `Hola, ${state.userName}. Selecciona el tipo de documento.`)}
        <div class="space-y-3">
          ${docTypes
            .map(
              (d, i) => `
            <button data-idx="${i}" class="doc-type-btn w-full bg-facer-surface hover:bg-facer-card border border-facer-border hover:border-facer-accent/50 rounded-xl p-4 flex items-center gap-4 transition-all cursor-pointer text-left">
              <span class="text-3xl">${d.icon}</span>
              <div class="flex-1 min-w-0">
                <div class="font-medium text-facer-text text-sm">${d.label}</div>
                <div class="text-xs text-facer-text-muted mt-0.5">${d.desc}</div>
              </div>
              <svg class="w-5 h-5 text-facer-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
              </svg>
            </button>
          `,
            )
            .join("")}
        </div>
        <button id="btn-logout" class="btn-secondary w-full py-2.5 rounded-xl text-facer-text-muted font-medium text-sm cursor-pointer mt-4">
          Cerrar sesión
        </button>
      </div>
    </div>
  `;

  document.querySelectorAll(".doc-type-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const idx = parseInt((btn as HTMLElement).dataset.idx!, 10);
      const d = docTypes[idx];
      state.country = d.country;
      state.documentType = d.type;
      state.screen = "capture";
      render();
    });
  });

  document.getElementById("btn-logout")!.addEventListener("click", () => {
    state.userId = 0;
    state.userName = "";
    state.screen = "login";
    render();
  });
}

// ── Screen: Camera Capture ─────────────────────────────
function renderCapture() {
  const docLabel =
    state.documentType === "INE"
      ? "INE / IFE"
      : state.documentType === "PASSPORT_MX"
        ? "Pasaporte MX"
        : state.documentType === "CEDULA_CO"
          ? "Cédula CO"
          : "Pasaporte CO";

  app.innerHTML = `
    <div class="min-h-screen flex flex-col items-center justify-center p-4">
      <div class="w-full max-w-lg fade-in">
        ${headerHTML("Captura de Documento", `Coloca tu ${docLabel} dentro del marco`)}
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
  `;

  const video = document.getElementById("cam-video") as HTMLVideoElement;
  const hint = document.getElementById("cam-hint")!;
  const captureBtn = document.getElementById("cam-capture") as HTMLButtonElement;

  startCamera(video, "environment")
    .then((cam) => {
      state.camera = cam;
      hint.textContent = "Alinea el documento dentro del marco y presiona Capturar";
      captureBtn.disabled = false;
    })
    .catch((err) => {
      hint.innerHTML = `<span class="text-red-400">Error: ${err.message}</span>`;
    });

  captureBtn.addEventListener("click", () => {
    if (!state.camera) return;
    const blob = state.camera.capture(0.92);
    if (!blob) return;
    state.capturedBlob = blob;
    state.capturedUrl = URL.createObjectURL(blob);
    state.camera.stop();
    state.camera = null;
    state.screen = "review";
    render();
  });

  document.getElementById("cam-back")!.addEventListener("click", () => {
    if (state.camera) {
      state.camera.stop();
      state.camera = null;
    }
    state.screen = "select";
    render();
  });
}

// ── Screen: Review Capture ─────────────────────────────
function renderReview() {
  app.innerHTML = `
    <div class="min-h-screen flex items-center justify-center p-4">
      <div class="w-full max-w-lg fade-in">
        ${headerHTML("Revisar Captura", "Verifica que el documento se vea claro y completo")}
        <div class="bg-facer-surface rounded-2xl overflow-hidden border border-facer-border shadow-xl">
          <img src="${state.capturedUrl}" alt="Documento capturado" class="w-full aspect-[4/3] object-cover" />
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
  `;

  const qualityEl = document.getElementById("quality-info")!;
  const sendBtn = document.getElementById("rev-send") as HTMLButtonElement;

  if (state.capturedBlob) {
    // Run analysis and compression in parallel
    const analysisPromise = analyzeCapture(state.capturedBlob).catch(() => null);
    const compressionPromise = compressImage(state.capturedBlob, {
      maxWidth: 1600,
      maxHeight: 1200,
      quality: 0.82,
      maxSizeBytes: 1.5 * 1024 * 1024,
    });

    Promise.all([analysisPromise, compressionPromise])
      .then(([analysis, compressionResult]) => {
        state.compressionInfo = compressionResult;
        state.compressedBlob = compressionResult.blob;

        if (analysis) {
          state.analysis = analysis;
          const scorePercent = Math.round(analysis.quality_score * 100);
          const scoreColor = analysis.meets_minimum ? "text-facer-success" : "text-facer-warning";
          const scoreIcon = analysis.meets_minimum
            ? `<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>`
            : `<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>`;

          qualityEl.innerHTML = `
            <div class="space-y-3">
              <div class="flex items-center justify-between">
                <span class="text-sm text-facer-text-muted">Calidad de imagen</span>
                <span class="flex items-center gap-1.5 text-sm font-medium ${scoreColor}">
                  ${scoreIcon}
                  ${scorePercent}%
                </span>
              </div>
              <div class="w-full h-2 bg-facer-card rounded-full overflow-hidden">
                <div class="h-full rounded-full transition-all duration-500 ${analysis.meets_minimum ? "bg-facer-success" : "bg-facer-warning"}" style="width: ${scorePercent}%"></div>
              </div>
              <div class="flex items-center justify-between bg-facer-card rounded-lg p-2">
                <span class="text-xs text-facer-text-muted">Compresión</span>
                <span class="text-xs font-medium text-facer-accent">
                  ${formatBytes(compressionResult.originalSize)} → ${formatBytes(compressionResult.compressedSize)}
                  (${Math.round((1 - compressionResult.compressionRatio) * 100)}% reducido)
                </span>
              </div>
              ${analysis.recapture_recommended ? `<p class="text-xs text-facer-warning text-center">Se recomienda recapturar para mejores resultados</p>` : ""}
            </div>
          `;
        } else {
          // Analysis failed but compression succeeded - still allow sending
          qualityEl.innerHTML = `
            <div class="space-y-2">
              <div class="flex items-center gap-2 text-sm text-facer-success">
                <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>
                Imagen lista para enviar
              </div>
              <div class="flex items-center justify-between bg-facer-card rounded-lg p-2">
                <span class="text-xs text-facer-text-muted">Tamaño</span>
                <span class="text-xs font-medium text-facer-accent">
                  ${formatBytes(compressionResult.compressedSize)}
                </span>
              </div>
            </div>
          `;
        }
        sendBtn.disabled = false;
      })
      .catch(() => {
        qualityEl.innerHTML = `<p class="text-sm text-facer-warning">No se pudo preparar la imagen. Puedes enviar de todos modos.</p>`;
        // Still allow sending with original blob
        state.compressedBlob = state.capturedBlob;
        sendBtn.disabled = false;
      });
  }

  document.getElementById("rev-retake")!.addEventListener("click", () => {
    state.capturedBlob = null;
    state.capturedUrl = "";
    state.compressedBlob = null;
    state.compressionInfo = null;
    state.analysis = null;
    state.screen = "capture";
    render();
  });

  sendBtn.addEventListener("click", async () => {
    if (!state.capturedBlob) return;
    sendBtn.disabled = true;
    sendBtn.textContent = "Enviando...";
    state.screen = "processing";
    render();
  });
}

// ── Screen: Processing ─────────────────────────────────
function renderProcessing() {
  app.innerHTML = `
    <div class="min-h-screen flex items-center justify-center p-4">
      <div class="w-full max-w-md fade-in text-center">
        ${headerHTML("Procesando Documento")}
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
              <span class="text-facer-text-muted">Enviando imagen${state.compressionInfo ? ` (${formatBytes(state.compressionInfo.compressedSize)})` : ""}...</span>
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
  `;

  runProcessing();
}

async function runProcessing() {
  const stepUpload = document.getElementById("step-upload")!;
  const stepOcr = document.getElementById("step-ocr")!;
  const stepParse = document.getElementById("step-parse")!;
  const errorEl = document.getElementById("proc-error")!;

  const checkIcon = `<div class="w-6 h-6 rounded-full bg-facer-success/20 flex items-center justify-center shrink-0"><svg class="w-3.5 h-3.5 text-facer-success" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/></svg></div>`;
  const spinIcon = `<div class="w-6 h-6 rounded-full bg-facer-accent/20 flex items-center justify-center shrink-0"><svg class="w-3.5 h-3.5 text-facer-accent animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg></div>`;

  try {
    // Use combined upload-and-process endpoint
    const blobToUpload = state.compressedBlob || state.capturedBlob!;

    // Simulate step progression for UX
    stepUpload.innerHTML = `${spinIcon}<span class="text-facer-text-muted">Enviando y procesando...</span>`;
    stepOcr.classList.remove("opacity-40");
    stepOcr.innerHTML = `${spinIcon}<span class="text-facer-text-muted">Extrayendo texto (OCR)...</span>`;

    const processRes = await uploadAndProcess(state.userId, state.country, state.documentType, blobToUpload);

    // All steps complete
    stepUpload.innerHTML = `${checkIcon}<span class="text-facer-success">Imagen enviada</span>`;
    stepOcr.innerHTML = `${checkIcon}<span class="text-facer-success">Texto extraído</span>`;
    stepParse.classList.remove("opacity-40");
    stepParse.innerHTML = `${checkIcon}<span class="text-facer-success">Campos analizados</span>`;

    state.results = processRes;
    setTimeout(() => {
      state.screen = "results";
      render();
    }, 800);
  } catch (err: any) {
    // Show user-friendly error, never raw SQL or technical details
    const rawMsg: string = err.message || "";
    let friendlyMsg = "Ocurrió un error al procesar el documento.";
    if (rawMsg.includes("foto más clara") || rawMsg.includes("OCR")) {
      friendlyMsg = "No se pudo leer el documento. Intenta con una foto más clara y bien iluminada.";
    } else if (rawMsg.includes("Usuario no encontrado")) {
      friendlyMsg = "Tu sesión expiró. Inicia sesión de nuevo.";
    } else if (rawMsg.includes("País") || rawMsg.includes("inválido")) {
      friendlyMsg = "Tipo de documento no válido. Selecciona otro.";
    } else if (rawMsg.includes("fetch") || rawMsg.includes("network") || rawMsg.includes("Failed")) {
      friendlyMsg = "Error de conexión. Verifica tu internet e intenta de nuevo.";
    }
    errorEl.classList.remove("hidden");
    errorEl.innerHTML = `
      <div class="bg-facer-error/10 border border-facer-error/30 rounded-xl p-4 mb-3">
        <div class="flex items-center gap-2 mb-2">
          <svg class="w-5 h-5 text-facer-error shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/>
          </svg>
          <span class="font-medium text-facer-error">Error</span>
        </div>
        <p class="text-sm text-facer-text">${friendlyMsg}</p>
      </div>
      <div class="flex gap-2 justify-center">
        <button id="proc-retry" class="btn-primary px-5 py-2.5 rounded-xl text-white text-sm cursor-pointer border-0">Reintentar</button>
        <button id="proc-back" class="btn-secondary px-5 py-2.5 rounded-xl text-sm cursor-pointer">Volver</button>
      </div>
    `;
    document.getElementById("proc-retry")?.addEventListener("click", () => {
      state.screen = "processing";
      render();
    });
    document.getElementById("proc-back")?.addEventListener("click", () => {
      state.screen = "select";
      render();
    });
  }
}

// ── Screen: Results ────────────────────────────────────
function renderResults() {
  const r = state.results;
  if (!r) return;

  const fields = r.extracted_fields || {};
  const nombreCompleto = fields.nombre_completo || fields.full_name || "";

  app.innerHTML = `
    <div class="min-h-screen flex items-center justify-center p-4">
      <div class="w-full max-w-md fade-in">
        ${headerHTML("Documento Validado")}
        
        <!-- Success indicator -->
        <div class="flex justify-center mb-6">
          <div class="w-20 h-20 rounded-full bg-facer-success/20 flex items-center justify-center">
            <svg class="w-10 h-10 text-facer-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
            </svg>
          </div>
        </div>

        <!-- Validation message -->
        <div class="bg-facer-surface rounded-2xl border border-facer-border shadow-xl overflow-hidden">
          <div class="p-6 text-center">
            <p class="text-lg font-semibold text-facer-text mb-2">Tu documento ha sido validado</p>
            ${nombreCompleto ? `
              <div class="mt-4 pt-4 border-t border-facer-border/50">
                <p class="text-xs text-facer-text-muted mb-1">Nombre registrado</p>
                <p class="text-base font-medium text-facer-text">${nombreCompleto}</p>
              </div>
            ` : ""}
          </div>
        </div>

        <!-- Actions -->
        <div class="flex gap-3 mt-6">
          <button id="res-new" class="btn-primary flex-1 py-3 rounded-xl text-white font-medium text-sm cursor-pointer border-0">
            Nuevo documento
          </button>
        </div>
      </div>
    </div>
  `;

  document.getElementById("res-new")!.addEventListener("click", () => {
    state.capturedBlob = null;
    state.capturedUrl = "";
    state.compressedBlob = null;
    state.compressionInfo = null;
    state.analysis = null;
    state.results = null;
    state.screen = "select";
    render();
  });
}

// ── Boot ───────────────────────────────────────────────
render();

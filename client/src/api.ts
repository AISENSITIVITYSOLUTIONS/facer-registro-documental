// API client for facer-registro-documental
// Configuration is hardcoded - no user input needed

const API_BASE_URL = "https://registro-documental-344497085765.us-central1.run.app";
const API_KEY = "FaceR2026Key";

function headers(): HeadersInit {
  return {
    Authorization: `Bearer ${API_KEY}`,
  };
}

// ── Auth ──────────────────────────────────────────────────

export interface LoginResponse {
  success: boolean;
  user_id: number;
  full_name: string;
  role: string;
  message: string;
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({ detail: "Error de conexión" }));
    throw new Error(data.detail || `Error ${res.status}`);
  }
  return res.json();
}

// ── Documents ─────────────────────────────────────────────

export interface CaptureAnalysis {
  file_size_bytes: number;
  width: number;
  height: number;
  brightness: number;
  contrast: number;
  sharpness: number;
  glare_score: number;
  quality_score: number;
  meets_minimum: boolean;
  recapture_recommended: boolean;
  recommended_action: string;
  preprocessing_enabled: boolean;
}

export interface ProcessResponse {
  id: number;
  uuid: string;
  status: string;
  validation_status: string;
  comparison_status: string | null;
  comparison_score: number | null;
  extraction_confidence: number | null;
  capture_quality_score: number | null;
  extracted_fields: Record<string, string | null>;
}

export async function analyzeCapture(file: Blob): Promise<CaptureAnalysis> {
  const form = new FormData();
  form.append("file", file, "capture.jpg");
  const res = await fetch(`${API_BASE_URL}/api/v1/documents/analyze-capture`, {
    method: "POST",
    headers: headers(),
    body: form,
  });
  if (!res.ok) throw new Error(`Analyze failed: ${res.status} ${await res.text()}`);
  return res.json();
}

/**
 * Combined upload + OCR + parse in a single request.
 * This is the main endpoint - avoids ephemeral storage issues on Cloud Run.
 */
export async function uploadAndProcess(
  userId: number,
  country: string,
  documentType: string,
  file: Blob,
): Promise<ProcessResponse> {
  const form = new FormData();
  form.append("user_id", String(userId));
  form.append("country", String(country));
  form.append("document_type", String(documentType));
  form.append("file", file, "document.jpg");
  const res = await fetch(`${API_BASE_URL}/api/v1/documents/upload-and-process`, {
    method: "POST",
    headers: headers(),
    body: form,
  });
  if (!res.ok) {
    const errorText = await res.text();
    let detail = `Error ${res.status}`;
    try {
      const errorJson = JSON.parse(errorText);
      detail = errorJson.detail || detail;
    } catch {
      detail = errorText || detail;
    }
    throw new Error(detail);
  }
  return res.json();
}

export async function healthCheck(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE_URL}/health`);
    return res.ok;
  } catch {
    return false;
  }
}

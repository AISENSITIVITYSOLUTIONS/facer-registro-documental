// API client for facer-registro-documental

const DEFAULT_BASE_URL = "http://localhost:8080";

export interface ApiConfig {
  baseUrl: string;
  apiKey: string;
}

let config: ApiConfig = {
  baseUrl: DEFAULT_BASE_URL,
  apiKey: "",
};

export function setApiConfig(c: Partial<ApiConfig>) {
  config = { ...config, ...c };
}

export function getApiConfig(): ApiConfig {
  return { ...config };
}

function headers(): HeadersInit {
  const h: HeadersInit = {};
  if (config.apiKey) {
    h["Authorization"] = `Bearer ${config.apiKey}`;
  }
  return h;
}

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

export interface UploadResponse {
  id: number;
  uuid: string;
  user_id: number;
  country: string;
  document_type: string;
  status: string;
  validation_status: string;
  capture_quality_score: number | null;
  created_at: string;
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

export interface ResultsResponse {
  id: number;
  uuid: string;
  user_id: number;
  country: string;
  document_type: string;
  status: string;
  validation_status: string;
  comparison_status: string | null;
  comparison_score: number | null;
  extraction_confidence: number | null;
  capture_quality_score: number | null;
  ocr_engine: string | null;
  extracted_fields: Record<string, string | null> | null;
  created_at: string;
  updated_at: string;
}

export async function analyzeCapture(file: Blob): Promise<CaptureAnalysis> {
  const form = new FormData();
  form.append("file", file, "capture.jpg");
  const res = await fetch(`${config.baseUrl}/api/v1/documents/analyze-capture`, {
    method: "POST",
    headers: headers(),
    body: form,
  });
  if (!res.ok) throw new Error(`Analyze failed: ${res.status} ${await res.text()}`);
  return res.json();
}

export async function uploadDocument(
  userId: number,
  country: string,
  documentType: string,
  file: Blob,
): Promise<UploadResponse> {
  const form = new FormData();
  form.append("user_id", String(userId));
  form.append("country", String(country));
  form.append("document_type", String(documentType));
  form.append("file", file, "document.jpg");
  const res = await fetch(`${config.baseUrl}/api/v1/documents/upload`, {
    method: "POST",
    headers: headers(),
    body: form,
  });
  if (!res.ok) throw new Error(`Upload failed: ${res.status} ${await res.text()}`);
  return res.json();
}

export async function processDocument(documentId: number): Promise<ProcessResponse> {
  const res = await fetch(`${config.baseUrl}/api/v1/documents/${documentId}/process`, {
    method: "POST",
    headers: headers(),
  });
  if (!res.ok) throw new Error(`Process failed: ${res.status} ${await res.text()}`);
  return res.json();
}

export async function getResults(documentId: number): Promise<ResultsResponse> {
  const res = await fetch(`${config.baseUrl}/api/v1/documents/${documentId}/results`, {
    method: "GET",
    headers: headers(),
  });
  if (!res.ok) throw new Error(`Results failed: ${res.status} ${await res.text()}`);
  return res.json();
}

export async function healthCheck(): Promise<boolean> {
  try {
    const res = await fetch(`${config.baseUrl}/health`);
    return res.ok;
  } catch {
    return false;
  }
}

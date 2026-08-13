import type {
  AnalyzeResponse,
  FinalizeRequest,
  FinalizeResponse,
  ResumeBullet,
  UploadResponse,
} from "./types";

export const API_BASE: string =
  (import.meta.env.VITE_API_BASE as string | undefined) ||
  // 127.0.0.1, not "localhost" — this network has a broken IPv6 loopback path
  // (see resume_agent/llm.py) where "localhost" can resolve to ::1 and hang.
  "http://127.0.0.1:8000/api";

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = "";
    try {
      const body = await res.text();
      detail = body;
    } catch {
      // ignore
    }
    throw new Error(
      `Request failed (${res.status} ${res.statusText})${detail ? `: ${detail}` : ""}`
    );
  }
  return res.json() as Promise<T>;
}

export async function uploadResume(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/resume/upload`, {
    method: "POST",
    body: formData,
  });
  return handle<UploadResponse>(res);
}

export async function getResumeBullets(): Promise<ResumeBullet[]> {
  const res = await fetch(`${API_BASE}/resume/bullets`);
  return handle<ResumeBullet[]>(res);
}

export async function analyzeJD(jdText: string): Promise<AnalyzeResponse> {
  const res = await fetch(`${API_BASE}/tailor/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jd_text: jdText }),
  });
  return handle<AnalyzeResponse>(res);
}

export async function finalizeResume(
  payload: FinalizeRequest
): Promise<FinalizeResponse> {
  const res = await fetch(`${API_BASE}/tailor/finalize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handle<FinalizeResponse>(res);
}

export function downloadUrl(relativePath: string): string {
  // relativePath looks like "/api/download/tailored_resume.docx".
  // API_BASE already ends in "/api", so strip a leading "/api" from the
  // relative path if present to avoid duplicating it; otherwise just
  // prefix with the base's origin.
  if (relativePath.startsWith("/api/")) {
    const origin = API_BASE.replace(/\/api\/?$/, "");
    return `${origin}${relativePath}`;
  }
  return `${API_BASE}${relativePath.startsWith("/") ? "" : "/"}${relativePath}`;
}

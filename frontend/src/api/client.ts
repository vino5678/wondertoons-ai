import type {
  ApiErrorBody,
  Character,
  CharacterCreateRequest,
  CreateProjectRequest,
  ExportItem,
  ExportRequest,
  HealthResponse,
  Job,
  Project,
  StoryPlan,
  StoryRequest,
} from "../types/api";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/+$/, "");
const REQUEST_TIMEOUT_MS = 15_000;

export class ApiError extends Error {
  readonly status: number;
  readonly code?: string;
  readonly hint?: string;

  constructor(message: string, status: number, code?: string, hint?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.hint = hint;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  const externalSignal = init.signal;
  const abortFromCaller = () => controller.abort();
  externalSignal?.addEventListener("abort", abortFromCaller);

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      signal: controller.signal,
      headers: {
        ...(init.body ? { "Content-Type": "application/json" } : {}),
        ...init.headers,
      },
    });

    if (response.status === 204) return undefined as T;

    const body = (await response.json().catch(() => null)) as ApiErrorBody | null;
    if (!response.ok) {
      const message =
        body?.error?.message ??
        (typeof body?.detail === "string" ? body.detail : `Request failed with status ${response.status}.`);
      throw new ApiError(message, response.status, body?.error?.code, body?.error?.hint ?? undefined);
    }
    return body as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (controller.signal.aborted) {
      if (externalSignal?.aborted) throw new ApiError("The request was cancelled.", 0);
      throw new ApiError("The backend request timed out. Check that the API is responding and try again.", 0);
    }
    throw new ApiError(
      `Could not connect to the backend via ${API_BASE_URL}. Make sure this project's FastAPI server is running at http://127.0.0.1:8001.`,
      0,
    );
  } finally {
    window.clearTimeout(timeout);
    externalSignal?.removeEventListener("abort", abortFromCaller);
  }
}

export const api = {
  getHealth: () => request<HealthResponse>("/health"),
  listProjects: () => request<Project[]>("/projects"),
  listCharacters: () => request<Character[]>("/characters"),
  createCharacter: (payload: CharacterCreateRequest) =>
    request<Character>("/characters", { method: "POST", body: JSON.stringify(payload) }),
  createProject: (payload: CreateProjectRequest) =>
    request<Project>("/projects", { method: "POST", body: JSON.stringify(payload) }),
  getStory: (projectId: string) => request<StoryPlan>(`/projects/${encodeURIComponent(projectId)}/story`),
  startStory: (projectId: string, payload: StoryRequest) =>
    request<Job>(`/projects/${encodeURIComponent(projectId)}/story`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getJob: (jobId: string, signal?: AbortSignal) =>
    request<Job>(`/jobs/${encodeURIComponent(jobId)}`, { signal }),
  startExport: (projectId: string, payload: ExportRequest) =>
    request<Job>(`/projects/${encodeURIComponent(projectId)}/exports`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listExports: (projectId: string) =>
    request<ExportItem[]>(`/projects/${encodeURIComponent(projectId)}/exports`),
};

export function mediaUrl(path: string): string {
  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

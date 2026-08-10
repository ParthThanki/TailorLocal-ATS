import type { ResumeDocument } from "./pdf-export";

export type Provider = "ollama" | "openai";

export type AtsAnalysis = {
  score: number;
  matchedKeywords: string[];
  missingKeywords: string[];
  improvements: string[];
  breakdown: Array<{
    label: string;
    score: number;
    maxScore: number;
    detail: string;
  }>;
};

export type GenerationResult = {
  resume: ResumeDocument;
  analysis: AtsAnalysis;
  beforeAnalysis: AtsAnalysis;
  jobDescription: string;
  refinementPasses: number;
};

export const PYTHON_BACKEND_URL = (
  process.env.NEXT_PUBLIC_TAILORLOCAL_BACKEND_URL || "http://127.0.0.1:8000"
).replace(/\/$/, "");

async function backendRequest<T>(path: string, init: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${PYTHON_BACKEND_URL}${path}`, init);
  } catch {
    throw new Error(`Could not reach the local Python backend at ${PYTHON_BACKEND_URL}. Start it and try again.`);
  }

  const payload = await response.json().catch(() => null) as { detail?: string } | null;
  if (!response.ok) {
    throw new Error(payload?.detail || `The Python backend returned ${response.status}.`);
  }
  return payload as T;
}

export async function listLocalModels(input: { provider: Provider; endpoint: string }): Promise<string[]> {
  const response = await backendRequest<{ models: string[] }>("/api/models", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return response.models;
}

export async function generateTailoredResume(input: {
  provider: Provider;
  endpoint: string;
  model: string;
  resumeText: string;
  jobDescription: string;
  targetScore?: number;
  maxRefinementPasses?: number;
}): Promise<GenerationResult> {
  return backendRequest<GenerationResult>("/api/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      targetScore: 80,
      maxRefinementPasses: 2,
      ...input,
    }),
  });
}

export async function scoreTailoredResume(input: {
  resume: ResumeDocument;
  jobDescription: string;
}): Promise<AtsAnalysis> {
  const response = await backendRequest<{ analysis: AtsAnalysis }>("/api/score", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return response.analysis;
}

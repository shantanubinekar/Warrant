import {
  ScenarioSummary,
  ScenarioDetail,
  ScenarioAnalysisResponse,
  AnalysisResponse,
  UploadResult,
  AskResponse,
  ReasoningResult,
} from '../types';

const API_BASE = '/api';

export async function fetchScenarios(): Promise<ScenarioSummary[]> {
  const res = await fetch(`${API_BASE}/scenarios`);
  if (!res.ok) {
    throw new Error(`Failed to fetch scenarios: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchScenario(id: number): Promise<ScenarioDetail> {
  const res = await fetch(`${API_BASE}/scenarios/${id}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch scenario ${id}: ${res.statusText}`);
  }
  return res.json();
}

export async function analyzeScenario(id: number): Promise<ScenarioAnalysisResponse> {
  const res = await fetch(`${API_BASE}/scenarios/${id}/analyze`, {
    method: 'POST',
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to analyze scenario ${id}: ${res.statusText}`);
  }
  return res.json();
}

export async function analyzeCustomCase(patientCase: any): Promise<AnalysisResponse> {
  const res = await fetch(`${API_BASE}/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(patientCase),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to analyze custom case: ${res.statusText}`);
  }
  return res.json();
}

export async function uploadClinicalText(
  clinicalText: string,
  caseDescription?: string
): Promise<UploadResult> {
  const res = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      clinical_text: clinicalText,
      case_description: caseDescription,
    }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Upload extraction failed: ${res.statusText}`);
  }
  return res.json();
}

export async function uploadClinicalFile(
  file: File,
  caseDescription?: string
): Promise<UploadResult> {
  const formData = new FormData();
  formData.append('file', file);
  if (caseDescription) {
    formData.append('case_description', caseDescription);
  }
  const res = await fetch(`${API_BASE}/upload-file`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `File upload failed: ${res.statusText}`);
  }
  return res.json();
}

export async function askAboutCase(
  question: string,
  reasoningResult: ReasoningResult,
  caseId?: string
): Promise<AskResponse> {
  const res = await fetch(`${API_BASE}/ask`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      question,
      case_id: caseId,
      reasoning_result: reasoningResult,
    }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Question failed: ${res.statusText}`);
  }
  return res.json();
}

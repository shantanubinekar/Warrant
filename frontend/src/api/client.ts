import {
  ScenarioSummary,
  ScenarioDetail,
  ScenarioAnalysisResponse,
  AnalysisResponse,
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
): Promise<{ extracted_case: any; analysis: AnalysisResponse }> {
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

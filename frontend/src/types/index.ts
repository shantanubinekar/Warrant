// TypeScript types mirroring Warrant backend schemas

export type EvidenceState =
  | 'SUFFICIENT'
  | 'INCOMPLETE'
  | 'CONFLICTING'
  | 'QUESTIONABLE'
  | 'ADDITIONAL_INFORMATION_REQUIRED'
  | 'NO_RELIABLE_CONCLUSION';

export type ConditionResult = 'PASS' | 'FAIL' | 'UNKNOWN';

export type ConflictStatus = 'CONFLICT' | 'NO_CONFLICT' | 'NOT_ASSESSABLE';

export type CorroborationStatus =
  | 'CORROBORATED'
  | 'NOT_CORROBORATED'
  | 'NOT_ASSESSABLE'
  | 'LIMITED_CORROBORATION';

export type ActionType =
  | 'RETURN_CONCLUSION'
  | 'REQUEST_INFORMATION'
  | 'REPORT_CONFLICT'
  | 'FLAG_LOW_CONFIDENCE'
  | 'ESCALATE_TO_HUMAN'
  | 'WITHHOLD_CONCLUSION';

export interface ConditionCheck {
  condition_name: string;
  result: ConditionResult;
  reason: string;
  evidence_used?: string | null;
  source_reference?: string | null;
}

export interface MissingInformation {
  field: string;
  reason_needed: string;
  askable: boolean;
  ask_prompt?: string | null;
  criticality: 'REQUIRED' | 'RECOMMENDED' | 'OPTIONAL';
}

export interface ConflictDetail {
  claim: string;
  source_a: string;
  source_a_position: string;
  source_b: string;
  source_b_position: string;
  resolution_possible: boolean;
  resolution_note?: string | null;
}

export interface SourceTraceEntry {
  source_id: string;
  source_name: string;
  claim_supported: string;
  reliability: string;
  recency_status: string;
  applicability: string;
}

export interface ReasoningResult {
  state: EvidenceState;
  supported_claims: string[];
  unsupported_claims: string[];
  missing_information: MissingInformation[];
  conflicts: ConflictDetail[];
  source_trace: SourceTraceEntry[];
  reasons: string[];
  condition_checks: ConditionCheck[];
  conflict_status: ConflictStatus;
  corroboration_status: CorroborationStatus;
  generic_completeness: ConditionResult;
  criteria_specific_completeness: ConditionResult;
}

export interface StateAction {
  state: EvidenceState;
  action: ActionType;
  action_description: string;
  escalation_required: boolean;
}

export interface PipelineStageTrace {
  stage: string;
  status?: string;
  result?: string;
  sources_assessed?: number;
  conflict_status?: string;
  conflicts_found?: number;
  state?: string;
  condition_checks?: number;
  action?: string;
  escalation_required?: boolean;
}

export interface PipelineTrace {
  case_id: string;
  pipeline_stages: PipelineStageTrace[];
  total_condition_checks: number;
  total_sources: number;
  total_missing_info: number;
  total_conflicts: number;
}

export interface AnalysisResponse {
  case_id: string;
  reasoning_result: ReasoningResult;
  action: StateAction;
  explanation: string;
  explanation_source: 'llm' | 'template';
  pipeline_trace?: PipelineTrace | null;
  timestamp: string;
}

export interface ScenarioSummary {
  id: number;
  title: string;
  description: string;
  target_state: EvidenceState;
}

export interface ScenarioDetail extends ScenarioSummary {
  patient_case: any;
}

export interface ScenarioAnalysisResponse {
  scenario: ScenarioSummary;
  analysis: AnalysisResponse;
}

export interface UploadResult {
  extracted_case: any;
  analysis: AnalysisResponse;
}

export interface AskResponse {
  answer: string;
}

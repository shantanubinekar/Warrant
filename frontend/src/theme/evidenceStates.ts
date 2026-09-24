import { AlertTriangle, CheckCircle2, HelpCircle, MinusCircle, XCircle, Zap } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { EvidenceState } from '../types';

export interface EvidenceStateConfig {
  label: string;
  short: string;
  description: string;
  icon: LucideIcon;
  text: string;
  soft: string;
  line: string;
  solid: string;
}

// The ONLY place the three signal colors (good/caution/critical) are
// mapped to meaning. Every other component imports this rather than
// hardcoding its own palette.
export const EVIDENCE_STATE_CONFIG: Record<EvidenceState, EvidenceStateConfig> = {
  SUFFICIENT: {
    label: 'Sufficient evidence',
    short: 'SUFFICIENT',
    description: 'Evidence satisfies authoritative clinical criteria to justify a conclusion.',
    icon: CheckCircle2,
    text: 'text-state-good',
    soft: 'bg-state-good-soft',
    line: 'border-state-good-line',
    solid: 'bg-state-good',
  },
  INCOMPLETE: {
    label: 'Incomplete evidence',
    short: 'INCOMPLETE',
    description: 'Critical evidence required by clinical guidelines is missing.',
    icon: MinusCircle,
    text: 'text-state-caution',
    soft: 'bg-state-caution-soft',
    line: 'border-state-caution-line',
    solid: 'bg-state-caution',
  },
  ADDITIONAL_INFORMATION_REQUIRED: {
    label: 'Additional information required',
    short: 'INFO REQUIRED',
    description: 'A specific, askable piece of information (e.g. repeat troponin) can resolve uncertainty.',
    icon: HelpCircle,
    text: 'text-state-caution',
    soft: 'bg-state-caution-soft',
    line: 'border-state-caution-line',
    solid: 'bg-state-caution',
  },
  QUESTIONABLE: {
    label: 'Questionable quality',
    short: 'QUESTIONABLE',
    description: 'Evidence exists, but its extraction confidence or document quality is inadequate.',
    icon: AlertTriangle,
    text: 'text-state-caution',
    soft: 'bg-state-caution-soft',
    line: 'border-state-caution-line',
    solid: 'bg-state-caution',
  },
  CONFLICTING: {
    label: 'Conflicting sources',
    short: 'CONFLICTING',
    description: 'Two or more authoritative clinical sources materially disagree on criteria.',
    icon: Zap,
    text: 'text-state-critical',
    soft: 'bg-state-critical-soft',
    line: 'border-state-critical-line',
    solid: 'bg-state-critical',
  },
  NO_RELIABLE_CONCLUSION: {
    label: 'No reliable conclusion',
    short: 'NO CONCLUSION',
    description: 'Available evidence cannot establish the requested claims — escalating to a human clinician.',
    icon: XCircle,
    text: 'text-state-critical',
    soft: 'bg-state-critical-soft',
    line: 'border-state-critical-line',
    solid: 'bg-state-critical',
  },
};

export function evidenceStateConfig(state: EvidenceState): EvidenceStateConfig {
  return EVIDENCE_STATE_CONFIG[state] || EVIDENCE_STATE_CONFIG.NO_RELIABLE_CONCLUSION;
}

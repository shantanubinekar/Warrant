import React from 'react';
import { EvidenceState, StateAction } from '../types';

interface Props {
  state: EvidenceState;
  action: StateAction;
  explanationSource: 'llm' | 'template';
}

interface StateStyle {
  label: string;
  bg: string;
  text: string;
  border: string;
  iconBg: string;
  iconColor: string;
  description: string;
}

const STATE_CONFIG: Record<EvidenceState, StateStyle> = {
  SUFFICIENT: {
    label: 'SUFFICIENT EVIDENCE',
    bg: 'bg-emerald-50',
    text: 'text-emerald-900',
    border: 'border-emerald-300',
    iconBg: 'bg-emerald-500',
    iconColor: 'text-white',
    description: 'Evidence satisfies authoritative clinical criteria to justify a conclusion.',
  },
  INCOMPLETE: {
    label: 'INCOMPLETE EVIDENCE',
    bg: 'bg-amber-50',
    text: 'text-amber-900',
    border: 'border-amber-300',
    iconBg: 'bg-amber-500',
    iconColor: 'text-white',
    description: 'Critical evidence required by clinical guidelines is missing.',
  },
  CONFLICTING: {
    label: 'CONFLICTING SOURCES',
    bg: 'bg-rose-50',
    text: 'text-rose-900',
    border: 'border-rose-300',
    iconBg: 'bg-rose-600',
    iconColor: 'text-white',
    description: 'Two or more authoritative clinical sources materially disagree on criteria.',
  },
  QUESTIONABLE: {
    label: 'QUESTIONABLE QUALITY',
    bg: 'bg-orange-50',
    text: 'text-orange-900',
    border: 'border-orange-300',
    iconBg: 'bg-orange-500',
    iconColor: 'text-white',
    description: 'Evidence exists, but its extraction confidence or document quality is inadequate.',
  },
  ADDITIONAL_INFORMATION_REQUIRED: {
    label: 'ADDITIONAL INFORMATION REQUIRED',
    bg: 'bg-amber-50',
    text: 'text-amber-900',
    border: 'border-amber-300',
    iconBg: 'bg-amber-500',
    iconColor: 'text-white',
    description: 'A specific, askable piece of information (e.g. repeat troponin) can resolve uncertainty.',
  },
  NO_RELIABLE_CONCLUSION: {
    label: 'NO RELIABLE CONCLUSION',
    bg: 'bg-slate-100',
    text: 'text-slate-900',
    border: 'border-slate-300',
    iconBg: 'bg-slate-700',
    iconColor: 'text-white',
    description: 'Available evidence cannot establish requested claims; escalating to human clinician.',
  },
};

export const EvidenceStateIndicator: React.FC<Props> = ({ state, action, explanationSource }) => {
  const config = STATE_CONFIG[state] || STATE_CONFIG.NO_RELIABLE_CONCLUSION;

  return (
    <div className={`p-5 rounded-xl border ${config.border} ${config.bg} shadow-sm transition-all`}>
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-start gap-3.5">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center font-bold text-lg shrink-0 ${config.iconBg} ${config.iconColor}`}>
            {state === 'SUFFICIENT' && '✓'}
            {state === 'INCOMPLETE' && '⋯'}
            {state === 'ADDITIONAL_INFORMATION_REQUIRED' && '!'}
            {state === 'CONFLICTING' && '⚡'}
            {state === 'QUESTIONABLE' && '?'}
            {state === 'NO_RELIABLE_CONCLUSION' && '✕'}
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className={`text-xs font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full ${config.border} border bg-white/70 ${config.text}`}>
                {config.label}
              </span>
              <span className="text-xs text-slate-500 font-medium">
                Engine State: <code className="font-mono font-semibold">{state}</code>
              </span>
              <span className="text-xs bg-slate-200/80 text-slate-700 px-2 py-0.5 rounded">
                Explanation: {explanationSource === 'llm' ? '🤖 LLM Verified' : '🔒 Deterministic Template'}
              </span>
            </div>
            <p className={`mt-1.5 text-sm font-medium ${config.text}`}>
              {config.description}
            </p>
          </div>
        </div>

        {/* Action Badge */}
        <div className="md:text-right shrink-0">
          <div className="inline-flex flex-col md:items-end">
            <span className="text-xs uppercase font-semibold text-slate-500 tracking-wider">
              System Action
            </span>
            <span className="text-sm font-bold text-slate-800 bg-white/90 border border-slate-200 px-3 py-1 rounded-md shadow-xs mt-1">
              {action.action.replace(/_/g, ' ')}
            </span>
            {action.escalation_required && (
              <span className="text-xs font-semibold text-rose-600 mt-1 flex items-center gap-1">
                <span>⚠️</span> Escalation Required
              </span>
            )}
          </div>
        </div>
      </div>

      {action.action_description && (
        <div className="mt-4 pt-3 border-t border-slate-200/60 text-xs text-slate-700 flex items-center gap-2">
          <span className="font-semibold text-slate-900">Action Protocol:</span>
          <span>{action.action_description}</span>
        </div>
      )}
    </div>
  );
};

import React from 'react';
import { motion } from 'framer-motion';
import { Bot, Lock, AlertTriangle } from 'lucide-react';
import { EvidenceState, StateAction } from '../types';
import { evidenceStateConfig } from '../theme/evidenceStates';

interface Props {
  state: EvidenceState;
  action: StateAction;
  explanationSource: 'llm' | 'template';
}

export const EvidenceStateIndicator: React.FC<Props> = ({ state, action, explanationSource }) => {
  const config = evidenceStateConfig(state);
  const Icon = config.icon;

  return (
    <motion.div
      key={state}
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: 'easeOut' }}
      className={`rounded border ${config.line} bg-paper-raised shadow-bezel overflow-hidden`}
    >
      <div className={`flex items-stretch`}>
        {/* Signal rail — the reserved state color lives here and nowhere decorative */}
        <div className={`w-1.5 shrink-0 ${config.solid}`} aria-hidden="true" />

        <div className="flex-1 p-5">
          <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
            <div className="flex items-start gap-3.5">
              <div className={`w-9 h-9 rounded flex items-center justify-center shrink-0 ${config.soft} ${config.text}`}>
                <Icon size={19} strokeWidth={2.25} />
              </div>
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-[15px] font-bold text-ink leading-tight">
                    {config.label}
                  </span>
                  <span className={`text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded border ${config.line} ${config.text}`}>
                    {state}
                  </span>
                </div>
                <p className="mt-1 text-sm text-ink-soft max-w-xl leading-relaxed">
                  {config.description}
                </p>
              </div>
            </div>

            {/* Action readout */}
            <div className="shrink-0 md:text-right">
              <div className="text-[11px] font-semibold text-ink-faint mb-1">
                System action
              </div>
              <div className="inline-flex items-center gap-1.5 text-sm font-semibold text-ink bg-paper border border-line px-2.5 py-1 rounded font-mono">
                {action.action.replace(/_/g, ' ')}
              </div>
              {action.escalation_required && (
                <div className="text-xs font-semibold text-state-critical mt-1.5 flex items-center gap-1 md:justify-end">
                  <AlertTriangle size={13} /> Escalation required
                </div>
              )}
            </div>
          </div>

          {action.action_description && (
            <div className="mt-4 pt-3 border-t border-line text-xs text-ink-soft flex items-start gap-2">
              <span className="font-semibold text-ink shrink-0">Protocol —</span>
              <span>{action.action_description}</span>
            </div>
          )}

          <div className="mt-3 flex items-center gap-1.5 text-[11px] text-ink-faint">
            {explanationSource === 'llm' ? (
              <>
                <Bot size={13} /> Explanation drafted by LLM, constrained to this reading
              </>
            ) : (
              <>
                <Lock size={13} /> Explanation generated from deterministic template
              </>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
};

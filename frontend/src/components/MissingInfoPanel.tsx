import React from 'react';
import { CheckCircle2, AlertTriangle } from 'lucide-react';
import { MissingInformation } from '../types';

interface Props {
  missingInfo: MissingInformation[];
}

export const MissingInfoPanel: React.FC<Props> = ({ missingInfo }) => {
  if (!missingInfo || missingInfo.length === 0) {
    return (
      <div className="p-5 flex items-center justify-center gap-2 text-state-good bg-state-good-soft rounded border border-state-good-line text-sm font-medium">
        <CheckCircle2 size={16} /> No critical clinical information is missing for this case.
      </div>
    );
  }

  const askableCount = missingInfo.filter((m) => m.askable).length;

  return (
    <div className="bg-paper-raised rounded border border-line overflow-hidden">
      <div className="px-5 py-4 bg-state-caution-soft/50 border-b border-state-caution-line/60 flex items-center justify-between gap-3">
        <div>
          <h3 className="font-semibold text-ink text-sm flex items-center gap-2">
            <AlertTriangle size={14} className="text-state-caution" /> Missing clinical information ({missingInfo.length})
          </h3>
          <p className="text-xs text-ink-soft mt-0.5">
            Guideline-required data points that are missing or unusable.
          </p>
        </div>
        {askableCount > 0 && (
          <span className="text-xs font-semibold px-2.5 py-1 rounded bg-state-caution text-white">
            {askableCount} actionable
          </span>
        )}
      </div>

      <div className="divide-y divide-line">
        {missingInfo.map((item, idx) => (
          <div key={idx} className="p-4 hover:bg-paper/60 transition-colors">
            <div className="flex items-start justify-between gap-4">
              <div className="space-y-1.5 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-mono text-xs font-semibold text-ink bg-paper px-2 py-0.5 rounded border border-line">
                    {item.field}
                  </span>
                  <span
                    className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border font-mono ${
                      item.criticality === 'REQUIRED'
                        ? 'bg-state-critical-soft text-state-critical border-state-critical-line'
                        : 'bg-paper text-ink-faint border-line'
                    }`}
                  >
                    {item.criticality}
                  </span>
                  {item.askable && (
                    <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded border font-mono bg-signal-soft text-signal border-signal/30">
                      ASKABLE
                    </span>
                  )}
                </div>

                <p className="text-sm text-ink-soft">{item.reason_needed}</p>

                {item.askable && item.ask_prompt && (
                  <div className="mt-2 text-xs bg-signal-soft border border-signal/20 rounded p-2.5 text-signal-dark flex items-start gap-2">
                    <span className="font-semibold shrink-0">Next step —</span>
                    <span>{item.ask_prompt}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

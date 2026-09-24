import React from 'react';
import { CheckCircle2, Zap } from 'lucide-react';
import { ConflictDetail } from '../types';

interface Props {
  conflicts: ConflictDetail[];
}

export const ConflictPanel: React.FC<Props> = ({ conflicts }) => {
  if (!conflicts || conflicts.length === 0) {
    return (
      <div className="p-5 flex items-center justify-center gap-2 text-state-good bg-state-good-soft rounded border border-state-good-line text-sm">
        <CheckCircle2 size={16} /> No guideline conflicts detected across applicable medical sources.
      </div>
    );
  }

  return (
    <div className="bg-paper-raised rounded border border-state-critical-line overflow-hidden">
      <div className="px-5 py-4 bg-state-critical-soft/60 border-b border-state-critical-line flex items-center justify-between gap-3">
        <div>
          <h3 className="font-semibold text-ink text-sm flex items-center gap-2">
            <Zap size={14} className="text-state-critical" /> Unresolved guideline disagreements ({conflicts.length})
          </h3>
          <p className="text-xs text-ink-soft mt-0.5">
            Two or more applicable sources materially disagree. Conflicts are reported
            explicitly — never resolved by majority vote.
          </p>
        </div>
        <span className="text-xs font-semibold px-2.5 py-1 rounded bg-state-critical text-white shrink-0">
          Reported
        </span>
      </div>

      <div className="divide-y divide-line">
        {conflicts.map((conflict, idx) => (
          <div key={idx} className="p-5 space-y-4">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-semibold text-ink-faint">
                Disputed claim —
              </span>
              <span className="text-sm font-semibold text-ink bg-paper px-2.5 py-0.5 rounded border border-line">
                {conflict.claim}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Source A */}
              <div className="p-3.5 bg-paper border border-line rounded space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-semibold text-ink-soft">
                    Source A: {conflict.source_a}
                  </span>
                  <span className="text-[10px] bg-paper-raised border border-line px-1.5 py-0.5 rounded text-ink-faint font-medium">
                    Guideline rule
                  </span>
                </div>
                <p className="text-sm text-ink font-medium leading-relaxed">
                  {conflict.source_a_position}
                </p>
              </div>

              {/* Source B */}
              <div className="p-3.5 bg-paper border border-line rounded space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-semibold text-ink-soft">
                    Source B: {conflict.source_b}
                  </span>
                  <span className="text-[10px] bg-paper-raised border border-line px-1.5 py-0.5 rounded text-ink-faint font-medium">
                    Guideline rule
                  </span>
                </div>
                <p className="text-sm text-ink font-medium leading-relaxed">
                  {conflict.source_b_position}
                </p>
              </div>
            </div>

            {conflict.resolution_note && (
              <div className="text-xs bg-state-critical-soft/60 border border-state-critical-line rounded p-3 text-state-critical flex items-start gap-2">
                <span className="font-semibold shrink-0">Engine policy —</span>
                <span>{conflict.resolution_note}</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

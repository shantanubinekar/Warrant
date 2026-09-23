import React from 'react';
import { ConflictDetail } from '../types';

interface Props {
  conflicts: ConflictDetail[];
}

export const ConflictPanel: React.FC<Props> = ({ conflicts }) => {
  if (!conflicts || conflicts.length === 0) {
    return (
      <div className="p-5 text-center text-slate-500 bg-white rounded-xl border border-slate-200 text-sm">
        ✓ No guideline conflicts detected across applicable medical sources.
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-rose-200 overflow-hidden shadow-xs">
      <div className="px-5 py-4 bg-rose-50/70 border-b border-rose-200 flex items-center justify-between gap-3">
        <div>
          <h3 className="font-semibold text-rose-900 text-sm flex items-center gap-2">
            <span>⚡</span> Unresolved Guideline Disagreements ({conflicts.length})
          </h3>
          <p className="text-xs text-rose-700 mt-0.5">
            Two or more applicable sources materially disagree. Per Warrant architecture principle, conflicts are reported explicitly — never resolved by majority vote.
          </p>
        </div>
        <span className="text-xs font-bold px-2.5 py-1 rounded bg-rose-200 text-rose-900 shrink-0">
          REPORTED
        </span>
      </div>

      <div className="divide-y divide-rose-100">
        {conflicts.map((conflict, idx) => (
          <div key={idx} className="p-5 space-y-4">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Disputed Clinical Claim:
              </span>
              <span className="text-sm font-semibold text-slate-900 bg-slate-100 px-2.5 py-0.5 rounded">
                {conflict.claim}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Source A */}
              <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-lg space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold text-slate-700">
                    Source A: {conflict.source_a}
                  </span>
                  <span className="text-[10px] bg-slate-200 px-1.5 py-0.5 rounded text-slate-600 font-medium">
                    Guideline Rule
                  </span>
                </div>
                <p className="text-sm text-slate-800 leading-relaxed font-medium">
                  {conflict.source_a_position}
                </p>
              </div>

              {/* Source B */}
              <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-lg space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold text-slate-700">
                    Source B: {conflict.source_b}
                  </span>
                  <span className="text-[10px] bg-slate-200 px-1.5 py-0.5 rounded text-slate-600 font-medium">
                    Guideline Rule
                  </span>
                </div>
                <p className="text-sm text-slate-800 leading-relaxed font-medium">
                  {conflict.source_b_position}
                </p>
              </div>
            </div>

            {conflict.resolution_note && (
              <div className="text-xs bg-rose-50 border border-rose-200/80 rounded-lg p-3 text-rose-800 flex items-start gap-2">
                <span className="font-bold text-rose-900 shrink-0">Engine Policy:</span>
                <span>{conflict.resolution_note}</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

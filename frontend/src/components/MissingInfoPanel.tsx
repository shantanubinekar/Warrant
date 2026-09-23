import React from 'react';
import { MissingInformation } from '../types';

interface Props {
  missingInfo: MissingInformation[];
}

export const MissingInfoPanel: React.FC<Props> = ({ missingInfo }) => {
  if (!missingInfo || missingInfo.length === 0) {
    return (
      <div className="p-5 text-center text-emerald-700 bg-emerald-50 rounded-xl border border-emerald-200 text-sm font-medium">
        ✓ No critical clinical information is missing for this case.
      </div>
    );
  }

  const askableCount = missingInfo.filter((m) => m.askable).length;

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-xs">
      <div className="px-5 py-4 bg-amber-50/50 border-b border-amber-200/60 flex items-center justify-between gap-3">
        <div>
          <h3 className="font-semibold text-slate-900 text-sm flex items-center gap-2">
            <span className="text-amber-600">⚠️</span> Missing Clinical Information ({missingInfo.length})
          </h3>
          <p className="text-xs text-slate-600 mt-0.5">
            Guideline-required data points that are missing or unusable.
          </p>
        </div>
        {askableCount > 0 && (
          <span className="text-xs font-semibold px-2.5 py-1 rounded bg-amber-200/80 text-amber-900">
            {askableCount} Actionable Item(s)
          </span>
        )}
      </div>

      <div className="divide-y divide-slate-100">
        {missingInfo.map((item, idx) => (
          <div key={idx} className="p-4 hover:bg-slate-50/50 transition-colors">
            <div className="flex items-start justify-between gap-4">
              <div className="space-y-1.5 flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-bold text-slate-900 bg-slate-100 px-2 py-0.5 rounded">
                    {item.field}
                  </span>
                  <span
                    className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${
                      item.criticality === 'REQUIRED'
                        ? 'bg-rose-100 text-rose-800 border border-rose-200'
                        : 'bg-slate-100 text-slate-700'
                    }`}
                  >
                    {item.criticality}
                  </span>
                  {item.askable && (
                    <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 border border-blue-200">
                      ASKABLE
                    </span>
                  )}
                </div>

                <p className="text-sm text-slate-700">{item.reason_needed}</p>

                {item.askable && item.ask_prompt && (
                  <div className="mt-2 text-xs bg-blue-50 border border-blue-200 rounded-lg p-2.5 text-blue-900 flex items-start gap-2">
                    <span className="font-bold text-blue-600 shrink-0">→ Next Step:</span>
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

import React from 'react';
import { ScenarioSummary, EvidenceState } from '../types';

interface Props {
  scenarios: ScenarioSummary[];
  selectedId: number | null;
  onSelect: (id: number) => void;
  isLoading: boolean;
  onOpenUpload: () => void;
}

const STATE_BADGES: Record<EvidenceState, { bg: string; text: string; label: string }> = {
  SUFFICIENT: { bg: 'bg-emerald-100', text: 'text-emerald-800', label: 'SUFFICIENT' },
  INCOMPLETE: { bg: 'bg-amber-100', text: 'text-amber-800', label: 'INCOMPLETE' },
  ADDITIONAL_INFORMATION_REQUIRED: { bg: 'bg-amber-100', text: 'text-amber-800', label: 'ADDITIONAL INFO' },
  CONFLICTING: { bg: 'bg-rose-100', text: 'text-rose-800', label: 'CONFLICTING' },
  QUESTIONABLE: { bg: 'bg-orange-100', text: 'text-orange-800', label: 'QUESTIONABLE' },
  NO_RELIABLE_CONCLUSION: { bg: 'bg-slate-200', text: 'text-slate-800', label: 'NO CONCLUSION' },
};

export const ScenarioList: React.FC<Props> = ({
  scenarios,
  selectedId,
  onSelect,
  isLoading,
  onOpenUpload,
}) => {
  return (
    <aside className="w-full md:w-80 lg:w-96 flex flex-col bg-white border-r border-slate-200 h-full shrink-0">
      <div className="p-4 border-b border-slate-200 bg-slate-50/50">
        <div className="flex items-center justify-between gap-2">
          <div>
            <h2 className="text-xs font-bold text-slate-500 uppercase tracking-wider">
              Mode A: Demo Scenarios
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              6 test cases covering all evidence states
            </p>
          </div>
          <button
            onClick={onOpenUpload}
            className="text-xs font-semibold px-2.5 py-1.5 bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 rounded-md transition-colors"
            title="Custom Clinical Text (Mode B)"
          >
            + Upload Note
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto divide-y divide-slate-100">
        {scenarios.map((sc) => {
          const isSelected = selectedId === sc.id;
          const badge = STATE_BADGES[sc.target_state] || STATE_BADGES.NO_RELIABLE_CONCLUSION;

          return (
            <button
              key={sc.id}
              onClick={() => onSelect(sc.id)}
              disabled={isLoading}
              className={`w-full text-left p-4 transition-all hover:bg-slate-50 relative flex flex-col gap-2 ${
                isSelected
                  ? 'bg-blue-50/50 border-l-4 border-blue-600 shadow-xs'
                  : 'border-l-4 border-transparent'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <span className="text-xs font-bold text-slate-400">
                  #{sc.id}
                </span>
                <span
                  className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${badge.bg} ${badge.text}`}
                >
                  {badge.label}
                </span>
              </div>

              <div>
                <h3 className={`text-sm font-semibold leading-snug ${isSelected ? 'text-blue-950 font-bold' : 'text-slate-800'}`}>
                  {sc.title}
                </h3>
                <p className="text-xs text-slate-500 line-clamp-2 mt-1 leading-relaxed">
                  {sc.description}
                </p>
              </div>
            </button>
          );
        })}
      </div>

      <div className="p-3 bg-slate-50 border-t border-slate-200 text-[11px] text-slate-500 leading-normal">
        <span className="font-semibold text-slate-700">Architecture Guarantee:</span> All cases run through the exact same deterministic reasoning pipeline — zero hardcoded results.
      </div>
    </aside>
  );
};

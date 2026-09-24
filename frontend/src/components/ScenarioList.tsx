import React from 'react';
import { FilePlus2 } from 'lucide-react';
import { ScenarioSummary } from '../types';
import { evidenceStateConfig } from '../theme/evidenceStates';

interface Props {
  scenarios: ScenarioSummary[];
  selectedId: number | null;
  onSelect: (id: number) => void;
  isLoading: boolean;
  onOpenUpload: () => void;
}

export const ScenarioList: React.FC<Props> = ({
  scenarios,
  selectedId,
  onSelect,
  isLoading,
  onOpenUpload,
}) => {
  return (
    <aside className="w-full md:w-80 lg:w-96 flex flex-col bg-paper-raised border-r border-line h-full shrink-0">
      <div className="p-4 border-b border-line">
        <div className="flex items-center justify-between gap-2">
          <div>
            <h2 className="text-xs font-semibold text-ink">
              Demo case set
            </h2>
            <p className="text-[11px] text-ink-faint mt-0.5">
              6 cases covering every evidence state
            </p>
          </div>
          <button
            onClick={onOpenUpload}
            className="flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1.5 text-signal hover:bg-signal-soft border border-line hover:border-signal/30 rounded transition-colors"
            title="Upload a case"
          >
            <FilePlus2 size={13} /> Upload
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto divide-y divide-line">
        {scenarios.map((sc) => {
          const isSelected = selectedId === sc.id;
          const config = evidenceStateConfig(sc.target_state);

          return (
            <button
              key={sc.id}
              onClick={() => onSelect(sc.id)}
              disabled={isLoading}
              className={`w-full text-left p-4 transition-colors relative flex flex-col gap-2 ${
                isSelected ? 'bg-signal-soft' : 'hover:bg-paper'
              }`}
            >
              {isSelected && (
                <span className="absolute left-0 top-0 bottom-0 w-0.5 bg-signal" aria-hidden="true" />
              )}
              <div className="flex items-start justify-between gap-2">
                <span className="text-[11px] font-mono font-semibold text-ink-faint">
                  CASE {String(sc.id).padStart(2, '0')}
                </span>
                <span
                  className={`text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded border ${config.line} ${config.text}`}
                >
                  {config.short}
                </span>
              </div>

              <div>
                <h3 className={`text-sm font-semibold leading-snug ${isSelected ? 'text-ink' : 'text-ink-soft'}`}>
                  {sc.title}
                </h3>
                <p className="text-xs text-ink-faint line-clamp-2 mt-1 leading-relaxed">
                  {sc.description}
                </p>
              </div>
            </button>
          );
        })}
      </div>

      <div className="p-3.5 border-t border-line text-[11px] text-ink-faint leading-normal">
        <span className="font-semibold text-ink-soft">Architecture guarantee —</span> every case runs
        through the same deterministic reasoning pipeline. No hardcoded results.
      </div>
    </aside>
  );
};

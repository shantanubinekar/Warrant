import React from 'react';
import { SourceTraceEntry } from '../types';

interface Props {
  sourceTrace: SourceTraceEntry[];
}

export const ProvenanceTrace: React.FC<Props> = ({ sourceTrace }) => {
  if (!sourceTrace || sourceTrace.length === 0) {
    return (
      <div className="p-5 text-center text-ink-faint bg-paper-raised rounded border border-line text-sm">
        No sources cited in the reasoning trace.
      </div>
    );
  }

  const reliabilityClass = (reliability: string) => {
    switch (reliability?.toUpperCase()) {
      case 'HIGH':
        return 'bg-state-good-soft text-state-good border-state-good-line';
      case 'MODERATE':
        return 'bg-state-caution-soft text-state-caution border-state-caution-line';
      case 'LOW':
        return 'bg-state-critical-soft text-state-critical border-state-critical-line';
      default:
        return 'bg-paper text-ink-soft border-line';
    }
  };

  const recencyClass = (recency: string) => {
    switch (recency?.toUpperCase()) {
      case 'CURRENT':
        return 'text-state-good';
      case 'AGING':
        return 'text-state-caution';
      case 'OUTDATED':
        return 'text-state-critical font-semibold';
      default:
        return 'text-ink-soft';
    }
  };

  return (
    <div className="bg-paper-raised rounded border border-line overflow-hidden">
      <div className="px-5 py-4 bg-paper border-b border-line">
        <h3 className="font-semibold text-ink text-sm">
          Medical knowledge provenance trace ({sourceTrace.length})
        </h3>
        <p className="text-xs text-ink-faint mt-0.5">
          Reliability, recency, and applicability are kept as separate dimensions — independent of claims.
        </p>
      </div>

      <div className="divide-y divide-line">
        {sourceTrace.map((source, idx) => (
          <div key={idx} className="p-4 hover:bg-paper/60 transition-colors space-y-2">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <span className="font-mono text-xs font-semibold text-ink bg-paper px-2 py-0.5 rounded border border-line mr-2">
                  [{source.source_id}]
                </span>
                <span className="text-sm font-semibold text-ink">
                  {source.source_name}
                </span>
              </div>

              <div className="flex items-center gap-2 flex-wrap text-xs">
                <span className={`px-2 py-0.5 rounded border font-medium ${reliabilityClass(source.reliability)}`}>
                  Reliability: {source.reliability}
                </span>
                <span className="px-2 py-0.5 rounded bg-paper border border-line text-ink-soft font-medium">
                  Recency: <span className={recencyClass(source.recency_status)}>{source.recency_status}</span>
                </span>
                <span className="px-2 py-0.5 rounded bg-signal-soft text-signal-dark font-medium border border-signal/20">
                  {source.applicability}
                </span>
              </div>
            </div>

            <div className="text-xs text-ink-faint pl-1">
              <span className="font-medium text-ink-soft">Supported claim —</span>{' '}
              <code className="text-ink-soft font-mono">{source.claim_supported}</code>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

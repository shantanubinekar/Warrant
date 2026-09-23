import React from 'react';
import { SourceTraceEntry } from '../types';

interface Props {
  sourceTrace: SourceTraceEntry[];
}

export const ProvenanceTrace: React.FC<Props> = ({ sourceTrace }) => {
  if (!sourceTrace || sourceTrace.length === 0) {
    return (
      <div className="p-5 text-center text-slate-500 bg-white rounded-xl border border-slate-200 text-sm">
        No sources cited in the reasoning trace.
      </div>
    );
  }

  const getReliabilityColor = (reliability: string) => {
    switch (reliability?.toUpperCase()) {
      case 'HIGH':
        return 'bg-emerald-100 text-emerald-800 border-emerald-200';
      case 'MODERATE':
        return 'bg-amber-100 text-amber-800 border-amber-200';
      case 'LOW':
        return 'bg-rose-100 text-rose-800 border-rose-200';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  const getRecencyColor = (recency: string) => {
    switch (recency?.toUpperCase()) {
      case 'CURRENT':
        return 'text-emerald-700';
      case 'AGING':
        return 'text-amber-700';
      case 'OUTDATED':
        return 'text-rose-700 font-semibold';
      default:
        return 'text-slate-600';
    }
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-xs">
      <div className="px-5 py-4 bg-slate-50/70 border-b border-slate-200 flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-slate-900 text-sm">
            Medical Knowledge Provenance Trace ({sourceTrace.length})
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Dimensions kept separate: reliability, recency, and applicability (independent of claims).
          </p>
        </div>
      </div>

      <div className="divide-y divide-slate-100">
        {sourceTrace.map((source, idx) => (
          <div key={idx} className="p-4 hover:bg-slate-50/50 transition-colors space-y-2">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <span className="font-mono text-xs font-bold text-slate-800 bg-slate-100 px-2 py-0.5 rounded mr-2">
                  [{source.source_id}]
                </span>
                <span className="text-sm font-semibold text-slate-900">
                  {source.source_name}
                </span>
              </div>

              <div className="flex items-center gap-2 flex-wrap text-xs">
                <span className={`px-2 py-0.5 rounded border font-medium ${getReliabilityColor(source.reliability)}`}>
                  Reliability: {source.reliability}
                </span>
                <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-medium">
                  Recency: <span className={getRecencyColor(source.recency_status)}>{source.recency_status}</span>
                </span>
                <span className="px-2 py-0.5 rounded bg-blue-50 text-blue-800 font-medium border border-blue-200">
                  {source.applicability}
                </span>
              </div>
            </div>

            <div className="text-xs text-slate-600 pl-1">
              <span className="font-medium text-slate-700">Supported Claim:</span>{' '}
              <code className="text-slate-800">{source.claim_supported}</code>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

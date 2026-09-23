import React from 'react';
import { ConditionCheck, ConditionResult } from '../types';

interface Props {
  checks: ConditionCheck[];
}

const RESULT_BADGE: Record<ConditionResult, { label: string; bg: string; text: string; border: string }> = {
  PASS: {
    label: 'PASS',
    bg: 'bg-emerald-50',
    text: 'text-emerald-700',
    border: 'border-emerald-200',
  },
  FAIL: {
    label: 'FAIL',
    bg: 'bg-rose-50',
    text: 'text-rose-700',
    border: 'border-rose-200',
  },
  UNKNOWN: {
    label: 'UNKNOWN',
    bg: 'bg-slate-100',
    text: 'text-slate-600',
    border: 'border-slate-300',
  },
};

export const ConditionCheckList: React.FC<Props> = ({ checks }) => {
  if (!checks || checks.length === 0) {
    return (
      <div className="p-6 text-center text-slate-500 bg-white rounded-lg border border-slate-200 text-sm">
        No condition checks recorded for this case.
      </div>
    );
  }

  const passCount = checks.filter((c) => c.result === 'PASS').length;
  const failCount = checks.filter((c) => c.result === 'FAIL').length;
  const unknownCount = checks.filter((c) => c.result === 'UNKNOWN').length;

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-xs">
      <div className="px-5 py-4 bg-slate-50/70 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="font-semibold text-slate-900 text-sm">
            Deterministic Condition Verification Log
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Individual guideline logic gates evaluated by deterministic engine (PASS / FAIL / UNKNOWN)
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 font-medium">
            {passCount} PASS
          </span>
          <span className="px-2 py-0.5 rounded bg-rose-100 text-rose-800 font-medium">
            {failCount} FAIL
          </span>
          <span className="px-2 py-0.5 rounded bg-slate-200 text-slate-800 font-medium">
            {unknownCount} UNKNOWN
          </span>
        </div>
      </div>

      <div className="divide-y divide-slate-100">
        {checks.map((check, idx) => {
          const badge = RESULT_BADGE[check.result] || RESULT_BADGE.UNKNOWN;
          return (
            <div key={idx} className="p-4 hover:bg-slate-50/50 transition-colors">
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono text-xs font-semibold text-slate-800">
                      {check.condition_name}
                    </span>
                    {check.evidence_used && (
                      <span className="text-xs text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded">
                        evidence: {check.evidence_used}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-slate-700 leading-relaxed">
                    {check.reason}
                  </p>
                  {check.source_reference && (
                    <div className="text-xs text-slate-400 italic">
                      Source ref: {check.source_reference}
                    </div>
                  )}
                </div>
                <span
                  className={`text-xs font-bold px-2.5 py-1 rounded-md border shrink-0 ${badge.bg} ${badge.text} ${badge.border}`}
                >
                  {badge.label}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

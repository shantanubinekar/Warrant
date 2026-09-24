import React from 'react';
import { Check, HelpCircle, X } from 'lucide-react';
import { ConditionCheck, ConditionResult } from '../types';

interface Props {
  checks: ConditionCheck[];
}

const RESULT_BADGE: Record<ConditionResult, { label: string; text: string; soft: string; line: string; icon: typeof Check }> = {
  PASS: { label: 'PASS', text: 'text-state-good', soft: 'bg-state-good-soft', line: 'border-state-good-line', icon: Check },
  FAIL: { label: 'FAIL', text: 'text-state-critical', soft: 'bg-state-critical-soft', line: 'border-state-critical-line', icon: X },
  UNKNOWN: { label: 'UNKNOWN', text: 'text-ink-faint', soft: 'bg-paper', line: 'border-line', icon: HelpCircle },
};

export const ConditionCheckList: React.FC<Props> = ({ checks }) => {
  if (!checks || checks.length === 0) {
    return (
      <div className="p-6 text-center text-ink-faint bg-paper-raised rounded border border-line text-sm">
        No condition checks recorded for this case.
      </div>
    );
  }

  const passCount = checks.filter((c) => c.result === 'PASS').length;
  const failCount = checks.filter((c) => c.result === 'FAIL').length;
  const unknownCount = checks.filter((c) => c.result === 'UNKNOWN').length;

  return (
    <div className="bg-paper-raised rounded border border-line overflow-hidden">
      <div className="px-5 py-4 bg-paper border-b border-line flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="font-semibold text-ink text-sm">
            Deterministic condition verification log
          </h3>
          <p className="text-xs text-ink-faint mt-0.5">
            Individual guideline logic gates evaluated by the deterministic engine
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono">
          <span className="px-2 py-0.5 rounded bg-state-good-soft text-state-good font-medium">
            {passCount} pass
          </span>
          <span className="px-2 py-0.5 rounded bg-state-critical-soft text-state-critical font-medium">
            {failCount} fail
          </span>
          <span className="px-2 py-0.5 rounded bg-paper border border-line text-ink-faint font-medium">
            {unknownCount} unknown
          </span>
        </div>
      </div>

      <div className="divide-y divide-line">
        {checks.map((check, idx) => {
          const badge = RESULT_BADGE[check.result] || RESULT_BADGE.UNKNOWN;
          const Icon = badge.icon;
          return (
            <div key={idx} className="p-4 hover:bg-paper/60 transition-colors">
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono text-xs font-semibold text-ink">
                      {check.condition_name}
                    </span>
                    {check.evidence_used && (
                      <span className="text-xs text-ink-faint bg-paper px-1.5 py-0.5 rounded border border-line">
                        evidence: {check.evidence_used}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-ink-soft leading-relaxed">
                    {check.reason}
                  </p>
                  {check.source_reference && (
                    <div className="text-xs text-ink-faint italic">
                      Source ref: {check.source_reference}
                    </div>
                  )}
                </div>
                <span
                  className={`text-xs font-semibold px-2 py-1 rounded border shrink-0 flex items-center gap-1 ${badge.soft} ${badge.text} ${badge.line}`}
                >
                  <Icon size={11} strokeWidth={3} /> {badge.label}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

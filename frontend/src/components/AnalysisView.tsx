import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Check, ClipboardList, MessageSquare, RotateCcw, X } from 'lucide-react';
import { AnalysisResponse, ScenarioSummary } from '../types';
import { EvidenceStateIndicator } from './EvidenceStateIndicator';
import { ConditionCheckList } from './ConditionCheckList';
import { MissingInfoPanel } from './MissingInfoPanel';
import { ConflictPanel } from './ConflictPanel';
import { ProvenanceTrace } from './ProvenanceTrace';
import { CaseQuestionBox } from './CaseQuestionBox';

interface Props {
  analysis: AnalysisResponse | null;
  scenario: ScenarioSummary | null;
  isLoading: boolean;
  onRerun?: () => void;
}

type TabType = 'overview' | 'conditions' | 'missing' | 'conflicts' | 'provenance' | 'pipeline';

export const AnalysisView: React.FC<Props> = ({
  analysis,
  scenario,
  isLoading,
  onRerun,
}) => {
  const [activeTab, setActiveTab] = useState<TabType>('overview');

  if (isLoading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-12 text-ink-faint space-y-3">
        <div className="w-7 h-7 border-2 border-signal border-t-transparent rounded-full animate-spin" />
        <div className="text-sm font-medium text-ink-soft">
          Running deterministic reasoning pipeline
        </div>
        <div className="text-xs text-ink-faint font-mono">
          schema · confidence gating · criteria · conflicts
        </div>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-12 text-center space-y-3">
        <ClipboardList className="text-ink-faint" size={32} strokeWidth={1.5} />
        <h3 className="text-base font-semibold text-ink-soft">No case selected</h3>
        <p className="text-sm text-ink-faint max-w-md">
          Choose one of the demo cases from the rail, or upload a custom clinical note to
          evaluate justified conclusions.
        </p>
      </div>
    );
  }

  const { reasoning_result, action, explanation, explanation_source, pipeline_trace } = analysis;

  const conflictCount = reasoning_result.conflicts?.length || 0;
  const missingCount = reasoning_result.missing_information?.length || 0;
  const conditionCount = reasoning_result.condition_checks?.length || 0;
  const sourceCount = reasoning_result.source_trace?.length || 0;

  const tabs: { id: TabType; label: string; count?: number; countTone?: 'neutral' | 'caution' | 'critical' }[] = [
    { id: 'overview', label: 'Summary & claims' },
    { id: 'conditions', label: 'Condition checks', count: conditionCount },
    { id: 'missing', label: 'Missing evidence', count: missingCount, countTone: 'caution' },
    { id: 'conflicts', label: 'Guideline conflicts', count: conflictCount, countTone: 'critical' },
    { id: 'provenance', label: 'Sources consulted', count: sourceCount },
    { id: 'pipeline', label: 'Pipeline trace' },
  ];

  const countClass = (tone?: 'neutral' | 'caution' | 'critical') =>
    tone === 'critical'
      ? 'bg-state-critical-soft text-state-critical'
      : tone === 'caution'
        ? 'bg-state-caution-soft text-state-caution'
        : 'bg-paper text-ink-faint';

  return (
    <main className="flex-1 overflow-y-auto bg-paper p-6 md:p-8 space-y-5">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-paper-raised p-5 rounded border border-line">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-mono font-semibold text-ink-faint">
              {analysis.case_id}
            </span>
            <span className="text-line">·</span>
            <span className="text-xs text-ink-faint font-mono">
              {new Date(analysis.timestamp).toLocaleTimeString()}
            </span>
          </div>
          <h1 className="text-lg font-bold text-ink mt-1">
            {scenario ? scenario.title : 'Custom clinical evaluation'}
          </h1>
          {scenario && (
            <p className="text-xs text-ink-soft mt-0.5 max-w-3xl">
              {scenario.description}
            </p>
          )}
        </div>

        {onRerun && (
          <button
            onClick={onRerun}
            disabled={isLoading}
            className="self-start sm:self-auto text-xs font-semibold px-3 py-2 text-ink-soft hover:text-ink hover:bg-paper rounded border border-line transition-colors shrink-0 flex items-center gap-1.5"
          >
            <RotateCcw size={13} /> Re-evaluate
          </button>
        )}
      </div>

      {/* Prominent Evidence State Indicator */}
      <EvidenceStateIndicator
        state={reasoning_result.state}
        action={action}
        explanationSource={explanation_source}
      />

      {/* Ask-about-this-case — separate, honest, best-effort LLM answer */}
      <CaseQuestionBox key={analysis.case_id} caseId={analysis.case_id} reasoningResult={reasoning_result} />

      {/* Navigation Tabs */}
      <div className="border-b border-line flex items-center gap-1 overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`relative px-3.5 py-2.5 text-xs font-semibold whitespace-nowrap flex items-center gap-1.5 transition-colors ${
              activeTab === tab.id ? 'text-ink' : 'text-ink-faint hover:text-ink-soft'
            }`}
          >
            <span>{tab.label}</span>
            {typeof tab.count === 'number' && tab.count > 0 && (
              <span className={`text-[10px] font-mono px-1.5 rounded ${countClass(tab.countTone)}`}>
                {tab.count}
              </span>
            )}
            {activeTab === tab.id && (
              <motion.div
                layoutId="tab-underline"
                className="absolute left-0 right-0 -bottom-px h-0.5 bg-signal"
                transition={{ type: 'spring', stiffness: 500, damping: 40 }}
              />
            )}
          </button>
        ))}
      </div>

      {/* Tab Panels */}
      <AnimatePresence mode="wait">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.15 }}
        >
          {activeTab === 'overview' && (
            <div className="space-y-5">
              {/* Clinical Explanation Card */}
              <div className="bg-paper-raised rounded border border-line p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-semibold text-ink flex items-center gap-2">
                    <MessageSquare size={15} className="text-ink-faint" /> Clinician explanation
                  </h2>
                  <span className="text-[11px] text-ink-faint">
                    Constrained to the reasoning payload
                  </span>
                </div>

                <div className="text-sm text-ink-soft bg-paper p-4 rounded border border-line leading-relaxed whitespace-pre-line">
                  {explanation}
                </div>
              </div>

              {/* Supported & Unsupported Claims Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {/* Supported Claims */}
                <div className="bg-paper-raised rounded border border-line p-5 space-y-3">
                  <h3 className="text-sm font-semibold text-ink flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-state-good-soft text-state-good flex items-center justify-center">
                      <Check size={12} strokeWidth={3} />
                    </span>
                    Claims supported by evidence
                  </h3>

                  {reasoning_result.supported_claims.length === 0 ? (
                    <p className="text-xs text-ink-faint italic">
                      No claims currently established by the available evidence.
                    </p>
                  ) : (
                    <ul className="space-y-2">
                      {reasoning_result.supported_claims.map((claim, i) => (
                        <li
                          key={i}
                          className="text-xs font-medium text-ink-soft bg-state-good-soft/50 border border-state-good-line p-2.5 rounded leading-relaxed"
                        >
                          {claim}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                {/* Unsupported Claims */}
                <div className="bg-paper-raised rounded border border-line p-5 space-y-3">
                  <h3 className="text-sm font-semibold text-ink flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-paper text-ink-faint flex items-center justify-center">
                      <X size={12} strokeWidth={3} />
                    </span>
                    Claims not supported
                  </h3>

                  {reasoning_result.unsupported_claims.length === 0 ? (
                    <p className="text-xs text-ink-faint italic">
                      No explicitly evaluated claims were rejected.
                    </p>
                  ) : (
                    <ul className="space-y-2">
                      {reasoning_result.unsupported_claims.map((claim, i) => (
                        <li
                          key={i}
                          className="text-xs font-medium text-ink-soft bg-paper border border-line p-2.5 rounded leading-relaxed"
                        >
                          {claim}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>

              {/* Reasoning Rationale Points */}
              {reasoning_result.reasons.length > 0 && (
                <div className="bg-paper-raised rounded border border-line p-5 space-y-2">
                  <h3 className="text-xs font-semibold text-ink-soft">
                    Deterministic engine rationale
                  </h3>
                  <ul className="space-y-1.5 text-xs text-ink-soft">
                    {reasoning_result.reasons.map((r, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <span className="text-signal font-bold">·</span>
                        <span>{r}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {activeTab === 'conditions' && (
            <ConditionCheckList checks={reasoning_result.condition_checks} />
          )}

          {activeTab === 'missing' && (
            <MissingInfoPanel missingInfo={reasoning_result.missing_information} />
          )}

          {activeTab === 'conflicts' && (
            <ConflictPanel conflicts={reasoning_result.conflicts} />
          )}

          {activeTab === 'provenance' && (
            <ProvenanceTrace sourceTrace={reasoning_result.source_trace} />
          )}

          {activeTab === 'pipeline' && (
            <div className="bg-paper-raised rounded border border-line p-6 space-y-4">
              <div>
                <h3 className="text-sm font-semibold text-ink">
                  Pipeline execution trace
                </h3>
                <p className="text-xs text-ink-faint mt-0.5">
                  Deterministic pipeline stage transitions executed for this case.
                </p>
              </div>

              {pipeline_trace?.pipeline_stages ? (
                <div className="space-y-2">
                  {pipeline_trace.pipeline_stages.map((stage, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between p-3 bg-paper rounded border border-line text-xs"
                    >
                      <div className="flex items-center gap-3">
                        <span className="w-5 h-5 rounded-full bg-signal-soft text-signal font-mono font-semibold flex items-center justify-center text-[10px]">
                          {i + 1}
                        </span>
                        <span className="font-semibold text-ink font-mono">
                          {stage.stage}
                        </span>
                      </div>
                      <div className="text-ink-soft font-medium">
                        {stage.result || stage.status || stage.state || stage.action || 'OK'}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-ink-faint italic">No pipeline trace available.</p>
              )}
            </div>
          )}
        </motion.div>
      </AnimatePresence>
    </main>
  );
};

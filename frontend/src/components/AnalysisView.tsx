import React, { useState } from 'react';
import { AnalysisResponse, ScenarioSummary } from '../types';
import { EvidenceStateIndicator } from './EvidenceStateIndicator';
import { ConditionCheckList } from './ConditionCheckList';
import { MissingInfoPanel } from './MissingInfoPanel';
import { ConflictPanel } from './ConflictPanel';
import { ProvenanceTrace } from './ProvenanceTrace';

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
      <div className="flex-1 flex flex-col items-center justify-center p-12 text-slate-400 space-y-3">
        <div className="w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
        <div className="text-sm font-medium text-slate-600">
          Running deterministic reasoning pipeline...
        </div>
        <div className="text-xs text-slate-400">
          Validating schema • Confidence gating • Evaluating criteria • Checking conflicts
        </div>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-12 text-center text-slate-400 space-y-2">
        <div className="text-4xl mb-2">📋</div>
        <h3 className="text-base font-semibold text-slate-700">No Patient Case Selected</h3>
        <p className="text-sm text-slate-500 max-w-md">
          Select one of the 6 demo clinical scenarios from the sidebar, or upload a custom clinical note to evaluate justified conclusions.
        </p>
      </div>
    );
  }

  const { reasoning_result, action, explanation, explanation_source, pipeline_trace } = analysis;

  const conflictCount = reasoning_result.conflicts?.length || 0;
  const missingCount = reasoning_result.missing_information?.length || 0;
  const conditionCount = reasoning_result.condition_checks?.length || 0;
  const sourceCount = reasoning_result.source_trace?.length || 0;

  return (
    <main className="flex-1 overflow-y-auto bg-slate-50 p-6 md:p-8 space-y-6">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
              CASE: {analysis.case_id}
            </span>
            <span className="text-xs text-slate-400">
              Evaluated at {new Date(analysis.timestamp).toLocaleTimeString()}
            </span>
          </div>
          <h1 className="text-lg font-bold text-slate-900 mt-1">
            {scenario ? scenario.title : 'Custom Clinical Evaluation'}
          </h1>
          {scenario && (
            <p className="text-xs text-slate-600 mt-0.5 max-w-3xl">
              {scenario.description}
            </p>
          )}
        </div>

        {onRerun && (
          <button
            onClick={onRerun}
            disabled={isLoading}
            className="self-start sm:self-auto text-xs font-semibold px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg border border-slate-300 transition-colors shrink-0 flex items-center gap-1.5"
          >
            <span>↻</span> Re-evaluate
          </button>
        )}
      </div>

      {/* Prominent Evidence State Indicator */}
      <EvidenceStateIndicator
        state={reasoning_result.state}
        action={action}
        explanationSource={explanation_source}
      />

      {/* Navigation Tabs */}
      <div className="border-b border-slate-200 flex items-center gap-2 overflow-x-auto pb-px">
        <button
          onClick={() => setActiveTab('overview')}
          className={`px-4 py-2.5 text-xs font-bold transition-all border-b-2 whitespace-nowrap ${
            activeTab === 'overview'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          Clinical Summary & Claims
        </button>
        <button
          onClick={() => setActiveTab('conditions')}
          className={`px-4 py-2.5 text-xs font-bold transition-all border-b-2 whitespace-nowrap flex items-center gap-1.5 ${
            activeTab === 'conditions'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          <span>Condition Checks</span>
          <span className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.2 rounded-full font-mono">
            {conditionCount}
          </span>
        </button>
        <button
          onClick={() => setActiveTab('missing')}
          className={`px-4 py-2.5 text-xs font-bold transition-all border-b-2 whitespace-nowrap flex items-center gap-1.5 ${
            activeTab === 'missing'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          <span>Missing Evidence</span>
          {missingCount > 0 && (
            <span className="text-[10px] bg-amber-100 text-amber-800 px-1.5 py-0.2 rounded-full font-mono">
              {missingCount}
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab('conflicts')}
          className={`px-4 py-2.5 text-xs font-bold transition-all border-b-2 whitespace-nowrap flex items-center gap-1.5 ${
            activeTab === 'conflicts'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          <span>Guideline Conflicts</span>
          {conflictCount > 0 && (
            <span className="text-[10px] bg-rose-100 text-rose-800 px-1.5 py-0.2 rounded-full font-mono font-bold">
              {conflictCount}
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab('provenance')}
          className={`px-4 py-2.5 text-xs font-bold transition-all border-b-2 whitespace-nowrap flex items-center gap-1.5 ${
            activeTab === 'provenance'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          <span>Sources Consulted</span>
          <span className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.2 rounded-full font-mono">
            {sourceCount}
          </span>
        </button>
        <button
          onClick={() => setActiveTab('pipeline')}
          className={`px-4 py-2.5 text-xs font-bold transition-all border-b-2 whitespace-nowrap ${
            activeTab === 'pipeline'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          Pipeline Trace
        </button>
      </div>

      {/* Tab Panels */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Clinical Explanation Card */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <span>💬</span> Clinician Explanation
              </h2>
              <span className="text-xs text-slate-400">
                Constrained to Authoritative Reasoning Payload
              </span>
            </div>

            <div className="prose prose-sm max-w-none text-slate-700 bg-slate-50/70 p-4 rounded-lg border border-slate-200/60 leading-relaxed font-sans whitespace-pre-line">
              {explanation}
            </div>
          </div>

          {/* Supported & Unsupported Claims Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Supported Claims */}
            <div className="bg-white rounded-xl border border-emerald-200 p-5 shadow-xs space-y-3">
              <h3 className="text-sm font-bold text-emerald-950 flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-emerald-100 text-emerald-800 text-xs flex items-center justify-center font-bold">
                  ✓
                </span>
                Claims Supported by Evidence
              </h3>

              {reasoning_result.supported_claims.length === 0 ? (
                <p className="text-xs text-slate-400 italic">
                  No claims currently established by the available evidence.
                </p>
              ) : (
                <ul className="space-y-2">
                  {reasoning_result.supported_claims.map((claim, i) => (
                    <li
                      key={i}
                      className="text-xs font-medium text-emerald-900 bg-emerald-50/60 border border-emerald-200/60 p-2.5 rounded-lg leading-relaxed"
                    >
                      {claim}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Unsupported Claims */}
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-3">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-slate-100 text-slate-600 text-xs flex items-center justify-center font-bold">
                  ✗
                </span>
                Claims NOT Supported
              </h3>

              {reasoning_result.unsupported_claims.length === 0 ? (
                <p className="text-xs text-slate-400 italic">
                  No explicitly evaluated claims were rejected.
                </p>
              ) : (
                <ul className="space-y-2">
                  {reasoning_result.unsupported_claims.map((claim, i) => (
                    <li
                      key={i}
                      className="text-xs font-medium text-slate-700 bg-slate-50 border border-slate-200/70 p-2.5 rounded-lg leading-relaxed"
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
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Deterministic Engine Rationales
              </h3>
              <ul className="space-y-1.5 text-xs text-slate-700">
                {reasoning_result.reasons.map((r, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="text-blue-500 font-bold">•</span>
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
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-4">
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              Pipeline Execution Trace (§1 Flowchart Audit)
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Deterministic pipeline stage transitions executed for this case.
            </p>
          </div>

          {pipeline_trace?.pipeline_stages ? (
            <div className="space-y-3">
              {pipeline_trace.pipeline_stages.map((stage, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs"
                >
                  <div className="flex items-center gap-3">
                    <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 font-bold flex items-center justify-center text-[10px]">
                      {i + 1}
                    </span>
                    <span className="font-semibold text-slate-800 font-mono">
                      {stage.stage}
                    </span>
                  </div>
                  <div className="text-slate-600 font-medium">
                    {stage.result || stage.status || stage.state || stage.action || 'OK'}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-400 italic">No pipeline trace available.</p>
          )}
        </div>
      )}
    </main>
  );
};

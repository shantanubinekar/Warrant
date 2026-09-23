import React, { useEffect, useState } from 'react';
import {
  ScenarioSummary,
  AnalysisResponse,
} from './types';
import {
  fetchScenarios,
  analyzeScenario,
  uploadClinicalText,
} from './api/client';
import { ScenarioList } from './components/ScenarioList';
import { AnalysisView } from './components/AnalysisView';
import { CustomUploadModal } from './components/CustomUploadModal';

export const App: React.FC = () => {
  const [scenarios, setScenarios] = useState<ScenarioSummary[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState<number | null>(null);
  const [currentScenario, setCurrentScenario] = useState<ScenarioSummary | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isUploadOpen, setIsUploadOpen] = useState<boolean>(false);

  // Load scenarios on mount
  useEffect(() => {
    async function loadInitial() {
      try {
        const list = await fetchScenarios();
        setScenarios(list);
        if (list.length > 0) {
          handleSelectScenario(list[0].id);
        }
      } catch (err: any) {
        console.error('Failed to load scenarios', err);
        setError('Could not connect to backend server. Make sure FastAPI is running on port 8000.');
      }
    }
    loadInitial();
  }, []);

  const handleSelectScenario = async (id: number) => {
    setSelectedScenarioId(id);
    setIsLoading(true);
    setError(null);
    try {
      const data = await analyzeScenario(id);
      setCurrentScenario(data.scenario);
      setAnalysis(data.analysis);
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Failed to analyze scenario');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCustomUpload = async (text: string, description?: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await uploadClinicalText(text, description);
      setSelectedScenarioId(null);
      setCurrentScenario({
        id: 0,
        title: description || 'Custom Clinical Note Upload',
        description: text.substring(0, 140) + '...',
        target_state: result.analysis.reasoning_result.state,
      });
      setAnalysis(result.analysis);
    } catch (err: any) {
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-slate-100">
      {/* Top Application Bar */}
      <header className="bg-white border-b border-slate-200 px-6 py-3.5 flex items-center justify-between shrink-0 shadow-xs z-10">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-blue-600 text-white font-black text-lg flex items-center justify-center shadow-xs">
            W
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-slate-900 tracking-tight text-base">
                WARRANT
              </span>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
                AMI / Cardiac CDS
              </span>
            </div>
            <p className="text-[11px] text-slate-500 font-medium">
              Evidence-Aware Clinical Decision Support System
            </p>
          </div>
        </div>

        {/* Principle Banner */}
        <div className="hidden lg:flex items-center gap-2 text-xs bg-slate-50 border border-slate-200 px-3.5 py-1.5 rounded-lg text-slate-600 font-mono">
          <span className="text-blue-600 font-bold">CORE PRINCIPLE:</span>
          <span>LLM proposes/structures/explains. Deterministic logic verifies/decides.</span>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsUploadOpen(true)}
            className="text-xs font-semibold px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors shadow-xs flex items-center gap-1.5"
          >
            <span>+</span> Upload Case
          </button>
        </div>
      </header>

      {/* Error alert */}
      {error && (
        <div className="bg-rose-50 border-b border-rose-200 px-6 py-2.5 text-xs text-rose-800 flex items-center justify-between shrink-0">
          <span className="font-medium">⚠️ {error}</span>
          <button
            onClick={() => setError(null)}
            className="text-rose-500 hover:text-rose-800 font-bold ml-4"
          >
            ✕
          </button>
        </div>
      )}

      {/* Main Container */}
      <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
        <ScenarioList
          scenarios={scenarios}
          selectedId={selectedScenarioId}
          onSelect={handleSelectScenario}
          isLoading={isLoading}
          onOpenUpload={() => setIsUploadOpen(true)}
        />

        <AnalysisView
          analysis={analysis}
          scenario={currentScenario}
          isLoading={isLoading}
          onRerun={
            selectedScenarioId !== null
              ? () => handleSelectScenario(selectedScenarioId)
              : undefined
          }
        />
      </div>

      {/* Upload Modal */}
      <CustomUploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUpload={handleCustomUpload}
        isLoading={isLoading}
      />
    </div>
  );
};

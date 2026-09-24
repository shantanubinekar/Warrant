import React, { useEffect, useState } from 'react';
import { Plus, AlertTriangle, X } from 'lucide-react';
import {
  ScenarioSummary,
  AnalysisResponse,
} from './types';
import {
  fetchScenarios,
  analyzeScenario,
  uploadClinicalText,
  uploadClinicalFile,
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

  const handleFileUpload = async (file: File, description?: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await uploadClinicalFile(file, description);
      setSelectedScenarioId(null);
      setCurrentScenario({
        id: 0,
        title: description || `Uploaded File: ${file.name}`,
        description: `Extracted from uploaded file "${file.name}"`,
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
    <div className="flex flex-col h-screen overflow-hidden bg-paper">
      {/* Instrument strip */}
      <header className="bg-ink text-paper px-6 py-3 flex items-center justify-between shrink-0 z-10">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded border border-paper/20 flex items-center justify-center font-mono font-bold text-sm text-paper">
            W
          </div>
          <div>
            <div className="flex items-baseline gap-2">
              <span className="font-mono font-semibold tracking-tight text-sm text-paper">
                WARRANT
              </span>
              <span className="text-[10px] font-mono text-paper/50">
                AMI · Cardiac CDS
              </span>
            </div>
            <p className="text-[11px] text-paper/60 leading-none mt-0.5">
              Evidence-aware clinical decision support
            </p>
          </div>
        </div>

        {/* Principle strip */}
        <div className="hidden lg:flex items-center gap-2 text-[11px] font-mono text-paper/70">
          <span className="text-signal-soft/90 font-semibold">PRINCIPLE</span>
          <span className="text-paper/30">/</span>
          <span>LLM proposes, structures, explains. Deterministic logic verifies, decides.</span>
        </div>

        <button
          onClick={() => setIsUploadOpen(true)}
          className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 bg-signal hover:bg-signal-dark text-white rounded transition-colors"
        >
          <Plus size={14} /> Upload case
        </button>
      </header>

      {/* Error alert */}
      {error && (
        <div className="bg-state-critical-soft border-b border-state-critical-line px-6 py-2.5 text-xs text-state-critical flex items-center justify-between shrink-0">
          <span className="font-medium flex items-center gap-1.5">
            <AlertTriangle size={14} /> {error}
          </span>
          <button
            onClick={() => setError(null)}
            className="text-state-critical/70 hover:text-state-critical"
          >
            <X size={14} />
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
        onUploadFile={handleFileUpload}
        isLoading={isLoading}
      />
    </div>
  );
};

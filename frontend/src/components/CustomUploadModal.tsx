import React, { useState } from 'react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onUpload: (text: string, description?: string) => Promise<void>;
  isLoading: boolean;
}

const SAMPLE_TEXT = `Patient: 64-year-old male with acute retrosternal chest pain radiating to left shoulder and jaw, onset 90 minutes ago.
ECG: Significant ST depression in leads V4-V6 with T wave inversion. No ST elevation. Good quality recording.
Laboratory: High-sensitivity cardiac troponin I (Abbott Architect STAT) 115 ng/L at 14:00 (baseline at 11:00 was 12 ng/L).
History: Hypertension, Type 2 diabetes mellitus, non-smoker. No prior MI or coronary interventions.`;

export const CustomUploadModal: React.FC<Props> = ({
  isOpen,
  onClose,
  onUpload,
  isLoading,
}) => {
  const [text, setText] = useState('');
  const [description, setDescription] = useState('');
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) {
      setError('Please provide clinical text to analyze.');
      return;
    }
    setError(null);
    try {
      await onUpload(text, description || undefined);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Analysis failed');
    }
  };

  const handleUseSample = () => {
    setText(SAMPLE_TEXT);
    setDescription('Clinical presentation: Acute chest pain with serial hs-cTnI rise');
    setError(null);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
      <div className="bg-white rounded-2xl max-w-2xl w-full shadow-2xl border border-slate-200 overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        <div className="px-6 py-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-900">
              Custom Clinical Document / Note Upload (Mode B)
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              LLM extracts structured evidence with confidence gating → Deterministic logic verifies/decides.
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 font-bold text-lg p-1"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 text-xs rounded-lg">
              {error}
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Case Label / Description (Optional)
            </label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g. ED presentation with atypical symptoms"
              className="w-full text-sm px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-xs font-semibold text-slate-700">
                Clinical Text (Discharge note, ED summary, Lab/ECG report)
              </label>
              <button
                type="button"
                onClick={handleUseSample}
                className="text-xs text-blue-600 hover:text-blue-800 font-medium"
              >
                Insert Sample Case
              </button>
            </div>
            <textarea
              rows={8}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Paste unstructured clinical note, troponin lab values, or ECG interpretation here..."
              className="w-full text-sm font-mono p-3 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 leading-relaxed"
            />
          </div>

          <div className="pt-2 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={isLoading}
              className="px-4 py-2 text-sm text-slate-600 hover:text-slate-800 font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-semibold shadow-xs disabled:opacity-50 flex items-center gap-2"
            >
              {isLoading ? (
                <>
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                  Processing Pipeline...
                </>
              ) : (
                'Extract & Verify Evidence'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

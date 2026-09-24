import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FileText, Loader2, Sparkles, UploadCloud, X } from 'lucide-react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onUpload: (text: string, description?: string) => Promise<void>;
  onUploadFile: (file: File, description?: string) => Promise<void>;
  isLoading: boolean;
}

const SAMPLE_TEXT = `Patient: 64-year-old male with acute retrosternal chest pain radiating to left shoulder and jaw, onset 90 minutes ago.
ECG: Significant ST depression in leads V4-V6 with T wave inversion. No ST elevation. Good quality recording.
Laboratory: High-sensitivity cardiac troponin I (Abbott Architect STAT) 115 ng/L at 14:00 (baseline at 11:00 was 12 ng/L).
History: Hypertension, Type 2 diabetes mellitus, non-smoker. No prior MI or coronary interventions.`;

const ACCEPTED_EXTENSIONS = '.pdf,.docx,.txt,.md';

type Mode = 'paste' | 'file';

export const CustomUploadModal: React.FC<Props> = ({
  isOpen,
  onClose,
  onUpload,
  onUploadFile,
  isLoading,
}) => {
  const [mode, setMode] = useState<Mode>('paste');
  const [text, setText] = useState('');
  const [description, setDescription] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  const resetAndClose = () => {
    setText('');
    setFile(null);
    setError(null);
    onClose();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (mode === 'paste') {
      if (!text.trim()) {
        setError('Please provide clinical text to analyze.');
        return;
      }
      try {
        await onUpload(text, description || undefined);
        resetAndClose();
      } catch (err: any) {
        setError(err.message || 'Analysis failed');
      }
    } else {
      if (!file) {
        setError('Please choose a file to upload.');
        return;
      }
      try {
        await onUploadFile(file, description || undefined);
        resetAndClose();
      } catch (err: any) {
        setError(err.message || 'File analysis failed');
      }
    }
  };

  const handleUseSample = () => {
    setText(SAMPLE_TEXT);
    setDescription('Clinical presentation: Acute chest pain with serial hs-cTnI rise');
    setError(null);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/40"
        >
          <motion.div
            initial={{ opacity: 0, y: 8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.98 }}
            transition={{ duration: 0.18, ease: 'easeOut' }}
            className="bg-paper-raised rounded max-w-2xl w-full shadow-bezel border border-line overflow-hidden"
          >
            <div className="px-6 py-4 border-b border-line flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-ink">
                  Custom clinical note or file
                </h2>
                <p className="text-xs text-ink-faint mt-0.5">
                  LLM extracts structured evidence with confidence gating → deterministic logic verifies/decides.
                </p>
              </div>
              <button
                onClick={onClose}
                className="text-ink-faint hover:text-ink p-1 rounded"
              >
                <X size={16} />
              </button>
            </div>

            {/* Mode toggle */}
            <div className="px-6 pt-4 flex gap-2">
              <button
                type="button"
                onClick={() => setMode('paste')}
                className={`flex-1 text-xs font-semibold py-2 rounded border transition-colors ${
                  mode === 'paste'
                    ? 'bg-signal text-white border-signal'
                    : 'bg-paper-raised text-ink-soft border-line hover:bg-paper'
                }`}
              >
                Paste text
              </button>
              <button
                type="button"
                onClick={() => setMode('file')}
                className={`flex-1 text-xs font-semibold py-2 rounded border transition-colors ${
                  mode === 'file'
                    ? 'bg-signal text-white border-signal'
                    : 'bg-paper-raised text-ink-soft border-line hover:bg-paper'
                }`}
              >
                Upload file (PDF / DOCX / TXT)
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              {error && (
                <div className="p-3 bg-state-critical-soft border border-state-critical-line text-state-critical text-xs rounded">
                  {error}
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-ink-soft mb-1">
                  Case label / description (optional)
                </label>
                <input
                  type="text"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="e.g. ED presentation with atypical symptoms"
                  className="w-full text-sm px-3 py-2 bg-paper border border-line rounded focus:outline-none focus:ring-2 focus:ring-signal/40"
                />
              </div>

              {mode === 'paste' ? (
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="block text-xs font-semibold text-ink-soft">
                      Clinical text (discharge note, ED summary, lab/ECG report)
                    </label>
                    <button
                      type="button"
                      onClick={handleUseSample}
                      className="text-xs text-signal hover:text-signal-dark font-medium flex items-center gap-1"
                    >
                      <Sparkles size={12} /> Insert sample case
                    </button>
                  </div>
                  <textarea
                    rows={8}
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    placeholder="Paste unstructured clinical note, troponin lab values, or ECG interpretation here..."
                    className="w-full text-sm font-mono p-3 bg-paper border border-line rounded focus:outline-none focus:ring-2 focus:ring-signal/40 leading-relaxed"
                  />
                </div>
              ) : (
                <div>
                  <label className="block text-xs font-semibold text-ink-soft mb-1">
                    Prescription / report file
                  </label>
                  <label className="flex flex-col items-center justify-center gap-2 border-2 border-dashed border-line rounded py-8 px-4 cursor-pointer hover:border-signal/50 hover:bg-signal-soft/40 transition-colors">
                    {file ? <FileText className="text-signal" size={22} /> : <UploadCloud className="text-ink-faint" size={22} />}
                    {file ? (
                      <span className="text-sm font-semibold text-ink">{file.name}</span>
                    ) : (
                      <span className="text-sm text-ink-faint">
                        Click to choose a file, or drag it here
                      </span>
                    )}
                    <input
                      type="file"
                      accept={ACCEPTED_EXTENSIONS}
                      className="hidden"
                      onChange={(e) => setFile(e.target.files?.[0] || null)}
                    />
                  </label>
                  <p className="text-[11px] text-ink-faint mt-1.5">
                    Supported: PDF, DOCX, TXT — text-based files only (scanned/photo pages
                    aren't OCR'd; paste the text instead if that's what you have).
                  </p>
                </div>
              )}

              <div className="pt-2 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={onClose}
                  disabled={isLoading}
                  className="px-4 py-2 text-sm text-ink-soft hover:text-ink font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isLoading}
                  className="px-5 py-2 bg-signal hover:bg-signal-dark text-white rounded text-sm font-semibold disabled:opacity-50 flex items-center gap-2"
                >
                  {isLoading ? (
                    <>
                      <Loader2 size={15} className="animate-spin" />
                      Processing pipeline…
                    </>
                  ) : (
                    'Extract & verify evidence'
                  )}
                </button>
              </div>
            </form>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { HelpCircle, Loader2, Send } from 'lucide-react';
import { ReasoningResult } from '../types';
import { askAboutCase } from '../api/client';

interface Props {
  caseId: string;
  reasoningResult: ReasoningResult;
}

interface QAEntry {
  question: string;
  answer: string;
}

/**
 * Free-form Q&A tied to the currently displayed case. This is deliberately
 * NOT part of the deterministic reasoning output above it — it's a
 * separate, best-effort LLM answer, grounded in this case's findings but
 * not verified by the reasoning engine. Kept visually distinct (caution
 * accent) so it's never mistaken for a verified clinical conclusion.
 */
export const CaseQuestionBox: React.FC<Props> = ({ caseId, reasoningResult }) => {
  const [question, setQuestion] = useState('');
  const [history, setHistory] = useState<QAEntry[]>([]);
  const [isAsking, setIsAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault();
    const q = question.trim();
    if (!q) return;

    setError(null);
    setIsAsking(true);
    try {
      const result = await askAboutCase(q, reasoningResult, caseId);
      setHistory((prev) => [...prev, { question: q, answer: result.answer }]);
      setQuestion('');
    } catch (err: any) {
      setError(err.message || 'Failed to get an answer');
    } finally {
      setIsAsking(false);
    }
  };

  return (
    <div className="bg-paper-raised rounded border border-line p-5 space-y-3">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h3 className="text-sm font-semibold text-ink flex items-center gap-2">
          <HelpCircle size={15} className="text-state-caution" /> Ask about this case
        </h3>
        <span className="text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded border border-state-caution-line text-state-caution">
          LLM ANSWER · NOT VERIFIED REASONING
        </span>
      </div>
      <p className="text-xs text-ink-faint">
        Ask anything about this case. If it's outside what this case's evidence can
        actually support, the answer will say so honestly instead of guessing.
      </p>

      <AnimatePresence initial={false}>
        {history.length > 0 && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="space-y-3 max-h-72 overflow-y-auto pr-1"
          >
            {history.map((entry, i) => (
              <div key={i} className="space-y-1.5">
                <div className="text-xs font-semibold text-ink bg-paper border border-line rounded px-3 py-2">
                  {entry.question}
                </div>
                <div className="text-xs text-ink-soft bg-state-caution-soft/50 border border-state-caution-line rounded px-3 py-2 leading-relaxed whitespace-pre-wrap">
                  {entry.answer}
                </div>
              </div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {error && (
        <div className="p-2.5 bg-state-critical-soft border border-state-critical-line text-state-critical text-xs rounded">
          {error}
        </div>
      )}

      <form onSubmit={handleAsk} className="flex items-center gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. Could this also mean he has cancer?"
          disabled={isAsking}
          className="flex-1 text-sm px-3 py-2 bg-paper border border-line rounded focus:outline-none focus:ring-2 focus:ring-state-caution/40 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={isAsking || !question.trim()}
          className="px-4 py-2 bg-state-caution hover:brightness-95 text-white rounded text-sm font-semibold disabled:opacity-50 flex items-center gap-2 shrink-0"
        >
          {isAsking ? <Loader2 size={15} className="animate-spin" /> : <Send size={14} />}
        </button>
      </form>
    </div>
  );
};

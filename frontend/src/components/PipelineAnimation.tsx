import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Play,
  Pause,
  SkipForward,
  SkipBack,
  FastForward,
  RotateCcw,
  Sparkles,
  ArrowRight,
  CheckCircle2,
  ListOrdered,
  Layers,
  Calculator,
  Workflow,
  Keyboard,
} from 'lucide-react';
import { TraceResponse, TraceStage } from '../types';

interface PipelineAnimationProps {
  trace: TraceResponse;
  onSelectSentence: (index: number) => void;
  onSkipToResults: () => void;
}

export const PipelineAnimation: React.FC<PipelineAnimationProps> = ({
  trace,
  onSelectSentence,
  onSkipToResults,
}) => {
  const [currentStageIdx, setCurrentStageIdx] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(2000); // 2000ms default

  const timerRef = useRef<number | null>(null);

  const stages = trace.stages;
  const currentStage: TraceStage = stages[currentStageIdx] || stages[0];

  // Auto-play timer
  useEffect(() => {
    if (isPlaying) {
      timerRef.current = window.setInterval(() => {
        setCurrentStageIdx((prev) => {
          if (prev >= stages.length - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, playbackSpeed);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isPlaying, stages.length, playbackSpeed]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if user is typing in a textarea or input
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes((e.target as HTMLElement).tagName)) {
        return;
      }
      if (e.code === 'Space') {
        e.preventDefault();
        setIsPlaying((prev) => !prev);
      } else if (e.code === 'ArrowRight') {
        e.preventDefault();
        setIsPlaying(false);
        setCurrentStageIdx((prev) => Math.min(stages.length - 1, prev + 1));
      } else if (e.code === 'ArrowLeft') {
        e.preventDefault();
        setIsPlaying(false);
        setCurrentStageIdx((prev) => Math.max(0, prev - 1));
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [stages.length]);

  const stepForward = () => {
    setIsPlaying(false);
    setCurrentStageIdx((prev) => Math.min(stages.length - 1, prev + 1));
  };

  const stepBack = () => {
    setIsPlaying(false);
    setCurrentStageIdx((prev) => Math.max(0, prev - 1));
  };

  const resetAnimation = () => {
    setIsPlaying(false);
    setCurrentStageIdx(0);
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-5 space-y-5">
      {/* Header & Controls Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-700 flex items-center justify-center font-bold text-xs">
            <Workflow className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold text-slate-900">
                Interactive Pipeline Execution Trace
              </h2>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                Step {currentStageIdx + 1} of {stages.length}
              </span>
            </div>
            <p className="text-xs text-slate-500">
              Live step-by-step animation driven by real data from your transcript
            </p>
          </div>
        </div>

        {/* Playback Controls */}
        <div className="flex items-center flex-wrap gap-2 text-xs">
          {/* Sentence Selector */}
          {trace.available_sentences.length > 1 && (
            <select
              value={trace.sample_sentence_index}
              onChange={(e) => onSelectSentence(Number(e.target.value))}
              className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
              title="Select sample sentence from transcript to animate"
            >
              {trace.available_sentences.map((s) => (
                <option key={s.index} value={s.index}>
                  Sentence #{s.index + 1} ({s.word_count} words)
                </option>
              ))}
            </select>
          )}

          {/* Reset */}
          <button
            type="button"
            onClick={resetAnimation}
            className="p-1.5 rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-600 transition"
            title="Reset to Stage 1"
            aria-label="Reset to Stage 1"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>

          {/* Step Back */}
          <button
            type="button"
            onClick={stepBack}
            disabled={currentStageIdx === 0}
            className="p-1.5 rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-600 disabled:opacity-40 transition"
            title="Previous Stage (ArrowLeft)"
            aria-label="Previous Stage"
          >
            <SkipBack className="w-3.5 h-3.5" />
          </button>

          {/* Play / Pause */}
          <button
            type="button"
            onClick={() => setIsPlaying(!isPlaying)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-semibold text-white bg-indigo-600 hover:bg-indigo-700 transition shadow-xs"
            title="Play / Pause Animation (Spacebar)"
            aria-label={isPlaying ? 'Pause Animation' : 'Play Animation'}
          >
            {isPlaying ? (
              <>
                <Pause className="w-3.5 h-3.5 fill-white" />
                <span>Pause</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-white" />
                <span>Play</span>
              </>
            )}
          </button>

          {/* Step Forward */}
          <button
            type="button"
            onClick={stepForward}
            disabled={currentStageIdx === stages.length - 1}
            className="p-1.5 rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-600 disabled:opacity-40 transition"
            title="Next Stage (ArrowRight)"
            aria-label="Next Stage"
          >
            <SkipForward className="w-3.5 h-3.5" />
          </button>

          {/* Speed Selector */}
          <div className="flex items-center gap-1 bg-slate-100 p-0.5 rounded-lg border border-slate-200 text-[11px] font-mono">
            <button
              onClick={() => setPlaybackSpeed(3000)}
              className={`px-1.5 py-0.5 rounded ${playbackSpeed === 3000 ? 'bg-white font-bold text-indigo-700 shadow-2xs' : 'text-slate-500'}`}
              title="Slow speed (3s per step)"
            >
              0.5x
            </button>
            <button
              onClick={() => setPlaybackSpeed(2000)}
              className={`px-1.5 py-0.5 rounded ${playbackSpeed === 2000 ? 'bg-white font-bold text-indigo-700 shadow-2xs' : 'text-slate-500'}`}
              title="Normal speed (2s per step)"
            >
              1x
            </button>
            <button
              onClick={() => setPlaybackSpeed(1000)}
              className={`px-1.5 py-0.5 rounded ${playbackSpeed === 1000 ? 'bg-white font-bold text-indigo-700 shadow-2xs' : 'text-slate-500'}`}
              title="Fast speed (1s per step)"
            >
              2x
            </button>
          </div>

          {/* Skip to Results */}
          <button
            type="button"
            onClick={onSkipToResults}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 font-medium transition"
            title="Scroll directly to ranked collocation tables"
          >
            <FastForward className="w-3.5 h-3.5 text-slate-500" />
            <span>Skip to Results</span>
          </button>
        </div>
      </div>

      {/* Stage Breadcrumb Stepper */}
      <div className="grid grid-cols-3 sm:grid-cols-9 gap-1.5">
        {stages.map((stg, idx) => {
          const isActive = idx === currentStageIdx;
          const isDone = idx < currentStageIdx;
          return (
            <button
              key={stg.id}
              onClick={() => {
                setIsPlaying(false);
                setCurrentStageIdx(idx);
              }}
              className={`flex flex-col items-center text-center p-2 rounded-xl transition border text-[11px] ${
                isActive
                  ? 'bg-indigo-50 border-indigo-300 text-indigo-900 font-bold ring-2 ring-indigo-500/20'
                  : isDone
                  ? 'bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100'
                  : 'bg-white border-slate-100 text-slate-400 hover:border-slate-200'
              }`}
            >
              <span className={`w-5 h-5 rounded-full flex items-center justify-center font-mono text-[10px] mb-1 ${
                isActive ? 'bg-indigo-600 text-white' : isDone ? 'bg-emerald-500 text-white' : 'bg-slate-200 text-slate-600'
              }`}>
                {isDone ? '✓' : idx + 1}
              </span>
              <span className="truncate w-full font-medium">{stg.id.replace('_', ' ')}</span>
            </button>
          );
        })}
      </div>

      {/* Main Animated Stage Viewer */}
      <div className="min-h-[260px] bg-slate-50/70 border border-slate-200 rounded-xl p-5 relative overflow-hidden">
        <AnimatePresence mode="wait">
          <motion.div
            key={currentStage.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.25 }}
            className="space-y-4"
          >
            {/* Stage Title and Subtitle */}
            <div className="flex items-start justify-between gap-4">
              <div>
                <span className="text-xs font-mono font-bold text-indigo-600 uppercase tracking-wider block">
                  {currentStage.title}
                </span>
                <h3 className="text-base font-bold text-slate-900">
                  {currentStage.subtitle}
                </h3>
              </div>
              <span className="text-xs text-slate-500 max-w-sm text-right hidden sm:block">
                {currentStage.description}
              </span>
            </div>

            {/* Dynamic Content Per Stage */}
            <div className="pt-2">
              {/* Stage 1: Raw Text */}
              {currentStage.id === 'raw_text' && (
                <div className="p-4 rounded-xl bg-white border border-slate-200 font-mono text-sm text-slate-800 shadow-2xs leading-relaxed">
                  "{currentStage.data.sentence}"
                </div>
              )}

              {/* Stage 2: Sentence Segmentation */}
              {currentStage.id === 'sentence_split' && (
                <div className="space-y-2">
                  <div className="text-xs text-slate-500 font-medium">
                    Segmented sentence #{currentStage.data.sentence_index + 1} of {currentStage.data.total_sentences}:
                  </div>
                  <div className="p-3.5 rounded-xl bg-white border-2 border-indigo-400 font-mono text-sm text-indigo-950 shadow-xs">
                    "{currentStage.data.chosen_sentence}"
                  </div>
                  <div className="text-[11px] text-slate-400 italic">
                    Boundary Guard: N-grams are extracted strictly within sentence boundaries to avoid false co-occurrences across speaker turns.
                  </div>
                </div>
              )}

              {/* Stage 3: Token Cleaning */}
              {currentStage.id === 'tokenize_clean' && (
                <div className="space-y-3">
                  <div className="flex flex-wrap gap-2">
                    {currentStage.data.token_transformations?.map((item: any, i: number) => (
                      <span
                        key={i}
                        className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-mono border ${
                          item.dropped
                            ? 'bg-rose-50 text-rose-500 border-rose-200 line-through'
                            : item.was_clitic
                            ? 'bg-amber-50 text-amber-800 border-amber-300 font-bold'
                            : 'bg-white text-slate-800 border-slate-200'
                        }`}
                        title={
                          item.dropped
                            ? `Dropped token: '${item.original}'`
                            : item.was_clitic
                            ? `Expanded clitic: '${item.original}' -> '${item.cleaned}'`
                            : `Clean token: '${item.cleaned}'`
                        }
                      >
                        {item.cleaned || item.original}
                        {item.was_clitic && <span className="text-[10px] text-amber-600 font-sans">expanded</span>}
                      </span>
                    ))}
                  </div>
                  <div className="text-[11px] text-slate-500">
                    {currentStage.data.original_count} raw tokens filtered down to {currentStage.data.cleaned_count} lexical tokens.
                  </div>
                </div>
              )}

              {/* Stage 4: Lemmatization */}
              {currentStage.id === 'lemmatize' && (
                <div className="space-y-3">
                  <div className="flex flex-wrap gap-2">
                    {currentStage.data.lemma_transformations?.map((item: any, i: number) => (
                      <div
                        key={i}
                        className={`p-2 rounded-xl text-xs font-mono border flex flex-col items-center min-w-[70px] ${
                          item.changed
                            ? 'bg-emerald-50 text-emerald-900 border-emerald-300 shadow-xs'
                            : 'bg-white text-slate-800 border-slate-200'
                        }`}
                      >
                        <span className="font-bold text-sm text-slate-900">{item.lemma}</span>
                        <div className="flex items-center gap-1 text-[10px] text-slate-400 font-sans mt-0.5">
                          <span>{item.token}</span>
                          <span className="font-mono text-indigo-600 font-semibold">[{item.pos_tag}]</span>
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="text-[11px] text-slate-500">
                    Averaged Perceptron POS tagger maps nouns, verbs, adjectives, and adverbs to WordNet lemmas.
                  </div>
                </div>
              )}

              {/* Stage 5: N-gram extraction */}
              {currentStage.id === 'ngram_extraction' && (
                <div className="space-y-3">
                  <div className="text-xs text-slate-600 font-medium">
                    Sentence-internal sliding window candidates:
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {currentStage.data.extracted_bigrams?.map((bg: string, i: number) => {
                      const isChosen = bg === currentStage.data.chosen_target_phrase;
                      return (
                        <span
                          key={i}
                          className={`px-3 py-1.5 rounded-xl text-xs font-mono border transition ${
                            isChosen
                              ? 'bg-brand-600 text-white font-bold border-brand-700 shadow-md ring-2 ring-brand-400/30'
                              : 'bg-white text-slate-700 border-slate-200 hover:border-slate-300'
                          }`}
                        >
                          {bg}
                          {isChosen && <span className="ml-1 text-[10px] font-sans font-normal opacity-90">(target)</span>}
                        </span>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Stage 6: Corpus Counting */}
              {currentStage.id === 'counting' && (
                <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
                  <div className="p-3 bg-white rounded-xl border border-slate-200 shadow-2xs">
                    <span className="text-[11px] text-slate-400 font-medium block">Joint Co-occurrence (O11)</span>
                    <span className="text-lg font-bold font-mono text-brand-600">{currentStage.data.f_joint_o11}</span>
                    <span className="text-[10px] text-slate-500 block">"{currentStage.data.phrase}"</span>
                  </div>
                  <div className="p-3 bg-white rounded-xl border border-slate-200 shadow-2xs">
                    <span className="text-[11px] text-slate-400 font-medium block">Left Marginal f(w1)</span>
                    <span className="text-lg font-bold font-mono text-slate-800">{currentStage.data.f_w1_left}</span>
                    <span className="text-[10px] text-slate-500 block">w1 = '{currentStage.data.w1}'</span>
                  </div>
                  <div className="p-3 bg-white rounded-xl border border-slate-200 shadow-2xs">
                    <span className="text-[11px] text-slate-400 font-medium block">Right Marginal f(w2)</span>
                    <span className="text-lg font-bold font-mono text-slate-800">{currentStage.data.f_w2_right}</span>
                    <span className="text-[10px] text-slate-500 block">w2 = '{currentStage.data.w2}'</span>
                  </div>
                  <div className="p-3 bg-white rounded-xl border border-slate-200 shadow-2xs">
                    <span className="text-[11px] text-slate-400 font-medium block">Total Bigram Tokens (N)</span>
                    <span className="text-lg font-bold font-mono text-indigo-700">{currentStage.data.total_bigram_tokens_N}</span>
                    <span className="text-[10px] text-slate-500 block">Sentence-internal sum</span>
                  </div>
                </div>
              )}

              {/* Stage 7: Contingency Table (Animated Cell Filling) */}
              {currentStage.id === 'contingency_table' && (
                <div className="space-y-3">
                  <div className="text-xs text-slate-600 font-medium">
                    Animating 4-cell distribution for "{currentStage.data.phrase}":
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono">
                    {currentStage.data.cells_step_by_step?.map((c: any, i: number) => (
                      <motion.div
                        key={c.cell}
                        initial={{ scale: 0.8, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        transition={{ delay: i * 0.15, duration: 0.3 }}
                        className="p-3.5 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col justify-between"
                      >
                        <div className="flex items-center justify-between text-xs text-indigo-700 font-bold mb-1">
                          <span>{c.cell}</span>
                          <span className="text-[10px] text-slate-400 font-sans font-normal">{c.formula}</span>
                        </div>
                        <div className="text-xl font-bold text-slate-900 my-1">{c.value}</div>
                        <span className="text-[10px] text-slate-500 font-sans leading-tight">{c.label}</span>
                      </motion.div>
                    ))}
                  </div>
                </div>
              )}

              {/* Stage 8: Association Scoring */}
              {currentStage.id === 'scoring' && (
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5 font-mono">
                  {Object.entries(currentStage.data.scores || {}).map(([metric, val]: any) => (
                    <div key={metric} className="p-3 bg-white rounded-xl border border-slate-200 shadow-2xs text-center">
                      <span className="text-[10px] text-slate-400 font-sans uppercase block">{metric}</span>
                      <span className="text-base font-bold text-brand-600">
                        {val !== null ? Number(val).toFixed(3) : 'n/a'}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {/* Stage 9: Global Ranking */}
              {currentStage.id === 'ranking' && (
                <div className="space-y-3">
                  <div className="flex items-center gap-2 p-3 rounded-xl bg-brand-50 border border-brand-200 text-brand-900 text-xs">
                    <CheckCircle2 className="w-4 h-4 text-brand-600 shrink-0" />
                    <span>
                      Target collocation <strong>"{currentStage.data.phrase}"</strong> placed at{' '}
                      <strong>Rank #{currentStage.data.target_rank ?? 'N/A'}</strong> out of{' '}
                      {currentStage.data.total_candidates} candidates.
                    </span>
                  </div>

                  <div className="flex flex-wrap gap-2 text-xs">
                    {currentStage.data.top_5_pmi?.map((item: any) => (
                      <span
                        key={item.rank}
                        className={`px-3 py-1.5 rounded-xl font-mono border ${
                          item.phrase === currentStage.data.phrase
                            ? 'bg-brand-600 text-white font-bold border-brand-700 shadow-xs'
                            : 'bg-white text-slate-700 border-slate-200'
                        }`}
                      >
                        #{item.rank} {item.phrase} ({Number(item.score).toFixed(2)})
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Keyboard Shortcut Hint */}
      <div className="flex items-center justify-between text-[11px] text-slate-400 px-1">
        <div className="flex items-center gap-1.5">
          <Keyboard className="w-3.5 h-3.5" />
          <span>Shortcuts: Space (Play/Pause) • Left/Right Arrows (Step)</span>
        </div>
        <span>Accessible animation • SVG / DOM / CSS transitions</span>
      </div>
    </div>
  );
};

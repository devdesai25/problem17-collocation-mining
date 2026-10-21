import React from 'react';
import { Sliders, Play, Loader2, Filter, BarChart3, HelpCircle } from 'lucide-react';
import { BigramMetric, NgramOrder } from '../types';

interface ControlsBarProps {
  ngram: NgramOrder;
  onChangeNgram: (val: NgramOrder) => void;
  minFreq: number;
  onChangeMinFreq: (val: number) => void;
  metric: BigramMetric;
  onChangeMetric: (val: BigramMetric) => void;
  dropStopwords: boolean;
  onChangeDropStopwords: (val: boolean) => void;
  topK: number;
  onChangeTopK: (val: number) => void;
  onRunAnalysis: () => void;
  isAnalyzing: boolean;
  disabled: boolean;
}

export const ControlsBar: React.FC<ControlsBarProps> = ({
  ngram,
  onChangeNgram,
  minFreq,
  onChangeMinFreq,
  metric,
  onChangeMetric,
  dropStopwords,
  onChangeDropStopwords,
  topK,
  onChangeTopK,
  onRunAnalysis,
  isAnalyzing,
  disabled,
}) => {
  const metricOptions: Array<{ id: BigramMetric; label: string; tag: string }> = [
    { id: 'pmi', label: 'Pointwise Mutual Inf (PMI)', tag: 'Rare terms' },
    { id: 'npmi', label: 'Normalized PMI (NPMI)', tag: '[-1, +1] bounded' },
    { id: 'pmi2', label: 'PMI² (Power of 2)', tag: 'Squared' },
    { id: 'pmi3', label: 'PMI³ (Power of 3)', tag: 'Cubed' },
    { id: 'chi_sq', label: "Pearson Chi-Square (χ²)", tag: 'Non-directional' },
    { id: 'chi_sq_yates', label: "Yates-Corrected χ²", tag: 'Continuity penalty' },
    { id: 'student_t', label: "Student's t-test", tag: 'High freq bias' },
    { id: 'likelihood_ratio', label: "Log-Likelihood (Dunning G²)", tag: 'Sparse robust' },
  ];

  return (
    <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-4 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-slate-100 text-slate-700 flex items-center justify-center font-bold text-xs">
            2
          </div>
          <div>
            <h2 className="text-sm font-semibold text-slate-900">
              Statistical Parameters & Mining Controls
            </h2>
            <p className="text-xs text-slate-500">
              Configure N-gram order, association paradigm, frequency threshold, and stopword policy
            </p>
          </div>
        </div>

        {/* Primary Action Button */}
        <button
          type="button"
          onClick={onRunAnalysis}
          disabled={disabled || isAnalyzing}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold text-white bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-700 hover:to-indigo-700 shadow-md shadow-brand-500/20 transition active:scale-98 disabled:opacity-50 disabled:pointer-events-none"
        >
          {isAnalyzing ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Computing Association Metrics...</span>
            </>
          ) : (
            <>
              <Play className="w-4 h-4 fill-white" />
              <span>Run Collocation Mining</span>
            </>
          )}
        </button>
      </div>

      {/* Grid of Controls */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* N-gram Order */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-slate-700 flex items-center gap-1">
            <span>N-Gram Order</span>
          </label>
          <div className="grid grid-cols-2 gap-1 p-1 bg-slate-100/80 rounded-xl border border-slate-200/60">
            <button
              type="button"
              onClick={() => onChangeNgram(2)}
              className={`py-1 text-xs font-medium rounded-lg transition ${
                ngram === 2
                  ? 'bg-white text-slate-900 shadow-xs font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Bigram (2)
            </button>
            <button
              type="button"
              onClick={() => onChangeNgram(3)}
              className={`py-1 text-xs font-medium rounded-lg transition ${
                ngram === 3
                  ? 'bg-white text-slate-900 shadow-xs font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Trigram (3)
            </button>
          </div>
        </div>

        {/* Primary Metric Selector */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-slate-700 flex items-center justify-between">
            <span>Primary Metric</span>
            {ngram === 3 && (
              <span className="text-[10px] text-amber-600 font-normal">Trigram uses PMI</span>
            )}
          </label>
          <select
            value={metric}
            onChange={(e) => onChangeMetric(e.target.value as BigramMetric)}
            disabled={ngram === 3}
            className="w-full text-xs bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 font-medium text-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 disabled:opacity-50 cursor-pointer"
          >
            {metricOptions.map((opt) => (
              <option key={opt.id} value={opt.id}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Minimum Frequency Slider */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-slate-700">Min Frequency (f ≥ {minFreq})</span>
            <span className="text-[11px] font-mono font-medium text-brand-600 bg-brand-50 px-1.5 py-0.5 rounded border border-brand-100">
              {minFreq}
            </span>
          </div>
          <input
            type="range"
            min={1}
            max={10}
            step={1}
            value={minFreq}
            onChange={(e) => onChangeMinFreq(Number(e.target.value))}
            className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-brand-600"
          />
          <div className="flex justify-between text-[10px] text-slate-400 font-mono px-0.5">
            <span>f≥1 (Hapax)</span>
            <span>f≥3 (Default)</span>
            <span>f≥10</span>
          </div>
        </div>

        {/* Top-K Selector */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-slate-700">Display Top-K</label>
          <select
            value={topK}
            onChange={(e) => onChangeTopK(Number(e.target.value))}
            className="w-full text-xs bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 font-medium text-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 cursor-pointer"
          >
            <option value={10}>Top 10 phrases</option>
            <option value={20}>Top 20 phrases (Standard)</option>
            <option value={50}>Top 50 phrases</option>
            <option value={100}>Top 100 phrases</option>
          </select>
        </div>

        {/* Stopword Ablation Toggle */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-slate-700">Ablation Policy</label>
          <label className="flex items-center gap-2 p-2 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 cursor-pointer transition select-none">
            <input
              type="checkbox"
              checked={dropStopwords}
              onChange={(e) => onChangeDropStopwords(e.target.checked)}
              className="w-3.5 h-3.5 text-brand-600 rounded border-slate-300 focus:ring-brand-500"
            />
            <div className="text-xs">
              <span className="font-medium text-slate-800 block">Drop Stopwords</span>
              <span className="text-[10px] text-slate-500 block">Blocks 'motion to', etc.</span>
            </div>
          </label>
        </div>
      </div>
    </div>
  );
};

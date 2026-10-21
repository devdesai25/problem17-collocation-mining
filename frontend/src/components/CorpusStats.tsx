import React from 'react';
import { AlertTriangle, Hash, Layers, FileCheck, BookOpen } from 'lucide-react';
import { CorpusStats as StatsType } from '../types';

interface CorpusStatsProps {
  stats: StatsType;
  cached?: boolean;
}

export const CorpusStats: React.FC<CorpusStatsProps> = ({ stats, cached }) => {
  return (
    <div className="space-y-3">
      {/* Small N Alert Banner */}
      {stats.warn_small_n && (
        <div className="flex items-start gap-3 p-3.5 rounded-xl bg-amber-50/90 border border-amber-200 text-amber-900 text-xs shadow-xs animate-in fade-in duration-200">
          <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <span className="font-semibold text-amber-950 block">
              Low Sample Size Warning (N = {stats.n_bigrams} Bigram Tokens)
            </span>
            <p className="text-amber-800 leading-relaxed">
              {stats.warning_message ||
                'Statistical association tests (Chi-Square, Student t, G²) require substantial token counts to satisfy asymptotic properties. Consider lowering the minimum frequency to 1 or loading a larger sample transcript.'}
            </p>
          </div>
        </div>
      )}

      {/* KPI Stats Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="bg-white p-3 rounded-xl border border-slate-200/80 shadow-2xs">
          <div className="flex items-center justify-between text-slate-500 mb-1">
            <span className="text-[11px] font-medium uppercase tracking-wider">Sentences</span>
            <FileCheck className="w-3.5 h-3.5 text-slate-400" />
          </div>
          <div className="text-lg font-bold font-mono text-slate-900">
            {stats.sentences.toLocaleString()}
          </div>
        </div>

        <div className="bg-white p-3 rounded-xl border border-slate-200/80 shadow-2xs">
          <div className="flex items-center justify-between text-slate-500 mb-1">
            <span className="text-[11px] font-medium uppercase tracking-wider">Tokens</span>
            <Hash className="w-3.5 h-3.5 text-slate-400" />
          </div>
          <div className="text-lg font-bold font-mono text-brand-600">
            {stats.tokens.toLocaleString()}
          </div>
        </div>

        <div className="bg-white p-3 rounded-xl border border-slate-200/80 shadow-2xs">
          <div className="flex items-center justify-between text-slate-500 mb-1">
            <span className="text-[11px] font-medium uppercase tracking-wider">Bigram N</span>
            <Layers className="w-3.5 h-3.5 text-slate-400" />
          </div>
          <div className="text-lg font-bold font-mono text-indigo-600">
            {stats.n_bigrams.toLocaleString()}
          </div>
          <span className="text-[10px] text-slate-400">Sentence-internal</span>
        </div>

        <div className="bg-white p-3 rounded-xl border border-slate-200/80 shadow-2xs">
          <div className="flex items-center justify-between text-slate-500 mb-1">
            <span className="text-[11px] font-medium uppercase tracking-wider">Unique Bigrams</span>
            <BookOpen className="w-3.5 h-3.5 text-slate-400" />
          </div>
          <div className="text-lg font-bold font-mono text-slate-900">
            {stats.unique_bigrams.toLocaleString()}
          </div>
        </div>

        <div className="bg-white p-3 rounded-xl border border-slate-200/80 shadow-2xs">
          <div className="flex items-center justify-between text-slate-500 mb-1">
            <span className="text-[11px] font-medium uppercase tracking-wider">Trigram N</span>
            <Layers className="w-3.5 h-3.5 text-slate-400" />
          </div>
          <div className="text-lg font-bold font-mono text-slate-900">
            {stats.n_trigrams.toLocaleString()}
          </div>
        </div>

        <div className="bg-white p-3 rounded-xl border border-slate-200/80 shadow-2xs">
          <div className="flex items-center justify-between text-slate-500 mb-1">
            <span className="text-[11px] font-medium uppercase tracking-wider">Unique Trigrams</span>
            <BookOpen className="w-3.5 h-3.5 text-slate-400" />
          </div>
          <div className="text-lg font-bold font-mono text-slate-900">
            {stats.unique_trigrams.toLocaleString()}
          </div>
        </div>
      </div>
    </div>
  );
};

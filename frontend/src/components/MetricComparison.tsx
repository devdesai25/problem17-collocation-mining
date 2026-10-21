import React from 'react';
import { Columns3, Info, ExternalLink } from 'lucide-react';
import { MetricTop5Item } from '../types';

interface MetricComparisonProps {
  perMetricTop5: Record<string, MetricTop5Item[]>;
  disagreementNote: string;
  onSelectPhrase: (phrase: string) => void;
}

export const MetricComparison: React.FC<MetricComparisonProps> = ({
  perMetricTop5,
  disagreementNote,
  onSelectPhrase,
}) => {
  const cards = [
    {
      key: 'pmi',
      title: 'Pointwise Mutual Inf (PMI)',
      badge: 'Information Gain',
      badgeColor: 'bg-blue-50 text-blue-700 border-blue-200',
      description: 'Favors specific, exclusive domain collocations. Prone to rare hapaxes.',
      items: perMetricTop5['pmi'] || [],
    },
    {
      key: 'chi_sq',
      title: 'Pearson Chi-Square (χ²)',
      badge: 'Statistical Dependence',
      badgeColor: 'bg-emerald-50 text-emerald-700 border-emerald-200',
      description: 'Non-directional dependence. Equal weight for exclusive pairs at count N.',
      items: perMetricTop5['chi_sq'] || [],
    },
    {
      key: 'student_t',
      title: "Student's t-test",
      badge: 'Frequency Weighted',
      badgeColor: 'bg-amber-50 text-amber-700 border-amber-200',
      description: 'Heavy raw frequency bias. High conversational noise (e.g. "thank you").',
      items: perMetricTop5['student_t'] || [],
    },
    {
      key: 'likelihood_ratio',
      title: 'Log-Likelihood (Dunning G²)',
      badge: 'Sparse Asymptotic',
      badgeColor: 'bg-indigo-50 text-indigo-700 border-indigo-200',
      description: 'Robust for skewed spoken text. Balances counts without normality assumptions.',
      items: perMetricTop5['likelihood_ratio'] || [],
    },
  ];

  return (
    <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-5 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-700 flex items-center justify-center font-bold text-xs">
            <Columns3 className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-slate-900">
              Side-by-Side Metric Comparison (Top-5 Rankings)
            </h2>
            <p className="text-xs text-slate-500">
              Comparing four distinct association paradigms on the exact same co-occurrence counts
            </p>
          </div>
        </div>
      </div>

      {/* Plain-English Disagreement Note */}
      <div className="flex items-start gap-2.5 p-3 rounded-xl bg-slate-50 border border-slate-200/80 text-xs text-slate-700">
        <Info className="w-4 h-4 text-brand-600 shrink-0 mt-0.5" />
        <div className="leading-relaxed">
          <strong className="text-slate-900 font-semibold">Why do the metrics disagree? </strong>
          {disagreementNote}
        </div>
      </div>

      {/* 4 Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        {cards.map((card) => (
          <div
            key={card.key}
            className="flex flex-col rounded-xl border border-slate-200/80 bg-white hover:border-slate-300 transition p-3.5 space-y-2.5"
          >
            <div className="flex items-center justify-between gap-1">
              <span className="text-xs font-bold text-slate-900 truncate" title={card.title}>
                {card.title}
              </span>
              <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded border ${card.badgeColor}`}>
                {card.badge}
              </span>
            </div>

            <p className="text-[11px] text-slate-500 line-clamp-2 leading-relaxed">
              {card.description}
            </p>

            <div className="border-t border-slate-100 pt-2 space-y-1.5 flex-1">
              {card.items.length === 0 ? (
                <div className="text-xs text-slate-400 italic py-3 text-center">
                  No phrases met frequency threshold
                </div>
              ) : (
                card.items.map((item) => (
                  <button
                    key={`${card.key}-${item.rank}-${item.phrase}`}
                    onClick={() => onSelectPhrase(item.phrase)}
                    className="w-full flex items-center justify-between p-1.5 rounded-lg text-xs hover:bg-slate-50 text-left transition group border border-transparent hover:border-slate-200"
                    title={`Click to inspect 2x2 contingency for '${item.phrase}'`}
                  >
                    <div className="flex items-center gap-1.5 min-w-0">
                      <span className="font-mono text-[11px] text-slate-400 w-4">
                        #{item.rank}
                      </span>
                      <span className="font-medium text-slate-800 truncate group-hover:text-brand-600">
                        {item.phrase}
                      </span>
                    </div>
                    <div className="flex items-center gap-1 shrink-0 font-mono text-[11px] text-slate-500">
                      <span>{item.score !== null ? item.score.toFixed(2) : 'n/a'}</span>
                      <ExternalLink className="w-3 h-3 text-slate-300 group-hover:text-brand-500" />
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

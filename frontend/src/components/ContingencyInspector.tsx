import React, { useEffect, useState } from 'react';
import { X, Calculator, HelpCircle, Check, Loader2, Sparkles } from 'lucide-react';
import { fetchContingency } from '../api';
import { ContingencyResponse } from '../types';

interface ContingencyInspectorProps {
  phrase: string | null;
  text: string;
  dropStopwords: boolean;
  useFullCorpus: boolean;
  onClose: () => void;
}

export const ContingencyInspector: React.FC<ContingencyInspectorProps> = ({
  phrase,
  text,
  dropStopwords,
  useFullCorpus,
  onClose,
}) => {
  const [data, setData] = useState<ContingencyResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!phrase) {
      setData(null);
      return;
    }

    const parts = phrase.trim().split(/\s+/);
    if (parts.length < 2) return;

    setIsLoading(true);
    setError(null);

    fetchContingency({
      w1: parts[0],
      w2: parts[1],
      text,
      drop_stopwords: dropStopwords,
      use_full_corpus: useFullCorpus,
    })
      .then((res) => setData(res))
      .catch((err) => setError(err.message || 'Could not compute contingency table'))
      .finally(() => setIsLoading(false));
  }, [phrase, text, dropStopwords, useFullCorpus]);

  if (!phrase) return null;

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden">
        {/* Modal Header */}
        <div className="p-4 sm:px-6 border-b border-slate-100 flex items-center justify-between gap-3 bg-slate-50/80">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-brand-600 text-white flex items-center justify-center">
              <Calculator className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-slate-900">
                  2×2 Contingency Table & Metric Inspector
                </h3>
                <span className="text-xs px-2 py-0.5 rounded bg-brand-50 text-brand-700 font-mono font-semibold border border-brand-200">
                  "{phrase}"
                </span>
              </div>
              <p className="text-xs text-slate-500">
                Exact observed cell frequencies, expected values under independence, and metric derivations
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 transition"
            title="Close Inspector"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-4 sm:p-6 overflow-y-auto space-y-6 flex-1 text-xs">
          {isLoading ? (
            <div className="py-20 flex flex-col items-center justify-center text-slate-400 space-y-2">
              <Loader2 className="w-8 h-8 animate-spin text-brand-600" />
              <span>Computing 2×2 contingency distribution...</span>
            </div>
          ) : error ? (
            <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800">
              <span className="font-semibold block mb-1">Error computing contingency table</span>
              <p>{error}</p>
            </div>
          ) : data ? (
            <>
              {/* 2x2 Contingency Matrix Table */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                  <span>Observed Frequencies vs Expected Marginals</span>
                </h4>

                <div className="overflow-x-auto rounded-xl border border-slate-200 bg-slate-50/50 p-3">
                  <table className="w-full text-center border-collapse text-xs">
                    <thead>
                      <tr>
                        <th className="p-2 text-slate-400 font-normal"></th>
                        <th className="p-2 font-semibold text-slate-700 border-b border-slate-200">
                          w2 = '{data.w2}'
                        </th>
                        <th className="p-2 font-semibold text-slate-700 border-b border-slate-200">
                          w2 ≠ '{data.w2}'
                        </th>
                        <th className="p-2 font-semibold text-indigo-700 border-b border-slate-200 bg-indigo-50/50 rounded-t">
                          Row Marginals (R)
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {/* Row 1 */}
                      <tr className="border-b border-slate-200/80">
                        <td className="p-2 font-semibold text-slate-700 text-left">
                          w1 = '{data.w1}'
                        </td>
                        <td className="p-3 bg-white font-mono font-bold text-brand-600 rounded-tl shadow-2xs border border-slate-200/60">
                          <div className="text-sm">{data.o11}</div>
                          <div className="text-[10px] text-slate-400 font-normal font-sans">
                            O11 (E11 = {data.expected.e11})
                          </div>
                        </td>
                        <td className="p-3 bg-white font-mono text-slate-700 rounded-tr shadow-2xs border border-slate-200/60">
                          <div className="text-sm">{data.o12}</div>
                          <div className="text-[10px] text-slate-400 font-normal font-sans">
                            O12 (E12 = {data.expected.e12})
                          </div>
                        </td>
                        <td className="p-3 bg-indigo-50/50 font-mono font-bold text-indigo-800 border-l border-slate-200">
                          R1 = {data.row1}
                        </td>
                      </tr>

                      {/* Row 2 */}
                      <tr className="border-b border-slate-200/80">
                        <td className="p-2 font-semibold text-slate-700 text-left">
                          w1 ≠ '{data.w1}'
                        </td>
                        <td className="p-3 bg-white font-mono text-slate-700 rounded-bl shadow-2xs border border-slate-200/60">
                          <div className="text-sm">{data.o21}</div>
                          <div className="text-[10px] text-slate-400 font-normal font-sans">
                            O21 (E21 = {data.expected.e21})
                          </div>
                        </td>
                        <td className="p-3 bg-white font-mono text-slate-700 rounded-br shadow-2xs border border-slate-200/60">
                          <div className="text-sm">{data.o22}</div>
                          <div className="text-[10px] text-slate-400 font-normal font-sans">
                            O22 (E22 = {data.expected.e22})
                          </div>
                        </td>
                        <td className="p-3 bg-indigo-50/50 font-mono font-bold text-indigo-800 border-l border-slate-200">
                          R2 = {data.row2}
                        </td>
                      </tr>

                      {/* Column Marginals */}
                      <tr>
                        <td className="p-2 font-semibold text-indigo-700 text-left">
                          Col Marginals (C)
                        </td>
                        <td className="p-2 bg-indigo-50/50 font-mono font-bold text-indigo-800 border-t border-slate-200">
                          C1 = {data.col1}
                        </td>
                        <td className="p-2 bg-indigo-50/50 font-mono font-bold text-indigo-800 border-t border-slate-200">
                          C2 = {data.col2}
                        </td>
                        <td className="p-3 bg-indigo-100/80 font-mono font-extrabold text-indigo-950 border-t border-l border-indigo-200 rounded-br">
                          N = {data.n}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Live Metric Derivations Grid */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                  Live Metric Computations & Formula Substitutions
                </h4>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {Object.entries(data.formulas).map(([key, f]) => (
                    <div
                      key={key}
                      className="p-3.5 rounded-xl border border-slate-200 bg-white hover:border-slate-300 transition space-y-1.5 shadow-2xs"
                    >
                      <div className="flex items-center justify-between gap-1">
                        <span className="font-semibold text-slate-900">{f.name}</span>
                        <span className="font-mono font-bold text-brand-600 bg-brand-50 px-2 py-0.5 rounded border border-brand-100 text-xs">
                          {f.result !== null ? f.result.toFixed(4) : 'Undefined'}
                        </span>
                      </div>

                      <div className="font-mono text-[11px] text-slate-600 bg-slate-50 p-2 rounded-lg border border-slate-100 space-y-1">
                        <div className="text-slate-400 font-sans text-[10px]">Formula:</div>
                        <div className="text-slate-800 font-semibold">{f.formula}</div>
                        <div className="text-slate-400 font-sans text-[10px] pt-0.5">Substituted:</div>
                        <div className="text-brand-700 break-all">{f.substituted}</div>
                      </div>

                      <p className="text-[11px] text-slate-500 leading-relaxed pt-0.5">
                        {f.explanation}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : null}
        </div>

        {/* Modal Footer */}
        <div className="p-3 px-6 border-t border-slate-100 bg-slate-50 flex items-center justify-between text-xs text-slate-500">
          <span>All 4 cells sum strictly to sentence-internal token count N</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white font-medium transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

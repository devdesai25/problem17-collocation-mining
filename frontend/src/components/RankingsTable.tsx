import React, { useState, useMemo } from 'react';
import { Download, Search, Table, ArrowUpDown, Eye, ExternalLink } from 'lucide-react';
import { CollocationRow } from '../types';

interface RankingsTableProps {
  rankings: CollocationRow[];
  metricName: string;
  ngram: number;
  onSelectPhrase: (phrase: string) => void;
}

export const RankingsTable: React.FC<RankingsTableProps> = ({
  rankings,
  metricName,
  ngram,
  onSelectPhrase,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [pageSize, setPageSize] = useState(15);
  const [currentPage, setCurrentPage] = useState(1);

  // Filter phrases
  const filtered = useMemo(() => {
    if (!searchTerm.trim()) return rankings;
    const term = searchTerm.toLowerCase();
    return rankings.filter((r) => r.phrase.toLowerCase().includes(term));
  }, [rankings, searchTerm]);

  // Pagination
  const totalPages = Math.ceil(filtered.length / pageSize) || 1;
  const pageItems = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filtered.slice(start, start + pageSize);
  }, [filtered, currentPage, pageSize]);

  // CSV Export
  const downloadCSV = () => {
    if (!rankings.length) return;
    const headers = ['Rank', 'Phrase', 'Score', 'Frequency (O11)', 'f(w1)', 'f(w2)', 'O12', 'O21', 'O22', 'N'];
    const rows = rankings.map((r) => [
      r.rank,
      `"${r.phrase}"`,
      r.score !== null ? r.score.toFixed(6) : 'n/a',
      r.freq,
      r.f_w1 ?? '',
      r.f_w2 ?? '',
      r.o12 ?? '',
      r.o21 ?? '',
      r.o22 ?? '',
      r.n ?? '',
    ]);

    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `collocations_${metricName}_${ngram}gram.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
      {/* Header bar */}
      <div className="p-4 sm:px-6 border-b border-slate-100 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-brand-50 text-brand-700 flex items-center justify-center font-bold text-xs">
            <Table className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-slate-900">
              Ranked Collocation Results ({filtered.length} phrases)
            </h2>
            <p className="text-xs text-slate-500">
              Scored via {metricName.toUpperCase()} with sentence-internal marginals
            </p>
          </div>
        </div>

        {/* Search & Export Controls */}
        <div className="flex items-center flex-wrap gap-2">
          {/* Search bar */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setCurrentPage(1);
              }}
              placeholder="Search phrases..."
              className="text-xs pl-8 pr-3 py-1.5 rounded-lg border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 w-44"
            />
          </div>

          {/* Export CSV button */}
          <button
            type="button"
            onClick={downloadCSV}
            disabled={!rankings.length}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-700 bg-slate-50 hover:bg-slate-100 border border-slate-200 transition disabled:opacity-50"
            title="Download full ranked collocations as CSV"
          >
            <Download className="w-3.5 h-3.5 text-slate-500" />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {/* Table container */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50/80 text-slate-600 font-semibold border-b border-slate-200">
            <tr>
              <th className="py-2.5 px-4 w-16">Rank</th>
              <th className="py-2.5 px-4">Collocation Phrase</th>
              <th className="py-2.5 px-4 text-right">Score</th>
              <th className="py-2.5 px-4 text-right">Freq (O11)</th>
              {ngram === 2 && (
                <>
                  <th className="py-2.5 px-4 text-right">f(w1)</th>
                  <th className="py-2.5 px-4 text-right">f(w2)</th>
                  <th className="py-2.5 px-4 text-center w-28">2×2 Matrix</th>
                </>
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {pageItems.length === 0 ? (
              <tr>
                <td
                  colSpan={ngram === 2 ? 7 : 4}
                  className="py-12 text-center text-slate-400 italic"
                >
                  No collocations found matching your criteria. Try lowering the minimum frequency threshold.
                </td>
              </tr>
            ) : (
              pageItems.map((r) => (
                <tr
                  key={`${r.rank}-${r.phrase}`}
                  className="hover:bg-slate-50/80 transition group"
                >
                  <td className="py-2.5 px-4 font-mono font-medium text-slate-400">
                    #{r.rank}
                  </td>
                  <td className="py-2.5 px-4">
                    <span className="font-semibold text-slate-800 text-sm">
                      {r.phrase}
                    </span>
                  </td>
                  <td className="py-2.5 px-4 text-right font-mono font-medium text-brand-600">
                    {r.score !== null ? r.score.toFixed(4) : <span className="text-slate-400">n/a</span>}
                  </td>
                  <td className="py-2.5 px-4 text-right font-mono text-slate-700">
                    {r.freq}
                  </td>
                  {ngram === 2 && (
                    <>
                      <td className="py-2.5 px-4 text-right font-mono text-slate-500">
                        {r.f_w1 ?? '-'}
                      </td>
                      <td className="py-2.5 px-4 text-right font-mono text-slate-500">
                        {r.f_w2 ?? '-'}
                      </td>
                      <td className="py-2.5 px-4 text-center">
                        <button
                          type="button"
                          onClick={() => onSelectPhrase(r.phrase)}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-medium text-brand-700 bg-brand-50 hover:bg-brand-100 border border-brand-200 transition"
                        >
                          <Eye className="w-3 h-3" />
                          <span>Inspect</span>
                        </button>
                      </td>
                    </>
                  )}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      {filtered.length > pageSize && (
        <div className="p-3 px-4 border-t border-slate-100 bg-slate-50/50 flex items-center justify-between text-xs text-slate-500">
          <div>
            Showing {(currentPage - 1) * pageSize + 1} to{' '}
            {Math.min(currentPage * pageSize, filtered.length)} of {filtered.length} phrases
          </div>

          <div className="flex items-center gap-1">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="px-2.5 py-1 rounded border border-slate-200 bg-white hover:bg-slate-50 disabled:opacity-50 transition"
            >
              Previous
            </button>
            <span className="px-2 font-mono text-slate-700">
              {currentPage} / {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="px-2.5 py-1 rounded border border-slate-200 bg-white hover:bg-slate-50 disabled:opacity-50 transition"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

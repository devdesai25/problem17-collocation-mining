import React, { useState, useEffect, useRef } from 'react';
import { Header } from './components/Header';
import { InputSection } from './components/InputSection';
import { ControlsBar } from './components/ControlsBar';
import { CorpusStats } from './components/CorpusStats';
import { PipelineAnimation } from './components/PipelineAnimation';
import { MetricComparison } from './components/MetricComparison';
import { RankingsTable } from './components/RankingsTable';
import { ContingencyInspector } from './components/ContingencyInspector';
import {
  analyzeText,
  checkHealth,
  fetchTrace,
} from './api';
import {
  AnalyzeResponse,
  BigramMetric,
  NgramOrder,
  TraceResponse,
} from './types';
import { AlertCircle, CheckCircle2, RefreshCw } from 'lucide-react';

const DEFAULT_SAMPLE_TEXT = `The city council met this morning to review the affordable housing master plan.
Council member Richardson moved to approve the annual action plan.
Those in favor please signify by saying aye.
The motion carries and the general fund allocation is secured.
Thank you council member for the presentation on law enforcement oversight.`;

export const App: React.FC = () => {
  // App state
  const [text, setText] = useState<string>(DEFAULT_SAMPLE_TEXT);
  const [useFullCorpus, setUseFullCorpus] = useState<boolean>(false);
  const [ngram, setNgram] = useState<NgramOrder>(2);
  const [minFreq, setMinFreq] = useState<number>(1);
  const [metric, setMetric] = useState<BigramMetric>('pmi');
  const [dropStopwords, setDropStopwords] = useState<boolean>(false);
  const [topK, setTopK] = useState<number>(20);

  // Async results
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);
  const [trace, setTrace] = useState<TraceResponse | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Contingency Inspector modal
  const [inspectorPhrase, setInspectorPhrase] = useState<string | null>(null);

  // Health
  const [backendReady, setBackendReady] = useState<boolean>(false);
  const [ffmpegAvailable, setFfmpegAvailable] = useState<boolean>(false);

  const resultsRef = useRef<HTMLDivElement | null>(null);

  // Check health on mount
  useEffect(() => {
    checkHealth()
      .then((h) => {
        setBackendReady(h.status === 'ok');
        setFfmpegAvailable(h.ffmpeg_available);
      })
      .catch(() => {
        setBackendReady(false);
      });
  }, []);

  // Run analysis function
  const handleRunAnalysis = async () => {
    if (!useFullCorpus && !text.trim()) {
      setError('Please provide text or select the full corpus before running analysis.');
      return;
    }

    setIsAnalyzing(true);
    setError(null);

    try {
      // 1. Run main collocation analysis
      const analysisData = await analyzeText({
        text,
        ngram,
        min_freq: minFreq,
        metric,
        drop_stopwords: dropStopwords,
        top_k: topK,
        use_full_corpus: useFullCorpus,
      });
      setAnalysis(analysisData);

      // 2. Run pipeline trace for animation
      const traceText = useFullCorpus
        ? (analysisData.rankings.length > 0 ? analysisData.rankings[0].phrase : text)
        : text;

      const topPhrase = analysisData.rankings[0]?.phrase;
      const traceData = await fetchTrace({
        text: traceText || text,
        sample_sentence_index: 0,
        target_phrase: topPhrase,
        drop_stopwords: dropStopwords,
        ngram,
      });
      setTrace(traceData);
    } catch (err: any) {
      setError(err.message || 'An error occurred during analysis.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Run initial analysis automatically on mount once backend is ready
  useEffect(() => {
    handleRunAnalysis();
  }, [useFullCorpus]);

  // Handle changing sample sentence within trace
  const handleSelectSentenceForTrace = async (sentenceIdx: number) => {
    try {
      const topPhrase = analysis?.rankings[0]?.phrase;
      const traceData = await fetchTrace({
        text,
        sample_sentence_index: sentenceIdx,
        target_phrase: topPhrase,
        drop_stopwords: dropStopwords,
        ngram,
      });
      setTrace(traceData);
    } catch (err) {
      console.warn('Could not update trace sentence:', err);
    }
  };

  const scrollToResults = () => {
    resultsRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 pb-16">
      {/* Top Header */}
      <Header backendReady={backendReady} ffmpegAvailable={ffmpegAvailable} />

      {/* Main Container */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Global Error Banner */}
        {error && (
          <div className="flex items-center justify-between p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs shadow-xs animate-in fade-in">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>{error}</span>
            </div>
            <button
              onClick={() => setError(null)}
              className="text-rose-700 hover:text-rose-900 font-bold ml-4"
            >
              ×
            </button>
          </div>
        )}

        {/* 1. Input Section */}
        <InputSection
          text={text}
          onChangeText={setText}
          useFullCorpus={useFullCorpus}
          onToggleFullCorpus={(val) => {
            setUseFullCorpus(val);
            if (val) setMinFreq(3);
          }}
          isAnalyzing={isAnalyzing}
        />

        {/* 2. Controls Bar */}
        <ControlsBar
          ngram={ngram}
          onChangeNgram={setNgram}
          minFreq={minFreq}
          onChangeMinFreq={setMinFreq}
          metric={metric}
          onChangeMetric={setMetric}
          dropStopwords={dropStopwords}
          onChangeDropStopwords={setDropStopwords}
          topK={topK}
          onChangeTopK={setTopK}
          onRunAnalysis={handleRunAnalysis}
          isAnalyzing={isAnalyzing}
          disabled={!useFullCorpus && !text.trim()}
        />

        {/* 3. Corpus Stats Row */}
        {analysis && (
          <CorpusStats stats={analysis.stats} cached={analysis.cached} />
        )}

        {/* 4. Process Animation Section */}
        {trace && (
          <PipelineAnimation
            trace={trace}
            onSelectSentence={handleSelectSentenceForTrace}
            onSkipToResults={scrollToResults}
          />
        )}

        {/* 5. Results Section Anchor */}
        <div ref={resultsRef} className="space-y-6">
          {analysis && (
            <>
              {/* Metric Comparison Top-5 */}
              {ngram === 2 && (
                <MetricComparison
                  perMetricTop5={analysis.per_metric_top5}
                  disagreementNote={analysis.disagreement_note}
                  onSelectPhrase={(phrase) => setInspectorPhrase(phrase)}
                />
              )}

              {/* Collocations Ranked Table */}
              <RankingsTable
                rankings={analysis.rankings}
                metricName={metric}
                ngram={ngram}
                onSelectPhrase={(phrase) => setInspectorPhrase(phrase)}
              />
            </>
          )}
        </div>
      </main>

      {/* 2x2 Contingency Inspector Modal */}
      <ContingencyInspector
        phrase={inspectorPhrase}
        text={text}
        dropStopwords={dropStopwords}
        useFullCorpus={useFullCorpus}
        onClose={() => setInspectorPhrase(null)}
      />
    </div>
  );
};

export default App;

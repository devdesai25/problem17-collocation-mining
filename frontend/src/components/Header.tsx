import React from 'react';
import { Sparkles, Terminal, Activity, FileText } from 'lucide-react';

interface HeaderProps {
  backendReady: boolean;
  ffmpegAvailable: boolean;
}

export const Header: React.FC<HeaderProps> = ({ backendReady, ffmpegAvailable }) => {
  return (
    <header className="border-b border-slate-200 bg-white/80 backdrop-blur sticky top-0 z-30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-700 via-brand-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-brand-500/20">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold tracking-tight text-slate-900">
                Collocation Mining & Association Scoring
              </h1>
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-brand-50 text-brand-700 border border-brand-200">
                Problem 17
              </span>
            </div>
            <p className="text-xs text-slate-500 font-medium">
              First-principles statistical lexical cohesion engine for municipal meeting transcripts
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-100 border border-slate-200 text-slate-600 font-mono">
            <span
              className={`w-2 h-2 rounded-full ${
                backendReady ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'
              }`}
            />
            <span>{backendReady ? 'FastAPI API Active' : 'Connecting to API...'}</span>
          </div>

          <div
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-mono ${
              ffmpegAvailable
                ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
                : 'bg-amber-50 border-amber-200 text-amber-700'
            }`}
            title={
              ffmpegAvailable
                ? 'FFmpeg is installed for full audio conversion'
                : 'FFmpeg CLI not detected; native PyAV decoder will handle standard audio'
            }
          >
            <Activity className="w-3.5 h-3.5" />
            <span>Whisper STT (CPU int8)</span>
          </div>

          <a
            href="https://github.com/devdesai25/problem17-collocation-mining"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-900 text-white hover:bg-slate-800 transition font-medium"
          >
            <Terminal className="w-3.5 h-3.5" />
            <span>GitHub</span>
          </a>
        </div>
      </div>
    </header>
  );
};

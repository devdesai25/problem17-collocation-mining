import React, { useState, useRef, useEffect } from 'react';
import {
  Mic,
  MicOff,
  Upload,
  FileText,
  RotateCcw,
  Sparkles,
  AlertCircle,
  Database,
  CheckCircle2,
  Volume2,
} from 'lucide-react';
import { fetchSamples, fetchSampleContent, transcribeAudioFile } from '../api';
import { SampleItem } from '../types';

interface InputSectionProps {
  text: string;
  onChangeText: (newText: string) => void;
  useFullCorpus: boolean;
  onToggleFullCorpus: (val: boolean) => void;
  isAnalyzing: boolean;
}

export const InputSection: React.FC<InputSectionProps> = ({
  text,
  onChangeText,
  useFullCorpus,
  onToggleFullCorpus,
  isAnalyzing,
}) => {
  const [samples, setSamples] = useState<SampleItem[]>([]);
  const [selectedSampleId, setSelectedSampleId] = useState<string>('');
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [transcribeStatus, setTranscribeStatus] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Microphone recording states
  const [isRecording, setIsRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerIntervalRef = useRef<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Load sample list on mount
  useEffect(() => {
    fetchSamples()
      .then((data) => setSamples(data))
      .catch((err) => console.warn('Could not load sample list:', err));
  }, []);

  // Timer for recording
  useEffect(() => {
    if (isRecording) {
      setRecordingSeconds(0);
      timerIntervalRef.current = window.setInterval(() => {
        setRecordingSeconds((prev) => prev + 1);
      }, 1000);
    } else {
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current);
        timerIntervalRef.current = null;
      }
    }
    return () => {
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
    };
  }, [isRecording]);

  // Handle sample selection
  const handleSelectSample = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    setSelectedSampleId(val);
    if (!val) return;
    try {
      setErrorMsg(null);
      const content = await fetchSampleContent(val);
      onChangeText(content);
      if (useFullCorpus) onToggleFullCorpus(false);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load sample transcript');
    }
  };

  // Handle Audio File Upload
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsTranscribing(true);
    setTranscribeStatus(`Uploading and transcribing "${file.name}" via faster-whisper...`);
    setErrorMsg(null);

    try {
      const res = await transcribeAudioFile(file);
      onChangeText(res.text);
      setTranscribeStatus(`Transcribed (${res.duration}s audio, language: ${res.language})`);
    } catch (err: any) {
      setErrorMsg(err.message || 'Audio transcription failed. Make sure audio format is supported.');
      setTranscribeStatus(null);
    } finally {
      setIsTranscribing(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // Start Microphone Recording
  const startRecording = async () => {
    setErrorMsg(null);
    setTranscribeStatus(null);

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setErrorMsg('Microphone recording is not supported in this browser. Please use text paste or file upload.');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];

      const candidateTypes = [
        { mime: 'audio/webm;codecs=opus', ext: 'webm' },
        { mime: 'audio/webm', ext: 'webm' },
        { mime: 'audio/mp4', ext: 'mp4' },
        { mime: 'audio/aac', ext: 'aac' },
        { mime: 'audio/ogg;codecs=opus', ext: 'ogg' },
        { mime: 'audio/wav', ext: 'wav' },
      ];

      let selectedMime = '';
      let fileExt = 'webm';
      for (const cand of candidateTypes) {
        if (typeof MediaRecorder.isTypeSupported === 'function' && MediaRecorder.isTypeSupported(cand.mime)) {
          selectedMime = cand.mime;
          fileExt = cand.ext;
          break;
        }
      }

      const recorderOptions: MediaRecorderOptions = selectedMime ? { mimeType: selectedMime } : {};
      const mediaRecorder = new MediaRecorder(stream, recorderOptions);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        const actualMime = mediaRecorder.mimeType || selectedMime || 'audio/webm';
        const audioBlob = new Blob(audioChunksRef.current, { type: actualMime });
        if (audioBlob.size === 0) return;

        const audioFile = new File([audioBlob], `mic_recording.${fileExt}`, { type: actualMime });
        setIsTranscribing(true);
        setTranscribeStatus('Transcribing recorded audio via faster-whisper...');

        try {
          const res = await transcribeAudioFile(audioFile);
          onChangeText(res.text);
          setTranscribeStatus(`Transcribed recorded memo (${res.duration}s, language: ${res.language})`);
        } catch (err: any) {
          setErrorMsg(err.message || 'Microphone audio transcription failed.');
          setTranscribeStatus(null);
        } finally {
          setIsTranscribing(false);
        }
      };

      mediaRecorder.start(250);
      setIsRecording(true);
    } catch (err: any) {
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setErrorMsg('Microphone permission was denied. Please allow microphone access in your browser bar, or upload an audio file instead.');
      } else {
        setErrorMsg(`Could not access microphone: ${err.message || err.name}`);
      }
    }
  };

  // Stop Microphone Recording
  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0;
  const charCount = text.length;

  return (
    <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-5 space-y-4">
      {/* Top Controls Row */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-slate-100 text-slate-700 flex items-center justify-center font-bold text-xs">
            1
          </div>
          <div>
            <h2 className="text-sm font-semibold text-slate-900">
              Spoken Transcript Input
            </h2>
            <p className="text-xs text-slate-500">
              Type or paste, upload audio (WAV/MP3/WebM), record with mic, or select a MeetingBank sample
            </p>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center flex-wrap gap-2">
          {/* Sample Loader */}
          <div className="relative">
            <select
              value={selectedSampleId}
              onChange={handleSelectSample}
              disabled={useFullCorpus || isAnalyzing || isTranscribing}
              className="text-xs bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg px-2.5 py-1.5 font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-brand-500/20 disabled:opacity-50 cursor-pointer"
            >
              <option value="">📂 Load sample transcript (28 available)...</option>
              {samples.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.id}. {s.city} ({s.word_count} words)
                </option>
              ))}
            </select>
          </div>

          {/* Full Corpus Checkbox */}
          <label className="flex items-center gap-1.5 text-xs font-medium text-slate-700 bg-slate-50 border border-slate-200 hover:bg-slate-100 px-2.5 py-1.5 rounded-lg cursor-pointer transition select-none">
            <input
              type="checkbox"
              checked={useFullCorpus}
              onChange={(e) => onToggleFullCorpus(e.target.checked)}
              disabled={isAnalyzing || isTranscribing}
              className="w-3.5 h-3.5 text-brand-600 rounded border-slate-300 focus:ring-brand-500"
            />
            <Database className="w-3.5 h-3.5 text-slate-500" />
            <span>Use Full Corpus (67k tokens)</span>
          </label>

          {/* Hidden File Input */}
          <input
            ref={fileInputRef}
            type="file"
            accept="audio/*,.wav,.mp3,.m4a,.webm,.ogg"
            onChange={handleFileUpload}
            className="hidden"
          />

          {/* Upload Audio Button */}
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={useFullCorpus || isAnalyzing || isTranscribing || isRecording}
            className="flex items-center gap-1.5 text-xs font-medium text-slate-700 bg-slate-50 hover:bg-slate-100 border border-slate-200 px-2.5 py-1.5 rounded-lg transition disabled:opacity-50"
            title="Upload audio file to transcribe with faster-whisper"
          >
            <Upload className="w-3.5 h-3.5 text-slate-500" />
            <span>Upload Audio</span>
          </button>

          {/* Microphone Record Button */}
          {!isRecording ? (
            <button
              type="button"
              onClick={startRecording}
              disabled={useFullCorpus || isAnalyzing || isTranscribing}
              className="flex items-center gap-1.5 text-xs font-medium text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200 px-2.5 py-1.5 rounded-lg transition disabled:opacity-50"
              title="Record voice dictation directly from your microphone"
            >
              <Mic className="w-3.5 h-3.5" />
              <span>Record Mic</span>
            </button>
          ) : (
            <button
              type="button"
              onClick={stopRecording}
              className="flex items-center gap-1.5 text-xs font-medium text-white bg-rose-600 hover:bg-rose-700 px-3 py-1.5 rounded-lg transition animate-pulse shadow-sm"
              title="Stop recording and transcribe"
            >
              <MicOff className="w-3.5 h-3.5" />
              <span>Stop ({recordingSeconds}s)</span>
            </button>
          )}

          {/* Clear Button */}
          {text && !useFullCorpus && (
            <button
              type="button"
              onClick={() => onChangeText('')}
              disabled={isAnalyzing || isTranscribing}
              className="text-xs text-slate-400 hover:text-slate-600 p-1.5 rounded-md hover:bg-slate-100 transition"
              title="Clear text"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Status Banners */}
      {isTranscribing && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-brand-50 border border-brand-200 text-brand-800 text-xs animate-pulse">
          <Volume2 className="w-4 h-4 animate-spin text-brand-600" />
          <span>{transcribeStatus || 'Transcribing audio...'}</span>
        </div>
      )}

      {transcribeStatus && !isTranscribing && (
        <div className="flex items-center justify-between px-3 py-2 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <span>{transcribeStatus}</span>
          </div>
          <button
            onClick={() => setTranscribeStatus(null)}
            className="text-emerald-700 hover:text-emerald-900 font-bold ml-2"
          >
            ×
          </button>
        </div>
      )}

      {errorMsg && (
        <div className="flex items-center justify-between px-3 py-2 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{errorMsg}</span>
          </div>
          <button
            onClick={() => setErrorMsg(null)}
            className="text-rose-700 hover:text-rose-900 font-bold ml-2"
          >
            ×
          </button>
        </div>
      )}

      {/* Main Textarea Area */}
      <div className="relative">
        {useFullCorpus ? (
          <div className="w-full h-40 bg-slate-50 border border-slate-200 rounded-xl p-4 flex flex-col items-center justify-center text-center text-slate-600 space-y-1">
            <Database className="w-8 h-8 text-brand-600 mb-1" />
            <p className="text-sm font-semibold text-slate-800">
              Full MeetingBank Corpus Selected (28 municipal transcripts)
            </p>
            <p className="text-xs text-slate-500 max-w-lg">
              Analysis will aggregate 67,046 lemmatized tokens across Alameda, Boston, Denver, King County,
              Long Beach, and Seattle city council sessions.
            </p>
          </div>
        ) : (
          <div className="relative">
            <textarea
              value={text}
              onChange={(e) => onChangeText(e.target.value)}
              placeholder="Type or paste already-transcribed text here, or use the audio upload / mic recorder above. You can freely edit this transcript before running the analysis..."
              rows={6}
              disabled={isAnalyzing || isTranscribing}
              className="w-full p-3.5 text-sm bg-slate-50/50 hover:bg-white focus:bg-white border border-slate-200 rounded-xl text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition leading-relaxed resize-y font-mono"
            />
            {/* Word / Char Counters */}
            <div className="absolute bottom-3 right-3 flex items-center gap-2 text-[11px] font-mono text-slate-400 bg-white/90 px-2 py-0.5 rounded border border-slate-200/80 shadow-xs">
              <span>{wordCount} words</span>
              <span>•</span>
              <span>{charCount} chars</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

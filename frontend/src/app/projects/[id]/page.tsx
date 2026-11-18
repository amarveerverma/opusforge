"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  Film,
  Sparkles,
  ArrowLeft,
  Play,
  Scissors,
  CheckCircle2,
  Clock,
  Layers,
  Flame,
  Zap,
  RefreshCw,
  Video,
  Download,
  Sliders,
  ExternalLink,
  ChevronRight,
  AlertCircle,
} from "lucide-react";
import {
  fetchProject,
  fetchProjectClips,
  runTranscription,
  runAnalysis,
  discoverClips,
  triggerRender,
  getThumbnailUrl,
  getVideoStreamUrl,
  Project,
  Clip,
} from "@/lib/api";

export default function ProjectPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params?.id as string;

  const [project, setProject] = useState<Project | null>(null);
  const [clips, setClips] = useState<Clip[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [processingStage, setProcessingStage] = useState<string>("");
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string>("");
  const [renderingClipId, setRenderingClipId] = useState<string | null>(null);

  const loadProjectData = async () => {
    try {
      if (!projectId) return;
      const proj = await fetchProject(projectId);
      setProject(proj);
      const projectClips = await fetchProjectClips(projectId);
      setClips(projectClips);
    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.message || "Failed to load project");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProjectData();
  }, [projectId]);

  // Run full pipeline sequentially
  const handleRunFullPipeline = async () => {
    try {
      setIsProcessing(true);
      setErrorMsg("");

      // 1. Transcription (WhisperX GPU)
      setProcessingStage("Transcribing audio with WhisperX (word timestamps)...");
      await runTranscription(projectId);

      // 2. Multi-Modal Analysis (Diarization + Scene Cuts + MediaPipe)
      setProcessingStage("Analyzing scenes, speaker turns & facial tracks...");
      await runAnalysis(projectId);

      // 3. AI Clip Discovery
      setProcessingStage("Scoring narrative moments & ranking 9:16 virality candidates...");
      const discovered = await discoverClips(projectId);
      setClips(discovered);

      setProcessingStage("");
      await loadProjectData();
    } catch (err: any) {
      setErrorMsg(err.message || "Pipeline execution failed");
    } finally {
      setIsProcessing(false);
      setProcessingStage("");
    }
  };

  // Render a specific clip directly
  const handleRenderClip = async (clipId: string) => {
    try {
      setRenderingClipId(clipId);
      await triggerRender(clipId);
      await loadProjectData();
    } catch (err: any) {
      alert(`Render failed: ${err.message}`);
    } finally {
      setRenderingClipId(null);
    }
  };

  const formatSeconds = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  const getGradeColor = (grade: string) => {
    if (grade.startsWith("A")) return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
    if (grade.startsWith("B")) return "bg-blue-500/10 text-blue-400 border-blue-500/30";
    return "bg-amber-500/10 text-amber-400 border-amber-500/30";
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-400">
        <RefreshCw className="w-8 h-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="min-h-screen bg-slate-950 p-8 text-white">
        <p className="text-red-400">Project not found</p>
        <Link href="/" className="text-indigo-400 mt-4 inline-block">← Back to Dashboard</Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0A0B0D] text-slate-100 flex flex-col font-sans">
      {/* Top Navigation — Gemini Carbon Header */}
      <header className="border-b border-white/[0.08] bg-[#0E1014]/90 backdrop-blur-md sticky top-0 z-40 px-6 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            href="/"
            className="p-2 rounded-lg bg-[#16191F] hover:bg-[#1E222A] text-slate-400 hover:text-white transition border border-white/[0.08]"
            title="Back to Dashboard"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <h1 className="text-base font-bold text-white flex items-center gap-2">
              {project.title}
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-[#16191F] border border-white/[0.08] text-sky-400 font-semibold tracking-wider">
                {project.status.toUpperCase()}
              </span>
            </h1>
            <p className="text-[11px] text-slate-400 font-mono">
              {project.width || 1920}x{project.height || 1080} · {project.fps || 30} FPS · {formatSeconds(project.duration)} Source
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href={`/projects/${projectId}/exports`}
            className="px-3.5 py-1.5 rounded-lg bg-[#16191F] hover:bg-[#1E222A] border border-white/[0.08] text-xs font-medium text-slate-200 flex items-center gap-2 transition"
          >
            <Download className="w-3.5 h-3.5 text-emerald-400" />
            Exports Gallery
          </Link>
          <button
            onClick={handleRunFullPipeline}
            disabled={isProcessing}
            className={`px-4 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-2 transition shadow-sm ${
              isProcessing
                ? "bg-sky-400/50 cursor-not-allowed text-slate-950"
                : "bg-sky-400 hover:bg-sky-300 text-slate-950"
            }`}
          >
            {isProcessing ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span>Processing Pipeline...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-3.5 h-3.5 text-slate-950" />
                <span>{clips.length > 0 ? "Re-Run AI Discovery" : "Run AI Discovery"}</span>
              </>
            )}
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 p-6 max-w-7xl mx-auto w-full space-y-6">
        {/* Processing Banner */}
        {isProcessing && (
          <div className="p-4 rounded-xl bg-sky-950/30 border border-sky-400/20 flex items-center gap-4 animate-pulse">
            <RefreshCw className="w-5 h-5 text-sky-400 animate-spin flex-shrink-0" />
            <div>
              <p className="text-sm font-semibold text-sky-200">Local AI Pipeline Active</p>
              <p className="text-xs text-slate-400 font-mono">{processingStage}</p>
            </div>
          </div>
        )}

        {/* Error Banner */}
        {errorMsg && (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center gap-3 text-rose-400 text-sm">
            <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0" />
            <p>{errorMsg}</p>
          </div>
        )}

        {/* Source Video Overview Card */}
        <section className="bg-[#111317] border border-white/[0.08] rounded-xl p-5 flex flex-col md:flex-row gap-5 items-start shadow-carbon-card">
          <div className="w-full md:w-72 h-40 rounded-lg overflow-hidden bg-[#0A0B0D] border border-white/[0.08] relative flex-shrink-0">
            <img
              src={getThumbnailUrl(project.id)}
              alt={project.title}
              className="w-full h-full object-cover"
              onError={(e) => {
                (e.target as HTMLElement).style.display = "none";
              }}
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent flex items-end p-2.5">
              <span className="text-[11px] font-mono bg-black/80 px-2 py-0.5 rounded text-sky-300 border border-white/10">
                {formatSeconds(project.duration)}
              </span>
            </div>
          </div>

          <div className="flex-1 space-y-3">
            <div>
              <h2 className="text-sm font-bold text-white uppercase tracking-wider text-[11px] font-mono text-slate-400">Target Instructions</h2>
              <p className="text-xs text-slate-300 mt-1.5 leading-relaxed bg-[#16191F] p-3 rounded-lg border border-white/[0.06]">
                {project.instructions || "Find viral self-contained clips between 30 and 60 seconds."}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 pt-1 font-mono text-[11px]">
              <div className="flex items-center gap-1.5">
                <Video className="w-3.5 h-3.5 text-slate-500" />
                <span className="truncate max-w-xs">{project.original_filename}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-slate-500" />
                <span className="text-sky-400 font-semibold">{clips.length} Viral Moments Discovered</span>
              </div>
            </div>
          </div>
        </section>

        {/* Candidate Shorts Section */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Flame className="w-4 h-4 text-amber-400" />
                Ranked 9:16 Virality Candidates
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Ranked using 7 Opus Virality dimensions (Hook, Flow, Context, Value, Emotion, Ending, Visuals)
              </p>
            </div>
            <span className="text-xs text-slate-400 font-mono">
              {clips.length} moments available
            </span>
          </div>

          {clips.length === 0 ? (
            <div className="text-center py-16 bg-[#111317]/50 border border-dashed border-white/[0.10] rounded-xl space-y-4">
              <Sparkles className="w-8 h-8 text-sky-400 mx-auto opacity-70" />
              <div className="space-y-1">
                <p className="text-sm font-medium text-slate-200">No clips discovered yet</p>
                <p className="text-xs text-slate-400 max-w-md mx-auto">
                  Click "Run AI Discovery" above to transcribe audio, detect scenes, track speakers, and rank viral 9:16 moments.
                </p>
              </div>
              <button
                onClick={handleRunFullPipeline}
                disabled={isProcessing}
                className="px-4 py-2 rounded-lg bg-sky-400 hover:bg-sky-300 text-slate-950 text-xs font-semibold shadow-sm inline-flex items-center gap-2 transition"
              >
                <Zap className="w-3.5 h-3.5" />
                Start AI Analysis
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {clips.map((clip) => {
                const isRendering = renderingClipId === clip.id;
                return (
                  <div
                    key={clip.id}
                    className="bg-[#111317] border border-white/[0.08] hover:border-white/[0.16] rounded-xl p-5 flex flex-col justify-between transition-all group shadow-carbon-card space-y-4"
                  >
                    <div className="space-y-3">
                      {/* Header with Rank & Virality Score */}
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono font-bold px-2 py-0.5 rounded-md bg-[#16191F] text-slate-300 border border-white/[0.08]">
                          #{clip.rank}
                        </span>
                        <div className={`px-2.5 py-0.5 rounded-md border text-xs font-bold font-mono flex items-center gap-1.5 ${getGradeColor(clip.letter_grade)}`}>
                          <span>{clip.letter_grade}</span>
                          <span className="opacity-75 font-normal">| {Math.round(clip.virality_score)}/100</span>
                        </div>
                      </div>

                      {/* Clip Title & Duration */}
                      <div>
                        <h3 className="text-sm font-bold text-white group-hover:text-sky-300 transition line-clamp-2">
                          {clip.title}
                        </h3>
                        <p className="text-[11px] text-slate-400 font-mono mt-1 flex items-center gap-1.5">
                          <Clock className="w-3 h-3 text-slate-500" />
                          {formatSeconds(clip.start_time)} – {formatSeconds(clip.end_time)} ({clip.duration.toFixed(1)}s)
                        </p>
                      </div>

                      {/* Hook Quote */}
                      {clip.hook && (
                        <div className="p-2.5 rounded-lg bg-[#16191F] border border-white/[0.06] text-xs text-amber-300/90 italic">
                          "{clip.hook}..."
                        </div>
                      )}

                      {/* Summary */}
                      {clip.summary && (
                        <p className="text-xs text-slate-400 line-clamp-3 leading-relaxed">
                          {clip.summary}
                        </p>
                      )}
                    </div>

                    {/* Card Actions */}
                    <div className="pt-3 border-t border-white/[0.06] flex items-center gap-2">
                      <Link
                        href={`/projects/${projectId}/clips/${clip.id}`}
                        className="flex-1 py-1.5 rounded-lg bg-[#16191F] hover:bg-[#1E222A] text-slate-200 text-xs font-medium text-center flex items-center justify-center gap-1.5 transition border border-white/[0.08]"
                      >
                        <Sliders className="w-3.5 h-3.5 text-sky-400" />
                        Edit in Studio
                      </Link>

                      <button
                        onClick={() => handleRenderClip(clip.id)}
                        disabled={isRendering}
                        className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition ${
                          clip.rendered
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/20"
                            : "bg-sky-400 hover:bg-sky-300 text-slate-950"
                        }`}
                      >
                        {isRendering ? (
                          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        ) : clip.rendered ? (
                          <>
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                            Rendered
                          </>
                        ) : (
                          <>
                            <Zap className="w-3.5 h-3.5" />
                            Render
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

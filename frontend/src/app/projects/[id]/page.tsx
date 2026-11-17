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
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Top Navigation */}
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur sticky top-0 z-40 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            href="/"
            className="p-2 rounded-lg bg-slate-800/80 hover:bg-slate-750 text-slate-400 hover:text-white transition"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-lg font-bold text-white flex items-center gap-2">
              {project.title}
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 border border-slate-700 text-slate-300 font-normal">
                {project.status.toUpperCase()}
              </span>
            </h1>
            <p className="text-xs text-slate-400">
              {project.width}x{project.height} · {project.fps} FPS · {formatSeconds(project.duration)}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href={`/projects/${projectId}/exports`}
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-sm font-medium flex items-center gap-2 transition"
          >
            <Download className="w-4 h-4 text-emerald-400" />
            Exports Gallery
          </Link>
          <button
            onClick={handleRunFullPipeline}
            disabled={isProcessing}
            className={`px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition shadow-lg ${
              isProcessing
                ? "bg-indigo-600/50 cursor-not-allowed text-indigo-200"
                : "bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-600/30"
            }`}
          >
            {isProcessing ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Processing AI...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4 text-amber-300" />
                {clips.length > 0 ? "Re-Run AI Discovery" : "Run AI Discovery"}
              </>
            )}
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 p-8 max-w-7xl mx-auto w-full space-y-8">
        {/* Processing Banner */}
        {isProcessing && (
          <div className="p-4 rounded-xl bg-indigo-950/40 border border-indigo-500/30 flex items-center gap-4 animate-pulse">
            <RefreshCw className="w-6 h-6 text-indigo-400 animate-spin flex-shrink-0" />
            <div>
              <p className="text-sm font-semibold text-indigo-200">AI Pipeline Running</p>
              <p className="text-xs text-indigo-300/80">{processingStage}</p>
            </div>
          </div>
        )}

        {/* Error Banner */}
        {errorMsg && (
          <div className="p-4 rounded-xl bg-red-950/40 border border-red-500/30 flex items-center gap-3 text-red-200 text-sm">
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
            <p>{errorMsg}</p>
          </div>
        )}

        {/* Source Video Overview Card */}
        <section className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 flex flex-col md:flex-row gap-6 items-start">
          <div className="w-full md:w-80 h-44 rounded-xl overflow-hidden bg-slate-950 border border-slate-800 relative flex-shrink-0">
            <img
              src={getThumbnailUrl(project.id)}
              alt={project.title}
              className="w-full h-full object-cover"
              onError={(e) => {
                (e.target as HTMLElement).style.display = "none";
              }}
            />
            <div className="absolute inset-0 bg-gradient-to-t from-slate-950/80 via-transparent to-transparent flex items-end p-3">
              <span className="text-xs font-mono bg-black/60 px-2 py-0.5 rounded text-slate-200">
                {formatSeconds(project.duration)}
              </span>
            </div>
          </div>

          <div className="flex-1 space-y-3">
            <div>
              <h2 className="text-base font-semibold text-white">Target Instructions</h2>
              <p className="text-sm text-slate-300 mt-1 leading-relaxed bg-slate-950/50 p-3 rounded-lg border border-slate-800/80">
                {project.instructions || "Find viral self-contained clips between 30 and 60 seconds."}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 pt-2">
              <div className="flex items-center gap-1.5">
                <Video className="w-4 h-4 text-slate-500" />
                <span>{project.original_filename}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Layers className="w-4 h-4 text-slate-500" />
                <span>{clips.length} Discovered Moments</span>
              </div>
            </div>
          </div>
        </section>

        {/* Candidate Shorts Section */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                <Flame className="w-5 h-5 text-amber-400" />
                Ranked Viral Candidates
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Evaluated across 7 Opus virality dimensions (Hook, Flow, Context, Value, Emotion, Ending, Visuals)
              </p>
            </div>
            <span className="text-xs text-slate-400 font-mono">
              Showing {clips.length} moments
            </span>
          </div>

          {clips.length === 0 ? (
            <div className="text-center py-16 bg-slate-900/30 border border-dashed border-slate-800 rounded-2xl space-y-4">
              <Sparkles className="w-10 h-10 text-indigo-400 mx-auto opacity-60" />
              <div className="space-y-1">
                <p className="text-base font-medium text-slate-300">No clips discovered yet</p>
                <p className="text-xs text-slate-500 max-w-md mx-auto">
                  Click "Run AI Discovery" above to transcribe, track faces, and extract viral 9:16 vertical shorts.
                </p>
              </div>
              <button
                onClick={handleRunFullPipeline}
                disabled={isProcessing}
                className="px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition shadow-lg shadow-indigo-600/30 inline-flex items-center gap-2"
              >
                <Zap className="w-4 h-4" />
                Start AI Analysis
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {clips.map((clip) => {
                const isRendering = renderingClipId === clip.id;
                return (
                  <div
                    key={clip.id}
                    className="bg-slate-900/80 border border-slate-800 hover:border-slate-700/80 rounded-2xl p-5 flex flex-col justify-between transition-all group hover:shadow-xl hover:shadow-indigo-500/5 space-y-4"
                  >
                    <div className="space-y-3">
                      {/* Header with Rank & Virality Score */}
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                          #{clip.rank}
                        </span>
                        <div className={`px-2.5 py-1 rounded-full border text-xs font-bold flex items-center gap-1.5 ${getGradeColor(clip.letter_grade)}`}>
                          <span>{clip.letter_grade}</span>
                          <span className="opacity-70 font-normal">| {Math.round(clip.virality_score)}/100</span>
                        </div>
                      </div>

                      {/* Clip Title & Duration */}
                      <div>
                        <h3 className="text-base font-bold text-white group-hover:text-indigo-300 transition line-clamp-2">
                          {clip.title}
                        </h3>
                        <p className="text-xs text-slate-400 font-mono mt-1 flex items-center gap-1.5">
                          <Clock className="w-3.5 h-3.5 text-slate-500" />
                          {formatSeconds(clip.start_time)} – {formatSeconds(clip.end_time)} ({clip.duration.toFixed(1)}s)
                        </p>
                      </div>

                      {/* Hook Quote */}
                      {clip.hook && (
                        <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80 text-xs text-amber-200/90 italic">
                          "{clip.hook}..."
                        </div>
                      )}

                      {/* Why Chosen Rationale */}
                      {clip.summary && (
                        <p className="text-xs text-slate-400 line-clamp-3 leading-relaxed">
                          {clip.summary}
                        </p>
                      )}
                    </div>

                    {/* Card Actions */}
                    <div className="pt-2 border-t border-slate-800/80 flex items-center gap-2">
                      <Link
                        href={`/projects/${projectId}/clips/${clip.id}`}
                        className="flex-1 py-2 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-200 text-xs font-medium text-center flex items-center justify-center gap-1.5 transition border border-slate-700/60"
                      >
                        <Sliders className="w-3.5 h-3.5 text-indigo-400" />
                        Edit in Studio
                      </Link>

                      <button
                        onClick={() => handleRenderClip(clip.id)}
                        disabled={isRendering}
                        className={`px-3 py-2 rounded-lg text-xs font-medium flex items-center gap-1.5 transition ${
                          clip.rendered
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/20"
                            : "bg-indigo-600 hover:bg-indigo-500 text-white"
                        }`}
                      >
                        {isRendering ? (
                          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        ) : clip.rendered ? (
                          <>
                            <CheckCircle2 className="w-3.5 h-3.5" />
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

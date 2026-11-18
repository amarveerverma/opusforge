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
      setProcessingStage("Transcribing audio with WhisperX (word timestamps on RTX 4060)...");
      await runTranscription(projectId);

      // 2. Multi-Modal Analysis (Diarization + Scene Cuts + MediaPipe)
      setProcessingStage("Analyzing scenes, speaker turns & facial tracks (MediaPipe)...");
      await runAnalysis(projectId);

      // 3. AI Clip Discovery
      setProcessingStage("Executing OmniRoute AI decision engine for viral hooks & rankings...");
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
    if (grade.startsWith("B")) return "bg-purple-500/10 text-purple-400 border-purple-500/30";
    return "bg-zinc-800 text-zinc-300 border-zinc-700";
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0B0B10] flex items-center justify-center text-zinc-400 font-mono text-sm">
        <RefreshCw className="w-5 h-5 animate-spin mr-3 text-purple-400" />
        Loading Opus.pro project workspace...
      </div>
    );
  }

  if (!project) {
    return (
      <div className="min-h-screen bg-[#0B0B10] flex flex-col items-center justify-center text-zinc-400 space-y-4">
        <p className="text-zinc-200 font-semibold">Project not found</p>
        <Link href="/" className="px-4 py-2 rounded-lg bg-[#181824] border border-[#28243C] text-xs text-purple-300">
          ← Return to Dashboard
        </Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0B0B10] text-zinc-100 flex flex-col font-sans">
      {/* Top Header */}
      <header className="border-b border-[#28243C] bg-[#121219]/90 backdrop-blur-md sticky top-0 z-40 px-6 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            href="/"
            className="p-1.5 rounded-lg bg-[#181824] hover:bg-[#202030] text-zinc-400 hover:text-white transition border border-[#28243C]"
            title="Back to Dashboard"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <h1 className="font-bold text-sm md:text-base text-white truncate max-w-md">
              {project.title}
            </h1>
            <p className="text-[11px] text-zinc-400 flex items-center gap-2">
              <span>Opus.pro Discovery Hub</span>
              <span className="text-purple-400 font-mono font-medium">⚡ Powered by OmniRoute</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href={`/projects/${project.id}/exports`}
            className="px-3.5 py-1.5 rounded-lg bg-[#181824] hover:bg-[#202030] text-zinc-300 text-xs font-semibold flex items-center gap-2 border border-[#28243C] transition"
          >
            <Download className="w-3.5 h-3.5 text-purple-400" />
            <span>Exports</span>
          </Link>

          <button
            onClick={handleRunFullPipeline}
            disabled={isProcessing}
            className="px-4 py-1.5 rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-bold flex items-center gap-2 shadow-lg shadow-purple-600/25 transition disabled:opacity-50"
          >
            {isProcessing ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span>Analyzing Video...</span>
              </>
            ) : (
              <>
                <Zap className="w-3.5 h-3.5" />
                <span>{clips.length > 0 ? "Re-Run OmniRoute Discovery" : "Run OmniRoute Discovery"}</span>
              </>
            )}
          </button>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-8 space-y-8">
        {/* Processing Banner */}
        {isProcessing && (
          <div className="p-4 rounded-xl bg-purple-950/40 border border-purple-500/40 flex items-center gap-4 animate-pulse">
            <RefreshCw className="w-5 h-5 text-purple-400 animate-spin flex-shrink-0" />
            <div>
              <p className="text-sm font-semibold text-purple-200">Local AI Pipeline Active</p>
              <p className="text-xs text-zinc-400 font-mono">{processingStage}</p>
            </div>
          </div>
        )}

        {/* Error Banner */}
        {errorMsg && (
          <div className="p-4 rounded-xl bg-red-950/40 border border-red-500/40 flex items-center gap-3 text-red-300 text-sm">
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
            <p>{errorMsg}</p>
          </div>
        )}

        {/* Source Video Overview Card */}
        <section className="bg-[#121219] border border-[#28243C] rounded-2xl p-5 flex flex-col md:flex-row gap-5 items-start shadow-xl shadow-purple-950/10">
          <div className="w-full md:w-72 h-40 rounded-xl overflow-hidden bg-black/60 border border-zinc-800 relative flex-shrink-0">
            <img
              src={getThumbnailUrl(project.id)}
              alt={project.title}
              className="w-full h-full object-cover"
              onError={(e) => {
                (e.target as HTMLElement).style.display = "none";
              }}
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent flex items-end p-2.5">
              <span className="text-[11px] font-mono bg-black/80 px-2 py-0.5 rounded text-purple-300 border border-white/10">
                {formatSeconds(project.duration)}
              </span>
            </div>
          </div>

          <div className="flex-1 space-y-3">
            <div>
              <h2 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider font-mono">
                AI Clipping Focus
              </h2>
              <p className="text-xs text-zinc-200 mt-1.5 leading-relaxed bg-[#171722] p-3 rounded-xl border border-[#28243C]">
                {project.instructions || "Find viral self-contained clips between 30 and 60 seconds."}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-4 text-xs text-zinc-400 pt-1 font-mono text-[11px]">
              <div className="flex items-center gap-1.5">
                <Video className="w-3.5 h-3.5 text-zinc-500" />
                <span className="truncate max-w-xs">{project.original_filename}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-zinc-500" />
                <span className="text-purple-400 font-semibold">{clips.length} Viral Moments Ready</span>
              </div>
            </div>
          </div>
        </section>

        {/* Candidate Shorts Section */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Flame className="w-4 h-4 text-purple-400" />
                Ranked Viral 9:16 Shorts
              </h2>
              <p className="text-xs text-zinc-400 mt-0.5">
                Ranked using Opus Virality scoring (Hook Strength, Retention, Emotional Pacing, Decisive Ending)
              </p>
            </div>
            <span className="text-xs text-purple-400 font-mono font-semibold">
              {clips.length} clips discovered
            </span>
          </div>

          {clips.length === 0 ? (
            <div className="text-center py-16 bg-[#121219]/60 border border-dashed border-[#28243C] rounded-2xl space-y-4">
              <Sparkles className="w-8 h-8 text-purple-400 mx-auto opacity-70" />
              <div className="space-y-1">
                <p className="text-sm font-medium text-zinc-200">No clips generated yet</p>
                <p className="text-xs text-zinc-400 max-w-md mx-auto">
                  Click "Run OmniRoute Discovery" above to run audio transcription, speaker diarization, face tracking, and viral ranking.
                </p>
              </div>
              <button
                onClick={handleRunFullPipeline}
                disabled={isProcessing}
                className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-bold shadow-lg shadow-purple-600/30 inline-flex items-center gap-2 transition"
              >
                <Zap className="w-4 h-4" />
                Start OmniRoute Analysis
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {clips.map((clip) => {
                const isRendering = renderingClipId === clip.id;
                return (
                  <div
                    key={clip.id}
                    className="bg-[#121219] border border-[#28243C] hover:border-purple-500/50 rounded-2xl p-5 flex flex-col justify-between transition-all group shadow-xl hover:shadow-purple-950/20 space-y-4"
                  >
                    <div className="space-y-3">
                      {/* Header with Rank & Opus Virality Dial */}
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono font-bold px-2 py-0.5 rounded-md bg-[#171722] text-zinc-300 border border-zinc-800">
                          #{clip.rank}
                        </span>
                        <div className={`px-2.5 py-1 rounded-full border text-xs font-bold font-mono flex items-center gap-1.5 ${getGradeColor(clip.letter_grade)}`}>
                          <span>🔥 {Math.round(clip.virality_score)}</span>
                          <span className="opacity-75 font-normal">({clip.letter_grade})</span>
                        </div>
                      </div>

                      {/* Clip Title & Duration */}
                      <div>
                        <h3 className="text-sm font-bold text-white group-hover:text-purple-300 transition line-clamp-2">
                          {clip.title}
                        </h3>
                        <p className="text-[11px] text-zinc-400 font-mono mt-1 flex items-center gap-1.5">
                          <Clock className="w-3 h-3 text-zinc-500" />
                          {formatSeconds(clip.start_time)} – {formatSeconds(clip.end_time)} ({clip.duration.toFixed(1)}s)
                        </p>
                      </div>

                      {/* Hook Quote */}
                      {clip.hook && (
                        <div className="p-3 rounded-xl bg-[#171722] border border-[#28243C] text-xs text-yellow-300/90 italic">
                          "{clip.hook}..."
                        </div>
                      )}

                      {/* Summary */}
                      {clip.summary && (
                        <p className="text-xs text-zinc-400 line-clamp-3 leading-relaxed">
                          {clip.summary}
                        </p>
                      )}
                    </div>

                    {/* Card Actions */}
                    <div className="pt-3 border-t border-zinc-800/80 flex items-center gap-2">
                      <Link
                        href={`/projects/${projectId}/clips/${clip.id}`}
                        className="flex-1 py-2 rounded-xl bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 text-xs font-semibold text-center flex items-center justify-center gap-1.5 transition border border-purple-500/30"
                      >
                        <Sliders className="w-3.5 h-3.5" />
                        Edit 9:16 Short
                      </Link>

                      <button
                        onClick={() => handleRenderClip(clip.id)}
                        disabled={isRendering}
                        className={`px-3 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition ${
                          clip.rendered
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/20"
                            : "bg-[#181824] hover:bg-[#222234] border border-[#28243C] text-zinc-200"
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
                            <Zap className="w-3.5 h-3.5 text-purple-400" />
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

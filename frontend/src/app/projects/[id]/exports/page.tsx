"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  Download,
  FolderOpen,
  Film,
  Play,
  CheckCircle2,
  Clock,
  HardDrive,
  RefreshCw,
  Video,
  Sparkles,
  Sliders,
} from "lucide-react";
import {
  fetchProject,
  fetchProjectRenders,
  revealRender,
  getRenderStreamUrl,
  getRenderDownloadUrl,
  Project,
  Render,
} from "@/lib/api";

export default function ExportsPage() {
  const params = useParams();
  const projectId = params?.id as string;

  const [project, setProject] = useState<Project | null>(null);
  const [renders, setRenders] = useState<Render[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const loadData = async () => {
    try {
      if (!projectId) return;
      const [proj, rlist] = await Promise.all([
        fetchProject(projectId),
        fetchProjectRenders(projectId),
      ]);
      setProject(proj);
      setRenders(rlist);
    } catch (err: any) {
      console.error("Failed to load exports:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [projectId]);

  const handleReveal = async (renderId: string) => {
    try {
      await revealRender(renderId);
    } catch {
      alert("Could not open file location");
    }
  };

  const formatSeconds = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  const formatBytes = (bytes: number) => {
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(1)} MB`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-400">
        <RefreshCw className="w-8 h-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0A0B0D] text-slate-100 flex flex-col font-sans">
      {/* Header — Gemini Carbon */}
      <header className="border-b border-white/[0.08] bg-[#0E1014]/90 backdrop-blur-md sticky top-0 z-40 px-6 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            href={`/projects/${projectId}`}
            className="p-2 rounded-lg bg-[#16191F] hover:bg-[#1E222A] text-slate-400 hover:text-white transition border border-white/[0.08]"
            title="Back to Project"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <h1 className="text-base font-bold text-white flex items-center gap-2">
              Rendered Exports Library
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-semibold">
                {renders.length} Rendered Shorts
              </span>
            </h1>
            <p className="text-[11px] text-slate-400 font-mono">
              {project?.title || "Project Exports"}
            </p>
          </div>
        </div>

        <Link
          href={`/projects/${projectId}`}
          className="px-3.5 py-1.5 rounded-lg bg-sky-400 hover:bg-sky-300 text-slate-950 text-xs font-semibold flex items-center gap-2 transition shadow-sm"
        >
          <Sliders className="w-3.5 h-3.5" />
          <span>Back to Project Clips</span>
        </Link>
      </header>

      {/* Main Grid */}
      <main className="flex-1 p-6 max-w-7xl mx-auto w-full space-y-6">
        {renders.length === 0 ? (
          <div className="text-center py-20 bg-[#111317]/50 border border-dashed border-white/[0.10] rounded-xl space-y-4">
            <Film className="w-10 h-10 text-slate-600 mx-auto" strokeWidth={1.5} />
            <div className="space-y-1">
              <p className="text-sm font-semibold text-slate-200">No rendered shorts yet</p>
              <p className="text-xs text-slate-400 max-w-sm mx-auto">
                Select your candidate clips and click "Render" or customize subtitles and framing in the Clip Studio.
              </p>
            </div>
            <Link
              href={`/projects/${projectId}`}
              className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-[#16191F] hover:bg-[#1E222A] text-xs font-medium text-slate-200 transition border border-white/[0.08]"
            >
              Browse Candidate Clips
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {renders.map((render) => (
              <div
                key={render.id}
                className="bg-[#111317] border border-white/[0.08] hover:border-white/[0.16] rounded-xl overflow-hidden shadow-carbon-card flex flex-col justify-between transition-all"
              >
                {/* 9:16 Video Player */}
                <div className="w-full bg-black flex items-center justify-center relative aspect-[9/16] max-h-[460px] overflow-hidden">
                  <video
                    src={getRenderStreamUrl(render.id)}
                    controls
                    className="w-full h-full object-cover"
                    playsInline
                  />
                  <div className="absolute top-3 left-3 bg-[#0A0B0D]/80 backdrop-blur px-2 py-0.5 rounded text-[10px] font-mono text-emerald-400 border border-emerald-500/30">
                    {render.encoder_used.toUpperCase()} NVENC
                  </div>
                </div>

                {/* Video Info & Controls */}
                <div className="p-4 space-y-3">
                  <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3 text-slate-500" />
                      {formatSeconds(render.duration)}
                    </span>
                    <span className="flex items-center gap-1">
                      <HardDrive className="w-3 h-3 text-slate-500" />
                      {formatBytes(render.file_size_bytes)}
                    </span>
                    <span className="bg-[#16191F] border border-white/[0.08] px-1.5 py-0.5 rounded text-[10px]">
                      {render.width}x{render.height}
                    </span>
                  </div>

                  <div className="pt-2 border-t border-white/[0.06] grid grid-cols-2 gap-2">
                    <button
                      onClick={() => handleReveal(render.id)}
                      className="py-1.5 rounded-lg bg-[#16191F] hover:bg-[#1E222A] text-slate-200 text-xs font-medium flex items-center justify-center gap-1.5 transition border border-white/[0.08]"
                    >
                      <FolderOpen className="w-3.5 h-3.5 text-amber-400" />
                      <span>Explorer</span>
                    </button>

                    <a
                      href={getRenderDownloadUrl(render.id)}
                      download
                      className="py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-semibold flex items-center justify-center gap-1.5 transition shadow-sm"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Download</span>
                    </a>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

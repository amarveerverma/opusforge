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
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur sticky top-0 z-40 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            href={`/projects/${projectId}`}
            className="p-2 rounded-lg bg-slate-800/80 hover:bg-slate-750 text-slate-400 hover:text-white transition"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-lg font-bold text-white flex items-center gap-2">
              Exports Library
              <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-normal">
                {renders.length} Rendered Shorts
              </span>
            </h1>
            <p className="text-xs text-slate-400">
              {project?.title || "Project Exports"}
            </p>
          </div>
        </div>

        <Link
          href={`/projects/${projectId}`}
          className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-2 transition"
        >
          <Sliders className="w-4 h-4" />
          Back to Project Clips
        </Link>
      </header>

      {/* Main Grid */}
      <main className="flex-1 p-8 max-w-7xl mx-auto w-full space-y-6">
        {renders.length === 0 ? (
          <div className="text-center py-20 bg-slate-900/30 border border-dashed border-slate-800 rounded-3xl space-y-4">
            <Film className="w-12 h-12 text-slate-600 mx-auto" />
            <div className="space-y-1">
              <p className="text-base font-semibold text-slate-300">No rendered shorts yet</p>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Open your project candidates and click "Render" or customize them in the Clip Studio Editor.
              </p>
            </div>
            <Link
              href={`/projects/${projectId}`}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-white transition border border-slate-700"
            >
              Browse Clips
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {renders.map((render) => (
              <div
                key={render.id}
                className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden shadow-lg flex flex-col justify-between"
              >
                {/* 9:16 Video Player */}
                <div className="w-full bg-black flex items-center justify-center relative aspect-[9/16] max-h-[460px] overflow-hidden">
                  <video
                    src={getRenderStreamUrl(render.id)}
                    controls
                    className="w-full h-full object-cover"
                    playsInline
                  />
                  <div className="absolute top-3 left-3 bg-black/60 backdrop-blur px-2 py-0.5 rounded text-[10px] font-mono text-emerald-400 border border-emerald-500/20">
                    {render.encoder_used.toUpperCase()}
                  </div>
                </div>

                {/* Video Info & Controls */}
                <div className="p-4 space-y-3">
                  <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5 text-slate-500" />
                      {formatSeconds(render.duration)}
                    </span>
                    <span className="flex items-center gap-1">
                      <HardDrive className="w-3.5 h-3.5 text-slate-500" />
                      {formatBytes(render.file_size_bytes)}
                    </span>
                    <span className="bg-slate-800 px-1.5 py-0.5 rounded text-[10px]">
                      {render.width}x{render.height}
                    </span>
                  </div>

                  <div className="pt-2 border-t border-slate-800/80 grid grid-cols-2 gap-2">
                    <button
                      onClick={() => handleReveal(render.id)}
                      className="py-2 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-200 text-xs font-medium flex items-center justify-center gap-1.5 transition border border-slate-700"
                    >
                      <FolderOpen className="w-3.5 h-3.5 text-amber-400" />
                      Explorer
                    </button>

                    <a
                      href={getRenderDownloadUrl(render.id)}
                      download
                      className="py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center justify-center gap-1.5 transition shadow"
                    >
                      <Download className="w-3.5 h-3.5" />
                      Download
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

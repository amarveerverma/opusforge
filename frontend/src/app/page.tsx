"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import {
  Film,
  Sparkles,
  Cpu,
  HardDrive,
  Activity,
  Plus,
  Trash2,
  Play,
  Clock,
  Video,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  X,
  Zap,
  UploadCloud,
  FileVideo,
  ArrowRight,
  Youtube,
  Link2,
} from "lucide-react";
import {
  fetchHealth,
  fetchSystemStatus,
  fetchProjects,
  createProject,
  deleteProject,
  uploadVideoWithProgress,
  importYouTubeVideo,
  getThumbnailUrl,
  Project,
  SystemStatus,
} from "@/lib/api";

export default function Dashboard() {
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [backendOnline, setBackendOnline] = useState<boolean>(false);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [modalOpen, setModalOpen] = useState<boolean>(false);
  
  // New Project Form & Upload State
  const [sourceMode, setSourceMode] = useState<"file" | "youtube">("file");
  const [youtubeUrl, setYoutubeUrl] = useState<string>("");
  const [newTitle, setNewTitle] = useState<string>("");
  const [newInstructions, setNewInstructions] = useState<string>(
    "Find the 5 most engaging educational moments, create 30–60 second clips, use dynamic captions and focus on the active speaker."
  );
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState<boolean>(false);
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadPercent, setUploadPercent] = useState<number>(0);
  const [uploadStage, setUploadStage] = useState<string>("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load telemetry & projects
  const loadData = async () => {
    try {
      await fetchHealth();
      setBackendOnline(true);
      const [sys, projs] = await Promise.all([
        fetchSystemStatus(),
        fetchProjects(),
      ]);
      setSystemStatus(sys);
      setProjects(projs);
    } catch (err: any) {
      setBackendOnline(false);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      setSelectedFile(file);
      if (!newTitle) {
        setNewTitle(file.name.replace(/\.[^/.]+$/, ""));
      }
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      setSelectedFile(file);
      if (!newTitle) {
        setNewTitle(file.name.replace(/\.[^/.]+$/, ""));
      }
    }
  };

  const handleCreateAndUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;

    setUploading(true);
    setUploadStage("Creating project record...");
    try {
      // 1. Create project record
      const created = await createProject(newTitle.trim(), newInstructions.trim());

      // 2. Ingest video file or YouTube URL
      if (sourceMode === "youtube" && youtubeUrl.trim()) {
        setUploadStage("Downloading YouTube video via local yt-dlp...");
        setUploadPercent(50);
        const updated = await importYouTubeVideo(created.id, youtubeUrl.trim());
        setProjects([updated, ...projects.filter((p) => p.id !== updated.id)]);
      } else if (selectedFile) {
        setUploadStage("Uploading media to local storage...");
        const updated = await uploadVideoWithProgress(
          created.id,
          selectedFile,
          (percent) => {
            setUploadPercent(percent);
            if (percent === 100) {
              setUploadStage("FFprobe inspecting & generating thumbnails...");
            }
          }
        );
        setProjects([updated, ...projects.filter((p) => p.id !== updated.id)]);
      } else {
        setProjects([created, ...projects]);
      }

      // Reset modal state
      setNewTitle("");
      setSelectedFile(null);
      setYoutubeUrl("");
      setUploadPercent(0);
      setUploadStage("");
      setModalOpen(false);
    } catch (err: any) {
      alert("Failed to create and upload project: " + err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteProject = async (id: string) => {
    if (!confirm("Are you sure you want to delete this project?")) return;
    try {
      await deleteProject(id);
      setProjects(projects.filter((p) => p.id !== id));
    } catch (err: any) {
      alert("Failed to delete project: " + err.message);
    }
  };

  const formatDuration = (sec: number) => {
    if (!sec || sec <= 0) return "--:--";
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}:${s < 10 ? "0" : ""}${s}`;
  };

  const vramPercent = systemStatus?.gpu.vram_total_mb
    ? Math.round((systemStatus.gpu.vram_used_mb / systemStatus.gpu.vram_total_mb) * 100)
    : 0;

  return (
    <div className="min-h-screen bg-[#0A0B0D] text-slate-100 flex flex-col font-sans">
      {/* Top Navigation Bar — Gemini Carbon Studio Header */}
      <header className="border-b border-white/[0.08] bg-[#0E1014]/90 backdrop-blur-md sticky top-0 z-40 px-6 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3.5">
          <div className="w-8 h-8 rounded-lg bg-sky-400/10 border border-sky-400/30 flex items-center justify-center shadow-sm">
            <Film className="w-4 h-4 text-sky-400" strokeWidth={1.75} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-base tracking-tight text-white flex items-center gap-1.5">
                CLIPFORGE <span className="w-1.5 h-1.5 rounded-full bg-sky-400 inline-block animate-pulse" />
              </span>
              <span className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded-md bg-[#16191F] text-slate-300 border border-white/[0.08]">
                Gemini Carbon Studio
              </span>
            </div>
            <p className="text-[11px] text-slate-400">100% Offline AI Video Repurposing Suite</p>
          </div>
        </div>

        {/* Live Hardware Telemetry Pills */}
        <div className="flex items-center gap-3">
          {/* GPU Telemetry */}
          <div className="hidden lg:flex items-center gap-3 px-3.5 py-1.5 rounded-lg bg-[#111317] border border-white/[0.08] text-xs">
            <div className="flex items-center gap-1.5 text-emerald-400 font-medium">
              <Zap className="w-3.5 h-3.5 fill-emerald-400/20" strokeWidth={1.75} />
              <span>{systemStatus?.gpu.name || "RTX 4060 GPU"}</span>
            </div>
            <div className="h-3 w-[1px] bg-white/[0.10]" />
            <div className="flex items-center gap-2">
              <span className="text-slate-400">VRAM:</span>
              <div className="w-16 h-1.5 bg-[#1E222A] rounded-full overflow-hidden">
                <div
                  className="h-full bg-sky-400 rounded-full transition-all duration-500"
                  style={{ width: `${vramPercent}%` }}
                />
              </div>
              <span className="font-mono text-slate-200 text-[11px]">
                {systemStatus ? `${systemStatus.gpu.vram_used_mb}MB / ${systemStatus.gpu.vram_total_mb}MB` : "--"}
              </span>
            </div>
          </div>

          {/* RAM Telemetry */}
          <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#111317] border border-white/[0.08] text-xs text-slate-400">
            <Cpu className="w-3.5 h-3.5 text-slate-400" strokeWidth={1.75} />
            <span>RAM:</span>
            <span className="font-mono text-slate-200 text-[11px]">
              {systemStatus ? `${systemStatus.ram.used_gb} / ${systemStatus.ram.total_gb} GB` : "--"}
            </span>
          </div>

          {/* Disk Telemetry */}
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#111317] border border-white/[0.08] text-xs text-slate-400">
            <HardDrive className="w-3.5 h-3.5 text-slate-400" strokeWidth={1.75} />
            <span className="font-mono text-slate-200 text-[11px]">
              {systemStatus ? `${systemStatus.disk.free_gb} GB Free` : "--"}
            </span>
          </div>

          {/* Server Status Dot */}
          <div className="flex items-center gap-2 px-2.5 py-1 rounded-lg bg-[#111317] border border-white/[0.08] text-xs">
            <span
              className={`w-2 h-2 rounded-full ${
                backendOnline ? "bg-emerald-400 shadow-sm shadow-emerald-400/50 animate-pulse" : "bg-rose-500"
              }`}
            />
            <span className="text-slate-300 font-medium text-[11px]">
              {backendOnline ? "CUDA Hardware Active" : "Offline"}
            </span>
          </div>

          {/* New Project Button */}
          <button
            onClick={() => setModalOpen(true)}
            className="flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-sky-400 hover:bg-sky-300 text-slate-950 font-semibold text-xs tracking-wide shadow-sm transition-all hover:scale-[1.01] active:scale-[0.99]"
          >
            <Plus className="w-3.5 h-3.5" strokeWidth={2.5} />
            <span>+ New Project</span>
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-8">
        {/* Banner Alert if Offline */}
        {!backendOnline && !loading && (
          <div className="mb-8 p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center gap-3">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <div>
              <p className="font-semibold text-sm">FastAPI Backend is Offline</p>
              <p className="text-xs text-rose-400/80">
                Start the backend server on port 8000 using{" "}
                <code className="bg-black/40 px-1.5 py-0.5 rounded text-white">python -m uvicorn backend.app.main:app --port 8000</code>
              </p>
            </div>
          </div>
        )}

        {/* Studio Overview Metrics */}
        <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <div className="p-5 rounded-xl bg-[#111317] border border-white/[0.08] hover:border-white/[0.14] transition-all shadow-carbon-card">
            <div className="flex items-center justify-between text-slate-400 mb-2">
              <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400">Total Projects</span>
              <Video className="w-4 h-4 text-sky-400" strokeWidth={1.75} />
            </div>
            <div className="text-2xl font-bold font-mono tracking-tight text-white">{projects.length}</div>
            <p className="text-[11px] text-slate-400 mt-1">Saved locally in SQLite WAL</p>
          </div>

          <div className="p-5 rounded-xl bg-[#111317] border border-white/[0.08] hover:border-white/[0.14] transition-all shadow-carbon-card">
            <div className="flex items-center justify-between text-slate-400 mb-2">
              <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400">Target Hardware</span>
              <Cpu className="w-4 h-4 text-emerald-400" strokeWidth={1.75} />
            </div>
            <div className="text-lg font-bold tracking-tight text-slate-100 truncate">
              {systemStatus?.gpu.name || "NVIDIA RTX 4060"}
            </div>
            <p className="text-[11px] text-emerald-400/90 mt-1">8 GB VRAM · CUDA 12.2 FP16 Active</p>
          </div>

          <div className="p-5 rounded-xl bg-[#111317] border border-white/[0.08] hover:border-white/[0.14] transition-all shadow-carbon-card">
            <div className="flex items-center justify-between text-slate-400 mb-2">
              <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400">NVENC Engine</span>
              <Zap className="w-4 h-4 text-amber-400" strokeWidth={1.75} />
            </div>
            <div className="text-2xl font-bold font-mono tracking-tight text-white">Ready</div>
            <p className="text-[11px] text-slate-400 mt-1">0.000s Audio/Video Drift</p>
          </div>

          <div className="p-5 rounded-xl bg-[#111317] border border-white/[0.08] hover:border-white/[0.14] transition-all shadow-carbon-card">
            <div className="flex items-center justify-between text-slate-400 mb-2">
              <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400">Privacy Mode</span>
              <Sparkles className="w-4 h-4 text-sky-400" strokeWidth={1.75} />
            </div>
            <div className="text-2xl font-bold font-mono tracking-tight text-white">100% Local</div>
            <p className="text-[11px] text-slate-400 mt-1">Zero cloud dependencies</p>
          </div>
        </section>

        {/* Projects Section */}
        <section>
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-base font-bold tracking-tight text-white">Active Projects</h2>
              <p className="text-xs text-slate-400">Video source files, AI transcripts, and 9:16 virality candidate clips</p>
            </div>
            <button
              onClick={loadData}
              className="p-2 rounded-lg bg-[#16191F] border border-white/[0.08] hover:bg-[#1E222A] text-slate-400 hover:text-white transition-colors"
              title="Refresh projects"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>

          {loading ? (
            <div className="h-64 rounded-2xl border border-white/5 bg-[#121216]/50 flex items-center justify-center">
              <div className="flex items-center gap-3 text-zinc-400 text-sm">
                <RefreshCw className="w-5 h-5 animate-spin text-violet-500" />
                <span>Loading studio projects...</span>
              </div>
            </div>
          ) : projects.length === 0 ? (
            <div className="h-72 rounded-xl border border-dashed border-white/[0.10] bg-[#111317]/50 flex flex-col items-center justify-center text-center p-6">
              <div className="w-12 h-12 rounded-xl bg-sky-400/10 border border-sky-400/20 flex items-center justify-center text-sky-400 mb-4">
                <Video className="w-6 h-6" strokeWidth={1.75} />
              </div>
              <h3 className="font-semibold text-sm text-slate-200 mb-1">No Projects in Local Storage</h3>
              <p className="text-xs text-slate-400 max-w-sm mb-5">
                Import a video or paste a YouTube URL to discover viral 9:16 vertical clips on your RTX GPU.
              </p>
              <button
                onClick={() => setModalOpen(true)}
                className="flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-sky-400 hover:bg-sky-300 text-slate-950 font-semibold text-xs tracking-wide shadow-sm transition-all"
              >
                <Plus className="w-3.5 h-3.5" strokeWidth={2.5} />
                <span>Create New Project</span>
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {projects.map((proj) => {
                const hasMedia = proj.status === "ready" && proj.duration > 0;
                return (
                  <div
                    key={proj.id}
                    className="rounded-xl bg-[#111317] border border-white/[0.08] hover:border-white/[0.16] transition-all duration-200 overflow-hidden flex flex-col group shadow-carbon-card"
                  >
                    {/* Thumbnail / Media Header */}
                    <div className="h-44 bg-[#0A0B0D] relative flex items-center justify-center overflow-hidden border-b border-white/[0.08]">
                      {hasMedia ? (
                        <img
                          src={getThumbnailUrl(proj.id)}
                          alt={proj.title}
                          className="w-full h-full object-cover group-hover:scale-102 transition-transform duration-300"
                          onError={(e) => {
                            (e.target as HTMLImageElement).style.display = "none";
                          }}
                        />
                      ) : (
                        <Film className="w-8 h-8 text-slate-600 group-hover:text-sky-400/70 transition-colors" strokeWidth={1.5} />
                      )}

                      <div className="absolute inset-0 bg-gradient-to-t from-[#111317] via-transparent to-black/40 z-10" />

                      {/* Status Badge */}
                      <div className="absolute top-3 left-3 z-20">
                        <span className={`px-2 py-0.5 rounded-md text-[10px] font-mono tracking-wider uppercase backdrop-blur-md border ${
                          proj.status === "ready" || proj.status === "discovered"
                            ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/30"
                            : "bg-[#16191F]/90 text-slate-300 border-white/[0.10]"
                        }`}>
                          {proj.status}
                        </span>
                      </div>

                      {/* Resolution & Duration Pill */}
                      {hasMedia && (
                        <div className="absolute bottom-3 left-3 z-20 flex items-center gap-1.5">
                          <span className="px-2 py-0.5 rounded-md text-[10px] font-mono bg-black/80 backdrop-blur-md text-slate-200 border border-white/10">
                            {formatDuration(proj.duration)}
                          </span>
                          <span className="px-2 py-0.5 rounded-md text-[10px] font-mono font-medium bg-[#16191F]/90 backdrop-blur-md text-sky-300 border border-sky-400/30">
                            {proj.height || 1080}p
                          </span>
                        </div>
                      )}

                      {/* Delete button */}
                      <div className="absolute top-3 right-3 z-20 flex items-center gap-1.5">
                        <button
                          onClick={() => handleDeleteProject(proj.id)}
                          className="p-1.5 rounded-lg bg-black/60 hover:bg-rose-500/20 text-slate-400 hover:text-rose-400 transition-colors"
                          title="Delete project"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    {/* Card Content */}
                    <Link
                      href={`/projects/${proj.id}`}
                      className="p-5 flex-1 flex flex-col justify-between cursor-pointer group-hover:bg-white/[0.01] transition-colors"
                    >
                      <div>
                        <h3 className="font-semibold text-sm text-slate-100 group-hover:text-sky-300 transition-colors line-clamp-1 mb-1.5">
                          {proj.title}
                        </h3>
                        {proj.instructions && (
                          <p className="text-xs text-slate-400 line-clamp-2 mb-3 leading-relaxed">
                            {proj.instructions}
                          </p>
                        )}
                      </div>

                      <div className="pt-3 border-t border-white/[0.06] flex items-center justify-between text-[11px] text-slate-500 font-mono">
                        <div className="flex items-center gap-1.5">
                          <Clock className="w-3.5 h-3.5" />
                          <span>{new Date(proj.created_at).toLocaleDateString()}</span>
                        </div>
                        <div className="flex items-center gap-1 text-sky-400 font-medium">
                          <span>{proj.clips_count || 0} clips</span>
                          <ArrowRight className="w-3.5 h-3.5 ml-0.5" />
                        </div>
                      </div>
                    </Link>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      </main>

      {/* New Project & Video Upload Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-xl rounded-xl bg-[#111317] border border-white/[0.12] shadow-2xl p-6 relative">
            <button
              onClick={() => {
                if (!uploading) setModalOpen(false);
              }}
              disabled={uploading}
              className="absolute top-4 right-4 text-slate-400 hover:text-white p-1 rounded-lg transition-colors disabled:opacity-30"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-3 mb-5">
              <div className="w-9 h-9 rounded-lg bg-sky-400/10 border border-sky-400/30 flex items-center justify-center text-sky-400">
                <Video className="w-4 h-4" strokeWidth={1.75} />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">Create New Project</h3>
                <p className="text-xs text-slate-400">Import source video and specify natural language clipping targets</p>
              </div>
            </div>

            <form onSubmit={handleCreateAndUpload} className="space-y-4">
              {/* Source Mode Switcher: Upload File vs YouTube Link */}
              <div className="grid grid-cols-2 gap-2 p-1 bg-[#16191F] border border-white/[0.08] rounded-lg">
                <button
                  type="button"
                  onClick={() => setSourceMode("file")}
                  className={`py-2 rounded-md text-xs font-semibold flex items-center justify-center gap-2 transition-all ${
                    sourceMode === "file"
                      ? "bg-sky-400 text-slate-950 shadow-sm"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  <UploadCloud className="w-4 h-4" />
                  Upload Local File
                </button>
                <button
                  type="button"
                  onClick={() => setSourceMode("youtube")}
                  className={`py-2 rounded-md text-xs font-semibold flex items-center justify-center gap-2 transition-all ${
                    sourceMode === "youtube"
                      ? "bg-rose-500 text-white shadow-sm"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  <Youtube className="w-4 h-4 text-white" />
                  YouTube Link
                </button>
              </div>

              {sourceMode === "youtube" ? (
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">
                    YouTube Video URL *
                  </label>
                  <div className="relative">
                    <input
                      type="url"
                      placeholder="https://www.youtube.com/watch?v=..."
                      value={youtubeUrl}
                      onChange={(e) => setYoutubeUrl(e.target.value)}
                      required={sourceMode === "youtube"}
                      className="w-full pl-10 pr-3.5 py-2.5 rounded-lg bg-[#16191F] border border-white/[0.10] text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-sky-400 transition-colors"
                    />
                    <Youtube className="w-4 h-4 text-rose-500 absolute left-3.5 top-3" />
                  </div>
                  <p className="text-[11px] text-slate-500 mt-1.5">
                    Downloaded directly via local <code className="text-slate-400 font-mono">yt-dlp</code> up to 1080p MP4.
                  </p>
                </div>
              ) : (
                /* Drag and Drop Upload Zone */
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">
                    Source Video *
                  </label>
                  <div
                    onDragOver={(e) => {
                      e.preventDefault();
                      setDragOver(true);
                    }}
                    onDragLeave={() => setDragOver(false)}
                    onDrop={handleFileDrop}
                    onClick={() => fileInputRef.current?.click()}
                    className={`border border-dashed rounded-lg p-6 flex flex-col items-center justify-center cursor-pointer transition-all ${
                      dragOver
                        ? "border-sky-400 bg-sky-400/10"
                        : selectedFile
                        ? "border-emerald-500/40 bg-emerald-500/5"
                        : "border-white/[0.12] hover:border-white/[0.24] bg-[#16191F]/40"
                    }`}
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="video/mp4,video/quicktime,video/webm,video/x-matroska"
                      onChange={handleFileSelect}
                      className="hidden"
                    />

                    {selectedFile ? (
                      <div className="flex items-center gap-3 text-emerald-400">
                        <FileVideo className="w-8 h-8 flex-shrink-0" />
                        <div className="text-left overflow-hidden">
                          <p className="text-xs font-semibold text-slate-200 truncate max-w-[280px]">
                            {selectedFile.name}
                          </p>
                          <p className="text-[11px] text-slate-400 font-mono">
                            {(selectedFile.size / (1024 * 1024)).toFixed(1)} MB · Ready to ingest
                          </p>
                        </div>
                      </div>
                    ) : (
                      <>
                        <UploadCloud className="w-7 h-7 text-slate-500 mb-2" strokeWidth={1.5} />
                        <p className="text-xs font-medium text-slate-200 text-center">
                          Drag and drop video here, or <span className="text-sky-400 font-semibold">browse files</span>
                        </p>
                        <p className="text-[10px] text-slate-500 mt-1">
                          MP4, MOV, WebM, MKV · Stays 100% on your local disk
                        </p>
                      </>
                    )}
                  </div>
                </div>
              )}

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Project Title *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Sam Altman AI Interview"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-lg bg-[#16191F] border border-white/[0.10] text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-sky-400 transition-colors"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Natural Language AI Instructions
                </label>
                <textarea
                  rows={2}
                  value={newInstructions}
                  onChange={(e) => setNewInstructions(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-lg bg-[#16191F] border border-white/[0.10] text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-sky-400 transition-colors"
                  placeholder="Describe the moments you want discovered..."
                />
              </div>

              {/* Upload Progress Bar if Uploading */}
              {uploading && (
                <div className="p-3.5 rounded-lg bg-sky-950/30 border border-sky-400/20">
                  <div className="flex items-center justify-between text-xs mb-1.5">
                    <span className="text-sky-300 font-medium">{uploadStage}</span>
                    <span className="text-slate-400 font-mono">{uploadPercent}%</span>
                  </div>
                  <div className="w-full h-1.5 bg-[#16191F] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-sky-400 transition-all duration-300"
                      style={{ width: `${uploadPercent}%` }}
                    />
                  </div>
                </div>
              )}

              <div className="pt-2 flex items-center justify-end gap-3">
                <button
                  type="button"
                  disabled={uploading}
                  onClick={() => setModalOpen(false)}
                  className="px-3.5 py-2 rounded-lg bg-[#16191F] hover:bg-[#1E222A] text-slate-300 text-xs font-medium transition-colors disabled:opacity-40 border border-white/[0.08]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={uploading || !newTitle.trim()}
                  className="px-4 py-2 rounded-lg bg-sky-400 hover:bg-sky-300 disabled:opacity-50 text-slate-950 text-xs font-semibold shadow-sm transition-all"
                >
                  {uploading ? "Ingesting Video..." : "Create & Ingest Video"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

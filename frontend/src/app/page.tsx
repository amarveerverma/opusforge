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
} from "lucide-react";
import {
  fetchHealth,
  fetchSystemStatus,
  fetchProjects,
  createProject,
  deleteProject,
  uploadVideoWithProgress,
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

      // 2. Upload video file if provided
      if (selectedFile) {
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
    <div className="min-h-screen bg-[#09090B] text-zinc-100 flex flex-col">
      {/* Top Navigation Bar */}
      <header className="border-b border-white/5 bg-[#0D0D11]/80 backdrop-blur-md sticky top-0 z-40 px-6 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-violet-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-violet-600/20">
            <Film className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-zinc-200 to-zinc-400 bg-clip-text text-transparent">
                ClipForge
              </span>
              <span className="text-[10px] font-semibold tracking-wider uppercase px-2 py-0.5 rounded-full bg-violet-500/10 text-violet-400 border border-violet-500/20">
                Local Studio
              </span>
            </div>
            <p className="text-xs text-zinc-400">OpusClip-inspired AI Video Studio</p>
          </div>
        </div>

        {/* Live Hardware Telemetry Pills */}
        <div className="flex items-center gap-3">
          {/* GPU Telemetry */}
          <div className="hidden lg:flex items-center gap-3 px-3.5 py-1.5 rounded-lg bg-zinc-900/90 border border-white/5 text-xs">
            <div className="flex items-center gap-1.5 text-emerald-400 font-medium">
              <Zap className="w-3.5 h-3.5 fill-emerald-400/20" />
              <span>{systemStatus?.gpu.name || "RTX GPU"}</span>
            </div>
            <div className="h-3 w-[1px] bg-white/10" />
            <div className="flex items-center gap-2">
              <span className="text-zinc-400">VRAM:</span>
              <div className="w-16 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-violet-500 rounded-full transition-all duration-500"
                  style={{ width: `${vramPercent}%` }}
                />
              </div>
              <span className="font-mono text-zinc-300">
                {systemStatus ? `${systemStatus.gpu.vram_used_mb}MB / ${systemStatus.gpu.vram_total_mb}MB` : "--"}
              </span>
            </div>
          </div>

          {/* RAM Telemetry */}
          <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-zinc-900/90 border border-white/5 text-xs text-zinc-400">
            <Cpu className="w-3.5 h-3.5 text-zinc-400" />
            <span>RAM:</span>
            <span className="font-mono text-zinc-200">
              {systemStatus ? `${systemStatus.ram.used_gb} / ${systemStatus.ram.total_gb} GB` : "--"}
            </span>
          </div>

          {/* Disk Telemetry */}
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-zinc-900/90 border border-white/5 text-xs text-zinc-400">
            <HardDrive className="w-3.5 h-3.5 text-zinc-400" />
            <span className="font-mono text-zinc-200">
              {systemStatus ? `${systemStatus.disk.free_gb} GB Free` : "--"}
            </span>
          </div>

          {/* Server Status Dot */}
          <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-zinc-900 border border-white/5 text-xs">
            <span
              className={`w-2 h-2 rounded-full ${
                backendOnline ? "bg-emerald-500 shadow-sm shadow-emerald-500/50 animate-pulse" : "bg-rose-500"
              }`}
            />
            <span className="text-zinc-300 font-medium">
              {backendOnline ? "Local GPU Engine" : "Offline"}
            </span>
          </div>

          {/* New Project Button */}
          <button
            onClick={() => setModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-violet-600 hover:bg-violet-500 text-white font-medium text-xs tracking-wide shadow-md shadow-violet-600/20 transition-all hover:scale-[1.02] active:scale-[0.98]"
          >
            <Plus className="w-4 h-4" />
            <span>New Project</span>
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
          <div className="p-5 rounded-2xl bg-[#121216] border border-white/5 hover:border-white/10 transition-colors">
            <div className="flex items-center justify-between text-zinc-400 mb-3">
              <span className="text-xs font-medium uppercase tracking-wider">Total Projects</span>
              <Video className="w-4 h-4 text-violet-400" />
            </div>
            <div className="text-2xl font-bold tracking-tight text-white">{projects.length}</div>
            <p className="text-xs text-zinc-500 mt-1">Saved locally on your PC</p>
          </div>

          <div className="p-5 rounded-2xl bg-[#121216] border border-white/5 hover:border-white/10 transition-colors">
            <div className="flex items-center justify-between text-zinc-400 mb-3">
              <span className="text-xs font-medium uppercase tracking-wider">Target Hardware</span>
              <Cpu className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="text-lg font-bold tracking-tight text-zinc-100 truncate">
              {systemStatus?.gpu.name || "NVIDIA RTX 4060"}
            </div>
            <p className="text-xs text-emerald-400/90 mt-1">8 GB VRAM · CUDA 12.2 Active</p>
          </div>

          <div className="p-5 rounded-2xl bg-[#121216] border border-white/5 hover:border-white/10 transition-colors">
            <div className="flex items-center justify-between text-zinc-400 mb-3">
              <span className="text-xs font-medium uppercase tracking-wider">Hardware NVENC</span>
              <Zap className="w-4 h-4 text-amber-400" />
            </div>
            <div className="text-2xl font-bold tracking-tight text-white">Enabled</div>
            <p className="text-xs text-zinc-500 mt-1">h264_nvenc, hevc, av1 verified</p>
          </div>

          <div className="p-5 rounded-2xl bg-[#121216] border border-white/5 hover:border-white/10 transition-colors">
            <div className="flex items-center justify-between text-zinc-400 mb-3">
              <span className="text-xs font-medium uppercase tracking-wider">Privacy Mode</span>
              <Sparkles className="w-4 h-4 text-violet-400" />
            </div>
            <div className="text-2xl font-bold tracking-tight text-white">100% Local</div>
            <p className="text-xs text-zinc-500 mt-1">No videos sent to the cloud</p>
          </div>
        </section>

        {/* Projects Section */}
        <section>
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-lg font-bold tracking-tight text-white">Recent Projects</h2>
              <p className="text-xs text-zinc-400">Manage and inspect your video clipping pipelines</p>
            </div>
            <button
              onClick={loadData}
              className="p-2 rounded-lg bg-zinc-900 border border-white/5 hover:bg-zinc-800 text-zinc-400 hover:text-white transition-colors"
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
            <div className="h-72 rounded-2xl border border-dashed border-white/10 bg-[#121216]/40 flex flex-col items-center justify-center text-center p-6">
              <div className="w-14 h-14 rounded-2xl bg-violet-600/10 border border-violet-500/20 flex items-center justify-center text-violet-400 mb-4">
                <Video className="w-7 h-7" />
              </div>
              <h3 className="font-semibold text-base text-zinc-200 mb-1">No Projects Yet</h3>
              <p className="text-xs text-zinc-400 max-w-sm mb-5">
                Create your first project, upload a video, and let the local AI find viral 9:16 short moments automatically.
              </p>
              <button
                onClick={() => setModalOpen(true)}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-violet-600 hover:bg-violet-500 text-white font-medium text-xs tracking-wide shadow-md transition-all"
              >
                <Plus className="w-4 h-4" />
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
                    className="rounded-2xl bg-[#121216] border border-white/5 hover:border-violet-500/30 transition-all duration-300 overflow-hidden flex flex-col group shadow-lg shadow-black/40"
                  >
                    {/* Thumbnail / Media Header */}
                    <div className="h-44 bg-zinc-900 relative flex items-center justify-center overflow-hidden border-b border-white/5">
                      {hasMedia ? (
                        <img
                          src={getThumbnailUrl(proj.id)}
                          alt={proj.title}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                          onError={(e) => {
                            // Hide image if failed to load
                            (e.target as HTMLImageElement).style.display = "none";
                          }}
                        />
                      ) : (
                        <Film className="w-10 h-10 text-zinc-700 group-hover:text-violet-500/50 transition-colors" />
                      )}

                      <div className="absolute inset-0 bg-gradient-to-t from-[#121216] via-transparent to-black/30 z-10" />

                      {/* Status Badge */}
                      <div className="absolute top-3 left-3 z-20">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold tracking-wider uppercase backdrop-blur-md border ${
                          proj.status === "ready"
                            ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
                            : "bg-black/60 text-zinc-300 border-white/10"
                        }`}>
                          {proj.status}
                        </span>
                      </div>

                      {/* Resolution & Duration Pill */}
                      {hasMedia && (
                        <div className="absolute bottom-3 left-3 z-20 flex items-center gap-1.5">
                          <span className="px-2 py-0.5 rounded-md text-[10px] font-mono bg-black/70 backdrop-blur-md text-zinc-200 border border-white/10">
                            {formatDuration(proj.duration)}
                          </span>
                          <span className="px-2 py-0.5 rounded-md text-[10px] font-semibold bg-violet-950/80 backdrop-blur-md text-violet-300 border border-violet-500/30">
                            {proj.height}p
                          </span>
                        </div>
                      )}

                      {/* Action buttons */}
                      <div className="absolute top-3 right-3 z-20 flex items-center gap-1.5">
                        <button
                          onClick={() => handleDeleteProject(proj.id)}
                          className="p-1.5 rounded-lg bg-black/60 hover:bg-rose-500/20 text-zinc-400 hover:text-rose-400 transition-colors"
                          title="Delete project"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    {/* Card Content */}
                    <Link
                      href={`/projects/${proj.id}`}
                      className="p-5 flex-1 flex flex-col justify-between cursor-pointer group-hover:bg-white/[0.02] transition-colors"
                    >
                      <div>
                        <h3 className="font-semibold text-sm text-zinc-100 group-hover:text-violet-400 transition-colors line-clamp-1 mb-1">
                          {proj.title}
                        </h3>
                        {proj.instructions && (
                          <p className="text-xs text-zinc-400 line-clamp-2 mb-3">
                            {proj.instructions}
                          </p>
                        )}
                      </div>

                      <div className="pt-3 border-t border-white/5 flex items-center justify-between text-xs text-zinc-500">
                        <div className="flex items-center gap-1.5">
                          <Clock className="w-3.5 h-3.5" />
                          <span>{new Date(proj.created_at).toLocaleDateString()}</span>
                        </div>
                        <div className="flex items-center gap-1 text-violet-400 font-medium">
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
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-xl rounded-2xl bg-[#141419] border border-white/10 shadow-2xl p-6 relative">
            <button
              onClick={() => {
                if (!uploading) setModalOpen(false);
              }}
              disabled={uploading}
              className="absolute top-4 right-4 text-zinc-400 hover:text-white p-1 rounded-lg transition-colors disabled:opacity-30"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 rounded-xl bg-violet-600/20 border border-violet-500/30 flex items-center justify-center text-violet-400">
                <Video className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">Create New Project</h3>
                <p className="text-xs text-zinc-400">Upload a video and set natural language clipping instructions</p>
              </div>
            </div>

            <form onSubmit={handleCreateAndUpload} className="space-y-4">
              {/* Drag and Drop Upload Zone */}
              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1.5">
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
                  className={`border-2 border-dashed rounded-xl p-6 flex flex-col items-center justify-center cursor-pointer transition-all ${
                    dragOver
                      ? "border-violet-500 bg-violet-500/10"
                      : selectedFile
                      ? "border-emerald-500/40 bg-emerald-500/5"
                      : "border-white/10 hover:border-white/20 bg-zinc-900/50"
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
                        <p className="text-xs font-semibold text-zinc-200 truncate max-w-[280px]">
                          {selectedFile.name}
                        </p>
                        <p className="text-[11px] text-zinc-400">
                          {(selectedFile.size / (1024 * 1024)).toFixed(1)} MB · Ready to upload
                        </p>
                      </div>
                    </div>
                  ) : (
                    <>
                      <UploadCloud className="w-8 h-8 text-zinc-500 mb-2" />
                      <p className="text-xs font-medium text-zinc-200 text-center">
                        Drag and drop your video file here, or <span className="text-violet-400">browse</span>
                      </p>
                      <p className="text-[10px] text-zinc-500 mt-1">
                        MP4, MOV, WebM, MKV supported · Stays 100% on your PC
                      </p>
                    </>
                  )}
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                  Project Title *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Lex Fridman AI Debate"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-zinc-900 border border-white/10 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-violet-500 transition-colors"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                  Natural Language AI Instructions
                </label>
                <textarea
                  rows={2}
                  value={newInstructions}
                  onChange={(e) => setNewInstructions(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-zinc-900 border border-white/10 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-violet-500 transition-colors"
                  placeholder="Describe the moments you want discovered..."
                />
              </div>

              {/* Upload Progress Bar if Uploading */}
              {uploading && (
                <div className="p-3.5 rounded-xl bg-violet-950/30 border border-violet-500/20">
                  <div className="flex items-center justify-between text-xs mb-1.5">
                    <span className="text-violet-300 font-medium">{uploadStage}</span>
                    <span className="text-zinc-400 font-mono">{uploadPercent}%</span>
                  </div>
                  <div className="w-full h-2 bg-zinc-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-violet-500 transition-all duration-300"
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
                  className="px-4 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-medium transition-colors disabled:opacity-40"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={uploading || !newTitle.trim()}
                  className="px-5 py-2 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white text-xs font-semibold shadow-md shadow-violet-600/20 transition-all"
                >
                  {uploading ? "Processing Media..." : "Create & Ingest Video"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

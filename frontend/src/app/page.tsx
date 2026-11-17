"use client";

import { useEffect, useState } from "react";
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
} from "lucide-react";
import {
  fetchHealth,
  fetchSystemStatus,
  fetchProjects,
  createProject,
  deleteProject,
  Project,
  SystemStatus,
} from "@/lib/api";

export default function Dashboard() {
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [backendOnline, setBackendOnline] = useState<boolean>(false);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [modalOpen, setModalOpen] = useState<boolean>(false);
  
  // New Project Form State
  const [newTitle, setNewTitle] = useState<string>("");
  const [newInstructions, setNewInstructions] = useState<string>(
    "Find the 5 most engaging educational moments, create 30–60 second clips, use dynamic captions and focus on the active speaker."
  );
  const [creating, setCreating] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

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
      setErrorMsg(null);
    } catch (err: any) {
      setBackendOnline(false);
      setErrorMsg("Backend server offline. Ensure FastAPI is running on port 8000.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 4000); // Poll telemetry every 4s
    return () => clearInterval(interval);
  }, []);

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;
    setCreating(true);
    try {
      const created = await createProject(newTitle.trim(), newInstructions.trim());
      setProjects([created, ...projects]);
      setNewTitle("");
      setModalOpen(false);
    } catch (err: any) {
      alert("Failed to create project: " + err.message);
    } finally {
      setCreating(false);
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
              {projects.map((proj) => (
                <div
                  key={proj.id}
                  className="rounded-2xl bg-[#121216] border border-white/5 hover:border-violet-500/30 transition-all duration-300 overflow-hidden flex flex-col group shadow-lg shadow-black/40"
                >
                  {/* Thumbnail / Media Header */}
                  <div className="h-40 bg-zinc-900 relative flex items-center justify-center overflow-hidden border-b border-white/5">
                    <div className="absolute inset-0 bg-gradient-to-t from-[#121216] via-transparent to-transparent z-10" />
                    <Film className="w-10 h-10 text-zinc-700 group-hover:text-violet-500/50 transition-colors" />
                    <div className="absolute top-3 left-3 z-20">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold tracking-wider uppercase bg-black/60 backdrop-blur-md text-zinc-300 border border-white/10">
                        {proj.status}
                      </span>
                    </div>
                    <div className="absolute top-3 right-3 z-20">
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
                  <div className="p-5 flex-1 flex flex-col justify-between">
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
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </main>

      {/* New Project Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-lg rounded-2xl bg-[#141419] border border-white/10 shadow-2xl p-6 relative">
            <button
              onClick={() => setModalOpen(false)}
              className="absolute top-4 right-4 text-zinc-400 hover:text-white p-1 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 rounded-xl bg-violet-600/20 border border-violet-500/30 flex items-center justify-center text-violet-400">
                <Video className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">Create New Project</h3>
                <p className="text-xs text-zinc-400">Configure your local clipping session</p>
              </div>
            </div>

            <form onSubmit={handleCreateProject} className="space-y-4">
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
                  rows={3}
                  value={newInstructions}
                  onChange={(e) => setNewInstructions(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-zinc-900 border border-white/10 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-violet-500 transition-colors"
                  placeholder="Describe the moments you want discovered..."
                />
                <p className="text-[11px] text-zinc-500 mt-1">
                  The AI uses this guidance during narrative arc detection and scoring.
                </p>
              </div>

              <div className="pt-2 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-4 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating || !newTitle.trim()}
                  className="px-5 py-2 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white text-xs font-semibold shadow-md shadow-violet-600/20 transition-all"
                >
                  {creating ? "Creating..." : "Create Project"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

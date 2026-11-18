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
  Key,
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
  getOmniRouteConfig,
  Project,
  SystemStatus,
  OmniRouteConfig,
} from "@/lib/api";
import { OmniRouteModal } from "@/components/OmniRouteModal";

export default function Dashboard() {
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [backendOnline, setBackendOnline] = useState<boolean>(false);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [omniModalOpen, setOmniModalOpen] = useState<boolean>(false);
  const [omniConfig, setOmniConfig] = useState<OmniRouteConfig>({
    provider: "gemini",
    apiKey: "",
    baseUrl: "https://generativelanguage.googleapis.com/v1beta/openai",
    model: "gemini-2.0-flash",
  });

  // Opus.pro Ingestion State
  const [sourceMode, setSourceMode] = useState<"youtube" | "file">("youtube");
  const [youtubeUrl, setYoutubeUrl] = useState<string>("");
  const [projectTitle, setProjectTitle] = useState<string>("");
  const [durationPreset, setDurationPreset] = useState<string>("30-60");
  const [instructions, setInstructions] = useState<string>(
    "Find the 5 most engaging educational moments, create 30–60 second clips, use dynamic captions and focus on the active speaker."
  );
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState<boolean>(false);
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadPercent, setUploadPercent] = useState<number>(0);
  const [uploadStage, setUploadStage] = useState<string>("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load telemetry, projects, & OmniRoute config
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
    } catch {
      setBackendOnline(false);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setOmniConfig(getOmniRouteConfig());
    loadData();
    const interval = setInterval(loadData, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleDurationSelect = (dur: string) => {
    setDurationPreset(dur);
    if (dur === "<30") {
      setInstructions("Find the top moments under 30 seconds with explosive opening hooks.");
    } else if (dur === "30-60") {
      setInstructions("Find 30–60 second engaging moments with strong hooks, clear flow, and decisive punchlines.");
    } else if (dur === "60-90") {
      setInstructions("Find 60–90 second deep-dive educational takeaways with complete explanations.");
    } else {
      setInstructions("Find high-retention long narrative stories between 90 seconds and 3 minutes.");
    }
  };

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      setSelectedFile(file);
      if (!projectTitle) {
        setProjectTitle(file.name.replace(/\.[^/.]+$/, ""));
      }
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      setSelectedFile(file);
      if (!projectTitle) {
        setProjectTitle(file.name.replace(/\.[^/.]+$/, ""));
      }
    }
  };

  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    const titleToUse = projectTitle.trim() || (sourceMode === "youtube" ? "YouTube Video Repurposed" : selectedFile?.name.replace(/\.[^/.]+$/, "") || "Untitled Project");

    setUploading(true);
    setUploadStage("Initializing local workspace...");
    try {
      // 1. Create project record
      const created = await createProject(titleToUse, instructions.trim());

      // 2. Ingest video file or YouTube URL
      if (sourceMode === "youtube" && youtubeUrl.trim()) {
        setUploadStage("Downloading YouTube video via local yt-dlp...");
        setUploadPercent(50);
        const updated = await importYouTubeVideo(created.id, youtubeUrl.trim());
        setProjects([updated, ...projects.filter((p) => p.id !== updated.id)]);
      } else if (selectedFile) {
        setUploadStage("Uploading video file to local storage...");
        const updated = await uploadVideoWithProgress(
          created.id,
          selectedFile,
          (percent) => {
            setUploadPercent(percent);
            if (percent === 100) {
              setUploadStage("FFprobe inspecting metadata & generating keyframes...");
            }
          }
        );
        setProjects([updated, ...projects.filter((p) => p.id !== updated.id)]);
      }

      // Reset
      setProjectTitle("");
      setSelectedFile(null);
      setYoutubeUrl("");
      setUploadPercent(0);
      setUploadStage("");
    } catch (err: any) {
      alert("Failed to ingest video: " + err.message);
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

  return (
    <div className="min-h-screen bg-[#0B0B10] text-zinc-100 flex flex-col font-sans">
      {/* OmniRoute Settings Modal */}
      <OmniRouteModal
        isOpen={omniModalOpen}
        onClose={() => setOmniModalOpen(false)}
        onConfigSaved={() => setOmniConfig(getOmniRouteConfig())}
      />

      {/* Top Navigation Bar — Opus.pro Edition Header */}
      <header className="border-b border-[#28243C] bg-[#121219]/90 backdrop-blur-md sticky top-0 z-40 px-6 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3.5">
          <div className="w-8 h-8 rounded-lg bg-purple-600/20 border border-purple-500/40 flex items-center justify-center shadow-lg shadow-purple-600/20">
            <Zap className="w-4 h-4 text-purple-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-base tracking-tight text-white flex items-center gap-1.5">
                OPUSFORGE <span className="text-xs font-normal text-purple-400">⚡ Opus.pro Studio</span>
              </span>
              <span className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded-full bg-purple-950/60 text-purple-300 border border-purple-700/40">
                100% Local AI
              </span>
            </div>
          </div>
        </div>

        {/* Header Right Actions */}
        <div className="flex items-center gap-3">
          {/* Universal AI Provider BYOK Button */}
          <button
            onClick={() => setOmniModalOpen(true)}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold border transition shadow-sm ${
              omniConfig.apiKey
                ? "bg-emerald-950/40 text-emerald-300 border-emerald-500/40 hover:bg-emerald-900/40"
                : "bg-purple-950/40 text-purple-300 border-purple-500/40 hover:bg-purple-900/40"
            }`}
            title="Connect Any AI Provider (Gemini, Groq, DeepSeek, OpenAI, OmniRoute, etc.)"
          >
            <span
              className={`w-2 h-2 rounded-full ${
                omniConfig.apiKey ? "bg-emerald-400 animate-pulse" : "bg-purple-400"
              }`}
            />
            <span className="flex items-center gap-1.5">
              <Key className="w-3.5 h-3.5 text-yellow-400" />
              <span>
                {omniConfig.apiKey
                  ? `${omniConfig.provider?.toUpperCase() || "AI"}: Connected`
                  : "Connect Any AI Provider"}
              </span>
            </span>
          </button>

          {/* GPU Telemetry */}
          <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#181824] border border-[#28243C] text-xs">
            <Cpu className="w-3.5 h-3.5 text-purple-400" />
            <span className="font-medium text-zinc-300">
              {systemStatus?.gpu.available ? systemStatus.gpu.name.replace("Laptop GPU", "") : "RTX 4060 GPU"}
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-purple-950/80 text-purple-300 border border-purple-800/40">
              NVENC Active
            </span>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-10 space-y-12">
        {/* Opus.pro Hero Section */}
        <div className="text-center space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-950/50 border border-purple-700/40 text-purple-300 text-xs font-medium mb-1">
            <Sparkles className="w-3.5 h-3.5 text-purple-400" />
            <span>AI Virality Intelligence & Local NVENC Video Pipeline</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-white">
            1 Long Video → <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 via-violet-300 to-indigo-400">10 Viral Shorts in 1 Click</span>
          </h1>
          <p className="text-sm md:text-base text-zinc-400 max-w-2xl mx-auto">
            Automated hook evaluation, face-tracking 9:16 vertical reframe, and dynamic captions. Powered by your connected AI Provider (Gemini, Groq, DeepSeek, OpenAI, OmniRoute).
          </p>
        </div>

        {/* Opus.pro Signature Ingestion Card */}
        <div className="border border-[#28243C] rounded-2xl bg-[#121219] p-6 md:p-8 shadow-2xl shadow-purple-950/30 space-y-6">
          {/* Mode Switcher Tabs */}
          <div className="flex border-b border-zinc-800 pb-3 gap-6">
            <button
              type="button"
              onClick={() => setSourceMode("youtube")}
              className={`flex items-center gap-2 text-sm font-semibold pb-2 border-b-2 transition ${
                sourceMode === "youtube"
                  ? "border-purple-500 text-white"
                  : "border-transparent text-zinc-500 hover:text-zinc-300"
              }`}
            >
              <Youtube className="w-4 h-4 text-red-500" />
              <span>Paste YouTube Link</span>
            </button>
            <button
              type="button"
              onClick={() => setSourceMode("file")}
              className={`flex items-center gap-2 text-sm font-semibold pb-2 border-b-2 transition ${
                sourceMode === "file"
                  ? "border-purple-500 text-white"
                  : "border-transparent text-zinc-500 hover:text-zinc-300"
              }`}
            >
              <UploadCloud className="w-4 h-4 text-purple-400" />
              <span>Upload Local Video File</span>
            </button>
          </div>

          <form onSubmit={handleIngest} className="space-y-6">
            {sourceMode === "youtube" ? (
              <div className="space-y-2">
                <label className="block text-xs font-semibold text-zinc-300 uppercase tracking-wider">
                  YouTube Video / Podcast URL
                </label>
                <div className="flex flex-col sm:flex-row gap-2">
                  <div className="relative flex-1">
                    <Link2 className="absolute left-3.5 top-3.5 w-4 h-4 text-zinc-500" />
                    <input
                      type="url"
                      value={youtubeUrl}
                      onChange={(e) => setYoutubeUrl(e.target.value)}
                      placeholder="https://www.youtube.com/watch?v=... (Drop any long video link)"
                      className="w-full pl-10 pr-4 py-3 rounded-xl bg-[#171722] border border-[#28243C] text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-purple-500 transition font-mono"
                    />
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-2">
                <label className="block text-xs font-semibold text-zinc-300 uppercase tracking-wider">
                  Select or Drag Local Video File
                </label>
                <div
                  onDragOver={(e) => {
                    e.preventDefault();
                    setDragOver(true);
                  }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={handleFileDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition ${
                    dragOver
                      ? "border-purple-500 bg-purple-950/20"
                      : "border-[#28243C] bg-[#171722] hover:border-purple-500/50"
                  }`}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="video/*"
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                  <FileVideo className="w-10 h-10 text-purple-400 mx-auto mb-2 opacity-80" />
                  <p className="text-sm font-semibold text-zinc-200">
                    {selectedFile ? selectedFile.name : "Drag & drop video file here, or click to browse"}
                  </p>
                  <p className="text-xs text-zinc-500 mt-1">
                    MP4, MOV, WebM, MKV up to 4K 60FPS · Stays 100% on your PC
                  </p>
                </div>
              </div>
            )}

            {/* Target Duration Preset Pills */}
            <div className="space-y-2">
              <label className="block text-xs font-semibold text-zinc-300 uppercase tracking-wider">
                Target Clip Duration
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {[
                  { id: "<30", label: "< 30s", desc: "Ultra Viral Hooks" },
                  { id: "30-60", label: "30s – 60s", desc: "Recommended (TikTok/Reels)" },
                  { id: "60-90", label: "60s – 90s", desc: "In-depth Context" },
                  { id: "90-180", label: "90s – 3m", desc: "Long Stories" },
                ].map((pill) => (
                  <button
                    key={pill.id}
                    type="button"
                    onClick={() => handleDurationSelect(pill.id)}
                    className={`p-3 rounded-xl border text-left transition flex flex-col justify-between ${
                      durationPreset === pill.id
                        ? "bg-purple-600/20 border-purple-500 text-white shadow-md shadow-purple-600/10"
                        : "bg-[#171722] border-[#28243C] text-zinc-400 hover:border-zinc-700"
                    }`}
                  >
                    <span className="font-bold text-sm text-zinc-100">{pill.label}</span>
                    <span className="text-[11px] text-zinc-500 mt-0.5">{pill.desc}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Optional Project Title & AI Instructions */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-zinc-300 uppercase tracking-wider mb-1.5">
                  Project Title (Optional)
                </label>
                <input
                  type="text"
                  value={projectTitle}
                  onChange={(e) => setProjectTitle(e.target.value)}
                  placeholder="e.g. Lex Fridman #412 AI Debate"
                  className="w-full px-3.5 py-2.5 rounded-lg bg-[#171722] border border-[#28243C] text-sm text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-purple-500 transition"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-zinc-300 uppercase tracking-wider mb-1.5">
                  AI Clipping Focus
                </label>
                <input
                  type="text"
                  value={instructions}
                  onChange={(e) => setInstructions(e.target.value)}
                  placeholder="e.g. Prioritize high-energy debates with actionable frameworks"
                  className="w-full px-3.5 py-2.5 rounded-lg bg-[#171722] border border-[#28243C] text-sm text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-purple-500 transition"
                />
              </div>
            </div>

            {/* Upload / Ingestion Progress Bar */}
            {uploading && (
              <div className="p-4 rounded-xl bg-purple-950/30 border border-purple-500/30 space-y-2">
                <div className="flex justify-between text-xs font-medium text-purple-300">
                  <span>{uploadStage || "Processing video..."}</span>
                  <span>{uploadPercent > 0 ? `${uploadPercent}%` : "In Progress"}</span>
                </div>
                <div className="w-full h-2 rounded-full bg-zinc-800 overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-purple-500 to-indigo-500 transition-all duration-300"
                    style={{ width: `${Math.max(5, uploadPercent)}%` }}
                  />
                </div>
              </div>
            )}

            {/* Ingestion Submit Button */}
            <button
              type="submit"
              disabled={uploading || (sourceMode === "youtube" ? !youtubeUrl.trim() : !selectedFile)}
              className="w-full py-4 rounded-xl font-bold text-base bg-gradient-to-r from-purple-600 via-indigo-600 to-purple-600 hover:from-purple-500 hover:to-indigo-500 text-white shadow-xl shadow-purple-600/30 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              <Zap className="w-5 h-5 text-yellow-300" />
              <span>{uploading ? "Ingesting & Preparing Video..." : "Get Clips in 1 Click (AI Engine + RTX 4060)"}</span>
            </button>
          </form>
        </div>

        {/* Existing Projects / Opus Gallery Section */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <Film className="w-5 h-5 text-purple-400" />
              <span>Your Repurposed Projects ({projects.length})</span>
            </h2>
            <button
              onClick={loadData}
              className="p-2 rounded-lg bg-[#171722] border border-[#28243C] text-zinc-400 hover:text-white transition"
              title="Refresh projects"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>

          {loading ? (
            <div className="text-center py-12 text-zinc-500 text-sm">Loading studio projects...</div>
          ) : projects.length === 0 ? (
            <div className="border border-[#28243C] rounded-2xl bg-[#121219] p-12 text-center text-zinc-400 space-y-2">
              <Film className="w-10 h-10 text-zinc-600 mx-auto" />
              <p className="font-semibold text-zinc-300">No projects yet</p>
              <p className="text-xs text-zinc-500">
                Paste a YouTube URL or drag a local video into the card above to generate viral shorts!
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {projects.map((proj) => (
                <div
                  key={proj.id}
                  className="group relative border border-[#28243C] hover:border-purple-500/50 rounded-2xl bg-[#121219] overflow-hidden transition shadow-lg hover:shadow-purple-950/20 flex flex-col justify-between"
                >
                  <div>
                    {/* Thumbnail Stage */}
                    <div className="relative aspect-video bg-black/60 overflow-hidden">
                      {proj.status === "ready" ? (
                        <img
                          src={getThumbnailUrl(proj.id)}
                          alt={proj.title}
                          className="w-full h-full object-cover group-hover:scale-105 transition duration-500"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-zinc-600">
                          <Film className="w-8 h-8 opacity-40" />
                        </div>
                      )}

                      {/* Duration Tag */}
                      <div className="absolute bottom-2 right-2 px-2 py-0.5 rounded bg-black/80 text-white text-[11px] font-mono">
                        {formatDuration(proj.duration)}
                      </div>

                      {/* Status Tag */}
                      <div className="absolute top-2 left-2">
                        <span
                          className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full border ${
                            proj.status === "ready"
                              ? "bg-emerald-950/80 text-emerald-300 border-emerald-500/30"
                              : "bg-purple-950/80 text-purple-300 border-purple-500/30 animate-pulse"
                          }`}
                        >
                          {proj.status}
                        </span>
                      </div>
                    </div>

                    {/* Card Meta */}
                    <div className="p-5 space-y-2">
                      <h3 className="font-bold text-base text-zinc-100 group-hover:text-purple-300 transition line-clamp-1">
                        {proj.title}
                      </h3>
                      <p className="text-xs text-zinc-400 line-clamp-2">
                        {proj.instructions || "Standard virality instructions"}
                      </p>
                    </div>
                  </div>

                  {/* Card Actions Footer */}
                  <div className="p-5 pt-0 flex items-center justify-between gap-2 border-t border-zinc-800/60 mt-4">
                    <Link
                      href={`/projects/${proj.id}`}
                      className="flex-1 py-2 rounded-lg bg-purple-600/20 hover:bg-purple-600/30 border border-purple-500/30 text-purple-300 text-xs font-semibold text-center transition flex items-center justify-center gap-1.5"
                    >
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>Open Studio & Clips</span>
                    </Link>

                    <button
                      onClick={() => handleDeleteProject(proj.id)}
                      className="p-2 rounded-lg text-zinc-500 hover:text-red-400 hover:bg-red-950/20 transition"
                      title="Delete project"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

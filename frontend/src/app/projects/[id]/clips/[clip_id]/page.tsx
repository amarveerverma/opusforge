"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Play,
  Pause,
  RotateCcw,
  Sliders,
  Type,
  Crop,
  CheckCircle2,
  RefreshCw,
  Zap,
  Download,
  FolderOpen,
  Sparkles,
  Layers,
  Flame,
  Clock,
  Eye,
  AlertCircle,
} from "lucide-react";
import {
  fetchProject,
  fetchClip,
  updateClip,
  fetchClipFraming,
  updateClipFraming,
  triggerRender,
  fetchClipRender,
  revealRender,
  getVideoStreamUrl,
  getRenderStreamUrl,
  getRenderDownloadUrl,
  Project,
  Clip,
  CropConfig,
  Render,
} from "@/lib/api";

export default function ClipEditorPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params?.id as string;
  const clipId = params?.clip_id as string;

  const [project, setProject] = useState<Project | null>(null);
  const [clip, setClip] = useState<Clip | null>(null);
  const [framing, setFraming] = useState<CropConfig | null>(null);
  const [renderData, setRenderData] = useState<Render | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // Tab State
  const [activeTab, setActiveTab] = useState<"framing" | "captions" | "transcript">("framing");

  // Video playback & trim state
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [startTime, setStartTime] = useState<number>(0);
  const [endTime, setEndTime] = useState<number>(30);
  const [title, setTitle] = useState<string>("");

  // Framing form state
  const [framingMode, setFramingMode] = useState<string>("smart_track");
  const [manualOffset, setManualOffset] = useState<number>(0.5);

  // Captions form state
  const [captionPreset, setCaptionPreset] = useState<string>("mrbeast");
  const [captionFontSize, setCaptionFontSize] = useState<number>(50);
  const [captionColor, setCaptionColor] = useState<string>("#00FF66");

  // Rendering state
  const [isRendering, setIsRendering] = useState<boolean>(false);
  const [renderProgress, setRenderProgress] = useState<string>("");
  const [errorMsg, setErrorMsg] = useState<string>("");

  const loadData = async () => {
    try {
      if (!projectId || !clipId) return;
      const [proj, cl, frm] = await Promise.all([
        fetchProject(projectId),
        fetchClip(clipId),
        fetchClipFraming(clipId).catch(() => null),
      ]);
      setProject(proj);
      setClip(cl);
      setStartTime(cl.start_time);
      setEndTime(cl.end_time);
      setTitle(cl.title);

      if (frm) {
        setFraming(frm);
        setFramingMode(frm.mode || "smart_track");
        if (frm.manual_x_offset !== undefined && frm.manual_x_offset !== null) {
          setManualOffset(frm.manual_x_offset);
        }
      }

      if (cl.caption_config) {
        if (cl.caption_config.preset) setCaptionPreset(cl.caption_config.preset);
        if (cl.caption_config.font_size) setCaptionFontSize(cl.caption_config.font_size);
      }

      // Check for render
      if (cl.rendered) {
        const rnd = await fetchClipRender(clipId).catch(() => null);
        setRenderData(rnd);
      }
    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.message || "Failed to load clip details");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [projectId, clipId]);

  // Video Time Update listener to loop inside [startTime, endTime]
  const handleTimeUpdate = () => {
    if (!videoRef.current) return;
    const t = videoRef.current.currentTime;
    setCurrentTime(t);

    if (t >= endTime) {
      videoRef.current.currentTime = startTime;
      if (!videoRef.current.paused) {
        videoRef.current.play();
      }
    }
  };

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
    } else {
      if (videoRef.current.currentTime < startTime || videoRef.current.currentTime >= endTime) {
        videoRef.current.currentTime = startTime;
      }
      videoRef.current.play();
      setIsPlaying(true);
    }
  };

  const seekToStart = () => {
    if (!videoRef.current) return;
    videoRef.current.currentTime = startTime;
    setCurrentTime(startTime);
  };

  // Save Trim & Title Updates
  const handleSaveTrim = async () => {
    try {
      const updated = await updateClip(clipId, {
        title,
        start_time: Number(startTime),
        end_time: Number(endTime),
      });
      setClip(updated);
      alert("Trim boundaries saved!");
    } catch (err: any) {
      alert(`Save failed: ${err.message}`);
    }
  };

  // Update Framing Mode & Offset
  const handleFramingChange = async (mode: string, offset?: number) => {
    setFramingMode(mode);
    const newOffset = offset !== undefined ? offset : manualOffset;
    if (offset !== undefined) setManualOffset(offset);

    try {
      const updated = await updateClipFraming(clipId, {
        mode,
        manual_x_offset: newOffset,
      });
      setFraming(updated);
    } catch (err: any) {
      console.error("Framing update error:", err);
    }
  };

  // Update Caption Settings
  const handleCaptionPresetChange = async (preset: string) => {
    setCaptionPreset(preset);
    try {
      const updated = await updateClip(clipId, {
        caption_config: {
          preset,
          font_size: captionFontSize,
        },
      });
      setClip(updated);
    } catch (err: any) {
      console.error("Caption update error:", err);
    }
  };

  // Trigger Hardware Render
  const handleTriggerRender = async () => {
    try {
      setIsRendering(true);
      setErrorMsg("");
      setRenderProgress("Encoding 9:16 vertical short with NVIDIA NVENC...");

      const render = await triggerRender(clipId);
      setRenderData(render);
      setClip((prev) => (prev ? { ...prev, rendered: true, render_id: render.id } : prev));
      setRenderProgress("");
      alert("Render complete! 9:16 vertical short is ready to watch and download.");
    } catch (err: any) {
      setErrorMsg(err.message || "Rendering failed");
    } finally {
      setIsRendering(false);
      setRenderProgress("");
    }
  };

  const handleReveal = async () => {
    if (!renderData) return;
    try {
      await revealRender(renderData.id);
    } catch (err: any) {
      alert("Could not open file location");
    }
  };

  const formatSeconds = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    const cs = Math.floor((sec - Math.floor(sec)) * 10);
    return `${m}:${s.toString().padStart(2, "0")}.${cs}`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-400">
        <RefreshCw className="w-8 h-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  if (!project || !clip) {
    return (
      <div className="min-h-screen bg-slate-950 p-8 text-white">
        <p className="text-red-400">Clip not found</p>
        <Link href="/" className="text-indigo-400 mt-4 inline-block">← Back to Dashboard</Link>
      </div>
    );
  }

  // Determine video URL (rendered short vs source video)
  const isViewingRendered = clip.rendered && renderData;
  const activeVideoSrc = isViewingRendered
    ? getRenderStreamUrl(renderData.id)
    : getVideoStreamUrl(project.id);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Top Header */}
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur sticky top-0 z-40 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            href={`/projects/${projectId}`}
            className="p-2 rounded-lg bg-slate-800/80 hover:bg-slate-750 text-slate-400 hover:text-white transition"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div className="flex-1 max-w-xl">
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="bg-transparent border border-transparent hover:border-slate-700 focus:border-indigo-500 focus:bg-slate-900 rounded px-2 py-1 text-base font-bold text-white transition outline-none w-full"
            />
            <p className="text-xs text-slate-400 px-2 flex items-center gap-2">
              <span>Opus Virality: <strong className="text-emerald-400">{clip.letter_grade} ({Math.round(clip.virality_score)}/100)</strong></span>
              <span>·</span>
              <span>Duration: {(endTime - startTime).toFixed(1)}s</span>
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-3">
          {renderData && (
            <button
              onClick={handleReveal}
              className="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-750 border border-slate-700 text-xs font-medium flex items-center gap-1.5 transition text-slate-300"
              title="Reveal in Windows Explorer"
            >
              <FolderOpen className="w-4 h-4 text-amber-400" />
              Reveal
            </button>
          )}

          {renderData && (
            <a
              href={getRenderDownloadUrl(renderData.id)}
              download
              className="px-3 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium flex items-center gap-1.5 transition shadow-lg shadow-emerald-600/20"
            >
              <Download className="w-4 h-4" />
              Download MP4
            </a>
          )}

          <button
            onClick={handleTriggerRender}
            disabled={isRendering}
            className={`px-4 py-2 rounded-lg text-sm font-semibold flex items-center gap-2 transition shadow-lg ${
              isRendering
                ? "bg-indigo-600/50 cursor-not-allowed text-indigo-200"
                : "bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-600/30"
            }`}
          >
            {isRendering ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Rendering NVENC...
              </>
            ) : (
              <>
                <Zap className="w-4 h-4 text-amber-300" />
                {clip.rendered ? "Re-Render Short" : "Render 9:16 Short"}
              </>
            )}
          </button>
        </div>
      </header>

      {/* Main Studio Body */}
      <main className="flex-1 p-6 max-w-7xl mx-auto w-full grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: 9:16 Vertical Video Studio Player */}
        <div className="lg:col-span-5 flex flex-col items-center space-y-4">
          <div className="relative w-[320px] h-[568px] sm:w-[340px] sm:h-[604px] bg-black rounded-3xl overflow-hidden border-2 border-slate-800 shadow-2xl flex items-center justify-center group">
            <video
              ref={videoRef}
              src={activeVideoSrc}
              onTimeUpdate={handleTimeUpdate}
              onEnded={() => setIsPlaying(false)}
              className="w-full h-full object-cover"
              playsInline
            />

            {/* Rendered Badge Indicator */}
            {isViewingRendered && (
              <div className="absolute top-3 left-3 bg-emerald-500/80 backdrop-blur px-2.5 py-1 rounded-full text-[10px] font-bold text-white flex items-center gap-1 shadow">
                <CheckCircle2 className="w-3 h-3" />
                Rendered 9:16 NVENC
              </div>
            )}

            {/* Play / Pause Overlay Button */}
            <button
              onClick={togglePlay}
              className="absolute inset-0 m-auto w-16 h-16 rounded-full bg-black/50 hover:bg-black/70 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity backdrop-blur-sm"
            >
              {isPlaying ? <Pause className="w-8 h-8" /> : <Play className="w-8 h-8 ml-1" />}
            </button>

            {/* Caption Preview Overlay (Simulated when watching source video) */}
            {!isViewingRendered && (
              <div
                className={`absolute bottom-16 inset-x-4 text-center pointer-events-none ${
                  captionPreset === "hormozi"
                    ? "font-black tracking-tight"
                    : captionPreset === "mrbeast"
                    ? "font-extrabold uppercase"
                    : "font-medium"
                }`}
              >
                <span
                  style={{ fontSize: `${Math.round(captionFontSize * 0.4)}px` }}
                  className="bg-black/80 px-3 py-1.5 rounded-lg text-white font-bold drop-shadow-[0_4px_4px_rgba(0,0,0,1)] border border-slate-800"
                >
                  <span className="text-emerald-400">LIVE PREVIEW:</span> {clip.title}
                </span>
              </div>
            )}
          </div>

          {/* Timeline Playback Controls */}
          <div className="w-[340px] bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-3">
            <div className="flex items-center justify-between text-xs font-mono text-slate-400">
              <span>{formatSeconds(currentTime)}</span>
              <div className="flex items-center gap-2">
                <button
                  onClick={seekToStart}
                  className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-white"
                  title="Return to start"
                >
                  <RotateCcw className="w-4 h-4" />
                </button>
                <button
                  onClick={togglePlay}
                  className="p-1 rounded bg-indigo-600 hover:bg-indigo-500 text-white"
                >
                  {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                </button>
              </div>
              <span>{formatSeconds(endTime)}</span>
            </div>

            {/* Scrub Slider */}
            <input
              type="range"
              min={startTime}
              max={endTime}
              step={0.1}
              value={currentTime}
              onChange={(e) => {
                const val = parseFloat(e.target.value);
                if (videoRef.current) {
                  videoRef.current.currentTime = val;
                }
                setCurrentTime(val);
              }}
              className="w-full accent-indigo-500 cursor-pointer"
            />

            {/* Trim Boundaries */}
            <div className="pt-2 border-t border-slate-800 grid grid-cols-2 gap-3 text-xs">
              <div>
                <label className="text-slate-400 block mb-1">Start Trim (s)</label>
                <input
                  type="number"
                  step={0.1}
                  value={startTime}
                  onChange={(e) => setStartTime(parseFloat(e.target.value) || 0)}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 font-mono text-white text-xs"
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-1">End Trim (s)</label>
                <input
                  type="number"
                  step={0.1}
                  value={endTime}
                  onChange={(e) => setEndTime(parseFloat(e.target.value) || 0)}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 font-mono text-white text-xs"
                />
              </div>
            </div>

            <button
              onClick={handleSaveTrim}
              className="w-full py-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 border border-slate-700 text-xs font-semibold text-slate-200 transition"
            >
              Save Trim Boundaries
            </button>
          </div>
        </div>

        {/* Right Column: Studio Settings Tabs */}
        <div className="lg:col-span-7 bg-slate-900/60 border border-slate-800 rounded-3xl p-6 space-y-6">
          {/* Tab Selector */}
          <div className="flex items-center gap-2 border-b border-slate-800 pb-4">
            <button
              onClick={() => setActiveTab("framing")}
              className={`px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 transition ${
                activeTab === "framing"
                  ? "bg-indigo-600 text-white"
                  : "bg-slate-800/60 text-slate-400 hover:text-white"
              }`}
            >
              <Crop className="w-4 h-4" />
              9:16 Framing
            </button>

            <button
              onClick={() => setActiveTab("captions")}
              className={`px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 transition ${
                activeTab === "captions"
                  ? "bg-indigo-600 text-white"
                  : "bg-slate-800/60 text-slate-400 hover:text-white"
              }`}
            >
              <Type className="w-4 h-4" />
              Captions & Presets
            </button>

            <button
              onClick={() => setActiveTab("transcript")}
              className={`px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 transition ${
                activeTab === "transcript"
                  ? "bg-indigo-600 text-white"
                  : "bg-slate-800/60 text-slate-400 hover:text-white"
              }`}
            >
              <Sliders className="w-4 h-4" />
              Virality & Rationale
            </button>
          </div>

          {/* TAB 1: 9:16 FRAMING */}
          {activeTab === "framing" && (
            <div className="space-y-6">
              <div>
                <h3 className="text-sm font-bold text-white">Framing & Subject Tracking Mode</h3>
                <p className="text-xs text-slate-400 mt-1">
                  Choose how ClipForge reframes widescreen landscape footage into 9:16 vertical shorts.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {[
                  {
                    id: "smart_track",
                    name: "Smart Face Tracking",
                    desc: "MediaPipe facial trajectory tracking with smooth EMA deadband pan.",
                  },
                  {
                    id: "blur_background",
                    name: "Blurred Background",
                    desc: "Centers video with blurred, scaled video background (great for tutorials).",
                  },
                  {
                    id: "split_screen",
                    name: "Split Screen",
                    desc: "Dual speakers (Top 1080x960 & Bottom 1080x960 stacked vertically).",
                  },
                  {
                    id: "center",
                    name: "Centered Crop",
                    desc: "Static centered 9:16 portrait crop.",
                  },
                  {
                    id: "manual",
                    name: "Manual Offset",
                    desc: "Manually adjust the horizontal focal position with slider below.",
                  },
                ].map((mode) => (
                  <button
                    key={mode.id}
                    onClick={() => handleFramingChange(mode.id)}
                    className={`p-4 rounded-xl border text-left transition ${
                      framingMode === mode.id
                        ? "bg-indigo-950/40 border-indigo-500/80 shadow-md shadow-indigo-500/10"
                        : "bg-slate-950/40 border-slate-800 hover:border-slate-700"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-white">{mode.name}</span>
                      {framingMode === mode.id && (
                        <CheckCircle2 className="w-4 h-4 text-indigo-400" />
                      )}
                    </div>
                    <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">{mode.desc}</p>
                  </button>
                ))}
              </div>

              {/* Manual Horizontal Offset Slider */}
              {framingMode === "manual" && (
                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-300 font-medium">Horizontal Focal Center</span>
                    <span className="text-indigo-400 font-mono">{(manualOffset * 100).toFixed(0)}%</span>
                  </div>
                  <input
                    type="range"
                    min={0.0}
                    max={1.0}
                    step={0.01}
                    value={manualOffset}
                    onChange={(e) => handleFramingChange("manual", parseFloat(e.target.value))}
                    className="w-full accent-indigo-500 cursor-pointer"
                  />
                  <div className="flex justify-between text-[10px] text-slate-500">
                    <span>Left (0%)</span>
                    <span>Center (50%)</span>
                    <span>Right (100%)</span>
                  </div>
                </div>
              )}

              {/* Technical Framing Readout */}
              <div className="p-4 rounded-xl bg-slate-950/40 border border-slate-800 space-y-2 text-xs">
                <span className="text-slate-400 font-semibold uppercase tracking-wider text-[10px]">
                  Output Specifications
                </span>
                <div className="grid grid-cols-2 gap-2 text-slate-300 font-mono text-[11px]">
                  <div>Target: 1080x1920 (9:16)</div>
                  <div>Crop Window: {framing?.crop_w || 608}x{framing?.crop_h || 1080}</div>
                  <div>Encoder: NVIDIA NVENC (p5, cq20)</div>
                  <div>Status: {framing?.fallback_applied ? "Fallback Applied" : "Optimal Track"}</div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: CAPTIONS */}
          {activeTab === "captions" && (
            <div className="space-y-6">
              <div>
                <h3 className="text-sm font-bold text-white">Subtitle Style & Presets</h3>
                <p className="text-xs text-slate-400 mt-1">
                  Burn high-retention karaoke word-level animations synchronized with WhisperX.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {[
                  {
                    id: "mrbeast",
                    name: "MrBeast",
                    font: "Arial Black",
                    desc: "Electric yellow highlight, bold uppercase, high-contrast black border.",
                    badge: "HIGH VIRALITY",
                  },
                  {
                    id: "hormozi",
                    name: "Hormozi",
                    font: "Impact",
                    desc: "Neon red highlight, punchy 3-word bursts, maximum impact.",
                    badge: "RETENTION",
                  },
                  {
                    id: "minimalist",
                    name: "Minimalist",
                    font: "Arial Clean",
                    desc: "Clean sky blue highlight, soft shadow, elegant documentary look.",
                    badge: "ELEGANT",
                  },
                ].map((preset) => (
                  <button
                    key={preset.id}
                    onClick={() => handleCaptionPresetChange(preset.id)}
                    className={`p-4 rounded-xl border text-left transition ${
                      captionPreset === preset.id
                        ? "bg-indigo-950/40 border-indigo-500/80 shadow-md shadow-indigo-500/10"
                        : "bg-slate-950/40 border-slate-800 hover:border-slate-700"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-bold text-white">{preset.name}</span>
                      <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300">
                        {preset.badge}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed">{preset.desc}</p>
                  </button>
                ))}
              </div>

              <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-4">
                <div>
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-slate-300 font-medium">Font Size</span>
                    <span className="text-indigo-400 font-mono">{captionFontSize} pt</span>
                  </div>
                  <input
                    type="range"
                    min={36}
                    max={64}
                    value={captionFontSize}
                    onChange={(e) => setCaptionFontSize(parseInt(e.target.value))}
                    className="w-full accent-indigo-500 cursor-pointer"
                  />
                </div>

                <div className="text-xs text-slate-400">
                  <p>Safe margins: Automatically elevated 240px from bottom to clear mobile overlays.</p>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: TRANSCRIPT & VIRALITY */}
          {activeTab === "transcript" && (
            <div className="space-y-6">
              <div>
                <h3 className="text-sm font-bold text-white">Opus Virality Breakdown</h3>
                <p className="text-xs text-slate-400 mt-1">
                  Why this narrative moment was chosen from the full video.
                </p>
              </div>

              <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-3">
                <span className="text-xs font-bold text-white flex items-center gap-1.5">
                  <Flame className="w-4 h-4 text-amber-400" />
                  Hook Excerpt
                </span>
                <p className="text-xs text-amber-200/90 italic bg-slate-900 p-3 rounded-lg border border-slate-800">
                  "{clip.hook || clip.transcript_excerpt}"
                </p>
              </div>

              {clip.score_breakdown && (
                <div className="space-y-2">
                  <h4 className="text-xs font-bold text-slate-300">7-Factor Virality Dials</h4>
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    {Object.entries(clip.score_breakdown).map(([key, val]) => (
                      <div key={key} className="bg-slate-950/40 p-2.5 rounded-lg border border-slate-800">
                        <span className="text-slate-400 capitalize block text-[11px]">
                          {key.replace("_", " ")}
                        </span>
                        <span className="text-sm font-bold text-indigo-400 font-mono">
                          {Math.round(val as number)}/100
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

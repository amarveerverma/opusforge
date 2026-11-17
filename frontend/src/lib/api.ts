/**
 * ClipForge Unified Frontend API Client
 */

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export interface GpuStatus {
  name: string;
  available: boolean;
  vram_total_mb: number;
  vram_used_mb: number;
  vram_free_mb: number;
  utilization_percent: number;
  temperature_c: number;
}

export interface RamStatus {
  total_gb: number;
  available_gb: number;
  used_gb: number;
  percent: number;
}

export interface DiskStatus {
  total_gb: number;
  used_gb: number;
  free_gb: number;
  percent_free: number;
}

export interface SystemStatus {
  status: string;
  gpu: GpuStatus;
  ram: RamStatus;
  disk: DiskStatus;
  encoders: string[];
}

export interface Project {
  id: string;
  title: string;
  original_filename: string;
  source_file_path: string;
  duration: number;
  width: number;
  height: number;
  fps: number;
  codec?: string;
  instructions?: string;
  status: string;
  created_at: string;
  updated_at: string;
  clips_count: number;
}

export interface ScoreBreakdown {
  hook_strength: number;
  narrative_flow: number;
  standalone_context: number;
  educational_value: number;
  emotional_impact: number;
  ending_quality: number;
  visual_potential: number;
}

export interface CropConfig {
  mode: string;
  source_width?: number;
  source_height?: number;
  target_width?: number;
  target_height?: number;
  crop_w?: number;
  crop_h?: number;
  crop_x?: number;
  crop_y?: number;
  manual_x_offset?: number;
  has_face?: boolean;
  face_confidence?: number;
  fallback_applied?: boolean;
  fallback_reason?: string;
  ffmpeg_video_filter?: string;
}

export interface CaptionConfig {
  preset?: string;
  font_size?: number;
  highlight_color?: string;
  outline_width?: number;
  uppercase?: boolean;
  margin_v?: number;
}

export interface Clip {
  id: string;
  project_id: string;
  rank: number;
  start_time: number;
  end_time: number;
  duration: number;
  title: string;
  hook?: string;
  summary?: string;
  virality_score: number;
  letter_grade: string;
  score_breakdown?: ScoreBreakdown;
  transcript_excerpt?: string;
  crop_config?: CropConfig;
  caption_config?: CaptionConfig;
  status: string;
  created_at: string;
  rendered?: boolean;
  render_id?: string;
}

export interface Render {
  id: string;
  clip_id: string;
  project_id: string;
  output_file_path: string;
  width: number;
  height: number;
  fps: number;
  duration: number;
  file_size_bytes: number;
  encoder_used: string;
  quality_report?: Record<string, any>;
  created_at: string;
}

export async function fetchHealth(): Promise<{ status: string; app: string; version: string }> {
  const res = await fetch(`${API_BASE}/health`, { cache: "no-store" });
  if (!res.ok) throw new Error("Backend offline");
  return res.json();
}

export async function fetchSystemStatus(): Promise<SystemStatus> {
  const res = await fetch(`${API_BASE}/system/status`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch system telemetry");
  return res.json();
}

export async function fetchProjects(): Promise<Project[]> {
  const res = await fetch(`${API_BASE}/projects`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch projects");
  const data = await res.json();
  return data.projects || [];
}

export async function fetchProject(id: string): Promise<Project> {
  const res = await fetch(`${API_BASE}/projects/${id}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Project not found");
  return res.json();
}

export async function createProject(title: string, instructions?: string): Promise<Project> {
  const res = await fetch(`${API_BASE}/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, instructions }),
  });
  if (!res.ok) throw new Error("Failed to create project");
  return res.json();
}

export async function deleteProject(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/projects/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete project");
}

export function uploadVideoWithProgress(
  projectId: string,
  file: File,
  onProgress?: (percent: number) => void
): Promise<Project> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append("file", file);

    xhr.open("POST", `${API_BASE}/projects/${projectId}/upload`, true);

    if (xhr.upload && onProgress) {
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          const percent = Math.round((event.loaded / event.total) * 100);
          onProgress(percent);
        }
      };
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const data = JSON.parse(xhr.responseText);
          resolve(data);
        } catch (e) {
          reject(new Error("Invalid response format from server"));
        }
      } else {
        try {
          const err = JSON.parse(xhr.responseText);
          reject(new Error(err.detail || "Video upload failed"));
        } catch {
          reject(new Error(`Upload failed with HTTP ${xhr.status}`));
        }
      }
    };

    xhr.onerror = () => reject(new Error("Network connection error during upload"));
    xhr.send(formData);
  });
}

export async function runTranscription(projectId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/transcript`, {
    method: "POST",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Transcription failed");
  }
  return res.json();
}

export async function runAnalysis(projectId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/analysis`, {
    method: "POST",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Analysis failed");
  }
  return res.json();
}

export async function discoverClips(projectId: string): Promise<Clip[]> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/discover`, {
    method: "POST",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Clip discovery failed");
  }
  return res.json();
}

export async function fetchProjectClips(projectId: string): Promise<Clip[]> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/clips`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to load clips");
  return res.json();
}

export async function fetchClip(clipId: string): Promise<Clip> {
  const res = await fetch(`${API_BASE}/clips/${clipId}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Clip not found");
  return res.json();
}

export async function updateClip(clipId: string, payload: Partial<Clip>): Promise<Clip> {
  const res = await fetch(`${API_BASE}/clips/${clipId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to update clip");
  return res.json();
}

export async function fetchClipFraming(clipId: string): Promise<CropConfig> {
  const res = await fetch(`${API_BASE}/clips/${clipId}/framing`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch clip framing");
  return res.json();
}

export async function updateClipFraming(
  clipId: string,
  payload: { mode?: string; manual_x_offset?: number }
): Promise<CropConfig> {
  const res = await fetch(`${API_BASE}/clips/${clipId}/framing`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to update framing");
  return res.json();
}

export async function triggerRender(clipId: string): Promise<Render> {
  const res = await fetch(`${API_BASE}/clips/${clipId}/render`, {
    method: "POST",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Render failed");
  }
  return res.json();
}

export async function fetchClipRender(clipId: string): Promise<Render> {
  const res = await fetch(`${API_BASE}/clips/${clipId}/render`, { cache: "no-store" });
  if (!res.ok) throw new Error("Render not found");
  return res.json();
}

export async function fetchProjectRenders(projectId: string): Promise<Render[]> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/renders`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch renders");
  return res.json();
}

export async function revealRender(renderId: string): Promise<void> {
  await fetch(`${API_BASE}/renders/${renderId}/reveal`, { method: "POST" });
}

export function getThumbnailUrl(projectId: string): string {
  return `${API_BASE}/projects/${projectId}/thumbnail`;
}

export function getVideoStreamUrl(projectId: string): string {
  return `${API_BASE}/projects/${projectId}/stream`;
}

export function getRenderStreamUrl(renderId: string): string {
  return `${API_BASE}/renders/${renderId}/stream`;
}

export function getRenderDownloadUrl(renderId: string): string {
  return `${API_BASE}/renders/${renderId}/download`;
}

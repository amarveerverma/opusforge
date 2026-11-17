/**
 * ClipForge API Client
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

export function getThumbnailUrl(projectId: string): string {
  return `${API_BASE}/projects/${projectId}/thumbnail`;
}

export function getVideoStreamUrl(projectId: string): string {
  return `${API_BASE}/projects/${projectId}/stream`;
}

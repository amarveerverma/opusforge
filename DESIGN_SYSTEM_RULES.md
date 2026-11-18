# ClipForge — Design System Rules & Figma Integration Guide

> Generated via `/mcp:figma_figma:create_design_system_rules`
> Design Philosophy: **Gemini Carbon** — Human-Crafted, High-Density Video Repurposing Studio

---

## 1. Design System Structure & Philosophy

ClipForge rejects generic "AI SaaS" templates (e.g. oversaturated neon violet blobs, oversized cartoon cards, and empty whitespace). Instead, it adopts the **Gemini Carbon** design system:
- **Human Craftsmanship**: Precision information density, micro-contrast borders (`rgba(255, 255, 255, 0.08)`), surgical status accents, and tactile desktop ergonomics inspired by professional video editing suites (DaVinci Resolve, Linear, Apple Pro Apps).
- **Deep Obsidian Surfaces**: Layered carbon shades (`#0A0B0D`, `#111317`, `#16191F`, `#1E222A`) providing rich contrast for 1080p and 4K video previews.
- **Micro-Interactions**: Subtle inset border highlights, crisp monospace timecodes (`00:00:00.000`), tactile pill toggles, and safe-zone framing overlays (TikTok / Instagram Reels preview grids).

---

## 2. Token Definitions

### Colors (Gemini Carbon Palette)

Tokens are defined in `frontend/tailwind.config.js` and referenced via Tailwind CSS utility classes and CSS variables in `frontend/src/app/globals.css`.

| Token Name | Hex / Value | Semantic Role |
| :--- | :--- | :--- |
| `carbon-bg` | `#0A0B0D` | Canvas background, letterbox matting |
| `carbon-card` | `#111317` | Base container, modal backdrops, sidebar panels |
| `carbon-surface` | `#16191F` | Segmented controls, list items, input fields |
| `carbon-elevated` | `#1E222A` | Hover states, popovers, active selection |
| `carbon-border` | `rgba(255, 255, 255, 0.08)` | Subtle 1px structural dividing lines |
| `carbon-border-strong` | `rgba(255, 255, 255, 0.16)` | Active borders, focused inputs, hovered cards |
| `carbon-accent` | `#38BDF8` | Primary CTA, playhead timeline, active tabs (Gemini Sky) |
| `carbon-emerald` | `#10B981` | GPU online, NVENC hardware active, rendered clips |
| `carbon-amber` | `#F59E0B` | Virality scores (80-89 B+ tier), warning badges |
| `carbon-rose` | `#F43F5E` | Delete actions, pipeline failure, error alerts |
| `text-primary` | `#F8FAFC` | Main headings, clip titles, primary values |
| `text-secondary` | `#94A3B8` | Body text, transcript excerpts, metadata labels |
| `text-muted` | `#64748B` | Timestamps, micro-badges, keyboard shortcuts |

### Typography & Spacing Scale
- **Font Stack**: Inter (`sans`), with `ui-monospace`, `SFMono-Regular`, `Menlo` for timestamps, frame counters, and score breakdowns.
- **Type Scale**:
  - `text-xs` (11px / 12px): Micro badges, telemetry pills, timecode stamps.
  - `text-sm` (13px / 14px): Standard UI labels, transcript text, table headers.
  - `text-base` (15px / 16px): Primary content titles, button labels.
  - `text-lg` (18px): Section headings, modal titles.
  - `text-xl` to `text-2xl` (20px - 24px): Project titles, primary studio headers.
- **Border Radius**:
  - `rounded-md` (6px): Inputs, buttons, segmented pills, micro-badges.
  - `rounded-lg` (8px): Clip cards, video player frame, modal windows.
  - `rounded-xl` (12px): Elevated sheets, dialog containers.

---

## 3. Component Library Architecture

UI components reside in `frontend/src/components/` and are composed into route views inside `frontend/src/app/`.

### Directory Layout
```
frontend/src/
├── app/
│   ├── layout.tsx                  # Root HTML wrapper, carbon fonts, metadata
│   ├── globals.css                 # Carbon CSS variables, custom scrollbars
│   ├── page.tsx                    # Studio Dashboard (Projects, GPU Telemetry, Import Modal)
│   └── projects/
│       └── [id]/
│           ├── page.tsx            # Project Overview & AI Candidate Shorts Gallery
│           ├── clips/
│           │   └── [clip_id]/
│           │       └── page.tsx    # 9:16 Interactive Framing Studio & Subtitle Editor
│           └── exports/
│               └── page.tsx        # Rendered Exports Library & Media Downloader
├── components/
│   ├── Header.tsx                  # Top navigation, hardware telemetry status pills
│   ├── TelemetryBar.tsx            # Live RTX 4060 VRAM, RAM, and Disk monitors
│   ├── CreateProjectModal.tsx      # Dual-tab (Local File Upload & YouTube URL Ingest)
│   ├── ClipCard.tsx                # Virality score card with 7-factor explainability
│   ├── VideoPlayer.tsx             # HTML5 player with 9:16 safe-zone framing overlay
│   └── SubtitleConfigurator.tsx    # Dynamic ASS subtitle style previewer
└── lib/
    ├── api.ts                      # Typed client SDK communicating with FastAPI backend
    └── utils.ts                    # Timecode formatting, grade color mappings, cn()
```

### Component Best Practices
- Every component is declared with `'use client'` where interactive state (audio/video, canvas, drag/drop) is needed.
- CSS classes use `tailwind-merge` (`cn(...)`) to allow seamless prop overriding.
- Structural elements use CSS Grid and Flexbox with explicit gap sizing (`gap-3`, `gap-4`, `gap-6`).

---

## 4. Frameworks & Libraries

- **Framework**: Next.js 14.2 (App Router with TypeScript).
- **UI Engine**: React 18.3.
- **Styling**: Tailwind CSS 3.4 + PostCSS with Autoprefixer.
- **Icons**: Lucide React 0.475 (`lucide-react`).
- **Backend API**: Python 3.11 / FastAPI (Uvicorn on `http://127.0.0.1:8000`).
- **Database**: SQLite 3 with Write-Ahead Logging (WAL mode enabled) at `data/database/clipforge.db`.

---

## 5. Asset Management

- **User Video Files**: Stored locally in `data/projects/{project_id}/source/`.
- **Extracted Audio & Transcripts**: `data/projects/{project_id}/transcripts/`.
- **Analysis JSON Artifacts**: `data/projects/{project_id}/analysis/` (`scenes.json`, `diarization.json`, `face_tracks.json`).
- **Thumbnails & Posters**: `data/projects/{project_id}/thumbnails/`, served directly via FastAPI static file mount `/static/`.
- **Rendered 9:16 Shorts**: `data/projects/{project_id}/renders/`, streamed via HTTP 206 partial content streaming.
- **Zero Cloud Leakage**: No external CDN dependencies; all fonts, media, and styles are bundled locally.

---

## 6. Icon System

Icons are imported exclusively from `lucide-react` using uniform styling rules:
- **Default Stroke**: `strokeWidth={1.75}` (refined, human hairline look, avoiding thick cartoon strokes).
- **Micro Icons**: `w-3.5 h-3.5` (timecodes, badges, inline metrics).
- **Action Icons**: `w-4 h-4` (buttons, dropdown chevrons, tabs).
- **Navigation / Brand Icons**: `w-5 h-5` (header logos, sidebar shortcuts).

```tsx
import { Play, Scissors, Sparkles, Youtube, UploadCloud, Cpu, HardDrive } from "lucide-react";

// Example pattern:
<button className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-carbon-surface hover:bg-carbon-elevated border border-carbon-border text-xs font-medium text-text-primary transition">
  <Sparkles className="w-3.5 h-3.5 text-carbon-accent" strokeWidth={1.75} />
  <span>Run AI Discovery</span>
</button>
```

---

## 7. Styling Approach & Code Patterns

### CSS Micro-Contrast & Tactile Depth Pattern
```css
/* Inset subtle highlight for carbon surfaces */
.carbon-panel {
  background-color: #111317;
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04), 0 4px 20px rgba(0, 0, 0, 0.4);
}
```

### Monospace Timecode Formatting
```typescript
export function formatTimecode(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  const ms = Math.floor((seconds % 1) * 100);
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}.${ms.toString().padStart(2, "0")}`;
}
```

---

## 8. Model Context Protocol (MCP) Figma Integration Rules

When synchronizing or generating screens in Figma via `figma_figma`:
1. **Target Team**: Use the designated user workspace plan (`Amarveer Verma kh's team` or `dreamx`).
2. **Color Mapping**: Bind design tokens to the Gemini Carbon palette (`#0A0B0D`, `#111317`, `#16191F`, `#38BDF8`).
3. **Typography**: Load `Inter` or `Roboto` font styles (`figma.loadFontAsync`) before applying text strings.
4. **Auto-Layout**: All containers MUST use Auto-Layout (`figma.createAutoLayout()`) with explicit horizontal/vertical padding and gaps (`gap: 12`, `padding: 16`).
5. **Editable Primitives**: Never flatten UI into image fills; all buttons, score badges, timelines, and cards must remain semantic, editable component layers.

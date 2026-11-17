"""
ClipForge Dynamic Animated Subtitle Engine
Generates pixel-perfect Advanced SubStation Alpha (.ass) subtitles with
word-level karaoke animations, safe margins for TikTok/Reels/Shorts,
and customizable viral aesthetic presets (MrBeast, Hormozi, Minimalist).
"""
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("clipforge.subtitles")

class SubtitlePreset(BaseModel):
    name: str
    font_name: str
    font_size: int = 48
    primary_color: str = "&H00FFFFFF"      # Crisp White
    highlight_color: str = "&H0000FF66"    # Vibrant Neon Lime / Yellow
    outline_color: str = "&H00000000"      # Opaque Black
    shadow_color: str = "&H80000000"       # 50% Alpha Black
    bold: int = 1
    outline_width: int = 5
    shadow_depth: int = 2
    alignment: int = 2                     # Bottom-Center
    margin_v: int = 240                    # Vertical safe margin from bottom
    uppercase: bool = True
    words_per_group: int = 4

PRESETS: Dict[str, SubtitlePreset] = {
    "mrbeast": SubtitlePreset(
        name="mrbeast",
        font_name="Arial Black",
        font_size=50,
        primary_color="&H00FFFFFF",
        highlight_color="&H0000D4FF",      # Electric Gold / Yellow
        outline_color="&H00000000",
        shadow_color="&H00000000",
        bold=1,
        outline_width=6,
        shadow_depth=3,
        alignment=2,
        margin_v=240,
        uppercase=True,
        words_per_group=4,
    ),
    "hormozi": SubtitlePreset(
        name="hormozi",
        font_name="Impact",
        font_size=54,
        primary_color="&H00FFFFFF",
        highlight_color="&H000033FF",      # High-intensity Neon Red
        outline_color="&H00000000",
        shadow_color="&H00000000",
        bold=1,
        outline_width=6,
        shadow_depth=3,
        alignment=2,
        margin_v=260,
        uppercase=True,
        words_per_group=3,
    ),
    "minimalist": SubtitlePreset(
        name="minimalist",
        font_name="Arial",
        font_size=42,
        primary_color="&H00FFFFFF",
        highlight_color="&H00FFCC00",      # Cyan
        outline_color="&H40000000",
        shadow_color="&H60000000",
        bold=1,
        outline_width=2,
        shadow_depth=1,
        alignment=2,
        margin_v=220,
        uppercase=False,
        words_per_group=5,
    ),
}

def format_ass_timestamp(seconds: float) -> str:
    """Formats float seconds into ASS timestamp: H:MM:SS.cs"""
    seconds = max(0.0, float(seconds))
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def generate_ass_file(
    words: List[Dict[str, Any]],
    clip_start: float,
    clip_end: float,
    output_path: Path,
    preset_name: str = "mrbeast",
    custom_config: Optional[Dict[str, Any]] = None,
) -> Path:
    """
    Generates a synchronized ASS subtitle file with animated word-level highlights.
    Words are normalized to clip_start (0.00s).
    """
    preset = PRESETS.get(preset_name.lower(), PRESETS["mrbeast"]).model_copy(deep=True)
    if custom_config:
        for k, v in custom_config.items():
            if hasattr(preset, k) and v is not None:
                setattr(preset, k, v)
                
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 1. Filter and normalize words to clip range [0.0, clip_duration]
    rel_words: List[Dict[str, Any]] = []
    for w in words:
        w_start = float(w.get("start", 0.0))
        w_end = float(w.get("end", 0.0))
        word_text = str(w.get("word", "")).strip()
        
        # Word must intersect clip boundaries
        if w_end > clip_start and w_start < clip_end and word_text:
            rel_s = max(0.0, round(w_start - clip_start, 2))
            rel_e = max(rel_s + 0.08, round(min(clip_end, w_end) - clip_start, 2))
            disp_word = word_text.upper() if preset.uppercase else word_text
            rel_words.append({
                "word": disp_word,
                "start": rel_s,
                "end": rel_e,
            })
            
    # 2. Chunk words into small punchy groups (e.g. 3 to 5 words)
    groups: List[List[Dict[str, Any]]] = []
    current_group: List[Dict[str, Any]] = []
    
    for w in rel_words:
        current_group.append(w)
        # End group if target size reached or sentence boundary punctuation
        if len(current_group) >= preset.words_per_group or any(p in w["word"] for p in [".", "!", "?", ","]):
            groups.append(current_group)
            current_group = []
            
    if current_group:
        groups.append(current_group)
        
    # 3. Generate ASS Header
    ass_lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,{preset.font_name},{preset.font_size},{preset.primary_color},&H000000FF,{preset.outline_color},{preset.shadow_color},{preset.bold},0,0,0,100,100,0,0,1,{preset.outline_width},{preset.shadow_depth},{preset.alignment},40,40,{preset.margin_v},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    
    # 4. Generate Animated Word Highlights
    for grp in groups:
        if not grp:
            continue
            
        grp_start = grp[0]["start"]
        grp_end = grp[-1]["end"]
        
        for active_idx, active_word in enumerate(grp):
            w_start_str = format_ass_timestamp(active_word["start"])
            # The active word highlighting stays until next word starts (or group ends)
            if active_idx + 1 < len(grp):
                next_start = grp[active_idx + 1]["start"]
                w_end_time = max(active_word["end"], next_start)
            else:
                w_end_time = active_word["end"]
            w_end_str = format_ass_timestamp(w_end_time)
            
            # Construct text with active word highlighted
            formatted_words = []
            for i, w in enumerate(grp):
                txt = w["word"]
                if i == active_idx:
                    formatted_words.append(f"{{\\c{preset.highlight_color}&}}{txt}{{\\c{preset.primary_color}&}}")
                else:
                    formatted_words.append(txt)
                    
            dialogue_text = " ".join(formatted_words)
            ass_lines.append(
                f"Dialogue: 0,{w_start_str},{w_end_str},Default,,0,0,0,,{dialogue_text}"
            )
            
    content = "\n".join(ass_lines) + "\n"
    output_path.write_text(content, encoding="utf-8")
    logger.info("Generated ASS subtitle file: %s (%d dialogue lines)", output_path.name, len(ass_lines) - 13)
    return output_path

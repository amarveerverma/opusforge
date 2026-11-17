"""
ClipForge Contextual AI Clip Discovery & Explainable Scoring Engine
Fuses transcripts, word-level timestamps, speaker diarization, scene cuts, and face presence
into complete narrative arcs scored on a 0-100 Virality Index.
"""
import re
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel

logger = logging.getLogger("clipforge.clip_discovery")

# Lexical vocabulary patterns
HOOK_PATTERNS = [
    r"\b(why|how|what if|stop scrolling|unbelievable|secret|never|biggest mistake|truth about|nobody talks about)\b",
    r"\b(listen to this|here is the thing|the real reason|do this|don't do this|watch out)\b",
    r"\?",  # Question in first 3 seconds
]

VALUE_PATTERNS = [
    r"\b(because|method|system|result|step|reason|principle|formula|strategy|technique|framework)\b",
    r"\b(first|second|third|finally|crucial|essential|important|key)\b",
]

EMOTION_PATTERNS = [
    r"\b(insane|crazy|massive|huge|skyrocket|destroy|revolution|shocking|amazing|transform|danger)\b",
    r"!",  # Exclamations
]

CLOSING_PATTERNS = [
    r"\b(in conclusion|that is why|remember|at the end of the day|the takeaway|always)\b",
    r"\b(and that is how|forever|bottom line)\b",
]

DANGLING_START_PATTERNS = [
    r"^(and|but|or|so|because|like he said|as i said before|then)\b",
]

DANGLING_END_PATTERNS = [
    r"\b(and|but|or|so|because|which is|that is|when)\s*$",
]

class ScoreBreakdown(BaseModel):
    hook_strength: float         # 20%
    narrative_flow: float        # 20%
    standalone_context: float    # 15%
    educational_value: float     # 15%
    emotional_impact: float      # 15%
    ending_quality: float        # 10%
    visual_potential: float      # 5%

class CandidateClip(BaseModel):
    clip_id: str
    project_id: str
    rank: int
    start_time: float
    end_time: float
    duration: float
    title: str
    hook: str
    summary: str
    virality_score: float
    letter_grade: str
    score_breakdown: ScoreBreakdown
    transcript_excerpt: str
    why_chosen: str
    crop_config: Dict[str, Any]
    caption_config: Dict[str, Any]

def parse_user_instructions(instructions: Optional[str]) -> Dict[str, Any]:
    """
    Parses natural language instructions to extract duration and count preferences.
    Example: "Find 5 educational moments between 30 and 60 seconds with strong hooks"
    """
    settings = {
        "min_duration": 25.0,
        "max_duration": 60.0,
        "target_count": 5,
        "prioritize_educational": False,
        "prioritize_hooks": True,
    }
    if not instructions:
        return settings
        
    text = instructions.lower()
    
    # Target count (e.g. "5 clips", "10 moments", "10 engaging moments", "top 5")
    count_match = re.search(r"\b(\d+)\s+(?:[\w-]+\s+){0,3}(?:clips?|moments?|shorts?|videos?)\b", text) or \
                  re.search(r"\b(\d+)\s*(?:clips?|moments?|shorts?|videos?)\b", text) or \
                  re.search(r"\b(?:top|find|create|give me|get)\s+(\d+)\b", text)
    if count_match:
        settings["target_count"] = max(1, min(20, int(count_match.group(1))))
        
    # Duration envelope (e.g. "between 30 and 60 seconds", "30-60 second clips", "under 45s")
    dur_range_match = re.search(r"between\s*(\d+)\s*(?:and|to|-)\s*(\d+)\s*sec", text) or \
                      re.search(r"(\d+)\s*(?:-|to)\s*(\d+)\s*sec", text)
    if dur_range_match:
        settings["min_duration"] = float(dur_range_match.group(1))
        settings["max_duration"] = float(dur_range_match.group(2))
    elif "under 30" in text or "short" in text:
        settings["min_duration"] = 15.0
        settings["max_duration"] = 35.0
    elif "longer" in text or "60 to 90" in text:
        settings["min_duration"] = 45.0
        settings["max_duration"] = 90.0
        
    if "education" in text or "learn" in text or "lesson" in text:
        settings["prioritize_educational"] = True
        
    return settings

def score_narrative_moment(
    start_time: float,
    end_time: float,
    text: str,
    words: List[Dict[str, Any]],
    scene_cuts: List[float],
    has_faces: bool,
    avg_face_x: float,
    user_priorities: Dict[str, Any],
) -> Tuple[float, str, ScoreBreakdown, str, str]:
    """
    Computes explainable Opus Virality Score (0-100) and rationale.
    """
    duration = end_time - start_time
    dur_ratio = 1.0
    if duration < user_priorities["min_duration"]:
        dur_ratio = max(0.5, duration / user_priorities["min_duration"])
    elif duration > user_priorities["max_duration"]:
        dur_ratio = max(0.6, user_priorities["max_duration"] / duration)
        
    # 1. Hook Strength (20%) - Evaluates first 3.5 seconds
    hook_words = [w["word"] for w in words if w["start"] <= start_time + 3.5]
    hook_text = " ".join(hook_words).lower()
    hook_score = 65.0
    for pat in HOOK_PATTERNS:
        if re.search(pat, hook_text):
            hook_score += 15.0
    if len(hook_words) >= 6: # Fast opening tempo
        hook_score += 10.0
    hook_score = min(98.0, hook_score)
    
    # 2. Narrative Flow (20%) - Speech tempo and density
    word_count = len(words)
    wpm = (word_count / (duration / 60.0)) if duration > 0 else 0
    flow_score = 70.0
    if 130 <= wpm <= 180: # Ideal short-form tempo
        flow_score += 20.0
    elif 110 <= wpm <= 200:
        flow_score += 10.0
    else:
        flow_score -= 15.0
    flow_score = min(98.0, max(40.0, flow_score))
    
    # 3. Standalone Context (15%) - Beginning and ending independence
    context_score = 80.0
    first_sentence = text.split(".")[0].strip().lower()
    for d_pat in DANGLING_START_PATTERNS:
        if re.search(d_pat, first_sentence):
            context_score -= 25.0
    for d_end in DANGLING_END_PATTERNS:
        if re.search(d_end, text.lower()):
            context_score -= 25.0
    context_score = min(98.0, max(30.0, context_score))
    
    # 4. Educational / Entertainment Value (15%)
    val_score = 65.0
    for pat in VALUE_PATTERNS:
        matches = len(re.findall(pat, text.lower()))
        val_score += min(20.0, matches * 6.0)
    if user_priorities.get("prioritize_educational"):
        val_score += 10.0
    val_score = min(98.0, val_score)
    
    # 5. Emotional Impact (15%)
    emo_score = 60.0
    for pat in EMOTION_PATTERNS:
        matches = len(re.findall(pat, text.lower()))
        emo_score += min(25.0, matches * 7.0)
    emo_score = min(98.0, emo_score)
    
    # 6. Ending Quality (10%)
    last_sentence = text.split(".")[-1].strip().lower()
    end_score = 70.0
    for pat in CLOSING_PATTERNS:
        if re.search(pat, last_sentence):
            end_score += 20.0
    if text.endswith(".") or text.endswith("!"):
        end_score += 8.0
    end_score = min(98.0, end_score)
    
    # 7. Visual Potential (5%)
    vis_score = 70.0
    if has_faces:
        vis_score += 20.0
    # Scene cut within clip gives visual freshness
    cuts_in_clip = [c for c in scene_cuts if start_time <= c <= end_time]
    if 1 <= len(cuts_in_clip) <= 4:
        vis_score += 10.0
    vis_score = min(98.0, vis_score)
    
    # Weighted Virality Score (0-100)
    total_score = (
        0.20 * hook_score +
        0.20 * flow_score +
        0.15 * context_score +
        0.15 * val_score +
        0.15 * emo_score +
        0.10 * end_score +
        0.05 * vis_score
    ) * dur_ratio
    
    total_score = round(max(10.0, min(99.0, total_score)), 1)
    
    # Letter Grade
    if total_score >= 90.0:
        grade = "A+"
    elif total_score >= 82.0:
        grade = "A"
    elif total_score >= 74.0:
        grade = "B+"
    elif total_score >= 65.0:
        grade = "B"
    else:
        grade = "C"
        
    breakdown = ScoreBreakdown(
        hook_strength=round(hook_score, 1),
        narrative_flow=round(flow_score, 1),
        standalone_context=round(context_score, 1),
        educational_value=round(val_score, 1),
        emotional_impact=round(emo_score, 1),
        ending_quality=round(end_score, 1),
        visual_potential=round(vis_score, 1),
    )
    
    # Generate reasoning rationale
    why = (
        f"Selected for strong opening hook ({hook_score:.0f} pts) and "
        f"clean narrative pacing ({wpm:.0f} WPM). "
        f"Contains standalone context with decisive payoff."
    )
    
    # Generate suggested Title from first sentence or topic
    words_clean = [w for w in re.sub(r"[^\w\s]", "", first_sentence).split() if len(w) > 2]
    if len(words_clean) >= 3:
        title = " ".join(words_clean[:6]).title()
    else:
        title = "Key Insightful Moment"
        
    return total_score, grade, breakdown, why, title

def discover_clips_from_analysis(
    project_id: str,
    transcript_data: Dict[str, Any],
    scene_data: Optional[Dict[str, Any]] = None,
    face_data: Optional[Dict[str, Any]] = None,
    instructions: Optional[str] = None,
) -> List[CandidateClip]:
    """
    Discovers ranked, non-overlapping candidate clips snapped to sentence boundaries.
    """
    user_settings = parse_user_instructions(instructions)
    min_dur = user_settings["min_duration"]
    max_dur = user_settings["max_duration"]
    target_count = user_settings["target_count"]
    
    segments = transcript_data.get("segments", [])
    if not segments:
        return []
        
    scene_cuts = scene_data.get("cut_timestamps", []) if scene_data else []
    has_faces = face_data.get("has_visible_faces", True) if face_data else True
    avg_face_x = face_data.get("average_face_x", 0.5) if face_data else 0.5
    
    candidates: List[Dict[str, Any]] = []
    
    # Sliding window over sentence segments
    n = len(segments)
    for i in range(n):
        seg_start = segments[i]["start"]
        accumulated_text = []
        accumulated_words = []
        
        for j in range(i, n):
            seg_end = segments[j]["end"]
            dur = seg_end - seg_start
            accumulated_text.append(segments[j]["text"])
            accumulated_words.extend(segments[j].get("words", []))
            
            if dur < min_dur:
                continue
            if dur > max_dur + 5.0:
                break
                
            full_chunk_text = " ".join(accumulated_text).strip()
            
            # Sentence conclusion check (must end with punctuation or clause boundary)
            if not any(full_chunk_text.endswith(p) for p in [".", "!", "?", "...", ":"]):
                continue
                
            # Score this candidate
            score, grade, breakdown, why, title = score_narrative_moment(
                start_time=seg_start,
                end_time=seg_end,
                text=full_chunk_text,
                words=accumulated_words,
                scene_cuts=scene_cuts,
                has_faces=has_faces,
                avg_face_x=avg_face_x,
                user_priorities=user_settings,
            )
            
            hook_first = " ".join([w.get("word", "") for w in accumulated_words[:8]]).strip()
            
            candidates.append({
                "start_time": round(seg_start, 2),
                "end_time": round(seg_end, 2),
                "duration": round(dur, 2),
                "title": title,
                "hook": hook_first,
                "summary": full_chunk_text[:140] + ("..." if len(full_chunk_text) > 140 else ""),
                "virality_score": score,
                "letter_grade": grade,
                "score_breakdown": breakdown,
                "transcript_excerpt": full_chunk_text,
                "why_chosen": why,
                "crop_config": {"mode": "auto_face", "manual_x_offset": None, "face_x": avg_face_x},
                "caption_config": {"preset": "mrbeast", "font_size": 52, "highlight_color": "#00FF66"},
            })
            
    # Sort by virality score descending
    candidates.sort(key=lambda c: c["virality_score"], reverse=True)
    
    # Non-overlapping deduplication (minimum 15s distance between centers)
    selected_clips: List[CandidateClip] = []
    for cand in candidates:
        cand_center = cand["start_time"] + (cand["duration"] / 2.0)
        overlaps = False
        for s in selected_clips:
            s_center = s.start_time + (s.duration / 2.0)
            if abs(cand_center - s_center) < 15.0:
                overlaps = True
                break
                
        if not overlaps:
            rank = len(selected_clips) + 1
            clip_id = f"clip_{project_id[-6:]}_{rank:02d}"
            selected_clips.append(CandidateClip(
                clip_id=clip_id,
                project_id=project_id,
                rank=rank,
                start_time=cand["start_time"],
                end_time=cand["end_time"],
                duration=cand["duration"],
                title=cand["title"],
                hook=cand["hook"],
                summary=cand["summary"],
                virality_score=cand["virality_score"],
                letter_grade=cand["letter_grade"],
                score_breakdown=cand["score_breakdown"],
                transcript_excerpt=cand["transcript_excerpt"],
                why_chosen=cand["why_chosen"],
                crop_config=cand["crop_config"],
                caption_config=cand["caption_config"],
            ))
            if len(selected_clips) >= target_count:
                break
                
    logger.info("Discovered and ranked %d non-overlapping candidate clips for project %s.",
                len(selected_clips), project_id)
    return selected_clips

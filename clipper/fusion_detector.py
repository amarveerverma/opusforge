import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from clipper.config import DEFAULT_CONFIG
from clipper.transcriber import TranscriptResult, SegmentTiming, WordTiming
from clipper.visual_analyzer import VisualAnalysisResult, VisualMoment
from clipper.audio_analyzer import AudioAnalysisResult, AudioMoment


class CandidateClip(BaseModel):
    id: int
    title: str
    start_time: float
    end_time: float
    duration: float
    hook_score: float
    flow_score: float
    visual_score: float
    audio_score: float
    raw_fusion_score: float
    transcript_snippet: str
    start_words: str
    end_words: str


HOOK_KEYWORDS = [
    "why", "how", "secret", "never", "always", "stop", "mistake", "truth",
    "imagine", "if you", "the reason", "nobody talks about", "here is what",
    "what happens when", "the craziest thing", "listen to this", "remember",
    "actually", "the problem with", "look at", "watch this", "think about"
]


def score_transcript_hook(first_segment_text: str) -> float:
    """Evaluate linguistic hook quality of opening segment."""
    text_lower = first_segment_text.lower()
    score = 50.0

    # Questions are great hooks
    if "?" in first_segment_text:
        score += 20.0

    # Check for hook triggers
    for kw in HOOK_KEYWORDS:
        if kw in text_lower:
            score += 15.0
            break

    # Exclamations or emphatic words
    if "!" in first_segment_text or any(w in text_lower for w in ["insane", "crazy", "shocking", "huge"]):
        score += 10.0

    return min(99.0, max(20.0, score))


def fuse_signals_to_candidates(
    transcript: TranscriptResult,
    visuals: VisualAnalysisResult,
    audio: AudioAnalysisResult,
    min_duration: float = 15.0,
    max_duration: float = 90.0,
    max_candidates: int = 15
) -> List[CandidateClip]:
    """
    Multimodal Signal Fusion:
    Combines transcript sentence segments, visual moments, and audio energy
    to find self-contained narrative clips with strong hooks and payoffs.
    """
    segments = transcript.segments
    if not segments:
        # If no transcript segments, synthesize uniform chunks based on audio duration
        duration = audio.duration
        if duration < min_duration:
            return []
        step = min(max_duration, max(min_duration, 30.0))
        chunks = []
        curr = 0.0
        clip_id = 1
        while curr + min_duration <= duration:
            end = min(duration, curr + step)
            chunks.append(CandidateClip(
                id=clip_id,
                title=f"Highlight Clip {clip_id}",
                start_time=round(curr, 2),
                end_time=round(end, 2),
                duration=round(end - curr, 2),
                hook_score=60.0,
                flow_score=60.0,
                visual_score=60.0,
                audio_score=60.0,
                raw_fusion_score=60.0,
                transcript_snippet="Audio-Visual Segment",
                start_words="",
                end_words=""
            ))
            curr += step * 0.75
            clip_id += 1
        return chunks

    raw_candidates: List[CandidateClip] = []
    clip_id_counter = 1

    # Slide window over transcript sentence segments
    num_segs = len(segments)

    for i in range(num_segs):
        start_seg = segments[i]
        start_t = start_seg.start

        # Audio energy around start (Hook 0-3s)
        sec_start = int(start_t)
        start_audio_energy = 50.0
        if 0 <= sec_start < len(audio.per_second_energy):
            start_audio_energy = max(audio.per_second_energy[sec_start:sec_start + 4] or [50.0])

        # Visual score around start
        start_visual_score = 50.0
        if 0 <= sec_start < len(visuals.per_second_visual_score):
            start_visual_score = max(visuals.per_second_visual_score[sec_start:sec_start + 4] or [50.0])

        # Hook score combines linguistic hook, audio spike, and visual hook
        lang_hook = score_transcript_hook(start_seg.text)
        hook_score = round(0.4 * lang_hook + 0.3 * start_audio_energy + 0.3 * start_visual_score, 1)

        # Look forward to find natural endpoints between min_duration and max_duration
        for j in range(i, num_segs):
            end_seg = segments[j]
            end_t = end_seg.end
            duration = end_t - start_t

            if duration < min_duration:
                continue
            if duration > max_duration:
                break

            # Clip spans segments[i:j+1]
            clip_segs = segments[i:j + 1]
            clip_text = " ".join([s.text for s in clip_segs])

            # Evaluate audio across the clip
            sec_end = min(int(end_t), len(audio.per_second_energy))
            clip_audio_slice = audio.per_second_energy[sec_start:sec_end]
            avg_audio_energy = float(sum(clip_audio_slice) / len(clip_audio_slice)) if clip_audio_slice else 50.0

            # Count energy peaks and reactions in this range
            peaks_in_clip = sum(1 for p in audio.energy_peaks if start_t <= p <= end_t)
            reactions_in_clip = sum(1 for r in audio.reaction_moments if start_t <= r.timestamp <= end_t)
            audio_factor_score = min(98.0, avg_audio_energy + (peaks_in_clip * 3.5) + (reactions_in_clip * 5.0))

            # Evaluate visuals across the clip
            clip_visual_slice = visuals.per_second_visual_score[sec_start:min(int(end_t), len(visuals.per_second_visual_score))]
            avg_visual_score = float(sum(clip_visual_slice) / len(clip_visual_slice)) if clip_visual_slice else 50.0
            highlights_in_clip = sum(1 for h in visuals.highlight_timestamps if start_t <= h <= end_t)
            visual_factor_score = min(98.0, avg_visual_score + (highlights_in_clip * 3.0))

            # Flow score: density of sentences, absence of long dead silences
            silence_penalty = 0.0
            for s_start, s_end in audio.silence_intervals:
                if s_start >= start_t and s_end <= end_t:
                    if (s_end - s_start) > 2.5:
                        silence_penalty += 8.0

            flow_score = max(25.0, min(98.0, 75.0 + (len(clip_segs) * 2.5) - silence_penalty))

            # Payoff score: concluding sentence characteristics
            last_text = end_seg.text.strip()
            payoff_bonus = 0.0
            if last_text.endswith((".", "!", "?")):
                payoff_bonus += 8.0
            if any(term in last_text.lower() for term in ["so", "that's why", "remember", "in the end", "conclusion"]):
                payoff_bonus += 8.0

            # Weighted fusion score (0 - 100)
            raw_score = (
                0.35 * hook_score +
                0.25 * flow_score +
                0.20 * visual_factor_score +
                0.20 * audio_factor_score +
                payoff_bonus
            )
            raw_score = round(min(99.0, max(20.0, raw_score)), 1)

            # Generate a catchy clip title from the opening hook or first 6 words
            words = start_seg.text.split()
            title = " ".join(words[:6]).strip(".,?!:;")
            if len(title) < 10 and len(words) > 6:
                title = " ".join(words[:9]).strip(".,?!:;")
            if not title:
                title = f"Moment at {int(start_t)}s"

            start_words = " ".join(clip_text.split()[:5])
            end_words = " ".join(clip_text.split()[-5:])

            raw_candidates.append(CandidateClip(
                id=clip_id_counter,
                title=title,
                start_time=round(start_t, 2),
                end_time=round(end_t, 2),
                duration=round(duration, 2),
                hook_score=round(hook_score, 1),
                flow_score=round(flow_score, 1),
                visual_score=round(visual_factor_score, 1),
                audio_score=round(audio_factor_score, 1),
                raw_fusion_score=raw_score,
                transcript_snippet=clip_text[:280] + ("..." if len(clip_text) > 280 else ""),
                start_words=start_words,
                end_words=end_words
            ))
            clip_id_counter += 1

    # Deduplicate and merge overlapping candidate windows
    # Sort by raw fusion score descending
    raw_candidates.sort(key=lambda c: c.raw_fusion_score, reverse=True)

    selected: List[CandidateClip] = []
    # First pass: strictly deduplicated
    for cand in raw_candidates:
        intersection_thresh = 0.55
        overlap = any(
            (max(0.0, min(cand.end_time, s.end_time) - max(cand.start_time, s.start_time)) > intersection_thresh * min(cand.duration, s.duration))
            for s in selected
        )
        if not overlap:
            selected.append(cand)
            if len(selected) >= max_candidates:
                break

    # Second pass: if we need more clips to reach max_candidates, relax overlap
    if len(selected) < max_candidates:
        for cand in raw_candidates:
            if cand in selected:
                continue
            intersection_thresh = 0.80
            overlap = any(
                (max(0.0, min(cand.end_time, s.end_time) - max(cand.start_time, s.start_time)) > intersection_thresh * min(cand.duration, s.duration))
                for s in selected
            )
            if not overlap:
                selected.append(cand)
                if len(selected) >= max_candidates:
                    break

    # Re-index IDs cleanly
    for idx, c in enumerate(selected, 1):
        c.id = idx

    print(f"[*] Signal fusion complete: detected {len(selected)} distinct self-contained clip candidates.")
    return selected

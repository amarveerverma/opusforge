import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from clipper.config import GEMINI_API_KEY, DEFAULT_CONFIG
from clipper.fusion_detector import CandidateClip


class FactorScore(BaseModel):
    score: int  # 0 - 99
    grade: str  # "A", "B", or "C"
    justification: str


class ScoredClip(BaseModel):
    id: int
    title: str
    start_time: float
    end_time: float
    duration: float
    virality_score: int  # 0 - 99
    overall_grade: str   # "A", "B", or "C"
    hook: FactorScore
    flow: FactorScore
    value: FactorScore
    trend: FactorScore
    one_line_reasoning: str
    transcript_snippet: str
    exported_file: Optional[str] = None


def score_to_grade(score: int) -> str:
    """Convert numeric score (0-99) to letter grade."""
    if score >= 85:
        return "A"
    elif score >= 70:
        return "B"
    else:
        return "C"


def score_clips_with_gemini(
    candidates: List[CandidateClip],
    model_name: Optional[str] = None
) -> List[ScoredClip]:
    """
    Score clips using Gemini LLM adhering to Opus Clip virality criteria:
    HOOK, FLOW, VALUE, TREND.
    """
    from google import genai
    from google.genai import types

    api_key = GEMINI_API_KEY
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")

    client = genai.Client(api_key=api_key)
    model = model_name or DEFAULT_CONFIG["gemini_model"]

    scored_clips: List[ScoredClip] = []

    for cand in candidates:
        system_instruction = (
            "You are an expert viral content producer and video editor replicating Opus Clip's Virality Score system. "
            "Evaluate this candidate short clip (15-90 seconds) for TikTok, YouTube Shorts, and Instagram Reels. "
            "Score these 4 factors from 0 to 99 with a letter grade (A for 85-99, B for 70-84, C for <70) and a concise one-line justification: "
            "1. HOOK: Does the first 3 seconds grab attention, introduce curiosity/tension, and relate to the topic? "
            "2. FLOW: Does it have a logical narrative progression with a satisfying punchline or conclusion? "
            "3. VALUE: Practical usefulness, high emotional resonance, humor, or personal connection? "
            "4. TREND: Alignment with current short-form trends (pacing, snappy delivery, memeable or relatable angle). "
            "Calculate composite virality_score = round(0.30*hook + 0.25*flow + 0.25*value + 0.20*trend). "
            "Also suggest a punchy, click-worthy title (max 6 words)."
        )

        user_content = (
            f"Candidate Clip ID: {cand.id}\n"
            f"Duration: {cand.duration}s ({cand.start_time}s to {cand.end_time}s)\n"
            f"Opening words (first 3s): \"{cand.start_words}\"\n"
            f"Concluding words: \"{cand.end_words}\"\n"
            f"Full clip transcript:\n\"{cand.transcript_snippet}\"\n"
            f"Signal metrics: Audio score={cand.audio_score}, Visual score={cand.visual_score}, Raw hook={cand.hook_score}."
        )

        try:
            response = client.models.generate_content(
                model=model,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    temperature=0.3,
                )
            )

            data = json.loads(response.text)

            hook_sc = int(data.get("hook", {}).get("score", cand.hook_score))
            flow_sc = int(data.get("flow", {}).get("score", cand.flow_score))
            val_sc = int(data.get("value", {}).get("score", 75))
            trend_sc = int(data.get("trend", {}).get("score", 78))

            v_score = int(data.get("virality_score", round(0.30 * hook_sc + 0.25 * flow_sc + 0.25 * val_sc + 0.20 * trend_sc)))
            v_score = min(99, max(10, v_score))

            suggested_title = data.get("title") or cand.title

            scored_clips.append(ScoredClip(
                id=cand.id,
                title=suggested_title,
                start_time=cand.start_time,
                end_time=cand.end_time,
                duration=cand.duration,
                virality_score=v_score,
                overall_grade=score_to_grade(v_score),
                hook=FactorScore(
                    score=hook_sc,
                    grade=score_to_grade(hook_sc),
                    justification=data.get("hook", {}).get("justification", "Opening statement captures immediate curiosity.")
                ),
                flow=FactorScore(
                    score=flow_sc,
                    grade=score_to_grade(flow_sc),
                    justification=data.get("flow", {}).get("justification", "Clear narrative arc with complete conclusion.")
                ),
                value=FactorScore(
                    score=val_sc,
                    grade=score_to_grade(val_sc),
                    justification=data.get("value", {}).get("justification", "High educational and relatable insight.")
                ),
                trend=FactorScore(
                    score=trend_sc,
                    grade=score_to_grade(trend_sc),
                    justification=data.get("trend", {}).get("justification", "Fast-paced storytelling suited for modern feeds.")
                ),
                one_line_reasoning=data.get("one_line_reasoning", f"Strong hook with {score_to_grade(v_score)}-grade viral potential."),
                transcript_snippet=cand.transcript_snippet
            ))
        except Exception as e:
            print(f"[!] Warning: Gemini scoring call failed ({e}). Using heuristic scoring.")
            scored_clips.append(heuristic_score_clip(cand))

    return scored_clips


def heuristic_score_clip(cand: CandidateClip) -> ScoredClip:
    """
    Heuristic rule-based scoring engine mimicking Opus Virality Score
    when Gemini API is offline.
    """
    # 1. Hook score
    hook_sc = int(min(98, max(45, cand.hook_score)))

    # 2. Flow score
    flow_sc = int(min(98, max(40, cand.flow_score)))

    # 3. Value score: based on sentence density and length sweetspot (20-45s is optimal)
    val_base = 74
    if 20 <= cand.duration <= 50:
        val_base += 12
    if len(cand.transcript_snippet.split()) > 40:
        val_base += 6
    val_sc = int(min(98, max(50, val_base)))

    # 4. Trend score: based on audio peaks, visual activity, and brevity
    trend_base = 72
    if cand.audio_score > 70:
        trend_base += 8
    if cand.visual_score > 70:
        trend_base += 8
    if cand.duration <= 45:
        trend_base += 6
    trend_sc = int(min(99, max(50, trend_base)))

    composite = int(round(0.30 * hook_sc + 0.25 * flow_sc + 0.25 * val_sc + 0.20 * trend_sc))
    composite = min(99, max(25, composite))

    hook_just = (
        "Strong curiosity gap and high initial audio energy in the first 3 seconds."
        if hook_sc >= 80 else "Decent opening hook, relates directly to the core topic."
    )
    flow_just = (
        "Smooth narrative arc with satisfying resolution and natural pauses."
        if flow_sc >= 80 else "Logical progression that keeps viewers engaged throughout."
    )
    value_just = (
        "Delivers actionable, high-utility insight with strong emotional resonance."
        if val_sc >= 80 else "Informative perspective with relatable takeaway for the audience."
    )
    trend_just = (
        "Optimal short-form pacing and high engagement potential for Reels/Shorts/TikTok."
        if trend_sc >= 80 else "Matches current conversational video formats on short-form platforms."
    )

    reasoning = f"Scored {composite}/99 ({score_to_grade(composite)}) with compelling hook and cohesive narrative flow."

    return ScoredClip(
        id=cand.id,
        title=cand.title,
        start_time=cand.start_time,
        end_time=cand.end_time,
        duration=cand.duration,
        virality_score=composite,
        overall_grade=score_to_grade(composite),
        hook=FactorScore(score=hook_sc, grade=score_to_grade(hook_sc), justification=hook_just),
        flow=FactorScore(score=flow_sc, grade=score_to_grade(flow_sc), justification=flow_just),
        value=FactorScore(score=val_sc, grade=score_to_grade(val_sc), justification=value_just),
        trend=FactorScore(score=trend_sc, grade=score_to_grade(trend_sc), justification=trend_just),
        one_line_reasoning=reasoning,
        transcript_snippet=cand.transcript_snippet
    )


def score_and_rank_clips(
    candidates: List[CandidateClip],
    use_gemini: bool = True
) -> List[ScoredClip]:
    """
    Score all candidate clips and return them sorted by Virality Score descending.
    """
    if not candidates:
        return []

    has_key = bool(GEMINI_API_KEY)
    if use_gemini and has_key:
        print(f"[*] Scoring {len(candidates)} candidate clips with Gemini AI (Opus Virality criteria)...")
        scored = score_clips_with_gemini(candidates)
    else:
        if not has_key:
            print("[*] Notice: GEMINI_API_KEY not found in environment. Using heuristic scoring engine.")
        else:
            print("[*] Scoring clips using local heuristic engine.")
        scored = [heuristic_score_clip(c) for c in candidates]

    # Sort strictly by Virality Score descending
    scored.sort(key=lambda s: s.virality_score, reverse=True)

    # Re-assign rank IDs
    for rank, clip in enumerate(scored, 1):
        clip.id = rank

    return scored

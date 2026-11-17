"""
Phase 5 AI Clip Discovery & Scoring Test Suite
"""
import pytest
from pathlib import Path
from starlette.testclient import TestClient
from backend.app.main import app
from backend.app.core.clip_discovery import (
    parse_user_instructions,
    score_narrative_moment,
    discover_clips_from_analysis,
    ScoreBreakdown,
    CandidateClip,
)

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_instruction_parser():
    res1 = parse_user_instructions("Find 10 engaging moments between 30 and 60 seconds with strong hooks")
    assert res1["target_count"] == 10
    assert res1["min_duration"] == 30.0
    assert res1["max_duration"] == 60.0
    
    res2 = parse_user_instructions("Find 3 quick educational shorts under 30 sec")
    assert res2["target_count"] == 3
    assert res2["max_duration"] <= 35.0
    assert res2["prioritize_educational"] is True

def test_scoring_weights_and_rationale():
    words = [
        {"word": "Why", "start": 0.0, "end": 0.3},
        {"word": "does", "start": 0.3, "end": 0.5},
        {"word": "nobody", "start": 0.5, "end": 0.9},
        {"word": "talk", "start": 0.9, "end": 1.2},
        {"word": "about", "start": 1.2, "end": 1.5},
        {"word": "this", "start": 1.5, "end": 1.8},
        {"word": "unbelievable", "start": 1.8, "end": 2.5},
        {"word": "secret?", "start": 2.5, "end": 3.2},
    ]
    # Add filler to make 35 seconds of natural speech
    for i in range(80):
        t = 3.2 + (i * 0.4)
        words.append({"word": f"concept_{i}", "start": round(t, 2), "end": round(t + 0.35, 2)})
        
    full_text = "Why does nobody talk about this unbelievable secret? In 2026, content creators who rely on basic transcripts are falling behind. This method transforms your engagement forever."
    
    score, grade, breakdown, why, title = score_narrative_moment(
        start_time=0.0,
        end_time=35.0,
        text=full_text,
        words=words,
        scene_cuts=[10.0, 20.0],
        has_faces=True,
        avg_face_x=0.5,
        user_priorities={"min_duration": 25.0, "max_duration": 60.0},
    )
    
    assert 10.0 <= score <= 99.0
    assert grade in ["A+", "A", "B+", "B", "C"]
    assert isinstance(breakdown, ScoreBreakdown)
    assert breakdown.hook_strength >= 70.0 # High hook score due to "Why does nobody talk about this unbelievable secret?"
    assert len(why) > 20
    assert len(title) > 3

def test_discovery_from_transcript_data():
    mock_transcript = {
        "duration": 120.0,
        "segments": [
            {
                "id": 0, "start": 0.0, "end": 12.0,
                "text": "Stop scrolling right now! Why does nobody talk about this unbelievable AI video secret?",
                "words": [
                    {"word": "Stop", "start": 0.0, "end": 0.4},
                    {"word": "scrolling", "start": 0.4, "end": 0.9},
                    {"word": "right", "start": 0.9, "end": 1.2},
                    {"word": "now!", "start": 1.2, "end": 1.5},
                    {"word": "Why", "start": 1.5, "end": 1.8},
                    {"word": "does", "start": 1.8, "end": 2.1},
                    {"word": "nobody", "start": 2.1, "end": 2.5},
                    {"word": "talk", "start": 2.5, "end": 2.8},
                    {"word": "about", "start": 2.8, "end": 3.1},
                    {"word": "this", "start": 3.1, "end": 3.4},
                    {"word": "secret?", "start": 3.4, "end": 3.9},
                ]
            },
            {
                "id": 1, "start": 12.0, "end": 26.0,
                "text": "The real viral clips are discovered by fusing multimodal vision and audio energy peaks.",
                "words": [
                    {"word": "The", "start": 12.0, "end": 12.3},
                    {"word": "real", "start": 12.3, "end": 12.6},
                    {"word": "viral", "start": 12.6, "end": 13.0},
                    {"word": "clips", "start": 13.0, "end": 13.4},
                    {"word": "are", "start": 13.4, "end": 13.6},
                    {"word": "discovered.", "start": 13.6, "end": 14.2},
                ]
            },
            {
                "id": 2, "start": 26.0, "end": 38.0,
                "text": "Adopt this multimodal clipping pipeline today, and transform your content strategy forever.",
                "words": [
                    {"word": "Adopt", "start": 26.0, "end": 26.4},
                    {"word": "this", "start": 26.4, "end": 26.7},
                    {"word": "pipeline", "start": 26.7, "end": 27.2},
                    {"word": "today.", "start": 27.2, "end": 27.8},
                ]
            },
        ]
    }
    
    clips = discover_clips_from_analysis(
        project_id="test_proj_123",
        transcript_data=mock_transcript,
        instructions="Find 2 clips between 20 and 45 seconds",
    )
    
    assert len(clips) >= 1
    first_clip = clips[0]
    assert isinstance(first_clip, CandidateClip)
    assert first_clip.rank == 1
    assert first_clip.duration >= 20.0
    assert first_clip.start_time == 0.0
    assert first_clip.virality_score > 70.0

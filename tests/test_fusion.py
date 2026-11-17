from clipper.transcriber import TranscriptResult, SegmentTiming, WordTiming
from clipper.visual_analyzer import VisualAnalysisResult, VisualMoment
from clipper.audio_analyzer import AudioAnalysisResult
from clipper.fusion_detector import fuse_signals_to_candidates


def test_fusion_candidates_detection():
    # Construct mock transcript with 4 sentences spanning 40s
    segments = [
        SegmentTiming(
            id=1, start=0.0, end=8.0, text="Why does nobody talk about this unbelievable AI secret?",
            words=[WordTiming(word="Why", start=0.0, end=0.4, probability=0.99)]
        ),
        SegmentTiming(
            id=2, start=8.2, end=18.0, text="In 2026, content creators who ignore multimodal pipelines fall behind.",
            words=[WordTiming(word="In", start=8.2, end=8.5, probability=0.95)]
        ),
        SegmentTiming(
            id=3, start=18.5, end=28.0, text="By analyzing video frames and audio peaks together, clips achieve viral reach.",
            words=[WordTiming(word="By", start=18.5, end=18.8, probability=0.98)]
        ),
        SegmentTiming(
            id=4, start=28.5, end=35.0, text="That is why you must adopt this workflow today.",
            words=[WordTiming(word="That", start=28.5, end=28.8, probability=0.99)]
        ),
    ]
    transcript = TranscriptResult(
        full_text="Why does nobody talk about this unbelievable AI secret? In 2026, content creators who ignore multimodal pipelines fall behind. By analyzing video frames and audio peaks together, clips achieve viral reach. That is why you must adopt this workflow today.",
        language="en",
        segments=segments,
        words=[]
    )

    visuals = VisualAnalysisResult(
        total_frames_sampled=20,
        sampling_interval=2.0,
        moments=[
            VisualMoment(
                timestamp=0.0, scene="Face close-up", actions="Talking", on_screen_text="",
                facial_expression="Intense", emotional_moment="Hook", visual_interest_score=85.0, is_visual_hook=True
            )
        ],
        per_second_visual_score=[80.0] * 40,
        highlight_timestamps=[0.0, 18.0]
    )

    audio = AudioAnalysisResult(
        audio_path="",
        duration=40.0,
        avg_energy=65.0,
        peak_count=3,
        energy_peaks=[1.0, 18.0, 30.0],
        silence_intervals=[(35.0, 40.0)],
        reaction_moments=[],
        per_second_energy=[70.0] * 40,
        per_second_speech_rate=[3.0] * 40
    )

    candidates = fuse_signals_to_candidates(
        transcript=transcript,
        visuals=visuals,
        audio=audio,
        min_duration=15.0,
        max_duration=40.0
    )

    assert len(candidates) > 0
    top_cand = candidates[0]
    assert 15.0 <= top_cand.duration <= 40.0
    assert top_cand.hook_score > 60.0
    print(f"test_fusion_candidates_detection: PASSED (found {len(candidates)} candidates, top duration: {top_cand.duration}s)")


if __name__ == "__main__":
    test_fusion_candidates_detection()

from clipper.fusion_detector import CandidateClip
from clipper.scorer import score_and_rank_clips


def test_scorer_ranking():
    candidates = [
        CandidateClip(
            id=1, title="Average Moment", start_time=0.0, end_time=25.0, duration=25.0,
            hook_score=52.0, flow_score=60.0, visual_score=55.0, audio_score=50.0,
            raw_fusion_score=54.0, transcript_snippet="Just an ordinary explanation of tools.",
            start_words="Just an ordinary", end_words="tools."
        ),
        CandidateClip(
            id=2, title="Viral AI Secret", start_time=26.0, end_time=56.0, duration=30.0,
            hook_score=94.0, flow_score=91.0, visual_score=88.0, audio_score=85.0,
            raw_fusion_score=90.0, transcript_snippet="Why does nobody talk about this crazy secret? It turns out everyone was wrong.",
            start_words="Why does nobody", end_words="everyone was wrong."
        )
    ]

    ranked = score_and_rank_clips(candidates, use_gemini=False)
    assert len(ranked) == 2
    # Highest score must be first
    assert ranked[0].title == "Viral AI Secret"
    assert ranked[0].virality_score > ranked[1].virality_score
    assert ranked[0].overall_grade in ["A", "B"]
    assert ranked[0].hook.grade in ["A", "B"]
    assert len(ranked[0].hook.justification) > 5
    print(f"test_scorer_ranking: PASSED (top score: {ranked[0].virality_score}/99 [{ranked[0].overall_grade}])")


if __name__ == "__main__":
    test_scorer_ranking()

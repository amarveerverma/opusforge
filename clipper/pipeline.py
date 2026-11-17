import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

from clipper.config import DEFAULT_CONFIG, OUTPUT_DIR, ensure_dirs
from clipper.downloader import ingest_video, VideoMetadata
from clipper.transcriber import transcribe_video_or_audio, TranscriptResult
from clipper.visual_analyzer import analyze_video_visuals, VisualAnalysisResult
from clipper.audio_analyzer import analyze_audio, AudioAnalysisResult
from clipper.fusion_detector import fuse_signals_to_candidates, CandidateClip
from clipper.scorer import score_and_rank_clips, ScoredClip
from clipper.exporter import export_top_clips
from clipper.dashboard import print_cli_dashboard, save_analysis_json


def run_pipeline(
    input_source: str,
    top_n: int = 3,
    min_duration: float = 15.0,
    max_duration: float = 90.0,
    output_dir: Optional[Path] = None,
    use_gemini: bool = True
) -> Dict[str, Any]:
    """
    Executes the full Opus Clip multimodal pipeline:
    1. Downloader / Ingest (YouTube URL or local file)
    2. Transcription (word-level timestamps)
    3. Multimodal Visual Analysis (scenes, text, expressions, hooks)
    4. Audio Programmatic Analysis (energy peaks, silence, laughter/reactions)
    5. Signal Fusion (self-contained moments detection)
    6. Virality Scoring (Opus Virality criteria: Hook/Flow/Value/Trend)
    7. Vertical 9:16 Export (active speaker centering + word captions)
    8. Analysis Report & Dashboard
    """
    start_total_time = time.time()
    ensure_dirs()
    target_out_dir = output_dir or OUTPUT_DIR
    target_out_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 60)
    print("🚀 LAUNCHING OPUS CLIP MULTIMODAL PIPELINE")
    print("=" * 60)

    # 1. Ingest input video
    print(f"\n[Stage 1/7] Ingesting video: {input_source}")
    metadata: VideoMetadata = ingest_video(input_source)
    print(f" -> Title: {metadata.title}")
    print(f" -> Duration: {metadata.duration}s | Resolution: {metadata.width}x{metadata.height} | FPS: {metadata.fps}")

    # 2. Transcribe audio with word-level timestamps
    print("\n[Stage 2/7] Transcribing audio with word-level timestamps...")
    transcript: TranscriptResult = transcribe_video_or_audio(metadata.file_path)
    print(f" -> Transcribed {len(transcript.words)} words across {len(transcript.segments)} sentences.")

    # 3. Sample frames and analyze multimodal visuals
    print("\n[Stage 3/7] Multimodal visual analysis (frames sampled every 2.0s)...")
    visuals: VisualAnalysisResult = analyze_video_visuals(
        metadata.file_path,
        interval_sec=DEFAULT_CONFIG["frame_sample_interval"],
        use_gemini=use_gemini
    )
    print(f" -> Sampled {visuals.total_frames_sampled} frames. Detected {len(visuals.highlight_timestamps)} visual highlight timestamps.")

    # 4. Programmatic audio track analysis
    print("\n[Stage 4/7] Programmatic audio analysis (energy, silence, reactions)...")
    audio: AudioAnalysisResult = analyze_audio(metadata.file_path)
    print(f" -> Detected {audio.peak_count} volume peaks, {len(audio.silence_intervals)} silence pauses, and {len(audio.reaction_moments)} reaction spikes.")

    # 5. Multimodal Signal Fusion
    print("\n[Stage 5/7] Fusing transcript + visual + audio signals to detect moments...")
    candidates: List[CandidateClip] = fuse_signals_to_candidates(
        transcript=transcript,
        visuals=visuals,
        audio=audio,
        min_duration=min_duration,
        max_duration=max_duration,
        max_candidates=max(top_n * 3, 25)
    )
    print(f" -> Identified {len(candidates)} candidate self-contained clips (15-90s).")

    if not candidates:
        print("[!] No candidate clips met duration and narrative thresholds.")
        return {"status": "error", "message": "No candidates found"}

    # 6. Scoring (Opus Virality criteria)
    print("\n[Stage 6/7] Computing Opus Virality Scores (HOOK, FLOW, VALUE, TREND)...")
    ranked_clips: List[ScoredClip] = score_and_rank_clips(candidates, use_gemini=use_gemini)
    print(f" -> Ranked {len(ranked_clips)} clips. Top clip score: {ranked_clips[0].virality_score}/99 [Grade {ranked_clips[0].overall_grade}]")

    # 7. Vertical 9:16 Reframe & Word-Synced Captions Export
    print(f"\n[Stage 7/7] Exporting top {min(top_n, len(ranked_clips))} vertical 9:16 clips with speaker centering and captions...")
    export_top_clips(
        source_video_path=metadata.file_path,
        scored_clips=ranked_clips,
        words=transcript.words,
        top_n=top_n,
        output_dir=target_out_dir
    )

    # 8. Save structured JSON report
    report_json_path = target_out_dir / "analysis_report.json"
    save_analysis_json(metadata, ranked_clips, report_json_path)

    # 9. Print Rich CLI Dashboard
    print("\n")
    print_cli_dashboard(metadata, ranked_clips, top_n=top_n)

    elapsed = round(time.time() - start_total_time, 1)
    print(f"\n✨ Pipeline successfully completed in {elapsed}s! Outputs stored in: {target_out_dir.resolve()}\n")

    return {
        "status": "ok",
        "metadata": metadata.model_dump(),
        "total_clips": len(ranked_clips),
        "exported_clips": min(top_n, len(ranked_clips)),
        "report_path": str(report_json_path.resolve())
    }

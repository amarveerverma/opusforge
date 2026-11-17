import argparse
import sys
from pathlib import Path
from clipper.pipeline import run_pipeline
from clipper.web_app import start_server


def main():
    parser = argparse.ArgumentParser(
        description="Opus Clip-style AI Video Clipping Pipeline (Multimodal + Virality Scoring + 9:16 Reframe)"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", type=str, help="YouTube video URL to download and process")
    group.add_argument("--file", type=str, help="Path to local video file (mp4, mov, mkv)")

    parser.add_argument("--top-n", type=int, default=3, help="Number of top clips to export as 9:16 mp4 (default: 3)")
    parser.add_argument("--min-duration", type=float, default=15.0, help="Minimum clip duration in seconds (default: 15.0)")
    parser.add_argument("--max-duration", type=float, default=90.0, help="Maximum clip duration in seconds (default: 90.0)")
    parser.add_argument("--output-dir", type=str, default="output", help="Output directory for clips and JSON report")
    parser.add_argument("--no-gemini", action="store_true", help="Force offline heuristic mode (skips Gemini API calls)")
    parser.add_argument("--web", action="store_true", help="Launch local web UI dashboard after processing")
    parser.add_argument("--port", type=int, default=8000, help="Port for web dashboard if --web is specified")

    args = parser.parse_args()

    input_source = args.url or args.file
    out_dir = Path(args.output_dir)

    run_pipeline(
        input_source=input_source,
        top_n=args.top_n,
        min_duration=args.min_duration,
        max_duration=args.max_duration,
        output_dir=out_dir,
        use_gemini=not args.no_gemini
    )

    if args.web:
        start_server(port=args.port)


if __name__ == "__main__":
    main()

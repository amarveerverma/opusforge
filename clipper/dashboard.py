import json
from pathlib import Path
from typing import List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from clipper.scorer import ScoredClip
from clipper.downloader import VideoMetadata


def print_cli_dashboard(
    metadata: VideoMetadata,
    scored_clips: List[ScoredClip],
    top_n: int = 3
):
    """
    Renders a formatted Opus Clip-style dashboard in the terminal using Rich.
    """
    console = Console()

    header_text = Text()
    header_text.append("✦ OPUS CLIP AI PIPELINE ✦\n", style="bold magenta")
    header_text.append(f"Video: {metadata.title}\n", style="bold white")
    header_text.append(f"Duration: {metadata.duration}s | Resolution: {metadata.width}x{metadata.height} | Source: {metadata.source_type}\n", style="dim white")
    header_text.append(f"Detected Moments: {len(scored_clips)} | Top Exported: {min(top_n, len(scored_clips))}", style="cyan")

    console.print(Panel(header_text, border_style="magenta", expand=False))

    table = Table(
        title="★ RANKED VIRAL CLIPS (Opus Virality Score) ★",
        header_style="bold cyan",
        border_style="dim white",
        show_lines=True
    )

    table.add_column("Rank", justify="center", style="bold yellow", width=6)
    table.add_column("Score", justify="center", width=12)
    table.add_column("Clip Title", style="bold white", width=26)
    table.add_column("Time (Dur)", justify="center", width=16)
    table.add_column("Factors (Hook / Flow / Val / Trnd)", justify="center", width=34)
    table.add_column("One-Line Justification & Status", width=42)

    for clip in scored_clips:
        # Grade colors
        grade_colors = {"A": "bold green", "B": "bold yellow", "C": "bold red"}
        v_color = grade_colors.get(clip.overall_grade, "white")

        score_text = Text()
        score_text.append(f"{clip.virality_score}", style=v_color)
        score_text.append("/99 ", style="dim")
        score_text.append(f"[{clip.overall_grade}]", style=v_color)

        time_range = f"{clip.start_time:04.1f}s - {clip.end_time:04.1f}s\n({clip.duration:04.1f}s)"

        factors_text = Text()
        factors_text.append(f"H: {clip.hook.grade}({clip.hook.score}) ", style=grade_colors.get(clip.hook.grade, "white"))
        factors_text.append(f"F: {clip.flow.grade}({clip.flow.score}) ", style=grade_colors.get(clip.flow.grade, "white"))
        factors_text.append(f"V: {clip.value.grade}({clip.value.score}) ", style=grade_colors.get(clip.value.grade, "white"))
        factors_text.append(f"T: {clip.trend.grade}({clip.trend.score})", style=grade_colors.get(clip.trend.grade, "white"))

        status_text = Text()
        status_text.append(f"{clip.one_line_reasoning}\n", style="white")
        if clip.exported_file:
            exported_name = Path(clip.exported_file).name
            status_text.append(f"✓ Exported: {exported_name}", style="bold green")
        else:
            status_text.append("○ Candidate (Not exported)", style="dim")

        table.add_row(
            f"#{clip.id}",
            score_text,
            clip.title,
            time_range,
            factors_text,
            status_text
        )

    console.print(table)


def save_analysis_json(
    metadata: VideoMetadata,
    scored_clips: List[ScoredClip],
    output_path: Path
) -> Path:
    """
    Saves full structured JSON analysis report alongside exported clips.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "pipeline": "Opus Clip AI Video Pipeline",
        "version": "1.0.0",
        "source_metadata": metadata.model_dump(),
        "total_clips_detected": len(scored_clips),
        "clips": [c.model_dump() for c in scored_clips]
    }

    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[+] Saved analysis report to: {output_path.resolve()}")
    return output_path

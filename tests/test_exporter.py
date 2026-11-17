from pathlib import Path
from clipper.transcriber import WordTiming
from clipper.exporter import generate_word_synced_ass, format_ass_timestamp
from clipper.config import TEMP_DIR, ensure_dirs


def test_ass_generation():
    ensure_dirs()
    words = [
        WordTiming(word="THIS", start=0.5, end=0.8, probability=0.99),
        WordTiming(word="IS", start=0.8, end=1.0, probability=0.99),
        WordTiming(word="VIRAL", start=1.0, end=1.5, probability=0.99),
        WordTiming(word="CONTENT", start=1.5, end=2.0, probability=0.99),
    ]

    ass_path = TEMP_DIR / "test_subs.ass"
    generate_word_synced_ass(words, clip_start=0.0, clip_end=2.5, output_ass_path=ass_path)

    assert ass_path.exists()
    content = ass_path.read_text(encoding="utf-8")
    assert "[Script Info]" in content
    assert "PlayResX: 1080" in content
    assert "Dialogue:" in content
    assert "VIRAL" in content
    print("test_ass_generation: PASSED (ASS file generated with word karaoke highlights)")


if __name__ == "__main__":
    test_ass_generation()

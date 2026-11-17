import os
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel

from clipper.config import DEFAULT_CONFIG
from clipper.audio_analyzer import extract_audio_track


class WordTiming(BaseModel):
    word: str
    start: float
    end: float
    probability: float


class SegmentTiming(BaseModel):
    id: int
    start: float
    end: float
    text: str
    words: List[WordTiming]


class TranscriptResult(BaseModel):
    full_text: str
    language: str
    segments: List[SegmentTiming]
    words: List[WordTiming]

    def get_words_in_range(self, start_time: float, end_time: float) -> List[WordTiming]:
        """Return all words that fall within [start_time, end_time]."""
        return [w for w in self.words if w.start >= start_time - 0.1 and w.end <= end_time + 0.1]

    def snap_to_sentence_boundary(self, target_time: float, mode: str = "nearest", max_delta: float = 3.5) -> float:
        """
        Snap a timestamp to the closest segment boundary (start or end)
        to prevent cutting off mid-sentence.
        mode can be 'start' (prefers start of sentence), 'end' (prefers end of sentence), or 'nearest'.
        """
        if not self.segments:
            return target_time

        candidates = []
        for seg in self.segments:
            if mode in ["start", "nearest"]:
                candidates.append((seg.start, abs(seg.start - target_time)))
            if mode in ["end", "nearest"]:
                candidates.append((seg.end, abs(seg.end - target_time)))

        if not candidates:
            return target_time

        candidates.sort(key=lambda x: x[1])
        best_time, delta = candidates[0]
        if delta <= max_delta:
            return round(best_time, 2)
        return round(target_time, 2)


def transcribe_video_or_audio(
    input_path: str,
    model_size: Optional[str] = None,
    device: str = "cpu",
    compute_type: str = "int8"
) -> TranscriptResult:
    """
    Transcribes audio track using faster-whisper with word-level timestamps.
    """
    from faster_whisper import WhisperModel

    path_obj = Path(input_path)
    if path_obj.suffix.lower() in [".mp4", ".mov", ".mkv", ".avi", ".webm"]:
        audio_path = extract_audio_track(input_path)
    else:
        audio_path = str(input_path)

    model_name = model_size or DEFAULT_CONFIG["whisper_model"]
    print(f"[*] Loading faster-whisper model '{model_name}' on {device} ({compute_type})...")
    model = WhisperModel(model_name, device=device, compute_type=compute_type)

    print(f"[*] Transcribing audio with word-level timestamps...")
    segments_raw, info = model.transcribe(
        audio_path,
        beam_size=5,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500)
    )

    detected_lang = info.language or "en"
    all_segments: List[SegmentTiming] = []
    all_words: List[WordTiming] = []
    text_chunks = []

    for idx, seg in enumerate(segments_raw):
        seg_words: List[WordTiming] = []
        if seg.words:
            for w in seg.words:
                wt = WordTiming(
                    word=w.word.strip(),
                    start=round(float(w.start), 2),
                    end=round(float(w.end), 2),
                    probability=round(float(w.probability), 2)
                )
                seg_words.append(wt)
                all_words.append(wt)

        segment_text = seg.text.strip()
        text_chunks.append(segment_text)

        all_segments.append(SegmentTiming(
            id=idx,
            start=round(float(seg.start), 2),
            end=round(float(seg.end), 2),
            text=segment_text,
            words=seg_words
        ))

    full_text = " ".join(text_chunks)
    print(f"[*] Transcription completed: {len(all_words)} words across {len(all_segments)} sentences.")

    return TranscriptResult(
        full_text=full_text,
        language=detected_lang,
        segments=all_segments,
        words=all_words
    )

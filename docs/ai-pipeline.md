# ClipForge — AI & Narrative Analysis Pipeline

## 1. Overview
The ClipForge AI pipeline transforms raw audio/video streams into ranked, timestamped, self-contained short clips. It fuses **speech transcripts**, **speaker identity**, **visual scene cuts**, and **emotional/lexical cues** into an explainable **Opus Virality Score (0–100)**.

---

## 2. Pipeline Stages

```
Raw Video File
      │
      ├─► Audio Stream ──► WhisperX (CTranslate2) ──► Word Timestamps & Text
      │                         │
      │                         ▼
      │                    pyannote.audio ──────────► Speaker Diarization Segments
      │
      ├─► Visual Stream ─► PySceneDetect ───────────► Cut Boundaries & Transitions
      │                         │
      │                         ▼
      │                    MediaPipe Face Mesh ─────► Speaker Coordinates & Tracking
      │
      ▼
Signal Fusion Engine (Sentence Clumping + Scene Anchors)
      │
      ▼
Narrative Arc Discovery (Hook 0-3s, Premise, Expansion, Payoff)
      │
      ▼
Opus Virality Scorer (0-100 & Factor Breakdown)
      │
      ▼
Ranked Clip Candidates Ready for Preview & Edit
```

---

## 3. Clip Discovery Philosophy: Complete Narrative Arcs
A common flaw in rudimentary clip generators is slicing audio blindly on fixed timers (e.g. 0:00 to 0:45) or cutting a sentence mid-phrase. ClipForge enforces strict **Narrative Completeness Rules**:

1. **Sentence Boundary Snapping**: Every clip start timestamp snaps to the beginning of a grammatical sentence, and every end timestamp snaps to the end of a concluding clause or punctuation mark (`.`, `!`, `?`).
2. **Hook Window (First 3 Seconds)**: The opening sentence must establish a premise, question, provocative assertion, or clear subject focus.
3. **Pacing and Payoff**: The clip must contain a logical flow from setup to punchline/insight within a configurable duration envelope (Default: 30 to 60 seconds).
4. **Non-Overlapping Recommendation**: Candidates must have sufficient time separation (>15s distance between clip centers) so the user is not presented with redundant slices of the same discussion.

---

## 4. The Opus Virality Score (0–100)

Every clip candidate is evaluated across 7 weighted dimensions:

| Dimension | Weight | Criteria |
| :--- | :--- | :--- |
| **1. Hook Strength** | 20% | Curiosity gap, question words (*"Why", "How", "Never", "Secret"*), immediate energy punch in seconds 0–3. |
| **2. Narrative Flow** | 20% | Coherent flow between clauses, lack of extended dead silences (>1.5s), natural speech tempo (130–170 wpm). |
| **3. Standalone Context** | 15% | Does not begin with ambiguous pronouns (*"Like he said earlier"*) or end with dangling connectors (*"And then..."*). |
| **4. Educational / Entertainment Value**| 15% | High density of concrete nouns, explanations, contrasting concepts, or vivid takeaways. |
| **5. Emotional / Energy Impact** | 15% | Audio volume dynamics, vocal pitch inflection, exclamation frequency, laughter/reaction cues. |
| **6. Ending Quality** | 10% | Decisive punchline, conclusion, or natural rhetorical pause. |
| **7. Visual Dynamics** | 5% | Presence of clear speaker face(s), scene stability, absence of prolonged black frames or occlusions. |

### Letter Grade Classification:
- **90 – 100**: Grade **A+** (Exceptional viral potential)
- **80 – 89**: Grade **A** (Strong narrative arc & engagement)
- **70 – 79**: Grade **B** (Good informational or conversational clip)
- **< 70**: Grade **C** (Supplementary candidate)

---

## 5. Dual Engine Discovery: Offline Heuristic vs. Cloud LLM

1. **Local Heuristic Engine (Default, Offline)**:
   - Uses NLP sentence tokenization, pause duration analysis from word timestamps, keyword extraction, and acoustic energy curves.
   - 100% offline, instant execution, zero cost.
2. **Optional Cloud LLM Engine (Gemini / OpenAI)**:
   - If an API key is provided, ClipForge sends only the text transcript and scene timestamps to the LLM.
   - The LLM acts as an expert video editor, returning structured JSON with candidate start/end markers, suggested viral titles, hook text, and specific reasoning for each choice.
   - Strict privacy: No audio or video pixels are ever transmitted to third-party APIs.

"""
OmniRoute / OpenAI-Compatible Universal LLM Decision Engine for ClipForge
Routes viral clip discovery, hook detection, and narrative scoring through OmniRoute
or any OpenAI-compatible API gateway (e.g., local OmniRoute on http://localhost:20128/v1,
OpenRouter, LiteLLM, or direct providers).
"""
import json
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

logger = logging.getLogger("clipforge.omniroute")

DEFAULT_OMNIROUTE_URL = "http://localhost:20128/v1"
DEFAULT_MODEL = "google/gemini-2.0-flash-001"

DISCOVERY_SYSTEM_PROMPT = """You are an elite short-form video viral strategist and lead editor at OpusClip.
Your job is to analyze full video transcripts with word-level timestamps and extract the absolute most engaging, viral, high-retention 9:16 short clips (TikTok, Instagram Reels, YouTube Shorts).

For each clip you select, you must ensure:
1. Strong Hook (First 3 seconds): Must grab attention immediately with a bold question, controversial statement, or intrigue.
2. Complete Narrative Arc: Must have a clear beginning, middle, and satisfying punchline or actionable takeaway. Never start or cut off mid-sentence.
3. High Virality Score (0-100): Calculated based on hook strength, emotional resonance, educational/entertainment value, and retention potential.
4. Exact Timestamps: start_time and end_time (in seconds) matching exact sentence boundaries. Target duration between min_duration and max_duration.

Return STRICT JSON matching this schema:
{
  "clips": [
    {
      "rank": 1,
      "title": "Short Catchy Viral Title (Under 60 chars)",
      "hook": "The exact opening line of the clip",
      "summary": "1-sentence summary of what happens",
      "start_time": 12.5,
      "end_time": 47.8,
      "duration": 35.3,
      "virality_score": 96.0,
      "letter_grade": "A+",
      "why_chosen": "Detailed explanation of why this moment will perform well on social algorithms",
      "score_breakdown": {
        "hook_strength": 98.0,
        "narrative_flow": 95.0,
        "standalone_context": 94.0,
        "educational_value": 92.0,
        "emotional_impact": 96.0,
        "ending_quality": 95.0,
        "visual_potential": 90.0
      }
    }
  ]
}
"""

class OmniRouteClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = (api_key or "").strip()
        self.base_url = (base_url or DEFAULT_OMNIROUTE_URL).rstrip("/")
        self.model = (model or DEFAULT_MODEL).strip()

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def test_connection(self) -> Dict[str, Any]:
        """Tests connectivity and key validity against the OmniRoute endpoint."""
        if not self.api_key:
            return {"success": False, "error": "No OmniRoute API key provided."}
        
        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": "Respond with 'ok' to verify connection."}
            ],
            "max_tokens": 10,
        }
        
        try:
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {
                    "success": True,
                    "endpoint": self.base_url,
                    "model": self.model,
                    "response": data.get("choices", [{}])[0].get("message", {}).get("content", ""),
                }
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            logger.error("OmniRoute connection failed HTTP %s: %s", e.code, err_body)
            return {"success": False, "status_code": e.code, "error": err_body}
        except Exception as e:
            logger.error("OmniRoute connection error: %s", e)
            return {"success": False, "error": str(e)}

    def discover_clips(
        self,
        transcript_text: str,
        segments: List[Dict[str, Any]],
        instructions: Optional[str] = None,
        min_duration: float = 25.0,
        max_duration: float = 60.0,
        target_count: int = 5,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Calls OmniRoute to identify top viral clips from the transcript.
        Returns parsed list of candidate clips or None if unconfigured/failed.
        """
        if not self.is_configured:
            logger.info("OmniRoute API key not provided; skipping LLM discovery.")
            return None

        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        
        # Prepare context payload
        context_prompt = f"""VIDEO TRANSCRIPT WITH TIMESTAMPS:
Total Duration: {segments[-1].get('end', 0) if segments else 0:.1f} seconds.

User Clipping Preferences:
- Target Clip Count: {target_count}
- Target Duration Range: {min_duration:.0f}s - {max_duration:.0f}s
- User Instructions: {instructions or 'Find the most viral, educational, and high-retention moments.'}

TRANSCRIPT SEGMENTS:
"""
        # Compress segments to fit context cleanly
        segment_lines = []
        for s in segments[:300]:  # Up to 300 segments
            speaker = f"Speaker {s.get('speaker', 0)}: " if 'speaker' in s else ""
            segment_lines.append(f"[{s.get('start', 0):.2f}s -> {s.get('end', 0):.2f}s] {speaker}{s.get('text', '').strip()}")
            
        context_prompt += "\n".join(segment_lines)
        context_prompt += "\n\nAnalyze this transcript now and return the top viral clips strictly in JSON format."

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": DISCOVERY_SYSTEM_PROMPT},
                {"role": "user", "content": context_prompt},
            ],
            "temperature": 0.4,
            "response_format": {"type": "json_object"},
        }

        try:
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=45) as resp:
                raw_response = resp.read().decode("utf-8")
                resp_json = json.loads(raw_response)
                content = resp_json.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                # Parse JSON content
                parsed = json.loads(content)
                clips = parsed.get("clips", [])
                logger.info("OmniRoute successfully discovered %d viral clips using model %s", len(clips), self.model)
                return clips
        except Exception as e:
            logger.warning("OmniRoute LLM discovery encountered an error: %s. Falling back to local engine.", e)
            return None

"""
Universal AI Decision Engine for ClipForge
Connects directly to ANY AI Provider or Local Router:
- Google Gemini (Google AI Studio Free Tier via official OpenAI-compatible endpoint)
- Groq (Ultra-Fast Free Tier - Llama 3.3 70B)
- DeepSeek (DeepSeek-V3 / R1)
- OpenAI (GPT-4o, GPT-4o-mini)
- OpenRouter (Free & Paid pooled models)
- OmniRoute (Local AI Gateway on port 20128)
- FreeLLMAPI (Local AI Gateway on port 3001)
- Ollama (100% Offline Local Inference on port 11434)
- Custom OpenAI-Compatible Endpoints
"""
import json
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional

logger = logging.getLogger("clipforge.ai_provider")

PROVIDER_PRESETS = {
    "gemini": {
        "name": "Google Gemini (Free Tier)",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "default_model": "gemini-2.0-flash",
        "key_hint": "AIzaSy... from aistudio.google.com",
    },
    "groq": {
        "name": "Groq (Fast Free Tier)",
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "key_hint": "gsk_... from console.groq.com",
    },
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "key_hint": "sk-... from platform.deepseek.com",
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "key_hint": "sk-proj-... from platform.openai.com",
    },
    "openrouter": {
        "name": "OpenRouter (Free & Paid)",
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "google/gemini-2.0-flash-001",
        "key_hint": "sk-or-v1-... from openrouter.ai",
    },
    "omniroute": {
        "name": "OmniRoute (Local Gateway)",
        "base_url": "http://localhost:20128/v1",
        "default_model": "google/gemini-2.0-flash-001",
        "key_hint": "sk-omni-... from localhost:20128",
    },
    "freellmapi": {
        "name": "FreeLLMAPI (Local Gateway)",
        "base_url": "http://localhost:3001/v1",
        "default_model": "google/gemini-2.0-flash-001",
        "key_hint": "freellmapi-... from localhost:3001",
    },
    "ollama": {
        "name": "Ollama (100% Offline Local)",
        "base_url": "http://localhost:11434/v1",
        "default_model": "llama3.2",
        "key_hint": "No API key required",
    },
    "custom": {
        "name": "Custom OpenAI Compatible",
        "base_url": "http://localhost:8000/v1",
        "default_model": "custom-model",
        "key_hint": "API Key if required",
    },
}

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

class UniversalAIClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
    ):
        self.provider = (provider or "custom").lower()
        preset = PROVIDER_PRESETS.get(self.provider, {})
        
        self.api_key = (api_key or "").strip()
        self.base_url = (base_url or preset.get("base_url") or "http://localhost:20128/v1").rstrip("/")
        self.model = (model or preset.get("default_model") or "google/gemini-2.0-flash-001").strip()

    @property
    def is_configured(self) -> bool:
        # Ollama doesn't strictly require an API key
        if self.provider == "ollama" or "11434" in self.base_url:
            return bool(self.base_url)
        return bool(self.api_key)

    def test_connection(self) -> Dict[str, Any]:
        """Tests connectivity and key validity against the configured AI provider endpoint."""
        if not self.is_configured:
            return {"success": False, "error": f"No API key provided for {self.provider}."}
        
        endpoint = f"{self.base_url}/chat/completions"
        auth_token = self.api_key if self.api_key else "ollama"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": "Respond with 'ok'"}
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
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {
                    "success": True,
                    "provider": self.provider,
                    "endpoint": self.base_url,
                    "model": self.model,
                    "response": data.get("choices", [{}])[0].get("message", {}).get("content", "ok"),
                }
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            logger.error("AI provider connection failed HTTP %s: %s", e.code, err_body)
            return {"success": False, "status_code": e.code, "error": err_body}
        except Exception as e:
            logger.error("AI provider connection error: %s", e)
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
        Calls the connected AI provider to identify top viral clips from transcript.
        Returns parsed list of candidate clips or None on failure.
        """
        if not self.is_configured:
            logger.info("AI provider not configured; skipping external LLM discovery.")
            return None

        endpoint = f"{self.base_url}/chat/completions"
        auth_token = self.api_key if self.api_key else "ollama"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        }
        
        context_prompt = f"""VIDEO TRANSCRIPT WITH TIMESTAMPS:
Total Duration: {segments[-1].get('end', 0) if segments else 0:.1f} seconds.

User Clipping Preferences:
- Target Clip Count: {target_count}
- Target Duration Range: {min_duration:.0f}s - {max_duration:.0f}s
- User Instructions: {instructions or 'Find the most viral, educational, and high-retention moments.'}

TRANSCRIPT SEGMENTS:
"""
        segment_lines = []
        for s in segments[:300]:
            speaker = f"Speaker {s.get('speaker', 0)}: " if 'speaker' in s else ""
            segment_lines.append(f"[{s.get('start', 0):.2f}s -> {s.get('end', 0):.2f}s] {speaker}{s.get('text', '').strip()}")
            
        context_prompt += "\n".join(segment_lines)
        context_prompt += "\n\nAnalyze this transcript now and return the top viral clips strictly in JSON format matching the schema."

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
            with urllib.request.urlopen(req, timeout=50) as resp:
                raw_response = resp.read().decode("utf-8")
                resp_json = json.loads(raw_response)
                content = resp_json.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                parsed = json.loads(content)
                clips = parsed.get("clips", [])
                logger.info("AI Provider (%s, %s) discovered %d viral clips", self.provider, self.model, len(clips))
                return clips
        except Exception as e:
            logger.warning("AI provider discovery error (%s): %s. Falling back to local offline heuristics.", self.provider, e)
            return None

# Backward compatibility alias
OmniRouteClient = UniversalAIClient

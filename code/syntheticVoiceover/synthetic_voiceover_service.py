from __future__ import annotations

import html
import json
import os
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Match

import boto3
from botocore.exceptions import BotoCoreError, ClientError


@dataclass(frozen=True)
class VoiceoverAttempt:
    index: int
    label: str
    prompt: str
    temperature: float
    top_p: float
    force: bool
    notes: str


class SyntheticVoiceoverService:
    """Reusable orchestration layer for SSML generation and neural speech synthesis."""

    def __init__(
        self,
        *,
        model_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        bedrock_region: Optional[str] = None,
        polly_region: Optional[str] = None,
        max_tokens: int = 900,
        temperature: float = 0.6,
        top_p: float = 0.9,
        bedrock_client: Optional[Any] = None,
        polly_client: Optional[Any] = None,
    ) -> None:
        aws_region = os.environ.get("AWS_REGION")
        if not aws_region:
            raise RuntimeError("Set AWS_REGION before initializing SyntheticVoiceoverService")
        self.bedrock_region = bedrock_region or os.environ.get("BEDROCK_REGION", aws_region)
        self.polly_region = polly_region or os.environ.get("POLLY_REGION", self.bedrock_region)
        self.model_id = model_id or os.environ.get("VOICEOVER_MODEL_ID", "meta.llama3-70b-instruct-v1:0")
        self.system_prompt = system_prompt or os.environ.get(
            "VOICEOVER_SYSTEM_PROMPT",
            (
                "You are an expert voice director crafting expressive narration scripts in SSML. "
                "Produce vivid, engaging speech that sounds natural, with pacing shifts, pausing, and emphasis. "
                "Ensure the response is wrapped in <speak> tags and leverages <break>, <emphasis>, <prosody>, "
                "and other supported neural speech effects where appropriate."
            ),
        )
        self.max_tokens = max_tokens
        self.default_temperature = temperature
        self.default_top_p = top_p

        self.bedrock = bedrock_client or boto3.client("bedrock-runtime", region_name=self.bedrock_region)
        self.polly = polly_client or boto3.client("polly", region_name=self.polly_region)

        self._voice_cache: Optional[List[Dict[str, Any]]] = None
        self._voice_engine_cache: Dict[str, List[str]] = {}

    # ------------------------------------------------------------------
    # Prompt + generation helpers
    # ------------------------------------------------------------------

    def _compose_prompt(
        self,
        prompt: str,
        *,
        persona: Optional[str] = None,
        language: Optional[str] = None,
        force_speech: bool = False,
    ) -> str:
        instructions = [self.system_prompt.strip()]
        instructions.append(
            "Return only valid SSML wrapped in <speak>...</speak> with no commentary or explanations outside the tags."
        )
        instructions.append(
            "Do not repeat the user's prompt verbatim. Transform the ideas into an original spoken narration with multiple sentences."
        )
        if persona:
            instructions.append(f"Adopt the following tone guidance: {persona.strip()}")
        if language:
            instructions.append(f"Respond in {language.strip()} unless the user specifies otherwise.")
        if force_speech:
            instructions.append("If you are unsure, produce your best effort narration. Do not leave the response empty.")

        system_block = " ".join(instructions)
        clean_prompt = prompt.strip()
        return (
            "<s>[INST] <<SYS>>"
            f" {system_block} "
            "<</SYS>> "
            f"{clean_prompt}"
        model_id = (self.model_id or "").lower()
        if model_id.startswith("meta.llama3"):
            return (
                "<|begin_of_text|>"
                "<|start_header_id|>system<|end_header_id|>\n"
                f"{system_block}\n"
                "<|eot_id|>"
                "<|start_header_id|>user<|end_header_id|>\n"
                f"{clean_prompt}\n"
                "<|eot_id|>"
                "<|start_header_id|>assistant<|end_header_id|>\n"
            )

        return (
            "<s>[INST] <<SYS>>\n"
            f"{system_block}\n"
            "<</SYS>>\n\n"
            f"{clean_prompt}\n"
            "[/INST]"
        )
        def _collect_from_content(content: Any) -> str:
            if isinstance(content, list):
                parts: List[str] = []
                for block in content:
                    if isinstance(block, dict):
                        if "text" in block:
                            parts.append(str(block.get("text", "")))
                        elif block.get("type") == "tool_result":
                            parts.append(str(block.get("result", "")))
                    elif isinstance(block, str):
                        parts.append(block)
                return "".join(parts)
            if isinstance(content, dict):
                return _collect_from_content(content.get("content"))
            if isinstance(content, str):
                return content
            return ""

        generation = response_body.get("generation")
        if generation:
            return str(generation)

        generations = response_body.get("generations")
        if generations:
            collected = "".join(
                str(item.get("text", "")) for item in generations if isinstance(item, dict)
            )
            if collected:
                return collected

        outputs = response_body.get("outputs")
        if outputs:
            parts: List[str] = []
            for item in outputs:
                if isinstance(item, dict):
                    if "text" in item:
                        parts.append(str(item.get("text", "")))
                    else:
                        parts.append(_collect_from_content(item.get("content")))
                elif isinstance(item, str):
                    parts.append(item)
            combined = "".join(parts)
            if combined:
                return combined

        content = response_body.get("content")
        if content:
            collected = _collect_from_content(content)
            if collected:
                return collected

        message = response_body.get("message")
        if isinstance(message, dict):
            candidate = _collect_from_content(message.get("content"))
            if candidate:
                return candidate

        messages = response_body.get("messages")
        if isinstance(messages, list):
            for msg in reversed(messages):
                if isinstance(msg, dict) and msg.get("role") == "assistant":
                    candidate = _collect_from_content(msg.get("content"))
                    if candidate:
                        return candidate

        return ""

    def _invoke_bedrock(self, body: Dict[str, Any]) -> Dict[str, Any]:
        response = self.bedrock.invoke_model(
            modelId=self.model_id,
            body=json.dumps(body),
            accept="application/json",
            contentType="application/json",
        )
        payload = response["body"].read()
        return json.loads(payload)

    @staticmethod
    def _fallback_ssml(prompt: str) -> str:
        cleaned = re.sub(r"\s+", " ", (prompt or "").strip())
        if not cleaned:
            cleaned = "our story today"

        sentences = re.split(r"(?<=[.!?])\s+", cleaned)
        focus_sentence = sentences[0] if sentences and sentences[0].strip() else cleaned
        focus_phrase = html.escape(focus_sentence.strip()[:180])

        bullet_candidates = [part.strip() for part in re.split(r"[\n\r•\-]+", cleaned) if part.strip()]
        bullet_phrases = [html.escape(candidate[:160]) for candidate in bullet_candidates[:3]]

        intro = (
            f"<p><s>Welcome! Let's explore {focus_phrase} from a fresh perspective.</s>"
            "<break time=\"400ms\"/></p>"
        )
        if bullet_phrases:
            body_sentences = [
                f"<s>Key moment {idx}: {phrase}. We'll bring this idea to life with vivid storytelling.</s>"
                for idx, phrase in enumerate(bullet_phrases, start=1)
            ]
        else:
            body_sentences = [
                "<s>We'll unfold the main ideas step by step, highlighting the emotions and motivations along the way.</s>"
            ]
        body = "<p>" + "<break time=\"250ms\"/>".join(body_sentences) + "</p>"
        outro = (
            "<p><s>Stay tuned as we guide you through the narrative, keeping the energy dynamic and engaging.</s>"
            "<break time=\"350ms\"/><s>Thanks for listening.</s></p>"
        )
        return f"<speak>{intro}{body}{outro}</speak>"

    @staticmethod
    def _strip_ssml_tags(ssml: str) -> str:
        no_tags = re.sub(r"<[^>]+>", " ", ssml)
        return re.sub(r"\s+", " ", no_tags).strip()

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        cleaned = re.sub(r"[^\w\s]", " ", text).lower()
        return [token for token in cleaned.split() if token]

    @classmethod
    def _token_overlap(cls, prompt_tokens: List[str], ssml_tokens: List[str]) -> float:
        if not prompt_tokens or not ssml_tokens:
            return 0.0
        prompt_counter = Counter(prompt_tokens)
        ssml_counter = Counter(ssml_tokens)
        overlap = sum((prompt_counter & ssml_counter).values())
        return overlap / max(1, len(prompt_tokens))

    def _looks_like_prompt_echo(self, prompt: str, ssml: str) -> bool:
        if not prompt or not ssml:
            return False
        prompt_clean = re.sub(r"\s+", " ", prompt).strip().lower()
        ssml_clean = self._strip_ssml_tags(ssml).lower()
        if not prompt_clean or not ssml_clean:
            return False
        if prompt_clean == ssml_clean:
            return True

        if ssml_clean.startswith(prompt_clean):
            trailing = ssml_clean[len(prompt_clean):].strip()
            if not trailing or len(trailing.split()) <= 3:
                return True

        similarity = 0.0
        try:
            from difflib import SequenceMatcher

            similarity = SequenceMatcher(None, prompt_clean, ssml_clean).ratio()
        except Exception:
            similarity = 0.0

        prompt_tokens = self._tokenize(prompt_clean)
        ssml_tokens = self._tokenize(ssml_clean)
        overlap_ratio = self._token_overlap(prompt_tokens, ssml_tokens)

        length_ratio = 1.0
        if prompt_tokens and ssml_tokens:
            length_ratio = min(len(prompt_tokens), len(ssml_tokens)) / max(len(prompt_tokens), len(ssml_tokens))

        token_ratio = len(ssml_tokens) / max(1, len(prompt_tokens)) if prompt_tokens else 0.0

        if similarity >= 0.995 and length_ratio >= 0.97:
            return True
        if overlap_ratio >= 0.98 and length_ratio >= 0.95:
            return True
        if overlap_ratio >= 0.95 and length_ratio >= 0.9 and token_ratio <= 1.08:
            return True
        if overlap_ratio >= 0.96 and len(ssml_tokens) <= len(prompt_tokens) + 2:
            return True
        return False

    def _build_attempt_plan(
        self,
        user_prompt: str,
        persona: Optional[str],
        language: Optional[str],
        base_temperature: float,
        base_top_p: float,
        max_attempts: int,
    ) -> List[VoiceoverAttempt]:
        plan: List[VoiceoverAttempt] = []
        for attempt_index in range(max_attempts):
            if attempt_index == 0:
                plan.append(
                    VoiceoverAttempt(
                        index=attempt_index + 1,
                        label="primary",
                        prompt=self._compose_prompt(
                            user_prompt,
                            persona=persona,
                            language=language,
                            force_speech=False,
                        ),
                        temperature=base_temperature,
                        top_p=base_top_p,
                        force=False,
                        notes="initial generation",
                    )
                )
                continue

            if attempt_index == 1:
                prompt_text = (
                    f"{user_prompt}\n\n"
                    "Transform this into a fresh narration script with original phrasing, using expressive SSML tags. "
                    "Deliver 4-6 sentences split across paragraphs with varied pacing cues."
                )
                plan.append(
                    VoiceoverAttempt(
                        index=attempt_index + 1,
                        label="retry_force_speech",
                        prompt=self._compose_prompt(
                            prompt_text,
                            persona=persona,
                            language=language,
                            force_speech=True,
                        ),
                        temperature=min(1.0, base_temperature + 0.25),
                        top_p=min(0.99, base_top_p + 0.06),
                        force=True,
                        notes="first retry with force_speech",
                    )
                )
                continue

            if attempt_index == 2:
                prompt_text = (
                    f"{user_prompt}\n\n"
                    "Craft a vivid voiceover with an opening hook, middle build, and closing call-to-action. "
                    "Incorporate <p> sections, <break>, and <emphasis> tags. Avoid copying the input sentences directly."
                )
                plan.append(
                    VoiceoverAttempt(
                        index=attempt_index + 1,
                        label="retry_story_arc",
                        prompt=self._compose_prompt(
                            prompt_text,
                            persona=persona,
                            language=language,
                            force_speech=True,
                        ),
                        temperature=min(1.0, base_temperature + 0.35),
                        top_p=min(0.995, base_top_p + 0.08),
                        force=True,
                        notes="second retry with structured guidance",
                    )
                )
                continue

            escalation = attempt_index - 2
            prompt_text = (
                f"{user_prompt}\n\n"
                f"Attempt {attempt_index + 1}: Produce an entirely new narration with a cinematic arc, vivid sensory language,"
                " and varied pacing. Do not mirror the source sentences—paraphrase heavily and introduce fresh connective tissue.\n"
                "Use multiple <p> blocks, layer in <prosody rate=\"slow\"> and <emphasis> for key beats, and ensure at least five"
                " sentences total. Close with a motivating call-to-action."
            )
            plan.append(
                VoiceoverAttempt(
                    index=attempt_index + 1,
                    label=f"retry_escalation_{attempt_index + 1}",
                    prompt=self._compose_prompt(
                        prompt_text,
                        persona=persona,
                        language=language,
                        force_speech=True,
                    ),
                    temperature=min(1.0, base_temperature + 0.25 + 0.1 * escalation),
                    top_p=min(0.996, base_top_p + 0.06 + 0.02 * escalation),
                    force=True,
                    notes=f"escalation attempt {attempt_index + 1}",
                )
            )
        return plan

    # ------------------------------------------------------------------
    # SSML generation
    # ------------------------------------------------------------------

    def generate_ssml(
        self,
        user_prompt: str,
        *,
        persona: Optional[str] = None,
        language: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_attempts: Optional[int] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        if not user_prompt.strip():
            raise ValueError("Prompt is required")

        base_temperature = temperature if temperature is not None else self.default_temperature
        base_top_p = top_p if top_p is not None else self.default_top_p
        attempt_limit = max(4, max_attempts or int(os.environ.get("VOICEOVER_MAX_ATTEMPTS", "7")))

        attempt_plan = self._build_attempt_plan(
            user_prompt,
            persona,
            language,
            base_temperature,
            base_top_p,
            attempt_limit,
        )

        generation = ""
        response_body: Optional[Dict[str, Any]] = None
        attempt_logs: List[Dict[str, Any]] = []

        for attempt in attempt_plan:
            body = {
                "prompt": attempt.prompt,
                "max_gen_len": self.max_tokens,
                "temperature": attempt.temperature,
                "top_p": attempt.top_p,
            }
            try:
                candidate_response = self._invoke_bedrock(body)
            except (BotoCoreError, ClientError) as aws_error:
                attempt_logs.append(
                    {
                        "attempt": attempt.index,
                        "label": attempt.label,
                        "status": "error",
                        "error": f"Model runtime request failed: {aws_error}",
                    }
                )
                continue
            except Exception as runtime_error:
                attempt_logs.append(
                    {
                        "attempt": attempt.index,
                        "label": attempt.label,
                        "status": "error",
                        "error": f"Unexpected language runtime error: {runtime_error}",
                    }
                )
                continue

            raw_generation = self._extract_generation_text(candidate_response).strip()
            needs_retry, retry_reason = self._should_retry(user_prompt, raw_generation)
            attempt_logs.append(
                {
                    "attempt": attempt.index,
                    "label": attempt.label,
                    "status": "retry" if needs_retry else "ok",
                    "reason": retry_reason,
                    "notes": attempt.notes,
                    "generation_length": len(raw_generation),
                    "temperature": attempt.temperature,
                    "top_p": attempt.top_p,
                }
            )

            if raw_generation and not needs_retry:
                generation = raw_generation
                response_body = candidate_response
                break

            try:
                serialized_body = json.dumps(candidate_response, ensure_ascii=False)
            except Exception:
                serialized_body = str(candidate_response)
            attempt_logs[-1]["response"] = serialized_body[:1600]

        if not generation:
            fallback_ssml = self._fallback_ssml(user_prompt)
            reason_label = next(
                (log.get("reason") for log in reversed(attempt_logs) if log.get("reason")),
                "exhausted_attempts",
            )
            metadata = {
                "prompt_tokens": (response_body or {}).get("prompt_token_count"),
                "generation_tokens": (response_body or {}).get("generation_token_count"),
                "fallback": True,
                "fallback_template": True,
                "fallback_reason": (
                    "Model response was empty or simply echoed the prompt."
                    if reason_label in {"empty", "echo"}
                    else f"Model response failed validity check ({reason_label})."
                ),
                "attempt_count": len(attempt_logs),
                "attempts": attempt_logs,
            }
            return fallback_ssml, metadata

        metadata = {
            "prompt_tokens": (response_body or {}).get("prompt_token_count"),
            "generation_tokens": (response_body or {}).get("generation_token_count"),
            "attempt_count": len(attempt_logs),
            "attempts": attempt_logs,
        }
        return generation, metadata

    def _should_retry(self, user_prompt: str, ssml: str) -> Tuple[bool, Optional[str]]:
        if not ssml:
            return True, "empty"
        if self._looks_like_prompt_echo(user_prompt, ssml):
            return True, "echo"
        return False, None

    # ------------------------------------------------------------------
    # Polly helpers
    # ------------------------------------------------------------------

    def _list_neural_voices(self) -> List[Dict[str, Any]]:
        if self._voice_cache is not None:
            return self._voice_cache

        paginator = self.polly.get_paginator("describe_voices")
        voices: List[Dict[str, Any]] = []
        for page in paginator.paginate(Engine="neural"):
            for voice in page.get("Voices", []):
                if "neural" in [engine.lower() for engine in voice.get("SupportedEngines", [])]:
                    voices.append(
                        {
                            "id": voice.get("Id"),
                            "name": voice.get("Name"),
                            "language_code": voice.get("LanguageCode"),
                            "language_name": voice.get("LanguageName"),
                            "gender": voice.get("Gender"),
                            "style_list": voice.get("AdditionalLanguageCodes", []),
                        }
                    )
        voices.sort(key=lambda v: (v.get("language_name", ""), v.get("name", "")))
        self._voice_cache = voices
        return voices

    def list_voices(self) -> List[Dict[str, Any]]:
        return self._list_neural_voices()

    def _voice_supported_engines(self, voice_id: str) -> List[str]:
        if voice_id in self._voice_engine_cache:
            return self._voice_engine_cache[voice_id]
        try:
            response = self.polly.describe_voices(VoiceId=voice_id)
        except (BotoCoreError, ClientError):
            engines: List[str] = []
        else:
            voices = response.get("Voices", [])
            engines = [engine.lower() for engine in (voices[0].get("SupportedEngines", []) if voices else [])]
        self._voice_engine_cache[voice_id] = engines
        return engines

    @staticmethod
    def _sanitize_ssml_for_neural(ssml: str) -> str:
        sanitized = re.sub(r"<\s*/?amazon:(?:effect|domain|auto-breaths)[^>]*>", "", ssml, flags=re.IGNORECASE)
        sanitized = re.sub(r'rate="x-(fast|slow)"', r'rate="\1"', sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r'volume="x-(loud|soft)"', r'volume="\1"', sanitized, flags=re.IGNORECASE)

        def _sanitize_rate_decimal(match: Match[str]) -> str:
            value = match.group(1)
            try:
                numeric = float(value)
            except ValueError:
                return match.group(0)
            if numeric <= 0:
                return 'rate="100%"'
            if numeric < 10:
                percent = int(round(numeric * 100))
                return f'rate="{percent}%"'
            return match.group(0)

        sanitized = re.sub(r'rate="([0-9]*\.?[0-9]+)"', _sanitize_rate_decimal, sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r"<!--.*?-->", "", sanitized, flags=re.DOTALL)
        return sanitized

    def _normalize_ssml(self, ssml: str) -> Tuple[str, bool, List[str]]:
        notes: List[str] = []
        original = (ssml or "").strip()
        candidate = original

        if not candidate:
            fallback = "<speak></speak>"
            notes.append("empty_input")
            return fallback, True, notes

        new_candidate = re.sub(r"<\?xml[^>]*>", "", candidate, flags=re.IGNORECASE)
        new_candidate = re.sub(r"<!DOCTYPE[^>]*>", "", new_candidate, flags=re.IGNORECASE)
        if new_candidate != candidate:
            notes.append("removed_xml_header")
            candidate = new_candidate.strip()

        speak_match = re.search(r"<\s*speak\b[^>]*>(.*)</\s*speak\s*>", candidate, flags=re.IGNORECASE | re.DOTALL)
        if speak_match:
            inner = speak_match.group(1)
            leading = candidate[: speak_match.start()].strip()
            trailing = candidate[speak_match.end() :].strip()
            if leading or trailing:
                notes.append("trimmed_extra_wrappers")
            candidate = f"<speak>{inner}</speak>"
        else:
            notes.append("wrapped_in_speak")
            candidate = f"<speak>{candidate}</speak>"

        def _convert_break(match: Match[str]) -> str:
            time_value = match.group(1)
            suffix = match.group(2).lower()
            if suffix == "ms":
                return match.group(0)
            try:
                seconds = float(time_value)
                millis = int(round(seconds * 1000))
                return f'time="{millis}ms"'
            except ValueError:
                return match.group(0)

        converted_candidate = re.sub(
            r'time="([0-9]*\.?[0-9]+)(s|ms)"', _convert_break, candidate, flags=re.IGNORECASE
        )
        if converted_candidate != candidate:
            notes.append("normalized_break_time")
            candidate = converted_candidate

        def _convert_rate(match: Match[str]) -> str:
            value = match.group(1)
            try:
                numeric = float(value)
                if 0 < numeric < 10:
                    percent = int(round(numeric * 100))
                    return f'rate="{percent}%"'
            except ValueError:
                pass
            return match.group(0)

        converted_rate = re.sub(r'rate="([0-9]*\.?[0-9]+)"', _convert_rate, candidate, flags=re.IGNORECASE)
        if converted_rate != candidate:
            notes.append("normalized_rate_decimal")
            candidate = converted_rate

        escaped_candidate = re.sub(r"&(?![a-zA-Z]+;|#\d+;|#x[0-9A-Fa-f]+;)", "&amp;", candidate)
        if escaped_candidate != candidate:
            notes.append("escaped_ampersands")
            candidate = escaped_candidate

        inner_text = self._strip_ssml_tags(candidate)
        if not inner_text:
            notes.append("empty_after_strip")
            candidate = "<speak></speak>"

        try:
            from xml.etree import ElementTree as ET

            ET.fromstring(candidate)
        except ET.ParseError:
            safe_text = html.escape(inner_text or "Narration coming up.")
            candidate = f"<speak>{safe_text}</speak>"
            notes.append("parse_error_fallback")

        was_modified = candidate != original
        return candidate, was_modified, notes

    AUDIO_MIME = {
        "mp3": "audio/mpeg",
        "ogg_vorbis": "audio/ogg",
        "pcm": "audio/wav",
    }

    def synthesize_speech(
        self,
        *,
        voice_id: str,
        ssml: str,
        output_format: str = "mp3",
        sample_rate: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], bytes]:
        if not voice_id:
            raise ValueError("voiceId is required")
        if not ssml:
            raise ValueError("ssml content is required")
        fmt = output_format.lower()
        if fmt not in self.AUDIO_MIME:
            raise ValueError(f"Unsupported output format '{output_format}'")

        normalized_ssml, ssml_normalized, normalization_notes = self._normalize_ssml(ssml)
        original_plaintext = self._strip_ssml_tags(ssml)

        request_args: Dict[str, Any] = {
            "VoiceId": voice_id,
            "Text": normalized_ssml,
            "TextType": "ssml",
            "Engine": "neural",
            "OutputFormat": fmt,
        }
        if sample_rate:
            request_args["SampleRate"] = str(sample_rate)

        engine_used = request_args["Engine"]
        sanitized_used = False
        sanitized_ssml: Optional[str] = None
        plain_retry_used = False
        plain_retry_ssml: Optional[str] = None
        text_fallback_used = False
        text_fallback_text: Optional[str] = None
        safe_minimal_used = False
        safe_minimal_ssml: Optional[str] = None
        safe_minimal_engine: Optional[str] = None
        safe_minimal_mode: Optional[str] = None
        response: Optional[Dict[str, Any]] = None
        error_message: Optional[str] = None

        audio_bytes: Optional[bytes] = None

        def _try_safe_minimal(engine_sequence: List[str]) -> bool:
            nonlocal response, engine_used, normalized_ssml, safe_minimal_used
            nonlocal safe_minimal_ssml, safe_minimal_engine, safe_minimal_mode
            nonlocal error_message, text_fallback_used, text_fallback_text, audio_bytes

            safe_candidate_text = (
                original_plaintext or self._strip_ssml_tags(normalized_ssml) or "Narration coming up."
            )
            safe_candidate = f"<speak><s>{html.escape(safe_candidate_text[:320])}</s></speak>"

            attempted = False
            for engine_option in engine_sequence:
                safe_request = dict(request_args)
                safe_request["Engine"] = engine_option
                safe_request["Text"] = safe_candidate
                safe_request["TextType"] = "ssml"
                try:
                    response = self.polly.synthesize_speech(**safe_request)
                    engine_used = engine_option
                    normalized_ssml = safe_candidate
                    safe_minimal_used = True
                    safe_minimal_ssml = safe_candidate
                    safe_minimal_engine = engine_option
                    safe_minimal_mode = "ssml"
                    error_message = None
                    audio_bytes = response.get("AudioStream").read() if response else None
                    return audio_bytes is not None
                except (BotoCoreError, ClientError):
                    attempted = True
                    continue

            if attempted and not safe_minimal_used:
                error_message = error_message or "Safe minimal SSML attempt failed."

            for engine_option in engine_sequence:
                text_request = dict(request_args)
                text_request["Engine"] = engine_option
                text_request["Text"] = safe_candidate_text
                text_request["TextType"] = "text"
                try:
                    response = self.polly.synthesize_speech(**text_request)
                    engine_used = engine_option
                    safe_minimal_used = True
                    safe_minimal_ssml = safe_candidate
                    safe_minimal_engine = engine_option
                    safe_minimal_mode = "text"
                    text_fallback_used = True
                    text_fallback_text = safe_candidate_text
                    normalized_ssml = safe_candidate
                    audio_bytes = response.get("AudioStream").read() if response else None
                    error_message = None
                    return audio_bytes is not None
                except (BotoCoreError, ClientError):
                    continue

            return False

        try:
            response = self.polly.synthesize_speech(**request_args)
            audio_bytes = response.get("AudioStream").read() if response else None
        except (BotoCoreError, ClientError) as aws_error:
            error_message = str(aws_error)
            error_code = None
            if isinstance(aws_error, ClientError):
                error_code = aws_error.response.get("Error", {}).get("Code")
                error_message = aws_error.response.get("Error", {}).get("Message", error_message)

            if error_code == "InvalidSsmlException" and "unsupported neural feature" in error_message.lower():
                sanitized_candidate = self._sanitize_ssml_for_neural(normalized_ssml)
                if sanitized_candidate != normalized_ssml:
                    try:
                        request_args["Text"] = sanitized_candidate
                        response = self.polly.synthesize_speech(**request_args)
                        sanitized_used = True
                        sanitized_ssml = sanitized_candidate
                        audio_bytes = response.get("AudioStream").read() if response else None
                    except (BotoCoreError, ClientError) as retry_error:
                        request_args["Text"] = normalized_ssml
                        if isinstance(retry_error, ClientError):
                            error_message = retry_error.response.get("Error", {}).get("Message", str(retry_error))
                        else:
                            error_message = str(retry_error)
                    else:
                        error_message = None

                if audio_bytes is None:
                    supported_engines = self._voice_supported_engines(voice_id)
                    if "standard" in supported_engines:
                        fallback_args = dict(request_args)
                        fallback_args["Engine"] = "standard"
                        engine_used = "standard"
                        try:
                            response = self.polly.synthesize_speech(**fallback_args)
                            audio_bytes = response.get("AudioStream").read() if response else None
                        except (BotoCoreError, ClientError) as fallback_error:
                            fallback_msg = (
                                fallback_error.response.get("Error", {}).get("Message", str(fallback_error))
                                if isinstance(fallback_error, ClientError)
                                else str(fallback_error)
                            )
                            engine_sequence = ["neural", "standard"]
                            if not _try_safe_minimal(engine_sequence):
                                raise RuntimeError(
                                    "Voice synthesis failed: neural engine rejected SSML and standard fallback "
                                    f"also failed ({fallback_msg})"
                                ) from fallback_error
                        else:
                            error_message = None
                    else:
                        detail = (
                            "Voice does not support the standard engine and neural synthesis rejected SSML. "
                            "Try simplifying SSML effects or choose another voice."
                        )
                        if error_message:
                            detail = f"{detail} (Last error: {error_message})"
                        engine_sequence = [request_args.get("Engine", "neural")]
                        if not _try_safe_minimal(engine_sequence):
                            raise RuntimeError(detail)
            elif error_code == "InvalidSsmlException":
                sanitized_candidate = self._sanitize_ssml_for_neural(normalized_ssml)
                if sanitized_candidate != normalized_ssml:
                    try:
                        request_args["Text"] = sanitized_candidate
                        response = self.polly.synthesize_speech(**request_args)
                        sanitized_used = True
                        sanitized_ssml = sanitized_candidate
                        normalized_ssml = sanitized_candidate
                        audio_bytes = response.get("AudioStream").read() if response else None
                        error_message = None
                    except (BotoCoreError, ClientError) as retry_error:
                        request_args["Text"] = normalized_ssml
                        error_message = (
                            retry_error.response.get("Error", {}).get("Message", str(retry_error))
                            if isinstance(retry_error, ClientError)
                            else str(retry_error)
                        )

                if audio_bytes is None and error_message:
                    plain_text = self._strip_ssml_tags(normalized_ssml) or "Narration coming up."
                    plain_candidate = f"<speak>{html.escape(plain_text)}</speak>"
                    normalization_notes.append("plain_ssml_retry")
                    try:
                        request_args["Text"] = plain_candidate
                        response = self.polly.synthesize_speech(**request_args)
                        plain_retry_used = True
                        plain_retry_ssml = plain_candidate
                        normalized_ssml = plain_candidate
                        audio_bytes = response.get("AudioStream").read() if response else None
                        error_message = None
                    except (BotoCoreError, ClientError) as plain_error:
                        request_args["Text"] = normalized_ssml
                        plain_text_payload = (
                            self._strip_ssml_tags(normalized_ssml) or "Narration coming up."
                        )
                        text_args = dict(request_args)
                        text_args["Text"] = plain_text_payload
                        text_args["TextType"] = "text"
                        try:
                            response = self.polly.synthesize_speech(**text_args)
                            normalized_ssml = plain_candidate
                            audio_bytes = response.get("AudioStream").read() if response else None
                            text_fallback_used = True
                            text_fallback_text = plain_text_payload
                            error_message = None
                        except (BotoCoreError, ClientError) as text_error:
                            engine_sequence = [request_args.get("Engine", "neural")]
                            if not _try_safe_minimal(engine_sequence):
                                raise RuntimeError(
                                    "Voice synthesis failed: neural engine rejected SSML even after sanitization"
                                ) from text_error
            else:
                engine_sequence = [request_args.get("Engine", "neural")]
                if not _try_safe_minimal(engine_sequence):
                    raise RuntimeError(f"Voice synthesis failed: {error_message}") from aws_error
        except Exception:
            raise

        if response is None or audio_bytes is None:
            engine_sequence = [request_args.get("Engine", "neural"), "standard"]
            if not _try_safe_minimal(engine_sequence):
                raise RuntimeError("Failed to synthesize speech; no audio stream received")

        result_metadata = {
            "engine": engine_used,
            "normalized": ssml_normalized,
            "normalization_notes": normalization_notes,
            "sanitized": sanitized_used,
            "sanitized_ssml": sanitized_ssml,
            "plain_retry": plain_retry_used,
            "plain_retry_ssml": plain_retry_ssml,
            "text_fallback": text_fallback_used,
            "text_fallback_text": text_fallback_text,
            "safe_minimal": safe_minimal_used,
            "safe_minimal_ssml": safe_minimal_ssml,
            "safe_minimal_engine": safe_minimal_engine,
            "safe_minimal_mode": safe_minimal_mode,
            "content_type": self.AUDIO_MIME[fmt],
        }
        return result_metadata, audio_bytes

    def generate_voiceover(
        self,
        *,
        prompt: str,
        persona: Optional[str] = None,
        language: Optional[str] = None,
        voice_id: str,
        output_format: str = "mp3",
        sample_rate: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
    ) -> Dict[str, Any]:
        ssml, ssml_meta = self.generate_ssml(
            prompt,
            persona=persona,
            language=language,
            temperature=temperature,
            top_p=top_p,
        )
        audio_meta, audio_bytes = self.synthesize_speech(
            voice_id=voice_id,
            ssml=ssml,
            output_format=output_format,
            sample_rate=sample_rate,
        )
        return {
            "ssml": ssml,
            "ssml_meta": ssml_meta,
            "audio_meta": audio_meta,
            "audio_bytes": audio_bytes,
        }

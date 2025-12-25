from __future__ import annotations

import os
import json
import base64
import re
import html
from functools import lru_cache
from typing import Any, Dict, Tuple
from xml.etree import ElementTree as ET

from flask import Flask, jsonify, request
from flask_cors import CORS
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from botocore.config import Config
from difflib import SequenceMatcher
from collections import Counter
from shared.env_loader import load_environment

load_environment()

app = Flask(__name__)
CORS(app)

# Configure for large file uploads and long processing
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

DEFAULT_AWS_REGION = os.environ.get("AWS_REGION")
if not DEFAULT_AWS_REGION:
    raise RuntimeError("Set AWS_REGION before starting synthetic voiceover service")

BEDROCK_REGION = os.environ.get("BEDROCK_REGION", DEFAULT_AWS_REGION)
POLLY_REGION = os.environ.get("POLLY_REGION", BEDROCK_REGION)
MODEL_ID = os.environ.get("VOICEOVER_MODEL_ID", "meta.llama3-70b-instruct-v1:0")
SYSTEM_PROMPT = os.environ.get(
    "VOICEOVER_SYSTEM_PROMPT",
    (
        "You are an expert voice director crafting expressive narration scripts in SSML. "
        "Produce vivid, engaging speech that sounds natural, with pacing shifts, pausing, and emphasis. "
        "Ensure the response is wrapped in <speak> tags and leverages <break>, <emphasis>, <prosody>, and other supported neural speech effects where appropriate."
    )
)
DEFAULT_MAX_TOKENS = int(os.environ.get("VOICEOVER_MAX_TOKENS", "900"))
DEFAULT_TEMPERATURE = float(os.environ.get("VOICEOVER_TEMPERATURE", "0.6"))
DEFAULT_TOP_P = float(os.environ.get("VOICEOVER_TOP_P", "0.9"))

# FFmpeg paths - check common locations
FFMPEG_PATH = os.environ.get("FFMPEG_PATH")
if not FFMPEG_PATH:
    for path in ["/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg", "/usr/bin/ffmpeg", "ffmpeg"]:
        try:
            import subprocess
            result = subprocess.run([path, "-version"], capture_output=True, timeout=2)
            if result.returncode == 0:
                FFMPEG_PATH = path
                break
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    if not FFMPEG_PATH:
        FFMPEG_PATH = "ffmpeg"  # fallback

FFPROBE_PATH = FFMPEG_PATH.replace("ffmpeg", "ffprobe") if "ffmpeg" in FFMPEG_PATH else "ffprobe"

bedrock_runtime = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)
polly = boto3.client("polly", region_name=POLLY_REGION)
translate = boto3.client("translate", region_name=DEFAULT_AWS_REGION)


def _normalise_bucket_region(region: str | None) -> str:
    """Convert S3 location constraint values into usable region names."""
    if not region:
        return "us-east-1"
    if region == "EU":  # legacy response for eu-west-1
        return "eu-west-1"
    return region


def _detect_bucket_region(bucket_name: str) -> str | None:
    """Best-effort detection of an S3 bucket's region."""
    try:
        probe_client = boto3.client("s3", region_name=DEFAULT_AWS_REGION)
        response = probe_client.get_bucket_location(Bucket=bucket_name)
        detected = _normalise_bucket_region(response.get("LocationConstraint"))
        return detected
    except Exception as exc:  # pragma: no cover - network failures tolerated
        app.logger.warning(
            "Unable to determine region for bucket %s: %s", bucket_name, exc
        )
        return None


def _resolve_transcribe_region(bucket_region: str | None) -> str:
    """Pick the AWS region to use for Transcribe jobs."""
    override = os.environ.get("TRANSCRIBE_REGION")
    if override:
        if bucket_region and bucket_region != override:
            app.logger.warning(
                "TRANSCRIBE_REGION override (%s) differs from bucket region %s",
                override,
                bucket_region,
            )
        return override
    return bucket_region or DEFAULT_AWS_REGION


@app.route("/health", methods=["GET"])
def health() -> Any:
    return jsonify({
        "status": "ok",
        "model": MODEL_ID,
        "bedrock_region": BEDROCK_REGION,
        "polly_region": POLLY_REGION
    })


def _build_instruction_context(
    prompt: str,
    persona: str | None = None,
    language: str | None = None,
    force_speech: bool = False
) -> tuple[str, str]:
    instructions = [SYSTEM_PROMPT.strip()]
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
    if not clean_prompt:
        clean_prompt = "Please craft an expressive narration."
    return system_block, clean_prompt


def _compose_prompt(
    prompt: str,
    persona: str | None = None,
    language: str | None = None,
    force_speech: bool = False
) -> str:
    system_block, clean_prompt = _build_instruction_context(
        prompt,
        persona=persona,
        language=language,
        force_speech=force_speech,
    )
    model_id = (MODEL_ID or "").lower()
    # Llama 3 Instruct expects the Llama-3 chat template.
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

    # Llama 2 style prompt for older instruct models.
    return (
        "<s>[INST] <<SYS>>\n"
        f"{system_block}\n"
        "<</SYS>>\n\n"
        f"{clean_prompt}\n"
        "[/INST]"
    )


def _model_supports_messages(model_id: str) -> bool:
    """Return True only for models we know accept a 'messages' body via InvokeModel.

    NOTE: This service primarily targets Llama-style models (prompt-based). For unknown
    models, default to prompt-only to avoid ValidationException noise.
    """
    normalized = (model_id or "").lower()
    # Llama 3 runtime rejects 'messages' with the current InvokeModel schema.
    if normalized.startswith("meta.llama"):
        return False
    return False


def _compose_messages(
    prompt: str,
    persona: str | None = None,
    language: str | None = None,
    force_speech: bool = False
) -> list[dict[str, Any]]:
    system_block, clean_prompt = _build_instruction_context(
        prompt,
        persona=persona,
        language=language,
        force_speech=force_speech,
    )
    return [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": system_block,
                }
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": clean_prompt,
                }
            ],
        },
    ]


def _extract_generation_text(response_body: Dict[str, Any]) -> str:
    """Extract model text from multiple possible response shapes."""

    def _collect_from_content(content: Any) -> str:
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict):
                    if "text" in block:
                        parts.append(str(block.get("text", "")))
                    elif "type" in block and block.get("type") == "tool_result":
                        parts.append(str(block.get("result", "")))
                elif isinstance(block, str):
                    parts.append(block)
            return "".join(parts)
        if isinstance(content, dict):
            return _collect_from_content(content.get("content"))
        if isinstance(content, str):
            return content
        return ""

    # Common shapes
    generation = response_body.get("generation")
    if generation:
        return str(generation)

    generations = response_body.get("generations")
    if generations:
        collected = "".join(str(item.get("text", "")) for item in generations if isinstance(item, dict))
        if collected:
            return collected

    outputs = response_body.get("outputs")
    if outputs:
        parts = []
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


def _invoke_bedrock(body: Dict[str, Any]) -> Dict[str, Any]:
    response = bedrock_runtime.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps(body),
        accept="application/json",
        contentType="application/json"
    )
    return json.loads(response["body"].read())


def _fallback_ssml(prompt: str) -> str:
    """Construct a heuristic SSML narration when the model response fails."""

    cleaned = re.sub(r"\s+", " ", (prompt or "").strip())
    if not cleaned:
        cleaned = "our story today"

    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    focus_sentence = sentences[0] if sentences and sentences[0].strip() else cleaned
    focus_phrase = html.escape(focus_sentence.strip()[:180])

    bullet_candidates = [part.strip() for part in re.split(r"[\n\r•\-]+", cleaned) if part.strip()]
    bullet_phrases = [html.escape(candidate[:160]) for candidate in bullet_candidates[:3]]

    intro = f"<p><s>Welcome! Let's explore {focus_phrase} from a fresh perspective.</s><break time=\"400ms\"/></p>"
    body_sentences = []
    if bullet_phrases:
        for idx, phrase in enumerate(bullet_phrases, start=1):
            body_sentences.append(
                f"<s>Key moment {idx}: {phrase}. We'll bring this idea to life with vivid storytelling.</s>"
            )
    else:
        body_sentences.append(
            "<s>We'll unfold the main ideas step by step, highlighting the emotions and motivations along the way.</s>"
        )

    body = "<p>" + "<break time=\"250ms\"/>".join(body_sentences) + "</p>"
    outro = (
        "<p><s>Stay tuned as we guide you through the narrative, keeping the energy dynamic and engaging.</s>"
        "<break time=\"350ms\"/><s>Thanks for listening.</s></p>"
    )

    return f"<speak>{intro}{body}{outro}</speak>"


def _strip_ssml_tags(ssml: str) -> str:
    no_tags = re.sub(r"<[^>]+>", " ", ssml)
    return re.sub(r"\s+", " ", no_tags).strip()


def _tokenize(text: str) -> list[str]:
    cleaned = re.sub(r"[^\w\s]", " ", text).lower()
    tokens = [token for token in cleaned.split() if token]
    return tokens


def _token_overlap(prompt_tokens: list[str], ssml_tokens: list[str]) -> float:
    if not prompt_tokens or not ssml_tokens:
        return 0.0
    prompt_counter = Counter(prompt_tokens)
    ssml_counter = Counter(ssml_tokens)
    overlap = sum((prompt_counter & ssml_counter).values())
    return overlap / max(1, len(prompt_tokens))


def _looks_like_prompt_echo(prompt: str, ssml: str) -> bool:
    if not prompt or not ssml:
        return False
    prompt_clean = re.sub(r"\s+", " ", prompt).strip().lower()
    ssml_clean = _strip_ssml_tags(ssml).lower()
    if not prompt_clean or not ssml_clean:
        return False
    if prompt_clean == ssml_clean:
        return True

    # If the SSML simply repeats the prompt with minimal padding, treat as echo
    if ssml_clean.startswith(prompt_clean):
        trailing = ssml_clean[len(prompt_clean):].strip()
        if not trailing or len(trailing.split()) <= 3:
            return True

    similarity = SequenceMatcher(None, prompt_clean, ssml_clean).ratio()

    prompt_tokens = _tokenize(prompt_clean)
    ssml_tokens = _tokenize(ssml_clean)
    overlap_ratio = _token_overlap(prompt_tokens, ssml_tokens)

    length_ratio = 1.0
    if prompt_tokens and ssml_tokens:
        length_ratio = min(len(prompt_tokens), len(ssml_tokens)) / max(len(prompt_tokens), len(ssml_tokens))

    # Consider it an echo if overlap is high and lengths are similar,
    # or the string similarity itself is very high.
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


@app.route("/generate-ssml", methods=["POST"])
def generate_ssml() -> Any:
    payload: Dict[str, Any] = request.get_json(silent=True) or {}
    user_prompt = (payload.get("prompt") or "").strip()
    persona = (payload.get("persona") or "").strip() or None
    language = (payload.get("language") or "").strip() or None

    if not user_prompt:
        return jsonify({"error": "Prompt is required."}), 400

    prompt = _compose_prompt(user_prompt, persona=persona, language=language)

    base_temperature = float(payload.get("temperature", DEFAULT_TEMPERATURE))
    base_top_p = float(payload.get("top_p", DEFAULT_TOP_P))

    def _should_retry(current_ssml: str) -> tuple[bool, str | None]:
        if not current_ssml:
            return True, "empty"
        if _looks_like_prompt_echo(user_prompt, current_ssml):
            return True, "echo"
        return False, None

    max_attempts = max(4, int(os.environ.get("VOICEOVER_MAX_ATTEMPTS", "7")))

    attempt_plan: list[dict[str, Any]] = []
    for attempt_index in range(max_attempts):
        if attempt_index == 0:
            attempt_plan.append({
                "index": attempt_index + 1,
                "label": "primary",
                "prompt": prompt,
                "messages": _compose_messages(user_prompt, persona=persona, language=language)
                if _model_supports_messages(MODEL_ID)
                else None,
                "temperature": base_temperature,
                "top_p": base_top_p,
                "force": False,
                "notes": "initial generation",
            })
            continue

        if attempt_index == 1:
            prompt_text = (
                f"{user_prompt}\n\n"
                "Transform this into a fresh narration script with original phrasing, using expressive SSML tags. "
                "Deliver 4-6 sentences split across paragraphs with varied pacing cues."
            )
            attempt_plan.append({
                "index": attempt_index + 1,
                "label": "retry_force_speech",
                "prompt": _compose_prompt(prompt_text, persona=persona, language=language, force_speech=True),
                "messages": _compose_messages(prompt_text, persona=persona, language=language, force_speech=True)
                if _model_supports_messages(MODEL_ID)
                else None,
                "temperature": min(1.0, base_temperature + 0.25),
                "top_p": min(0.99, base_top_p + 0.06),
                "force": True,
                "notes": "first retry with force_speech",
            })
            continue

        if attempt_index == 2:
            prompt_text = (
                f"{user_prompt}\n\n"
                "Craft a vivid voiceover with an opening hook, middle build, and closing call-to-action. "
                "Incorporate <p> sections, <break>, and <emphasis> tags. Avoid copying the input sentences directly."
            )
            attempt_plan.append({
                "index": attempt_index + 1,
                "label": "retry_story_arc",
                "prompt": _compose_prompt(prompt_text, persona=persona, language=language, force_speech=True),
                "messages": _compose_messages(prompt_text, persona=persona, language=language, force_speech=True)
                if _model_supports_messages(MODEL_ID)
                else None,
                "temperature": min(1.0, base_temperature + 0.35),
                "top_p": min(0.995, base_top_p + 0.08),
                "force": True,
                "notes": "second retry with structured guidance",
            })
            continue

        # For subsequent attempts, progressively reinforce originality and richness.
        escalation = attempt_index - 2
        prompt_text = (
            f"{user_prompt}\n\n"
            f"Attempt {attempt_index + 1}: Produce an entirely new narration with a cinematic arc, vivid sensory language,"
            " and varied pacing. Do not mirror the source sentences—paraphrase heavily and introduce fresh connective tissue.\n"
            "Use multiple <p> blocks, layer in <prosody rate=\"slow\"> and <emphasis> for key beats, and ensure at least five"
            " sentences total. Close with a motivating call-to-action."
        )
        attempt_plan.append({
            "index": attempt_index + 1,
            "label": f"retry_escalation_{attempt_index + 1}",
            "prompt": _compose_prompt(prompt_text, persona=persona, language=language, force_speech=True),
            "messages": _compose_messages(prompt_text, persona=persona, language=language, force_speech=True)
            if _model_supports_messages(MODEL_ID)
            else None,
            "temperature": min(1.0, base_temperature + 0.25 + 0.1 * escalation),
            "top_p": min(0.996, base_top_p + 0.06 + 0.02 * escalation),
            "force": True,
            "notes": f"escalation attempt {attempt_index + 1}",
        })

    generation = ""
    response_body: Dict[str, Any] | None = None
    attempt_logs: list[dict[str, Any]] = []

    for attempt in attempt_plan:
        request_variants: list[tuple[str, Dict[str, Any]]] = [
            (
                "prompt",
                {
                    "prompt": attempt["prompt"],
                    "max_gen_len": DEFAULT_MAX_TOKENS,
                    "temperature": attempt["temperature"],
                    "top_p": attempt["top_p"],
                },
            ),
        ]
        if attempt.get("messages"):
            request_variants.append(
                (
                    "messages",
                    {
                        "messages": attempt["messages"],
                        "max_gen_len": DEFAULT_MAX_TOKENS,
                        "temperature": attempt["temperature"],
                        "top_p": attempt["top_p"],
                    },
                )
            )

        raw_generation = ""
        candidate_response: Dict[str, Any] | None = None
        variant_used: str | None = None
        variant_attempts: list[dict[str, Any]] = []
        last_error: str | None = None

        for variant_label, request_body in request_variants:
            try:
                candidate = _invoke_bedrock(request_body)
            except (BotoCoreError, ClientError) as aws_error:
                error_message = f"Model runtime request failed: {aws_error}"
                variant_attempts.append({
                    "variant": variant_label,
                    "status": "error",
                    "error": error_message,
                })
                last_error = error_message
                continue
            except Exception as runtime_error:  # pragma: no cover
                error_message = f"Unexpected language runtime error: {runtime_error}"
                variant_attempts.append({
                    "variant": variant_label,
                    "status": "error",
                    "error": error_message,
                })
                last_error = error_message
                continue

            raw_candidate = _extract_generation_text(candidate).strip()
            if raw_candidate:
                raw_generation = raw_candidate
                candidate_response = candidate
                variant_used = variant_label
                variant_attempts.append({
                    "variant": variant_label,
                    "status": "ok",
                    "generation_length": len(raw_candidate),
                })
                break

            try:
                serialized_body = json.dumps(candidate, ensure_ascii=False)
            except Exception:
                serialized_body = str(candidate)
            app.logger.warning(
                "SSML generation attempt '%s' (%s variant) invalid (empty). Response: %s",
                attempt["label"],
                variant_label,
                serialized_body,
            )
            variant_attempts.append({
                "variant": variant_label,
                "status": "invalid",
                "generation_length": len(raw_candidate),
            })
            response_body = candidate
            last_error = "empty"

        if candidate_response is None:
            entry: dict[str, Any] = {
                "attempt": attempt.get("index"),
                "label": attempt["label"],
                "notes": attempt.get("notes"),
                "temperature": attempt["temperature"],
                "top_p": attempt["top_p"],
                "variant_attempts": variant_attempts,
            }
            if last_error in {"empty", "echo"}:
                entry["status"] = "retry"
                entry["reason"] = last_error
            else:
                entry["status"] = "error"
                entry["error"] = last_error or "Model runtime request failed."
            attempt_logs.append(entry)
            continue

        needs_retry, retry_reason = _should_retry(raw_generation)
        attempt_logs.append({
            "attempt": attempt.get("index"),
            "label": attempt["label"],
            "status": "retry" if needs_retry else "ok",
            "reason": retry_reason,
            "notes": attempt.get("notes"),
            "generation_length": len(raw_generation),
            "temperature": attempt["temperature"],
            "top_p": attempt["top_p"],
            "inference_variant": variant_used,
            "variant_attempts": variant_attempts,
        })

        if raw_generation and not needs_retry:
            generation = raw_generation
            response_body = candidate_response
            break

        response_body = candidate_response
        if retry_reason:
            try:
                serialized_body = json.dumps(candidate_response, ensure_ascii=False)
            except Exception:
                serialized_body = str(candidate_response)
            app.logger.warning(
                "SSML generation attempt '%s' invalid (%s). Response: %s",
                attempt["label"],
                retry_reason,
                serialized_body,
            )

    if not generation:
        fallback_ssml = _fallback_ssml(user_prompt)
        reason_label = next(
            (log.get("reason") for log in reversed(attempt_logs) if log.get("reason")),
            "exhausted_attempts",
        )
        return jsonify({
            "ssml": fallback_ssml,
            "meta": {
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
        }), 200

    return jsonify({
        "ssml": generation,
        "meta": {
            "prompt_tokens": (response_body or {}).get("prompt_token_count"),
            "generation_tokens": (response_body or {}).get("generation_token_count"),
            "attempt_count": len(attempt_logs),
            "attempts": attempt_logs,
        }
    })


@lru_cache(maxsize=1)
def _list_neural_voices() -> list[dict[str, Any]]:
    """List all available voices from AWS Polly (neural, long-form, generative engines)."""
    voices_dict: dict[str, dict[str, Any]] = {}
    
    # Fetch voices from all high-quality engines
    engines = ["neural", "long-form", "generative"]
    
    for engine in engines:
        try:
            paginator = polly.get_paginator("describe_voices")
            for page in paginator.paginate(Engine=engine):
                for voice in page.get("Voices", []):
                    voice_id = voice.get("Id")
                    supported_engines = [e.lower() for e in voice.get("SupportedEngines", [])]
                    
                    # Only include high-quality engines (neural, long-form, generative)
                    quality_engines = [e for e in supported_engines if e in ["neural", "long-form", "generative"]]
                    
                    if quality_engines:
                        # Use voice_id as key to avoid duplicates
                        if voice_id not in voices_dict:
                            voices_dict[voice_id] = {
                                "id": voice_id,
                                "name": voice.get("Name"),
                                "language_code": voice.get("LanguageCode"),
                                "language_name": voice.get("LanguageName"),
                                "gender": voice.get("Gender"),
                                "style_list": voice.get("AdditionalLanguageCodes", []),
                                "engines": quality_engines,
                            }
                        else:
                            # Merge engines if voice already exists
                            existing_engines = voices_dict[voice_id].get("engines", [])
                            voices_dict[voice_id]["engines"] = list(set(existing_engines + quality_engines))
        except Exception as e:
            # Some engines might not be available in all regions
            app.logger.warning(f"Could not fetch voices for engine {engine}: {e}")
            continue
    
    voices = list(voices_dict.values())
    voices.sort(key=lambda v: (v.get("language_name", ""), v.get("name", "")))
    return voices


@app.route("/voices", methods=["GET"])
def list_voices() -> Any:
    try:
        voices = _list_neural_voices()
    except (BotoCoreError, ClientError) as aws_error:
        return jsonify({"error": f"Failed to load voices: {aws_error}"}), 502
    return jsonify({"voices": voices, "count": len(voices)})


@app.route("/translation-languages", methods=["GET"])
def list_translation_languages() -> Any:
    """Get list of supported translation languages."""
    # Common languages supported by AWS Translate and Polly
    languages = [
        {"code": "en", "name": "English", "polly_codes": ["en-US", "en-GB", "en-AU", "en-IN", "en-NZ", "en-ZA"]},
        {"code": "es", "name": "Spanish", "polly_codes": ["es-ES", "es-MX", "es-US"]},
        {"code": "fr", "name": "French", "polly_codes": ["fr-FR", "fr-CA", "fr-BE"]},
        {"code": "de", "name": "German", "polly_codes": ["de-DE", "de-AT"]},
        {"code": "it", "name": "Italian", "polly_codes": ["it-IT"]},
        {"code": "pt", "name": "Portuguese", "polly_codes": ["pt-BR", "pt-PT"]},
        {"code": "nl", "name": "Dutch", "polly_codes": ["nl-NL", "nl-BE"]},
        {"code": "pl", "name": "Polish", "polly_codes": ["pl-PL"]},
        {"code": "ru", "name": "Russian", "polly_codes": ["ru-RU"]},
        {"code": "ja", "name": "Japanese", "polly_codes": ["ja-JP"]},
        {"code": "ko", "name": "Korean", "polly_codes": ["ko-KR"]},
        {"code": "zh", "name": "Chinese", "polly_codes": ["cmn-CN", "yue-CN"]},
        {"code": "ar", "name": "Arabic", "polly_codes": ["ar-AE", "arb"]},
        {"code": "hi", "name": "Hindi", "polly_codes": ["hi-IN"]},
        {"code": "tr", "name": "Turkish", "polly_codes": ["tr-TR"]},
        {"code": "da", "name": "Danish", "polly_codes": ["da-DK"]},
        {"code": "sv", "name": "Swedish", "polly_codes": ["sv-SE"]},
        {"code": "no", "name": "Norwegian", "polly_codes": ["nb-NO"]},
        {"code": "fi", "name": "Finnish", "polly_codes": ["fi-FI"]},
        {"code": "ca", "name": "Catalan", "polly_codes": ["ca-ES"]},
    ]
    return jsonify({"languages": languages})


def _translate_text(text: str, source_lang: str, target_lang: str) -> str:
    """Translate text using AWS Translate."""
    try:
        # AWS Translate uses 'auto' for automatic source language detection
        if source_lang.lower() == "auto":
            source_lang = "auto"
        
        response = translate.translate_text(
            Text=text,
            SourceLanguageCode=source_lang,
            TargetLanguageCode=target_lang
        )
        
        return response.get("TranslatedText", text)
    except Exception as e:
        app.logger.error(f"Translation failed: {str(e)}")
        return text  # Return original text if translation fails


_AUDIO_MIME = {
    "mp3": "audio/mpeg",
    "ogg_vorbis": "audio/ogg",
    "pcm": "audio/wav",
}


@lru_cache(maxsize=128)
def _voice_supported_engines(voice_id: str) -> list[str]:
    try:
        response = polly.describe_voices(VoiceId=voice_id)
    except (BotoCoreError, ClientError):
        return []
    voices = response.get("Voices", [])
    if not voices:
        return []
    engines = voices[0].get("SupportedEngines", []) or []
    return [engine.lower() for engine in engines]


def _get_best_engine_for_voice(voice_id: str) -> str:
    """Get the best available engine for a voice (prefers generative > long-form > neural)."""
    engines = _voice_supported_engines(voice_id)
    
    # Priority order: generative (newest), long-form (high quality), neural (standard)
    if "generative" in engines:
        return "generative"
    elif "long-form" in engines:
        return "long-form"
    elif "neural" in engines:
        return "neural"
    else:
        # Fallback to standard if no high-quality engines available
        return "standard" if "standard" in engines else "neural"


def _create_natural_ssml(text: str, engine: str = "neural") -> str:
    """
    Create natural-sounding SSML with prosody, pauses, and emphasis.
    Makes synthetic speech sound more human-like and conversational.
    """
    if not text or not text.strip():
        return "<speak></speak>"
    
    text = text.strip()
    
    # Build SSML with natural elements
    ssml_parts = ['<speak>']
    
    # Split by sentence endings but keep the punctuation
    import re
    sentences = re.split(r'([.!?]+\s*)', text)
    
    # Reconstruct sentences with their punctuation
    reconstructed = []
    for i in range(0, len(sentences) - 1, 2):
        if sentences[i].strip():
            punct = sentences[i + 1] if i + 1 < len(sentences) else ''
            reconstructed.append(sentences[i].strip() + punct.strip())
    if len(sentences) % 2 == 1 and sentences[-1].strip():
        reconstructed.append(sentences[-1].strip())
    
    sentences = reconstructed if reconstructed else [text]
    
    for i, sentence in enumerate(sentences):
        if not sentence.strip():
            continue
        
        # Escape HTML entities
        sentence_escaped = html.escape(sentence)
        
        # Add natural pauses between sentences (like breathing)
        if i > 0:
            ssml_parts.append('<break time="350ms"/>')
        
        # Detect sentence type and apply appropriate prosody
        if '?' in sentence:
            # Questions: slightly higher pitch, emphasis on question words
            sentence_escaped = re.sub(
                r'\b(what|where|when|why|who|how|which|whose|can|could|would|should|will|do|does|did|is|are|was|were)\b',
                r'<emphasis level="moderate">\1</emphasis>',
                sentence_escaped,
                flags=re.IGNORECASE
            )
            ssml_parts.append(f'<prosody rate="100%" pitch="+3%">{sentence_escaped}</prosody>')
        
        elif '!' in sentence:
            # Exclamations: more energetic, slight volume boost
            ssml_parts.append(f'<prosody rate="103%" pitch="+2%" volume="+1dB">{sentence_escaped}</prosody>')
        
        else:
            # Regular sentences: natural pacing with slight variation
            word_count = len(sentence.split())
            
            if word_count > 20:
                # Long sentences: slower for clarity
                rate = "93%"
            elif word_count < 5:
                # Short sentences: slightly faster, more natural
                rate = "102%"
            else:
                # Medium sentences: normal pace
                rate = "98%"
            
            ssml_parts.append(f'<prosody rate="{rate}">{sentence_escaped}</prosody>')
        
        # Add micro-pauses after commas and conjunctions for natural breathing
        last_part = ssml_parts[-1]
        # After commas
        last_part = last_part.replace(',', ',<break time="250ms"/>')
        # After conjunctions (but, and, or, so)
        last_part = re.sub(
            r'\b(but|and|or|so|because|however|therefore)\b',
            r'\1<break time="200ms"/>',
            last_part,
            flags=re.IGNORECASE
        )
        ssml_parts[-1] = last_part
    
    ssml_parts.append('</speak>')
    return ''.join(ssml_parts)


def _sanitize_ssml_for_neural(ssml: str) -> str:
    sanitized = ssml
    # Remove amazon-specific tags unsupported by neural voices
    sanitized = re.sub(r"<\s*/?amazon:(?:effect|domain|auto-breaths)[^>]*>", "", sanitized, flags=re.IGNORECASE)
    # Simplify prosody attributes that can cause issues (e.g., extreme rates)
    sanitized = re.sub(r'rate="x-(fast|slow)"', r'rate="\1"', sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r'volume="x-(loud|soft)"', r'volume="\1"', sanitized, flags=re.IGNORECASE)
    def _sanitize_rate_decimal(match: re.Match[str]) -> str:
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
    # Remove speakable SSML comments if any
    sanitized = re.sub(r"<!--.*?-->", "", sanitized, flags=re.DOTALL)
    return sanitized


def _normalize_ssml(ssml: str) -> tuple[str, bool, list[str]]:
    """Attempt to massage model SSML into a synthesizer-friendly shape."""

    notes: list[str] = []
    original = (ssml or "").strip()
    candidate = original

    if not candidate:
        fallback = "<speak></speak>"
        notes.append("empty_input")
        return fallback, True, notes

    # remove xml declarations or doctypes that the speech service rejects
    new_candidate = re.sub(r"<\?xml[^>]*>", "", candidate, flags=re.IGNORECASE)
    new_candidate = re.sub(r"<!DOCTYPE[^>]*>", "", new_candidate, flags=re.IGNORECASE)
    if new_candidate != candidate:
        notes.append("removed_xml_header")
        candidate = new_candidate.strip()

    # Extract the first <speak>...</speak> block if multiple exists
    speak_match = re.search(r"<\s*speak\b[^>]*>(.*)</\s*speak\s*>", candidate, flags=re.IGNORECASE | re.DOTALL)
    if speak_match:
        inner = speak_match.group(1)
        leading = candidate[:speak_match.start()].strip()
        trailing = candidate[speak_match.end():].strip()
        if leading or trailing:
            notes.append("trimmed_extra_wrappers")
        candidate = f"<speak>{inner}</speak>"
    else:
        notes.append("wrapped_in_speak")
        candidate = f"<speak>{candidate}</speak>"

    # Convert break times expressed as fractional seconds to milliseconds (e.g., 0.5s -> 500ms)
    def _convert_break(match: re.Match[str]) -> str:
        time_value = match.group(1)
        suffix = match.group(2).lower()
        if suffix == "ms":
            return match.group(0)
        try:
            seconds = float(time_value)
            millis = int(round(seconds * 1000))
            return f"time=\"{millis}ms\""
        except ValueError:
            return match.group(0)

    converted_candidate = re.sub(r'time="([0-9]*\.?[0-9]+)(s|ms)"', _convert_break, candidate, flags=re.IGNORECASE)
    if converted_candidate != candidate:
        notes.append("normalized_break_time")
        candidate = converted_candidate

    # Normalize prosody rate values given as decimals (e.g., 0.9 -> 90%)
    def _convert_rate(match: re.Match[str]) -> str:
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

    # Escape bare ampersands that are not part of an entity reference
    escaped_candidate = re.sub(r"&(?![a-zA-Z]+;|#\d+;|#x[0-9A-Fa-f]+;)", "&amp;", candidate)
    if escaped_candidate != candidate:
        notes.append("escaped_ampersands")
        candidate = escaped_candidate

    # Ensure the inner text is not entirely whitespace after cleanup
    inner_text = _strip_ssml_tags(candidate)
    if not inner_text:
        notes.append("empty_after_strip")
        candidate = "<speak></speak>"

    # Validate by parsing; if parsing fails, fall back to a plain escaped narration
    try:
        ET.fromstring(candidate)
    except ET.ParseError:
        safe_text = html.escape(inner_text or "Narration coming up.")
        candidate = f"<speak>{safe_text}</speak>"
        notes.append("parse_error_fallback")

    was_modified = candidate != original
    return candidate, was_modified, notes


@app.route("/synthesize", methods=["POST"])
def synthesize_speech() -> Any:
    payload: Dict[str, Any] = request.get_json(silent=True) or {}
    voice_id = payload.get("voiceId")
    ssml_content = payload.get("ssml")
    output_format = payload.get("outputFormat", "mp3").lower()
    sample_rate = payload.get("sampleRate")
    
    # Translation parameters
    translate_enabled = payload.get("translateEnabled", False)
    source_language = payload.get("sourceLanguage", "auto")
    target_language = payload.get("targetLanguage", "en")
    target_polly_language = payload.get("targetPollyLanguage", "en-US")

    if not voice_id:
        return jsonify({"error": "voiceId is required"}), 400
    if not ssml_content:
        return jsonify({"error": "ssml content is required"}), 400
    if output_format not in _AUDIO_MIME:
        return jsonify({"error": f"Unsupported output format '{output_format}'"}), 400

    # Translate content if enabled
    if translate_enabled:
        original_plaintext = _strip_ssml_tags(ssml_content)
        translated_text = _translate_text(original_plaintext, source_language, target_language)
        app.logger.info(f"Translated text from {source_language} to {target_language}")
        # Wrap translated text in SSML
        ssml_content = f"<speak>{html.escape(translated_text)}</speak>"
    
    normalized_ssml, ssml_normalized, normalization_notes = _normalize_ssml(ssml_content)

    original_plaintext = _strip_ssml_tags(ssml_content)

    # Get the best available engine for this voice
    best_engine = _get_best_engine_for_voice(voice_id)

    request_args: Dict[str, Any] = {
        "VoiceId": voice_id,
        "Text": normalized_ssml,
        "TextType": "ssml",
        "Engine": best_engine,
        "OutputFormat": output_format,
    }
    if sample_rate:
        request_args["SampleRate"] = str(sample_rate)
    
    # Add language code if translation is enabled
    if translate_enabled and target_polly_language:
        request_args["LanguageCode"] = target_polly_language

    engine_used = request_args["Engine"]

    sanitized_used = False
    sanitized_ssml: str | None = None
    plain_retry_used = False
    plain_retry_ssml: str | None = None
    text_fallback_used = False
    text_fallback_text: str | None = None
    safe_minimal_used = False
    safe_minimal_ssml: str | None = None
    safe_minimal_engine: str | None = None
    safe_minimal_mode: str | None = None

    response: Dict[str, Any] | None = None

    def _try_safe_minimal(engine_sequence: list[str]) -> bool:
        nonlocal response, engine_used, normalized_ssml, safe_minimal_used, safe_minimal_ssml
        nonlocal safe_minimal_engine, safe_minimal_mode, error_message, text_fallback_used, text_fallback_text

        safe_candidate_text = original_plaintext or _strip_ssml_tags(normalized_ssml) or "Narration coming up."
        safe_candidate = f"<speak><s>{html.escape(safe_candidate_text[:320])}</s></speak>"

        attempted = False
        for engine_option in engine_sequence:
            safe_request = dict(request_args)
            safe_request["Engine"] = engine_option
            safe_request["Text"] = safe_candidate
            safe_request["TextType"] = "ssml"
            try:
                response = polly.synthesize_speech(**safe_request)
                engine_used = engine_option
                normalized_ssml = safe_candidate
                safe_minimal_used = True
                safe_minimal_ssml = safe_candidate
                safe_minimal_engine = engine_option
                safe_minimal_mode = "ssml"
                error_message = None
                return True
            except (BotoCoreError, ClientError):
                attempted = True
                continue

        if attempted and not safe_minimal_used:
            error_message = error_message or "Safe minimal SSML attempt failed."

        # Final attempt: plain text synthesis
        for engine_option in engine_sequence:
            text_request = dict(request_args)
            text_request["Engine"] = engine_option
            text_request["Text"] = safe_candidate_text
            text_request["TextType"] = "text"
            try:
                response = polly.synthesize_speech(**text_request)
                engine_used = engine_option
                safe_minimal_used = True
                safe_minimal_ssml = safe_candidate
                safe_minimal_engine = engine_option
                safe_minimal_mode = "text"
                text_fallback_used = True
                text_fallback_text = safe_candidate_text
                normalized_ssml = safe_candidate
                error_message = None
                return True
            except (BotoCoreError, ClientError):
                continue

        return False

    try:
        response = polly.synthesize_speech(**request_args)
    except (BotoCoreError, ClientError) as aws_error:
        error_message = str(aws_error)
        error_code = None
        if isinstance(aws_error, ClientError):
            error_code = aws_error.response.get("Error", {}).get("Code")
            error_message = aws_error.response.get("Error", {}).get("Message", error_message)

        if error_code == "InvalidSsmlException" and "unsupported neural feature" in error_message.lower():
            sanitized_candidate = _sanitize_ssml_for_neural(normalized_ssml)
            if sanitized_candidate != normalized_ssml:
                try:
                    request_args["Text"] = sanitized_candidate
                    response = polly.synthesize_speech(**request_args)
                    sanitized_used = True
                    sanitized_ssml = sanitized_candidate
                except (BotoCoreError, ClientError) as retry_error:
                    # restore original text before exploring other fallbacks
                    request_args["Text"] = normalized_ssml
                    if isinstance(retry_error, ClientError):
                        error_message = retry_error.response.get("Error", {}).get("Message", str(retry_error))
                    else:
                        error_message = str(retry_error)
                else:
                    error_message = None

            if not sanitized_used:
                supported_engines = _voice_supported_engines(voice_id)
                if "standard" in supported_engines:
                    fallback_args = dict(request_args)
                    fallback_args["Engine"] = "standard"
                    engine_used = "standard"
                    try:
                        response = polly.synthesize_speech(**fallback_args)
                    except (BotoCoreError, ClientError) as fallback_error:
                        fallback_msg = fallback_error
                        if isinstance(fallback_error, ClientError):
                            fallback_msg = fallback_error.response.get("Error", {}).get("Message", str(fallback_error))
                        engine_sequence = ["neural", "standard"]
                        if _try_safe_minimal(engine_sequence):
                            error_message = None
                        else:
                            return jsonify({
                                "error": (
                                    "Voice synthesis failed: neural engine rejected SSML and standard fallback "
                                    f"also failed ({fallback_msg})"
                                )
                            }), 502
                else:
                    detail = (
                        "Voice does not support the standard engine and neural synthesis rejected SSML. "
                        "Try simplifying SSML effects or choose another voice."
                    )
                    if error_message:
                        detail = f"{detail} (Last error: {error_message})"
                    engine_sequence = [request_args.get("Engine", "neural")]
                    if _try_safe_minimal(engine_sequence):
                        error_message = None
                    else:
                        return jsonify({"error": detail}), 502
        elif error_code == "InvalidSsmlException":
            sanitized_candidate = _sanitize_ssml_for_neural(normalized_ssml)
            if sanitized_candidate != normalized_ssml:
                try:
                    request_args["Text"] = sanitized_candidate
                    response = polly.synthesize_speech(**request_args)
                    sanitized_used = True
                    sanitized_ssml = sanitized_candidate
                    normalized_ssml = sanitized_candidate
                    error_message = None
                except (BotoCoreError, ClientError) as retry_error:
                    request_args["Text"] = normalized_ssml
                    if isinstance(retry_error, ClientError):
                        error_message = retry_error.response.get("Error", {}).get("Message", str(retry_error))
                    else:
                        error_message = str(retry_error)

            if error_message:
                plain_text = _strip_ssml_tags(normalized_ssml) or "Narration coming up."
                plain_candidate = f"<speak>{html.escape(plain_text)}</speak>"
                normalization_notes.append("plain_ssml_retry")
                try:
                    request_args["Text"] = plain_candidate
                    response = polly.synthesize_speech(**request_args)
                    plain_retry_used = True
                    plain_retry_ssml = plain_candidate
                    normalized_ssml = plain_candidate
                    error_message = None
                except (BotoCoreError, ClientError) as plain_error:
                    request_args["Text"] = normalized_ssml

                    plain_text_payload = _strip_ssml_tags(normalized_ssml) or "Narration coming up."
                    text_args = dict(request_args)
                    text_args["Text"] = plain_text_payload
                    text_args["TextType"] = "text"
                    try:
                        response = polly.synthesize_speech(**text_args)
                        text_fallback_used = True
                        text_fallback_text = plain_text_payload
                        engine_used = text_args.get("Engine", engine_used)
                        normalized_ssml = f"<speak>{html.escape(plain_text_payload)}</speak>"
                        error_message = None
                    except (BotoCoreError, ClientError):
                        supported_engines = _voice_supported_engines(voice_id)
                        engine_sequence = [request_args.get("Engine", "neural")]
                        if "standard" in supported_engines:
                            fallback_args = dict(request_args)
                            fallback_args["Engine"] = "standard"
                            fallback_args["Text"] = plain_candidate
                            engine_used = "standard"
                            try:
                                response = polly.synthesize_speech(**fallback_args)
                                plain_retry_used = True
                                plain_retry_ssml = plain_candidate
                                normalized_ssml = plain_candidate
                                error_message = None
                            except (BotoCoreError, ClientError) as fallback_error:
                                fallback_msg = fallback_error
                                if isinstance(fallback_error, ClientError):
                                    fallback_msg = fallback_error.response.get("Error", {}).get("Message", str(fallback_error))
                                engine_sequence.append("standard")
                                if not _try_safe_minimal(engine_sequence):
                                    return jsonify({
                                        "error": (
                                            "Voice synthesis failed: SSML invalid and standard fallback also failed "
                                            f"({fallback_msg})"
                                        )
                                    }), 502
                                error_message = None
                        else:
                            if not _try_safe_minimal(engine_sequence):
                                detail = (
                                    "SSML was invalid and selected voice has no standard fallback available. "
                                    "Plain text retry also failed."
                                )
                                if isinstance(plain_error, ClientError):
                                    detail = (
                                        f"{detail} (Last error: "
                                        f"{plain_error.response.get('Error', {}).get('Message', str(plain_error))})"
                                    )
                                return jsonify({"error": detail}), 502
        else:
            return jsonify({"error": f"Voice synthesis failed: {aws_error}"}), 502
    except Exception as runtime_error:  # pragma: no cover
        return jsonify({"error": f"Unexpected error calling Polly: {runtime_error}"}), 500

    audio_stream = response.get("AudioStream")
    if not audio_stream:
        return jsonify({"error": "No AudioStream in Polly response"}), 502
    audio_bytes = audio_stream.read()

    encoded_audio = base64.b64encode(audio_bytes).decode("utf-8")
    file_extension = "mp3" if output_format == "mp3" else ("ogg" if output_format == "ogg_vorbis" else "wav")

    return jsonify({
        "audio": encoded_audio,
        "contentType": _AUDIO_MIME[output_format],
        "fileExtension": file_extension,
        "meta": {
            "engineUsed": engine_used,
            "ssmlSanitized": sanitized_used,
            "sanitizedSsml": sanitized_ssml,
            "ssmlNormalized": ssml_normalized,
            "normalizationNotes": normalization_notes,
            "plainRetryUsed": plain_retry_used,
            "plainRetrySsml": plain_retry_ssml,
            "textFallbackUsed": text_fallback_used,
            "textFallbackText": text_fallback_text,
            "safeMinimalUsed": safe_minimal_used,
            "safeMinimalSsml": safe_minimal_ssml,
            "safeMinimalEngine": safe_minimal_engine,
            "safeMinimalMode": safe_minimal_mode,
        }
    })


@app.route("/replace-video-audio", methods=["POST"])
def replace_video_audio() -> Any:
    """
    Upload a video, extract audio, transcribe it, generate synthetic voiceover,
    and return a new video with replaced audio.
    
    Form parameters:
    - video: Video file (required)
    - voice_id: Polly voice ID (optional, default: Joanna)
    - engine: neural/standard (optional, default: neural)
    - language: Target language for transcription (optional, default: auto-detect)
    - persona: Voice persona/tone (optional)
    - output_format: mp4/mov (optional, default: mp4)
    """
    import subprocess
    import tempfile
    import uuid
    from pathlib import Path
    
    # Check if video file is provided
    if "video" not in request.files:
        return jsonify({"error": "Video file is required"}), 400
    
    video_file = request.files["video"]
    if video_file.filename == "":
        return jsonify({"error": "Video file name is empty"}), 400
    
    # Get parameters
    voice_id = request.form.get("voice_id", "Joanna")
    engine = request.form.get("engine", "neural")
    language = request.form.get("language", "en-US")
    persona = request.form.get("persona", "")
    output_format = request.form.get("output_format", "mp4")
    
    # Create temp directories
    job_id = uuid.uuid4().hex[:8]
    temp_dir = Path(tempfile.mkdtemp(prefix=f"voiceover_{job_id}_"))
    
    try:
        # Save uploaded video
        video_ext = Path(video_file.filename).suffix or ".mp4"
        input_video_path = temp_dir / f"input{video_ext}"
        video_file.save(str(input_video_path))
        
        app.logger.info(f"Job {job_id}: Video saved to {input_video_path}")
        
        # Step 1: Extract audio from video using FFmpeg
        audio_path = temp_dir / "extracted_audio.wav"
        ffmpeg_cmd = [
            FFMPEG_PATH, "-i", str(input_video_path),
            "-vn",  # No video
            "-acodec", "pcm_s16le",  # PCM format for compatibility
            "-ar", "16000",  # 16kHz sample rate
            "-ac", "1",  # Mono
            str(audio_path)
        ]
        
        app.logger.info(f"Job {job_id}: Extracting audio with FFmpeg...")
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        
        if result.returncode != 0 or not audio_path.exists():
            app.logger.error(f"Job {job_id}: FFmpeg audio extraction failed: {result.stderr}")
            return jsonify({
                "error": "Failed to extract audio from video",
                "details": result.stderr
            }), 500
        
        app.logger.info(f"Job {job_id}: Audio extracted successfully")
        
        # Step 2: Transcribe audio using AWS Transcribe
        bucket_name = os.environ.get("AWS_S3_BUCKET")
        bucket_region = _detect_bucket_region(bucket_name) if bucket_name else None
        if bucket_name and not bucket_region:
            app.logger.warning(
                "Job %s: Could not detect region for bucket %s; falling back to AWS_REGION %s",
                job_id,
                bucket_name,
                DEFAULT_AWS_REGION,
            )
        s3_region = bucket_region or DEFAULT_AWS_REGION
        transcribe_region = _resolve_transcribe_region(bucket_region)
        transcribe_client = boto3.client("transcribe", region_name=transcribe_region)
        s3_client = boto3.client("s3", region_name=s3_region)
        app.logger.info(
            "Job %s: Using S3 region %s and Transcribe region %s",
            job_id,
            s3_region,
            transcribe_region,
        )

        # Upload audio to S3 for transcription (Transcribe requires S3)
        if not bucket_name:
            # Fallback: Use a simple approach without S3
            # Read audio and use speech recognition library if available
            app.logger.warning(f"Job {job_id}: No S3 bucket configured, using placeholder transcription")
            transcript_text = "This is a placeholder transcription. Configure AWS S3 for real transcription."
        else:
            s3_key = f"voiceover-temp/{job_id}/audio.wav"
            s3_client.upload_file(str(audio_path), bucket_name, s3_key)
            
            # Start transcription job
            transcribe_job_name = f"voiceover_{job_id}"
            transcribe_client.start_transcription_job(
                TranscriptionJobName=transcribe_job_name,
                Media={"MediaFileUri": f"s3://{bucket_name}/{s3_key}"},
                MediaFormat="wav",
                LanguageCode=language if language else "en-US",
            )
            
            # Wait for transcription to complete
            import time
            max_wait = 60  # 60 seconds max
            waited = 0
            while waited < max_wait:
                status = transcribe_client.get_transcription_job(
                    TranscriptionJobName=transcribe_job_name
                )
                job_status = status["TranscriptionJob"]["TranscriptionJobStatus"]
                
                if job_status == "COMPLETED":
                    transcript_uri = status["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
                    # Download transcript
                    import requests
                    transcript_response = requests.get(transcript_uri)
                    transcript_data = transcript_response.json()
                    transcript_text = transcript_data["results"]["transcripts"][0]["transcript"]
                    app.logger.info(f"Job {job_id}: Transcription completed")
                    break
                elif job_status == "FAILED":
                    app.logger.error(f"Job {job_id}: Transcription failed")
                    transcript_text = "Transcription failed. Using placeholder text."
                    break
                
                time.sleep(2)
                waited += 2
            else:
                app.logger.warning(f"Job {job_id}: Transcription timeout")
                transcript_text = "Transcription timed out. Using placeholder text."
            
            # Cleanup transcription job
            try:
                transcribe_client.delete_transcription_job(TranscriptionJobName=transcribe_job_name)
            except:
                pass
        
        app.logger.info(f"Job {job_id}: Transcript: {transcript_text[:100]}...")
        
        # Step 3: Generate SSML from transcript
        prompt = f"Convert this text into an expressive voiceover narration: {transcript_text}"
        composed = _compose_prompt(prompt, persona=persona, language=language, force_speech=True)
        
        try:
            request_body = json.dumps({
                "prompt": composed,
                "max_gen_len": DEFAULT_MAX_TOKENS,
                "temperature": DEFAULT_TEMPERATURE,
                "top_p": DEFAULT_TOP_P,
            })
            
            bedrock_response = bedrock_runtime.invoke_model(
                modelId=MODEL_ID,
                contentType="application/json",
                accept="application/json",
                body=request_body,
            )
            
            response_json = json.loads(bedrock_response["body"].read().decode("utf-8"))
            generated_text = _extract_generation_text(response_json)
            
            # Extract SSML
            ssml_match = re.search(r"<speak>.*?</speak>", generated_text, re.DOTALL | re.IGNORECASE)
            if ssml_match:
                ssml_text = ssml_match.group(0)
            else:
                ssml_text = f"<speak>{html.escape(transcript_text)}</speak>"
            
            app.logger.info(f"Job {job_id}: SSML generated")
            
        except Exception as bedrock_error:
            app.logger.error(f"Job {job_id}: Bedrock generation failed: {bedrock_error}")
            ssml_text = f"<speak>{html.escape(transcript_text)}</speak>"
        
        # Step 4: Synthesize speech with Polly
        synth_audio_path = temp_dir / "synthetic_audio.mp3"
        
        try:
            # Use the best available engine for the selected voice
            best_engine = _get_best_engine_for_voice(voice_id)
            
            synth_response = polly.synthesize_speech(
                Text=ssml_text,
                TextType="ssml",
                VoiceId=voice_id,
                Engine=best_engine,
                OutputFormat="mp3",
            )
            
            audio_stream = synth_response.get("AudioStream")
            if not audio_stream:
                raise Exception("No audio stream in Polly response")
            
            with open(synth_audio_path, "wb") as f:
                f.write(audio_stream.read())
            
            app.logger.info(f"Job {job_id}: Synthetic audio generated")
            
        except Exception as polly_error:
            app.logger.error(f"Job {job_id}: Polly synthesis failed: {polly_error}")
            return jsonify({
                "error": "Failed to synthesize speech",
                "details": str(polly_error)
            }), 500
        
        # Step 5: Get video duration to match audio
        probe_cmd = [
            FFPROBE_PATH, "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(input_video_path)
        ]
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
        try:
            video_duration = float(probe_result.stdout.strip())
        except:
            video_duration = 0.0
        
        # Step 6: Replace audio in video using FFmpeg
        output_video_path = temp_dir / f"output_{job_id}.{output_format}"
        
        # Combine video with new audio
        replace_cmd = [
            FFMPEG_PATH, "-i", str(input_video_path),
            "-i", str(synth_audio_path),
            "-c:v", "copy",  # Copy video stream without re-encoding
            "-map", "0:v:0",  # Map video from input 0
            "-map", "1:a:0",  # Map audio from input 1 (synthetic)
            "-shortest",  # End at shortest stream
            str(output_video_path)
        ]
        
        app.logger.info(f"Job {job_id}: Replacing audio in video...")
        replace_result = subprocess.run(replace_cmd, capture_output=True, text=True)
        
        if replace_result.returncode != 0 or not output_video_path.exists():
            app.logger.error(f"Job {job_id}: FFmpeg audio replacement failed: {replace_result.stderr}")
            return jsonify({
                "error": "Failed to replace audio in video",
                "details": replace_result.stderr
            }), 500
        
        app.logger.info(f"Job {job_id}: Video with synthetic audio generated successfully")
        
        # Step 7: Read output video and return as base64
        with open(output_video_path, "rb") as f:
            video_bytes = f.read()
        
        encoded_video = base64.b64encode(video_bytes).decode("utf-8")
        video_size_mb = len(video_bytes) / (1024 * 1024)
        
        return jsonify({
            "success": True,
            "jobId": job_id,
            "video": encoded_video,
            "contentType": "video/mp4" if output_format == "mp4" else "video/quicktime",
            "fileExtension": output_format,
            "sizeBytes": len(video_bytes),
            "sizeMB": round(video_size_mb, 2),
            "originalTranscript": transcript_text,
            "ssml": ssml_text,
            "voiceId": voice_id,
            "engine": engine,
            "videoDuration": round(video_duration, 2),
        })
        
    except Exception as error:
        app.logger.error(f"Job {job_id}: Unexpected error: {error}", exc_info=True)
        return jsonify({
            "error": "Unexpected error processing video",
            "details": str(error)
        }), 500
    
    finally:
        # Cleanup temp files
        try:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            app.logger.info(f"Job {job_id}: Temp files cleaned up")
        except:
            pass


@app.route("/analyze-video-speakers", methods=["POST"])
def analyze_video_speakers() -> Any:
    """
    Analyze video to identify speakers and their characteristics.
    Returns speaker information for voice replacement.
    """
    import tempfile
    import shutil
    import subprocess
    import uuid
    from pathlib import Path
    
    app.logger.info("Received request to analyze video speakers")
    
    if "video" not in request.files:
        app.logger.error("No video file in request")
        return jsonify({"error": "No video file provided"}), 400
    
    video_file = request.files["video"]
    if not video_file.filename:
        app.logger.error("Empty video filename")
        return jsonify({"error": "Empty filename"}), 400
    
    job_id = str(uuid.uuid4())
    app.logger.info(f"Job {job_id}: Starting speaker analysis for file: {video_file.filename}")
    temp_dir = Path(tempfile.mkdtemp(prefix=f"speaker_analysis_{job_id}_"))
    
    try:
        # Save uploaded video
        video_path = temp_dir / "input_video.mp4"
        video_file.save(str(video_path))
        app.logger.info(f"Job {job_id}: Video saved to {video_path}")
        
        # Extract audio from video using FFmpeg
        # Use MP3 for smaller file size (AWS Transcribe supports MP3)
        audio_path = temp_dir / "extracted_audio.mp3"
        ffmpeg_cmd = [
            FFMPEG_PATH, "-i", str(video_path),
            "-vn", "-acodec", "libmp3lame", "-ar", "16000", "-ac", "1", "-b:a", "64k",
            str(audio_path), "-y"
        ]
        
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            app.logger.error(f"Job {job_id}: FFmpeg extraction failed: {result.stderr}")
            return jsonify({"error": "Failed to extract audio from video"}), 500
        
        app.logger.info(f"Job {job_id}: Audio extracted successfully")
        
        # Check audio file size
        audio_size = audio_path.stat().st_size
        audio_size_mb = audio_size / (1024 * 1024)
        app.logger.info(f"Job {job_id}: Audio file size: {audio_size_mb:.2f} MB")
        
        # Upload audio to S3 for Transcribe (Transcribe requires S3 input)
        bucket_name = os.environ.get("TRANSCRIBE_BUCKET") or os.environ.get("MEDIA_S3_BUCKET")
        if not bucket_name:
            return jsonify({"error": "Set TRANSCRIBE_BUCKET or MEDIA_S3_BUCKET to upload audio for transcription"}), 500
        bucket_region = _detect_bucket_region(bucket_name)
        if not bucket_region:
            app.logger.warning(
                "Job %s: Could not detect region for bucket %s; falling back to AWS_REGION %s",
                job_id,
                bucket_name,
                DEFAULT_AWS_REGION,
            )
        s3_region = bucket_region or DEFAULT_AWS_REGION
        s3_config = Config(
            region_name=s3_region,
            retries={'max_attempts': 3, 'mode': 'standard'},
            connect_timeout=60,
            read_timeout=300,
            signature_version='s3v4'
        )
        s3 = boto3.client("s3", region_name=s3_region, config=s3_config)
        s3_key = f"speaker-analysis/{job_id}/audio.mp3"
        
        try:
            # Use multipart upload for files larger than 10 MB
            if audio_size_mb > 10:
                app.logger.info(f"Job {job_id}: Using multipart upload for large file")
                from boto3.s3.transfer import TransferConfig
                
                # Configure multipart upload
                transfer_config = TransferConfig(
                    multipart_threshold=10 * 1024 * 1024,  # 10 MB
                    max_concurrency=5,
                    multipart_chunksize=10 * 1024 * 1024,  # 10 MB chunks
                    use_threads=True
                )
                
                s3.upload_file(
                    str(audio_path), 
                    bucket_name, 
                    s3_key,
                    Config=transfer_config
                )
            else:
                # Standard upload for smaller files
                app.logger.info(f"Job {job_id}: Using standard upload")
                s3.upload_file(str(audio_path), bucket_name, s3_key)
            
            s3_uri = f"s3://{bucket_name}/{s3_key}"
            app.logger.info(f"Job {job_id}: Audio uploaded to {s3_uri}")
            
        except Exception as e:
            app.logger.error(f"Job {job_id}: S3 upload failed: {str(e)}")
            # Check if it's a network/timeout error
            error_msg = str(e)
            if "Connection" in error_msg or "timeout" in error_msg.lower():
                return jsonify({
                    "error": f"Network error while uploading to S3. The audio file ({audio_size_mb:.2f} MB) may be too large or the connection timed out. Please try with a shorter video or check your network connection."
                }), 500
            else:
                return jsonify({"error": f"Failed to upload audio to S3: {error_msg}"}), 500
        
        # Start AWS Transcribe job with speaker diarization
        transcribe_region = _resolve_transcribe_region(bucket_region)
        transcribe = boto3.client("transcribe", region_name=transcribe_region)
        app.logger.info(
            "Job %s: Using S3 region %s and Transcribe region %s",
            job_id,
            s3_region,
            transcribe_region,
        )
        transcribe_job_name = f"speaker-analysis-{job_id}"
        
        try:
            transcribe.start_transcription_job(
                TranscriptionJobName=transcribe_job_name,
                Media={"MediaFileUri": s3_uri},
                MediaFormat="mp3",
                LanguageCode="en-US",
                Settings={
                    "ShowSpeakerLabels": True,
                    "MaxSpeakerLabels": 10,
                }
            )
            app.logger.info(f"Job {job_id}: Transcription job started")
        except Exception as e:
            app.logger.error(f"Job {job_id}: Transcribe job failed: {str(e)}")
            return jsonify({"error": f"Failed to start transcription: {str(e)}"}), 500
        
        # Wait for transcription to complete (with timeout)
        import time
        max_wait_time = 600  # 10 minutes for longer videos
        start_time = time.time()
        check_count = 0
        
        while time.time() - start_time < max_wait_time:
            try:
                status = transcribe.get_transcription_job(TranscriptionJobName=transcribe_job_name)
                job_status = status["TranscriptionJob"]["TranscriptionJobStatus"]
                
                check_count += 1
                elapsed = int(time.time() - start_time)
                
                if job_status == "IN_PROGRESS":
                    if check_count % 6 == 0:  # Log every 30 seconds
                        app.logger.info(f"Job {job_id}: Transcription still in progress ({elapsed}s elapsed)...")
                elif job_status == "COMPLETED":
                    transcript_uri = status["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
                    app.logger.info(f"Job {job_id}: Transcription completed")
                    
                    # Download and parse transcript
                    import requests
                    transcript_response = requests.get(transcript_uri)
                    transcript_data = transcript_response.json()
                    
                    # Extract speaker segments
                    speakers = {}
                    segments = transcript_data.get("results", {}).get("speaker_labels", {}).get("segments", [])
                    items = transcript_data.get("results", {}).get("items", [])
                    
                    # Build speaker information
                    for segment in segments:
                        speaker_label = segment.get("speaker_label", "spk_0")
                        if speaker_label not in speakers:
                            speakers[speaker_label] = {
                                "id": speaker_label,
                                "label": speaker_label.replace("spk_", "Speaker "),
                                "segments": [],
                                "total_duration": 0.0,
                                "word_count": 0,
                                "sample_text": "",
                            }
                        
                        segment_start = float(segment.get("start_time", 0))
                        segment_end = float(segment.get("end_time", 0))
                        duration = segment_end - segment_start
                        
                        # Get text for this segment
                        segment_items = segment.get("items", [])
                        segment_text = ""
                        for item_ref in segment_items:
                            start_time = float(item_ref.get("start_time", 0))
                            end_time = float(item_ref.get("end_time", 0))
                            # Find matching item in items array
                            for item in items:
                                if (item.get("type") == "pronunciation" and 
                                    abs(float(item.get("start_time", -1)) - start_time) < 0.01):
                                    segment_text += item.get("alternatives", [{}])[0].get("content", "") + " "
                                    break
                        
                        speakers[speaker_label]["segments"].append({
                            "start": segment_start,
                            "end": segment_end,
                            "duration": duration,
                            "text": segment_text.strip()
                        })
                        speakers[speaker_label]["total_duration"] += duration
                        speakers[speaker_label]["word_count"] += len(segment_text.split())
                        
                        # Use first significant segment as sample text
                        if not speakers[speaker_label]["sample_text"] and len(segment_text.split()) > 5:
                            speakers[speaker_label]["sample_text"] = segment_text.strip()[:100]
                    
                    # Estimate speaker characteristics based on speech patterns
                    for speaker_id, speaker_data in speakers.items():
                        # Simple heuristic: estimate gender based on speaking patterns
                        # In production, you'd use actual voice analysis
                        avg_words_per_segment = (
                            speaker_data["word_count"] / len(speaker_data["segments"])
                            if speaker_data["segments"] else 0
                        )
                        
                        # Default characteristics (would need actual audio analysis for accuracy)
                        speaker_data["characteristics"] = {
                            "estimated_gender": "neutral",  # Would need voice pitch analysis
                            "estimated_age_group": "adult",  # Would need voice analysis
                            "speaking_rate": "normal" if 3 <= avg_words_per_segment <= 5 else "fast" if avg_words_per_segment > 5 else "slow",
                            "segment_count": len(speaker_data["segments"]),
                        }
                        
                        # Suggest voice options
                        speaker_data["suggested_voices"] = _get_suggested_voices_for_speaker(speaker_data)
                    
                    # Clean up transcribe job and S3 file
                    try:
                        transcribe.delete_transcription_job(TranscriptionJobName=transcribe_job_name)
                        s3.delete_object(Bucket=bucket_name, Key=s3_key)
                    except:
                        pass
                    
                    return jsonify({
                        "job_id": job_id,
                        "status": "completed",
                        "speakers": list(speakers.values()),
                        "speaker_count": len(speakers),
                        "total_duration": sum(s["total_duration"] for s in speakers.values()),
                        "message": "Speaker analysis completed successfully"
                    }), 200
                
                elif job_status == "FAILED":
                    failure_reason = status["TranscriptionJob"].get("FailureReason", "Unknown error")
                    app.logger.error(f"Job {job_id}: Transcription failed: {failure_reason}")
                    return jsonify({"error": f"Transcription failed: {failure_reason}"}), 500
                
                # Still processing, wait a bit
                time.sleep(5)
                
            except Exception as e:
                app.logger.error(f"Job {job_id}: Error checking transcription status: {str(e)}")
                return jsonify({"error": f"Error checking transcription: {str(e)}"}), 500
        
        # Timeout
        return jsonify({"error": "Transcription timeout after 10 minutes. Video may be too long."}), 504
        
    except Exception as e:
        app.logger.error(f"Job {job_id}: Unexpected error: {str(e)}")
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500
    
    finally:
        # Cleanup temp files
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass


def _get_suggested_voices_for_speaker(speaker_data: Dict[str, Any]) -> list:
    """Suggest appropriate Polly voices based on speaker characteristics, organized by category."""
    characteristics = speaker_data.get("characteristics", {})
    gender = characteristics.get("estimated_gender", "neutral")
    
    # Get all available voices
    all_voices = _list_neural_voices()
    
    # Filter to English voices only
    english_voices = [v for v in all_voices if v.get("language_code", "").startswith("en-")]
    
    # Categorize voices by age and gender
    voice_categories = {
        "adult_male": [],
        "adult_female": [],
        "older_male": [],
        "older_female": [],
        "child_male": [],
        "child_female": [],
        "kids": []
    }
    
    # Define voice categories
    adult_male_voices = ["Matthew", "Joey", "Stephen", "Kevin", "Gregory", "Brian", "Arthur"]
    adult_female_voices = ["Joanna", "Kendra", "Salli", "Ruth", "Kimberly", "Danielle", "Ivy", "Amy", "Emma", "Olivia", "Aria", "Ayanda", "Kajal", "Niamh", "Jasmine"]
    older_male_voices = []  # AWS doesn't have specific older male voices marked
    older_female_voices = []  # AWS doesn't have specific older female voices marked
    child_male_voices = ["Justin"]
    child_female_voices = ["Ivy"]
    kids_voices = ["Justin", "Ivy"]
    
    for voice in english_voices:
        voice_gender = voice.get("gender", "")
        voice_name = voice.get("name", "")
        voice_id = voice.get("id", "")
        lang_name = voice.get("language_name", "")
        engines = voice.get("engines", [])
        
        # Add engine info
        engine_suffix = ""
        if "generative" in engines:
            engine_suffix = " [Gen AI]"
        elif "long-form" in engines:
            engine_suffix = " [Long-form]"
        
        formatted_voice = {
            "voice_id": voice_id,
            "name": f"{voice_name} - {lang_name}{engine_suffix}",
            "language": voice.get("language_code", ""),
            "gender": voice_gender
        }
        
        # Categorize the voice
        if voice_id in child_male_voices:
            voice_categories["child_male"].append(formatted_voice)
        elif voice_id in child_female_voices:
            voice_categories["child_female"].append(formatted_voice)
        elif voice_id in older_male_voices:
            voice_categories["older_male"].append(formatted_voice)
        elif voice_id in older_female_voices:
            voice_categories["older_female"].append(formatted_voice)
        elif voice_id in adult_male_voices:
            voice_categories["adult_male"].append(formatted_voice)
        elif voice_id in adult_female_voices:
            voice_categories["adult_female"].append(formatted_voice)
        elif voice_gender == "Male":
            voice_categories["adult_male"].append(formatted_voice)
        elif voice_gender == "Female":
            voice_categories["adult_female"].append(formatted_voice)
    
    # Build the final list with category headers
    result = []
    
    # Add category headers as special entries
    def add_category(category_name, voices, header_text):
        if voices:
            # Add header
            result.append({
                "voice_id": f"header_{category_name}",
                "name": header_text,
                "language": "",
                "gender": "",
                "is_header": True
            })
            # Add voices
            result.extend(voices)
    
    # Order based on estimated gender (put most relevant first)
    if gender == "male":
        add_category("adult_male", voice_categories["adult_male"], "━━━ ADULT MALE ━━━")
        add_category("older_male", voice_categories["older_male"], "━━━ OLDER MALE ━━━")
        add_category("adult_female", voice_categories["adult_female"], "━━━ ADULT FEMALE ━━━")
        add_category("older_female", voice_categories["older_female"], "━━━ OLDER FEMALE ━━━")
        add_category("child_male", voice_categories["child_male"], "━━━ CHILD MALE ━━━")
        add_category("child_female", voice_categories["child_female"], "━━━ CHILD FEMALE ━━━")
    elif gender == "female":
        add_category("adult_female", voice_categories["adult_female"], "━━━ ADULT FEMALE ━━━")
        add_category("older_female", voice_categories["older_female"], "━━━ OLDER FEMALE ━━━")
        add_category("adult_male", voice_categories["adult_male"], "━━━ ADULT MALE ━━━")
        add_category("older_male", voice_categories["older_male"], "━━━ OLDER MALE ━━━")
        add_category("child_female", voice_categories["child_female"], "━━━ CHILD FEMALE ━━━")
        add_category("child_male", voice_categories["child_male"], "━━━ CHILD MALE ━━━")
    else:
        # Default order for unknown gender
        add_category("adult_male", voice_categories["adult_male"], "━━━ ADULT MALE ━━━")
        add_category("adult_female", voice_categories["adult_female"], "━━━ ADULT FEMALE ━━━")
        add_category("older_male", voice_categories["older_male"], "━━━ OLDER MALE ━━━")
        add_category("older_female", voice_categories["older_female"], "━━━ OLDER FEMALE ━━━")
        add_category("child_male", voice_categories["child_male"], "━━━ CHILD MALE ━━━")
        add_category("child_female", voice_categories["child_female"], "━━━ CHILD FEMALE ━━━")
    
    return result


@app.route("/replace-multi-speaker-audio", methods=["POST"])
def replace_multi_speaker_audio() -> Any:
    """
    Replace audio in video with synthetic voices for multiple speakers.
    Expects JSON with speaker voice mappings.
    """
    import tempfile
    import shutil
    import subprocess
    import uuid
    from pathlib import Path
    
    if "video" not in request.files:
        return jsonify({"error": "No video file provided"}), 400
    
    video_file = request.files["video"]
    if not video_file.filename:
        return jsonify({"error": "Empty filename"}), 400
    
    # Get speaker voice mappings from form data
    speaker_mappings_json = request.form.get("speaker_mappings")
    if not speaker_mappings_json:
        return jsonify({"error": "No speaker_mappings provided"}), 400
    
    # Get translation settings
    translate_enabled = request.form.get("translate_enabled", "false").lower() == "true"
    source_language = request.form.get("source_language", "auto")
    target_language = request.form.get("target_language", "en")
    target_polly_language = request.form.get("target_polly_language", "en-US")
    
    try:
        speaker_mappings = json.loads(speaker_mappings_json)
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid speaker_mappings JSON"}), 400
    
    job_id = str(uuid.uuid4())
    temp_dir = Path(tempfile.mkdtemp(prefix=f"multi_speaker_{job_id}_"))
    
    app.logger.info(f"Job {job_id}: Translation enabled: {translate_enabled}, {source_language} -> {target_language}")
    
    try:
        # Save uploaded video
        video_path = temp_dir / "input_video.mp4"
        video_file.save(str(video_path))
        app.logger.info(f"Job {job_id}: Video saved")
        
        # Extract audio
        original_audio_path = temp_dir / "original_audio.wav"
        ffmpeg_cmd = [
            FFMPEG_PATH, "-i", str(video_path),
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            str(original_audio_path), "-y"
        ]
        subprocess.run(ffmpeg_cmd, capture_output=True, check=True)
        app.logger.info(f"Job {job_id}: Audio extracted")
        
        # Get speaker segments from the analysis data passed in speaker_mappings
        # Each mapping should have: speaker_id, voice_id, segments
        
        # Generate synthetic audio for each speaker's segments
        synthetic_segments = []
        
        for mapping in speaker_mappings:
            speaker_id = mapping.get("speaker_id")
            voice_id = mapping.get("voice_id", "Joanna")
            segments = mapping.get("segments", [])
            
            app.logger.info(f"Job {job_id}: Processing {len(segments)} segments for {speaker_id} with voice {voice_id}")
            
            for idx, segment in enumerate(segments):
                text = segment.get("text", "").strip()
                start_time = float(segment.get("start", 0))
                end_time = float(segment.get("end", 0))
                
                if not text:
                    continue
                
                # Translate text if enabled
                if translate_enabled:
                    original_text = text
                    text = _translate_text(text, source_language, target_language)
                    app.logger.info(f"Job {job_id}: Translated '{original_text[:50]}...' -> '{text[:50]}...'")
                
                # Synthesize this segment using the best available engine with natural SSML
                try:
                    best_engine = _get_best_engine_for_voice(voice_id)
                    
                    # Create natural-sounding SSML for human-like speech
                    natural_ssml = _create_natural_ssml(text, best_engine)
                    
                    # Build synthesis parameters
                    synth_params = {
                        "Text": natural_ssml,
                        "TextType": "ssml",
                        "OutputFormat": "mp3",
                        "VoiceId": voice_id,
                        "Engine": best_engine,
                        "LanguageCode": target_polly_language
                    }
                    
                    # Try with conversational style first for supported voices
                    synthesis_attempted = False
                    response = None
                    
                    # Voices that support conversational style
                    if voice_id in ["Matthew", "Joanna", "Ruth", "Stephen", "Kevin", "Salli", "Joey"]:
                        try:
                            # Wrap in conversational style for more natural delivery
                            natural_ssml_with_style = natural_ssml.replace(
                                '<speak>',
                                '<speak><amazon:domain name="conversational">'
                            ).replace('</speak>', '</amazon:domain></speak>')
                            synth_params_style = synth_params.copy()
                            synth_params_style["Text"] = natural_ssml_with_style
                            response = polly.synthesize_speech(**synth_params_style)
                            synthesis_attempted = True
                        except Exception as style_error:
                            app.logger.warning(f"Job {job_id}: Conversational style failed for {voice_id}, trying without style: {str(style_error)}")
                            synthesis_attempted = False
                    
                    # Fallback to regular SSML if style failed or not supported
                    if not synthesis_attempted:
                        response = polly.synthesize_speech(**synth_params)
                    
                    # Save segment audio as MP3 first
                    segment_mp3_path = temp_dir / f"segment_{speaker_id}_{idx}.mp3"
                    with open(segment_mp3_path, "wb") as f:
                        f.write(response["AudioStream"].read())
                    
                    # Convert MP3 to WAV with consistent format (16kHz, mono)
                    segment_wav_path = temp_dir / f"segment_{speaker_id}_{idx}.wav"
                    convert_cmd = [
                        FFMPEG_PATH, "-i", str(segment_mp3_path),
                        "-ar", "16000", "-ac", "1", "-acodec", "pcm_s16le",
                        str(segment_wav_path), "-y"
                    ]
                    subprocess.run(convert_cmd, capture_output=True, check=True)
                    
                    synthetic_segments.append({
                        "audio_file": segment_wav_path,
                        "start_time": start_time,
                        "end_time": end_time,
                        "speaker_id": speaker_id,
                    })
                    
                except Exception as e:
                    app.logger.error(f"Job {job_id}: Failed to synthesize segment {idx} for {speaker_id}: {str(e)}")
                    # Log more details about the error
                    import traceback
                    app.logger.error(f"Job {job_id}: Traceback: {traceback.format_exc()}")
                    continue
        
        app.logger.info(f"Job {job_id}: Generated {len(synthetic_segments)} synthetic audio segments")
        
        if not synthetic_segments:
            app.logger.error(f"Job {job_id}: No segments were successfully synthesized")
            return jsonify({"error": "Failed to synthesize any audio segments. Check if text content is valid."}), 500
        
        # Build FFmpeg complex filter to mix all segments at their timestamps
        # This is complex - we'll create a silent audio track and overlay each segment
        
        # Get video duration
        probe_cmd = [
            FFPROBE_PATH, "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)
        ]
        duration_result = subprocess.run(probe_cmd, capture_output=True, text=True)
        video_duration = float(duration_result.stdout.strip())
        
        # Instead of complex filter, use a simpler approach:
        # For each segment, create a full-length audio file with silence and the segment at the right time
        app.logger.info(f"Job {job_id}: Creating positioned audio segments...")
        
        positioned_segments = []
        for idx, segment in enumerate(synthetic_segments):
            positioned_path = temp_dir / f"positioned_{idx}.wav"
            start_time = segment['start_time']
            
            # Get the duration of the segment audio
            probe_cmd = [
                FFPROBE_PATH, "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(segment['audio_file'])
            ]
            probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
            try:
                segment_duration = float(probe_result.stdout.strip())
            except:
                segment_duration = segment['end_time'] - segment['start_time']
            
            # Calculate silence after
            end_time = start_time + segment_duration
            silence_after = max(0.1, video_duration - end_time)
            
            # Create a file with silence before the segment, then the audio, then silence after
            # Handle case where segment starts at beginning (no silence before)
            if start_time < 0.1:  # Starts at beginning
                position_cmd = [
                    FFMPEG_PATH,
                    "-i", str(segment['audio_file']),  # The actual audio
                    "-f", "lavfi", "-t", str(silence_after), "-i", "anullsrc=r=16000:cl=mono",  # Silence after
                    "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1[outa]",
                    "-map", "[outa]",
                    "-t", str(video_duration),
                    str(positioned_path), "-y"
                ]
            else:  # Segment starts later, need silence before
                position_cmd = [
                    FFMPEG_PATH,
                    "-f", "lavfi", "-t", str(start_time), "-i", "anullsrc=r=16000:cl=mono",  # Silence before
                    "-i", str(segment['audio_file']),  # The actual audio
                    "-f", "lavfi", "-t", str(silence_after), "-i", "anullsrc=r=16000:cl=mono",  # Silence after
                    "-filter_complex", "[0:a][1:a][2:a]concat=n=3:v=0:a=1[outa]",
                    "-map", "[outa]",
                    "-t", str(video_duration),
                    str(positioned_path), "-y"
                ]
            
            result = subprocess.run(position_cmd, capture_output=True, text=True)
            if result.returncode == 0:
                positioned_segments.append(positioned_path)
                app.logger.info(f"Job {job_id}: Positioned segment {idx} at {start_time}s (duration: {segment_duration}s)")
            else:
                app.logger.error(f"Job {job_id}: Failed to position segment {idx}: {result.stderr}")
                app.logger.error(f"Job {job_id}: FFmpeg command: {' '.join(position_cmd)}")
        
        if not positioned_segments:
            app.logger.error(f"Job {job_id}: No segments could be positioned out of {len(synthetic_segments)} synthesized segments")
            return jsonify({"error": f"No audio segments could be positioned. Synthesized {len(synthetic_segments)} segments but positioning failed. Check video format and audio compatibility."}), 500
        
        # Now mix all positioned segments together using amix
        app.logger.info(f"Job {job_id}: Mixing {len(positioned_segments)} positioned segments...")
        
        mixed_audio = temp_dir / "mixed_synthetic.wav"
        mix_cmd = [FFMPEG_PATH]
        
        # Add all positioned segments as inputs
        for seg_file in positioned_segments:
            mix_cmd.extend(["-i", str(seg_file)])
        
        # Build the amix filter
        if len(positioned_segments) == 1:
            # Just copy the single segment
            mix_cmd.extend(["-c:a", "pcm_s16le", "-ar", "16000", str(mixed_audio), "-y"])
        else:
            # Mix all inputs
            filter_str = f"amix=inputs={len(positioned_segments)}:duration=longest:normalize=0"
            mix_cmd.extend([
                "-filter_complex", filter_str,
                "-c:a", "pcm_s16le", "-ar", "16000",
                str(mixed_audio), "-y"
            ])
        
        subprocess.run(mix_cmd, capture_output=True, check=True)
        app.logger.info(f"Job {job_id}: Mixed synthetic audio created")
        
        # Replace audio in video
        output_video = temp_dir / "output_with_synthetic_audio.mp4"
        replace_cmd = [
            FFMPEG_PATH, "-i", str(video_path), "-i", str(mixed_audio),
            "-c:v", "copy", "-map", "0:v:0", "-map", "1:a:0",
            "-shortest", str(output_video), "-y"
        ]
        subprocess.run(replace_cmd, capture_output=True, check=True)
        app.logger.info(f"Job {job_id}: Audio replaced in video")
        
        # Read output video and return as base64
        with open(output_video, "rb") as f:
            video_data = f.read()
        
        video_base64 = base64.b64encode(video_data).decode("utf-8")
        
        return jsonify({
            "job_id": job_id,
            "status": "completed",
            "video": video_base64,
            "video_size_bytes": len(video_data),
            "segments_processed": len(synthetic_segments),
            "message": "Multi-speaker audio replacement completed successfully"
        }), 200
        
    except subprocess.CalledProcessError as e:
        app.logger.error(f"Job {job_id}: FFmpeg error: {e.stderr}")
        return jsonify({"error": f"FFmpeg processing failed: {e.stderr}"}), 500
    except Exception as e:
        app.logger.error(f"Job {job_id}: Unexpected error: {str(e)}")
        return jsonify({"error": f"Processing failed: {str(e)}"}), 500
    finally:
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, debug=False)

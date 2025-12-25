from __future__ import annotations

import json
import math
import os
import re
import textwrap
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, request
from flask_cors import CORS

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from unidecode import unidecode
from shared.env_loader import load_environment

load_environment()

app = Flask(__name__)
CORS(app)

DEFAULT_AWS_REGION = os.getenv("AWS_REGION")
if not DEFAULT_AWS_REGION:
    raise RuntimeError("Set AWS_REGION before starting movie script creation service")

BEDROCK_REGION = os.getenv("BEDROCK_REGION", DEFAULT_AWS_REGION)
MODEL_ID = os.getenv("MOVIE_SCRIPT_MODEL_ID", "meta.llama3-70b-instruct-v1:0")
MIN_TOKENS = int(os.getenv("MOVIE_SCRIPT_MIN_TOKENS", "3500"))
TARGET_WORDS = max(1, math.ceil(MIN_TOKENS * 0.75))
MAX_TOKENS = int(os.getenv("MOVIE_SCRIPT_MAX_TOKENS", "4096"))
TEMPERATURE = float(os.getenv("MOVIE_SCRIPT_TEMPERATURE", "0.65"))
TOP_P = float(os.getenv("MOVIE_SCRIPT_TOP_P", "0.9"))
SEGMENT_LENGTH_MINUTES = int(os.getenv("MOVIE_SCRIPT_SEGMENT_MINUTES", "10"))
DEFAULT_RUNTIME_MINUTES = int(os.getenv("MOVIE_SCRIPT_DEFAULT_RUNTIME", "130"))
MAX_SEGMENTS = int(os.getenv("MOVIE_SCRIPT_MAX_SEGMENTS", "18"))
TRANSLATE_REGION = os.getenv("TRANSLATE_REGION", DEFAULT_AWS_REGION)
MAX_TRANSLATE_CHARS = max(1000, min(5000, int(os.getenv("AWS_TRANSLATE_MAX_CHARS", "4500"))))

AWS_TRANSLATE_LANGUAGES: Dict[str, str] = {
    "af": "Afrikaans",
    "sq": "Albanian",
    "am": "Amharic",
    "ar": "Arabic",
    "hy": "Armenian",
    "az": "Azerbaijani",
    "bn": "Bengali",
    "bs": "Bosnian",
    "bg": "Bulgarian",
    "ca": "Catalan",
    "zh": "Chinese (Simplified)",
    "zh-TW": "Chinese (Traditional)",
    "hr": "Croatian",
    "cs": "Czech",
    "da": "Danish",
    "fa-AF": "Dari",
    "nl": "Dutch",
    "en": "English (default)",
    "et": "Estonian",
    "fa": "Farsi (Persian)",
    "fi": "Finnish",
    "fr": "French",
    "fr-CA": "French (Canada)",
    "ka": "Georgian",
    "de": "German",
    "el": "Greek",
    "gu": "Gujarati",
    "ht": "Haitian Creole",
    "ha": "Hausa",
    "he": "Hebrew",
    "hi": "Hindi",
    "hu": "Hungarian",
    "is": "Icelandic",
    "id": "Indonesian",
    "it": "Italian",
    "ja": "Japanese",
    "kn": "Kannada",
    "kk": "Kazakh",
    "ko": "Korean",
    "lv": "Latvian",
    "lt": "Lithuanian",
    "mk": "Macedonian",
    "ms": "Malay",
    "ml": "Malayalam",
    "mr": "Marathi",
    "mn": "Mongolian",
    "no": "Norwegian",
    "ps": "Pashto",
    "pl": "Polish",
    "pt": "Portuguese (Brazil)",
    "pt-PT": "Portuguese (Portugal)",
    "pa": "Punjabi",
    "ro": "Romanian",
    "ru": "Russian",
    "sr": "Serbian",
    "si": "Sinhala",
    "sk": "Slovak",
    "sl": "Slovenian",
    "so": "Somali",
    "es": "Spanish",
    "es-MX": "Spanish (Mexico)",
    "sw": "Swahili",
    "sv": "Swedish",
    "tl": "Tagalog",
    "ta": "Tamil",
    "te": "Telugu",
    "th": "Thai",
    "tr": "Turkish",
    "uk": "Ukrainian",
    "ur": "Urdu",
    "uz": "Uzbek",
    "vi": "Vietnamese",
    "cy": "Welsh",
}


def _build_language_config() -> Dict[str, Dict[str, str]]:
    config: Dict[str, Dict[str, str]] = {}
    for code, label in AWS_TRANSLATE_LANGUAGES.items():
        if code == "en":
            config[code] = {
                "label": label,
                "brief_line": "Dialogue language: English.",
                "segment_guidance": (
                    "Write all dialogue, scene directions, and on-screen text in polished English."
                ),
            }
        else:
            config[code] = {
                "label": label,
                "brief_line": f"Dialogue language: {label}.",
                "segment_guidance": (
                    f"Write dialogue and on-screen text in natural {label} while keeping stage directions in English."
                ),
            }
    return config


LANGUAGE_CONFIG = _build_language_config()
LANGUAGE_CODE_LOOKUP = {code.lower(): code for code in LANGUAGE_CONFIG.keys()}
TRANSLATE_LANGUAGE_CODES = {code: code for code in LANGUAGE_CONFIG.keys()}

CHARACTER_HEADING_PATTERN = re.compile(r'^[A-Z][A-Z0-9 .\'"()/\-]{0,60}$')

try:
    bedrock_runtime = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)
except Exception as exc:  # pragma: no cover - dependency on AWS credentials
    app.logger.warning("Unable to create bedrock-runtime client: %s", exc)
    bedrock_runtime = None

try:
    translate_client = boto3.client("translate", region_name=TRANSLATE_REGION)
except Exception as exc:  # pragma: no cover - depends on AWS credentials
    app.logger.warning(
        "Unable to create translate client in region %s: %s", TRANSLATE_REGION, exc
    )
    translate_client = None

SYSTEM_PROMPT = textwrap.dedent(
        f"""
        You are an award-winning showrunner and narrative designer who architects internationally appealing feature films.
        Analyse every creative brief with rigor before you write. Surface cultural research, mythic structure, character arcs,
        and audience retention tactics. Then craft a professional, industry-formatted screenplay that comfortably exceeds {MIN_TOKENS}
        tokens (roughly {TARGET_WORDS}+ words). Use ACT I, ACT II A, ACT II B, and ACT III headings, sluglines, action lines,
        dialogue, and transitions. Weave in set pieces that resonate with the specified regions and audience cohorts.

        Output requirements:
            • Provide only the finished screenplay — no analysis, summaries, commentary, token counts, or metadata.
            • Do not acknowledge these instructions or describe the writing process.
            • Maintain screenplay formatting with scene headings, character cues, and dialogue.
            • Introduce distinctive character names and keep them consistent across every segment of the story.

        Continue expanding the screenplay until it comfortably exceeds the minimum token target. Do not mention any model names.
        """
).strip()


def _safe_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def _compose_brief(payload: Dict[str, Any]) -> Dict[str, Any]:
    genres = _safe_list(payload.get("genres")) or _safe_list(payload.get("genre"))
    tones = _safe_list(payload.get("moods")) or _safe_list(payload.get("mood"))
    audience = _safe_list(payload.get("audience"))
    regions = _safe_list(payload.get("regions")) or _safe_list(payload.get("region"))
    era = str(payload.get("era") or payload.get("period") or "").strip()
    runtime = payload.get("targetRuntimeMinutes") or payload.get("runtimeMinutes")
    rating = payload.get("targetRating") or payload.get("rating")
    franchise = str(payload.get("franchiseContext") or "").strip()
    language = _normalise_language(payload.get("language"))

    title = str(payload.get("title") or "Untitled Feature")
    logline = str(payload.get("logline") or "Develop an original, compelling logline aligned to the brief.")
    guidance = str(payload.get("additionalGuidance") or payload.get("brief") or "").strip()

    brief_lines = [
        f"Project title: {title}",
        f"Logline or core idea: {logline}",
        f"Primary genres: {', '.join(genres) if genres else 'Blend genres for a fresh cinematic voice.'}",
        f"Tonality & moods: {', '.join(tones) if tones else 'Balance drama, humour, suspense, and awe as appropriate.'}",
        f"Target audience cohorts: {', '.join(audience) if audience else 'Design for a four-quadrant global audience.'}",
        f"Priority regions & cultural references: {', '.join(regions) if regions else 'Craft for worldwide resonance with localised authenticity.'}",
    ]

    if era:
        brief_lines.append(f"Era or setting: {era}")
    if runtime:
        brief_lines.append(f"Target runtime: {runtime} minutes")
    if rating:
        brief_lines.append(f"Intended rating or compliance: {rating}")
    if franchise:
        brief_lines.append(f"Franchise / IP continuity notes: {franchise}")
    if guidance:
        brief_lines.append(f"Additional guidance: {guidance}")

    brief_lines.append(language["brief_line"])

    return {
        "title": title,
        "logline": logline,
        "genres": genres,
        "tones": tones,
        "audience": audience,
        "regions": regions,
        "era": era,
        "runtime": runtime,
        "rating": rating,
        "franchise": franchise,
        "guidance": guidance,
        "language": language,
        "brief_text": "\n".join(brief_lines),
    }


def _normalise_language(raw_language: Any) -> Dict[str, str]:
    if isinstance(raw_language, dict):
        candidate = raw_language.get("value") or raw_language.get("code") or raw_language.get("name")
    else:
        candidate = raw_language

    default_code = "en"
    if candidate is None:
        canonical = default_code
    else:
        candidate_str = str(candidate).strip()
        if not candidate_str:
            canonical = default_code
        else:
            lowered = candidate_str.lower()
            canonical = LANGUAGE_CODE_LOOKUP.get(lowered)
            if not canonical:
                alias_lookup = {
                    "english": "en",
                    "en-us": "en",
                    "en-gb": "en",
                    "hindi": "hi",
                    "hinglish": "hi",
                    "spanish": "es",
                    "spanish (mexico)": "es-MX",
                    "french": "fr",
                    "french (canada)": "fr-CA",
                    "german": "de",
                    "portuguese": "pt",
                    "portuguese (portugal)": "pt-PT",
                    "chinese": "zh",
                    "chinese (simplified)": "zh",
                    "chinese (traditional)": "zh-TW",
                }
                canonical = alias_lookup.get(lowered)
            if not canonical:
                canonical = next(
                    (code for code, config in LANGUAGE_CONFIG.items() if lowered == config["label"].lower()),
                    None,
                )
            canonical = canonical or default_code

    config = LANGUAGE_CONFIG.get(canonical, LANGUAGE_CONFIG[default_code])
    return {"code": canonical, **config}


def _parse_runtime_minutes(raw_runtime: Any) -> Optional[int]:
    if raw_runtime is None:
        return None
    if isinstance(raw_runtime, (int, float)):
        if raw_runtime <= 0:
            return None
        return int(raw_runtime)
    text = str(raw_runtime).strip()
    if not text:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    if not digits:
        return None
    value = int(digits)
    return value if value > 0 else None


def _determine_segments(runtime_minutes: int) -> int:
    segments = max(1, math.ceil(runtime_minutes / SEGMENT_LENGTH_MINUTES))
    return min(segments, MAX_SEGMENTS)


def _truncate_context(script_text: str, limit: int = 4000) -> str:
    text = script_text.strip()
    if len(text) <= limit:
        return text
    return text[-limit:]


def _build_segment_prompt(
    brief: Dict[str, Any],
    segment_index: int,
    total_segments: int,
    runtime_minutes: int,
    script_so_far: str,
    language: Dict[str, str],
) -> str:
    segment_number = segment_index + 1
    start_minute = segment_index * SEGMENT_LENGTH_MINUTES
    end_minute = min(runtime_minutes, segment_number * SEGMENT_LENGTH_MINUTES)
    if segment_number == total_segments:
        end_minute = runtime_minutes

    context_instructions = ""
    if script_so_far.strip():
        context_instructions = textwrap.dedent(
            f"""
            Script so far (maintain continuity, do not repeat scenes or dialogue):
            {_truncate_context(script_so_far)}
            """
        ).strip()
    else:
        context_instructions = (
            "This is the opening segment. Establish the core world, introduce principal characters with memorable names, "
            "and ignite the inciting incident while setting tone and stakes."
        )

    segment_notes = (
        f"Write Segment {segment_number} of {total_segments}, covering approximately minutes {start_minute + 1} "
        f"through {end_minute} of the film (roughly {SEGMENT_LENGTH_MINUTES} minutes of screen time). "
        "Advance the plot with cinematic pacing, keeping character motivations and arcs coherent."
    )
    if segment_number == total_segments:
        segment_notes += (
            " This is the final segment—drive the climax, resolve character arcs, and deliver a satisfying denouement."  # noqa: E501
        )

    language_instructions = language.get("segment_guidance") or LANGUAGE_CONFIG["en"]["segment_guidance"]

    return textwrap.dedent(
        f"""
        {brief["brief_text"]}

        {segment_notes}

        {context_instructions}

        Language guidance:
        {language_instructions}

        Output only screenplay pages for this segment using proper scene headings, action lines, and dialogue. Do not include recaps, analysis, or meta commentary. Stop once this segment concludes.
        """
    ).strip()


def _is_scene_heading(text: str) -> bool:
    stripped = text.strip()
    return stripped.startswith(("INT.", "EXT.", "EST.", "INT/", "EXT/", "FADE", "CUT", "DISSOLVE"))


def _is_character_line(value: str) -> bool:
    stripped = value.strip()
    if not stripped:
        return False
    if _is_scene_heading(stripped):
        return False
    if stripped.endswith(":") and stripped == stripped.upper():
        return True
    if CHARACTER_HEADING_PATTERN.match(stripped):
        return True
    return False


def _translate_dialogue_line(text: str, target_language: str, romanize: bool) -> str:
    if translate_client is None:
        return text

    stripped = text.lstrip()
    if not stripped:
        return text
    prefix = text[: len(text) - len(stripped)]

    try:
        response = translate_client.translate_text(
            Text=stripped,
            SourceLanguageCode="en",
            TargetLanguageCode=target_language,
        )
        translated = response.get("TranslatedText", stripped)
    except (BotoCoreError, ClientError) as exc:
        app.logger.warning("Dialogue translation failed: %s", exc)
        return text
    except Exception as exc:  # pragma: no cover - defensive
        app.logger.warning("Unexpected dialogue translation error: %s", exc)
        return text

    if romanize:
        translated = unidecode(translated)

    return f"{prefix}{translated}"


def _chunk_text_for_translate(text: str, max_chars: int) -> List[str]:
    if not text:
        return [""]

    chunks: List[str] = []
    length = len(text)
    start = 0

    while start < length:
        end = min(start + max_chars, length)
        if end < length:
            # Try to break at a newline closest to the limit, otherwise at whitespace.
            newline_idx = text.rfind("\n", start + int(max_chars * 0.5), end)
            whitespace_idx = text.rfind(" ", start + int(max_chars * 0.5), end)
            candidate = max(newline_idx, whitespace_idx)
            if candidate != -1 and candidate >= start:
                end = min(candidate + 1, length)

        chunk = text[start:end]
        if not chunk:
            break
        chunks.append(chunk)
        start = end

    return chunks if chunks else [text]


def _translate_full_text(script_text: str, target_language: str) -> str:
    if translate_client is None or not script_text.strip():
        return script_text

    translated_chunks: List[str] = []
    for chunk in _chunk_text_for_translate(script_text, MAX_TRANSLATE_CHARS):
        try:
            response = translate_client.translate_text(
                Text=chunk,
                SourceLanguageCode="en",
                TargetLanguageCode=target_language,
            )
            translated_chunks.append(response.get("TranslatedText", chunk))
        except (BotoCoreError, ClientError) as exc:
            app.logger.warning("Chunk translation failed; returning original chunk: %s", exc)
            translated_chunks.append(chunk)
        except Exception as exc:  # pragma: no cover - defensive
            app.logger.warning("Unexpected chunk translation error; returning original chunk: %s", exc)
            translated_chunks.append(chunk)

    return "".join(translated_chunks)


def _translate_dialogue_segments(script_text: str, language: Dict[str, str]) -> str:
    code = (language or {}).get("code", "en")
    target_language = TRANSLATE_LANGUAGE_CODES.get(code)

    if not target_language or target_language.lower().startswith("en"):
        return script_text

    if translate_client is None:
        app.logger.warning("Translate client unavailable; skipping dialogue translation")
        return script_text

    if os.getenv("MOVIE_SCRIPT_TRANSLATE_FULL", "true").lower() in {"1", "true", "yes"}:
        full_translation = _translate_full_text(script_text, target_language)
        if full_translation != script_text:
            return full_translation

    lines = script_text.splitlines()
    translated_lines: List[str] = []
    in_dialogue = False
    romanize = bool(language.get("romanize"))

    for line in lines:
        stripped = line.strip()

        if not stripped:
            in_dialogue = False
            translated_lines.append(line)
            continue

        if _is_character_line(stripped):
            in_dialogue = True
            translated_lines.append(line)
            continue

        if in_dialogue and not stripped.startswith("("):
            translated_lines.append(_translate_dialogue_line(line, target_language, romanize))
            continue

        translated_lines.append(line)

    return "\n".join(translated_lines)


def _invoke_bedrock(prompt: str) -> Dict[str, Any]:
    if bedrock_runtime is None:
        raise RuntimeError("Bedrock runtime client is not configured")

    combined_prompt = (
        "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n"
        f"{SYSTEM_PROMPT}\n"
        "<|eot_id|><|start_header_id|>user<|end_header_id|>\n"
        f"{prompt}\n"
        "<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n"
    )

    body = {
        "prompt": combined_prompt,
        "max_gen_len": MAX_TOKENS,
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
    }
    try:
        response = bedrock_runtime.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps(body),
            accept="application/json",
            contentType="application/json",
        )
    except (BotoCoreError, ClientError) as exc:  # pragma: no cover - depends on AWS
        error_payload = getattr(exc, "response", None)
        app.logger.error("Bedrock invocation failed: %s | payload=%s", exc, error_payload)
        raise RuntimeError("Language model invocation failed") from exc

    return json.loads(response["body"].read())


def _extract_text(response_body: Dict[str, Any]) -> str:
    if not response_body:
        return ""

    def _from_content(value: Any) -> str:
        if isinstance(value, list):
            return "".join(_from_content(item) for item in value)
        if isinstance(value, dict):
            collected: List[str] = []
            if value.get("text"):
                collected.append(str(value.get("text", "")))
            if value.get("result"):
                collected.append(str(value.get("result", "")))
            if value.get("content"):
                collected.append(_from_content(value.get("content")))
            return "".join(collected)
        return str(value)

    for key in ("generation", "output", "result"):
        if isinstance(response_body.get(key), str):
            return str(response_body[key])

    if isinstance(response_body.get("generations"), list):
        return "".join(
            str(item.get("text", "")) for item in response_body["generations"] if isinstance(item, dict)
        )

    if isinstance(response_body.get("outputs"), list):
        return "".join(_from_content(item) for item in response_body.get("outputs", []))

    if response_body.get("content"):
        return _from_content(response_body.get("content"))

    if isinstance(response_body.get("messages"), list):
        for message in response_body["messages"]:
            if isinstance(message, dict) and message.get("role") == "assistant":
                return _from_content(message.get("content"))

    return ""


def _split_sections(raw_text: str) -> Dict[str, str]:
    text = raw_text or ""
    lowered = text.lower()
    analysis_marker = "<<analysis>>"
    script_marker = "<<script>>"

    if analysis_marker in lowered and script_marker in lowered:
        idx_analysis = lowered.index(analysis_marker)
        idx_script = lowered.index(script_marker)
        analysis_block = text[idx_analysis + len("<<ANALYSIS>>") : idx_script]
        end_idx = lowered.find("<<end>>", idx_script)
        if end_idx == -1:
            end_idx = len(text)
        script_block = text[idx_script + len("<<SCRIPT>>") : end_idx]
        return {
            "analysis": analysis_block.strip(),
            "script": script_block.strip(),
        }

    return {
        "analysis": "",
        "script": text.strip(),
    }


@app.route("/health", methods=["GET"])
def health() -> Any:
    return jsonify(
        {
            "status": "ok" if bedrock_runtime else "degraded",
            "modelId": MODEL_ID,
            "region": BEDROCK_REGION,
            "minTokens": MIN_TOKENS,
            "maxTokens": MAX_TOKENS,
        }
    )


@app.route("/generate-script", methods=["POST"])
def generate_script() -> Any:
    if request.content_type != "application/json":
        return jsonify({"error": "Request must be JSON"}), 415

    payload: Dict[str, Any] = request.get_json(silent=True) or {}
    brief = _compose_brief(payload)

    runtime_minutes = _parse_runtime_minutes(brief.get("runtime")) or DEFAULT_RUNTIME_MINUTES
    total_segments = _determine_segments(runtime_minutes)

    script_segments: List[str] = []
    script_so_far = ""

    for segment_index in range(total_segments):
        prompt = _build_segment_prompt(
            brief=brief,
            segment_index=segment_index,
            total_segments=total_segments,
            runtime_minutes=runtime_minutes,
            script_so_far=script_so_far,
            language=brief["language"],
        )

        try:
            response_body = _invoke_bedrock(prompt)
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 502

        raw_text = _extract_text(response_body)
        if not raw_text.strip():
            app.logger.warning(
                "Empty generation received from Bedrock for segment %s | response=%s",
                segment_index + 1,
                response_body,
            )
            continue

        segment_script = _split_sections(raw_text).get("script", "").strip()
        if not segment_script:
            app.logger.warning(
                "Parsed empty script for segment %s | raw_text=%s",
                segment_index + 1,
                raw_text,
            )
            continue

        script_segments.append(segment_script)
        script_so_far = f"{script_so_far}\n\n{segment_script}".strip()

    if not script_segments:
        return jsonify({"error": "Unable to generate screenplay segments"}), 502

    full_script = "\n\n".join(script_segments).strip()
    full_script = _translate_dialogue_segments(full_script, brief["language"])

    return jsonify(
        {
            "title": brief["title"],
            "script": full_script,
            "language": brief["language"].get("label", "English (default)"),
            "runtimeMinutes": runtime_minutes,
        }
    )


if __name__ == "__main__":  # pragma: no cover - manual execution utility
    port = int(os.getenv("PORT", "5005"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    reload = os.getenv("RELOADER", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=reload)

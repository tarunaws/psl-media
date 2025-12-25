# Synthetic Voiceover Service - Complete Technical Reference

**MediaGenAI Platform - Service Documentation**  
**Document Version:** 1.0  
**Service Port:** 5003  
**Last Updated:** October 21, 2025

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [System Components](#system-components)
4. [Backend Architecture Deep Dive](#backend-architecture-deep-dive)
5. [Frontend Architecture Deep Dive](#frontend-architecture-deep-dive)
6. [Data Flow & Processing Pipeline](#data-flow--processing-pipeline)
7. [AWS Integration](#aws-integration)
8. [API Reference](#api-reference)
9. [Configuration Management](#configuration-management)
10. [Deployment & Operations](#deployment--operations)
11. [Troubleshooting Guide](#troubleshooting-guide)
12. [Performance Optimization](#performance-optimization)

---

## 1. Executive Summary

### 1.1 Service Purpose

The Synthetic Voiceover Service is a sophisticated AI-powered text-to-speech platform that combines Large Language Models (LLMs) with neural text-to-speech synthesis to create expressive, natural-sounding voiceovers from simple text prompts or scripts.

**Core Capabilities:**
- **GenAI SSML Generation**: Uses AWS Bedrock (Llama3-70B) to transform plain text into expressive SSML scripts with prosody, emphasis, and pacing
- **Neural TTS Synthesis**: Leverages AWS Polly neural voices for high-quality audio rendering
- **Multi-Attempt Retry Logic**: Sophisticated echo detection and parameter escalation ensures quality output
- **Voice Catalog Management**: Access to 50+ neural voices across multiple languages and genders
- **Flexible Input Modes**: Supports GenAI generation, manual script pasting, or speech-to-text recording
- **Multi-Format Audio Output**: MP3, OGG Vorbis, or PCM/WAV formats with configurable sample rates

### 1.2 Technology Stack

**Backend Components:**
- **Framework**: Flask (Python 3.x)
- **AWS Services**: 
  - Bedrock Runtime (LLM inference)
  - Polly (Neural TTS synthesis)
- **Key Libraries**: boto3, flask-cors, difflib
- **Service Architecture**: Standalone Flask microservice on port 5003

**Frontend Components:**
- **Framework**: React 18+ with Hooks
- **Styling**: styled-components
- **HTTP Client**: axios
- **Browser APIs**: Web Speech API (SpeechRecognition)

### 1.3 Key Features

1. **Intelligent SSML Generation**
   - LLM-powered script creation with persona guidance
   - Automatic SSML tag injection (break, emphasis, prosody)
   - Multi-sentence structure with paragraph organization
   - Anti-echo detection prevents verbatim prompt repetition

2. **Advanced Retry Strategy**
   - 7-attempt escalation plan with increasing temperature/top_p
   - Multiple prompt variants (primary, force_speech, story_arc, escalation)
   - Fallback SSML template when all attempts exhausted
   - Detailed attempt logging for debugging

3. **Robust TTS Synthesis**
   - Neural engine with standard fallback
   - SSML sanitization for neural compatibility
   - Multi-stage error recovery (sanitize → plain → text-only → minimal)
   - Safe minimal fallback using plain text

4. **Interactive Frontend**
   - Three input modes: GenAI, Paste, Record
   - Persona preset library (warm guide, energetic launch, news brief, storyteller)
   - Voice artist selection with metadata (language, gender)
   - Real-time audio playback with download capability
   - Step-by-step wizard interface (Content → SSML → Narration)

---

## 2. Architecture Overview

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     SYNTHETIC VOICEOVER SERVICE                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    FRONTEND (React)                       │  │
│  │                      Port 3000                            │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │  • Input Mode Selection (GenAI/Paste/Record)            │  │
│  │  • Persona Preset Library                                │  │
│  │  • Speech Recognition Integration                        │  │
│  │  • Voice Artist Catalog Browser                          │  │
│  │  • SSML Editor with Syntax Highlighting                  │  │
│  │  • Audio Player with Download                            │  │
│  │  • Step Wizard (Content → SSML → Narration)             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              │ HTTP/JSON                         │
│                              ↓                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                 FLASK API LAYER                           │  │
│  │                    Port 5003                              │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │  • POST /generate-ssml                                    │  │
│  │  • GET  /voices                                           │  │
│  │  • POST /synthesize                                       │  │
│  │  • GET  /health                                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              │                                   │
│                    ┌─────────┴─────────┐                        │
│                    │                   │                         │
│                    ↓                   ↓                         │
│  ┌──────────────────────────┐  ┌─────────────────────────┐     │
│  │  SSML GENERATION ENGINE  │  │   TTS SYNTHESIS ENGINE  │     │
│  │  (Service Class)         │  │   (Service Class)       │     │
│  ├──────────────────────────┤  ├─────────────────────────┤     │
│  │  • Prompt Composition    │  │  • SSML Normalization   │     │
│  │  • Bedrock Invocation    │  │  • Neural Sanitization  │     │
│  │  • Echo Detection        │  │  • Polly Invocation     │     │
│  │  • Retry Orchestration   │  │  • Engine Fallback      │     │
│  │  • Fallback SSML Gen     │  │  • Audio Streaming      │     │
│  └──────────────────────────┘  └─────────────────────────┘     │
│                    │                      │                      │
│                    └──────────┬───────────┘                      │
│                               │                                  │
└───────────────────────────────┼──────────────────────────────────┘
                                │
                                ↓
                    ┌───────────────────────┐
                    │     AWS SERVICES      │
                    ├───────────────────────┤
                    │  • Bedrock Runtime    │
                    │    (Llama3-70B)       │
                    │  • Polly              │
                    │    (Neural Voices)    │
                    └───────────────────────┘
```

### 2.2 Service Architecture Pattern

**Design Pattern**: Dual-Engine Pipeline Architecture
- **Engine 1**: LLM-based SSML Script Generation (Bedrock)
- **Engine 2**: Neural TTS Audio Synthesis (Polly)
- **Coordination**: Flask API layer orchestrates both engines
- **Isolation**: Each engine has dedicated service class with independent error handling

**Key Architectural Decisions:**

1. **Separation of Concerns**
   - SSML generation logic isolated in `SyntheticVoiceoverService` class
   - Flask routes handle HTTP/validation, delegate to service layer
   - Frontend manages UI state, backend manages AI orchestration

2. **Stateless Service Design**
   - No session storage or user state
   - Each API request is independent
   - Voice catalog cached in memory (`@lru_cache`)

3. **Resilient Error Recovery**
   - Multi-layer fallback strategy
   - Progressive degradation (neural → standard → text → minimal)
   - Comprehensive error logging with attempt metadata

4. **Flexible LLM Integration**
   - Supports both prompt-based and messages-based Bedrock formats
   - Adaptive response parsing handles multiple Bedrock model shapes
   - Environment-driven model selection

---

## 3. System Components

### 3.1 Backend Components

#### 3.1.1 Flask Application (`app.py`)

**Responsibilities:**
- HTTP endpoint management
- Request validation and sanitization
- Response formatting
- CORS handling
- AWS client initialization

**Key Modules:**
```python
# Core imports
from flask import Flask, jsonify, request
from flask_cors import CORS
import boto3

# AWS clients (module-level singletons)
bedrock_runtime = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)
polly = boto3.client("polly", region_name=POLLY_REGION)
```

**Configuration Sources:**
- Environment variables (AWS regions, model ID, prompts)
- `.env` file (optional, via python-dotenv)
- Hardcoded defaults as fallbacks

#### 3.1.2 Service Layer (`synthetic_voiceover_service.py`)

**Responsibilities:**
- SSML generation orchestration
- Bedrock model invocation
- Echo detection and validation
- Retry strategy management
- TTS synthesis with error recovery
- SSML normalization and sanitization

**Class Structure:**
```python
@dataclass
class VoiceoverAttempt:
    """Represents a single retry attempt configuration"""
    index: int
    label: str
    prompt: str
    temperature: float
    top_p: float
    force: bool
    notes: str

class SyntheticVoiceoverService:
    """Main service orchestrator for voiceover generation"""
    
    def __init__(self, bedrock_runtime, polly, model_id, system_prompt, max_tokens)
    def generate_ssml(self, prompt, persona, language, temperature, top_p, max_attempts)
    def synthesize_speech(self, voice_id, ssml, output_format, sample_rate)
    def generate_voiceover(self, prompt, persona, language, voice_id, output_format, ...)
    def list_voices(self)
    
    # Private helpers
    def _compose_prompt(self, prompt, persona, language, force_speech)
    def _invoke_bedrock(self, body)
    def _extract_generation_text(self, response_body)
    def _looks_like_prompt_echo(self, user_prompt, generation)
    def _fallback_ssml(self, prompt)
    def _build_attempt_plan(self, prompt, persona, language, ...)
    def _should_retry(self, user_prompt, ssml)
    def _normalize_ssml(self, ssml)
    def _sanitize_ssml_for_neural(self, ssml)
    def _voice_supported_engines(self, voice_id)
    def _list_neural_voices(self)
    def _strip_ssml_tags(self, ssml)
```

**Caching Strategy:**
```python
# Voice catalog cached at instance level
self._voice_cache: Optional[List[Dict[str, Any]]] = None

# Engine support cached per voice ID
self._voice_engine_cache: Dict[str, List[str]] = {}
```

### 3.2 Frontend Components

#### 3.2.1 Main Component (`SyntheticVoiceover.js`)

**State Management:**
```javascript
// Input state
const [prompt, setPrompt] = useState('')
const [inputMode, setInputMode] = useState('genai') // 'genai' | 'paste' | 'audio'
const [persona, setPersona] = useState('')

// SSML generation state
const [ssml, setSsml] = useState('')
const [loadingSsml, setLoadingSsml] = useState(false)

// Voice selection state
const [voices, setVoices] = useState([])
const [selectedVoice, setSelectedVoice] = useState('')

// Audio synthesis state
const [audioUrl, setAudioUrl] = useState('')
const [audioFormat, setAudioFormat] = useState('mp3')
const [sampleRate, setSampleRate] = useState('')
const [synthLoading, setSynthLoading] = useState(false)

// Speech recognition state
const [isRecording, setIsRecording] = useState(false)
const [canRecord, setCanRecord] = useState(false)

// UI state
const [currentStep, setCurrentStep] = useState(1) // 1-3
const [status, setStatus] = useState('')
const [ssmlExpanded, setSsmlExpanded] = useState(false)
```

**Key Features:**

1. **Input Mode Switching**
   ```javascript
   const inputOptions = [
     { id: 'genai', title: 'Generate content via GenAI', ... },
     { id: 'paste', title: 'Paste finished script', ... },
     { id: 'audio', title: 'Record and transcribe', ... }
   ]
   ```

2. **Persona Presets**
   ```javascript
   const personaPresets = [
     { id: 'warm-guide', label: 'Warm guide', ... },
     { id: 'energetic-launch', label: 'Energetic launch', ... },
     { id: 'news-brief', label: 'News brief', ... },
     { id: 'storyteller', label: 'Storyteller', ... }
   ]
   ```

3. **Speech Recognition Integration**
   ```javascript
   const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
   recognition.continuous = true
   recognition.interimResults = true
   recognition.lang = 'en-US'
   ```

4. **Step Wizard Flow**
   - Step 1: Provide Content (choose input mode, enter text/record)
   - Step 2: Generate SSML (select persona, generate script)
   - Step 3: Render Narration (choose voice, synthesize audio)

#### 3.2.2 API Base Resolution

```javascript
const resolveVoiceApiBase = () => {
  // Priority 1: Environment variable
  if (process.env.REACT_APP_VOICE_API_BASE) {
    return process.env.REACT_APP_VOICE_API_BASE.replace(/\/$/, '')
  }
  
  // Priority 2: Smart localhost/LAN detection
  const { protocol, hostname } = window.location
  const localHosts = new Set(['localhost', '127.0.0.1', '0.0.0.0'])
  const isLanHost = /^(192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[0-1]))/.test(hostname)
  
  if (localHosts.has(hostname) || isLanHost) {
    return `${protocol}//${hostname}:5003`
  }
  
  return '' // Production: assumes same origin
}
```

### 3.3 Data Models

#### 3.3.1 Request Schemas

**Generate SSML Request:**
```json
{
  "prompt": "string (required)",
  "persona": "string (optional)",
  "language": "string (optional)",
  "temperature": "float (optional, default 0.6)",
  "top_p": "float (optional, default 0.9)"
}
```

**Synthesize Speech Request:**
```json
{
  "voiceId": "string (required)",
  "ssml": "string (required)",
  "outputFormat": "string (optional, default 'mp3')",
  "sampleRate": "string (optional)"
}
```

#### 3.3.2 Response Schemas

**Generate SSML Response:**
```json
{
  "ssml": "string",
  "meta": {
    "prompt_tokens": "integer",
    "generation_tokens": "integer",
    "attempt_count": "integer",
    "fallback": "boolean (optional)",
    "fallback_template": "boolean (optional)",
    "fallback_reason": "string (optional)",
    "attempts": [
      {
        "attempt": "integer",
        "label": "string",
        "status": "string (ok|retry|error)",
        "reason": "string (optional)",
        "notes": "string",
        "generation_length": "integer",
        "temperature": "float",
        "top_p": "float",
        "inference_variant": "string (optional)"
      }
    ]
  }
}
```

**Synthesize Speech Response:**
```json
{
  "audio": "base64-encoded audio bytes",
  "meta": {
    "engine": "string (neural|standard)",
    "normalized": "boolean",
    "normalization_notes": ["string"],
    "sanitized": "boolean",
    "plain_retry": "boolean",
    "text_fallback": "boolean",
    "safe_minimal": "boolean",
    "content_type": "string (audio/mpeg|audio/ogg|audio/wav)"
  }
}
```

**Voice List Response:**
```json
{
  "voices": [
    {
      "id": "string",
      "name": "string",
      "language_code": "string",
      "language_name": "string",
      "gender": "string (Male|Female)",
      "style_list": ["string"]
    }
  ]
}
```

---

## 4. Backend Architecture Deep Dive

### 4.1 SSML Generation Pipeline

#### 4.1.1 Prompt Composition

**Llama3 Instruction Format:**
```python
def _compose_prompt(self, prompt, persona=None, language=None, force_speech=False):
    system_block, clean_prompt = self._build_instruction_context(
        prompt, persona, language, force_speech
    )
    return (
        "<s>[INST] <<SYS>>\n"
        f"{system_block}\n"
        "<</SYS>>\n\n"
        f"{clean_prompt}\n"
        "[/INST]"
    )
```

**System Prompt Construction:**
```python
instructions = [SYSTEM_PROMPT.strip()]
instructions.append(
    "Return only valid SSML wrapped in <speak>...</speak> "
    "with no commentary or explanations outside the tags."
)
instructions.append(
    "Do not repeat the user's prompt verbatim. "
    "Transform the ideas into an original spoken narration with multiple sentences."
)
if persona:
    instructions.append(f"Adopt the following tone guidance: {persona.strip()}")
if language:
    instructions.append(f"Respond in {language.strip()} unless the user specifies otherwise.")
if force_speech:
    instructions.append(
        "If you are unsure, produce your best effort narration. "
        "Do not leave the response empty."
    )
system_block = " ".join(instructions)
```

**Default System Prompt:**
```
You are an expert voice director crafting expressive narration scripts in SSML.
Produce vivid, engaging speech that sounds natural, with pacing shifts, pausing, and emphasis.
Ensure the response is wrapped in <speak> tags and leverages <break>, <emphasis>, <prosody>,
and other supported neural speech effects where appropriate.
```

#### 4.1.2 Bedrock Invocation

**Request Body Construction:**
```python
def _invoke_bedrock(self, body: Dict[str, Any]) -> Dict[str, Any]:
    # Support both prompt-based and messages-based formats
    invoke_args = {
        "modelId": self.model_id,
        "contentType": "application/json",
        "accept": "application/json",
    }
    
    # Serialize body
    body_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")
    invoke_args["body"] = body_bytes
    
    # Invoke model
    response = self.bedrock.invoke_model(**invoke_args)
    
    # Parse response
    response_body = json.loads(response.get("body").read().decode("utf-8"))
    return response_body
```

**Request Parameters:**
```python
body = {
    "prompt": attempt.prompt,           # Formatted Llama3 prompt
    "max_gen_len": self.max_tokens,     # Default: 900
    "temperature": attempt.temperature,  # 0.6 - 1.0 (escalates)
    "top_p": attempt.top_p,             # 0.9 - 0.996 (escalates)
}
```

#### 4.1.3 Response Extraction

**Flexible Response Parser:**
```python
def _extract_generation_text(self, response_body: Dict[str, Any]) -> str:
    """Extract model text from multiple possible response shapes."""
    
    # Shape 1: Simple generation field
    generation = response_body.get("generation")
    if generation:
        return str(generation)
    
    # Shape 2: Generations array
    generations = response_body.get("generations")
    if generations:
        return "".join(str(item.get("text", "")) for item in generations)
    
    # Shape 3: Outputs array
    outputs = response_body.get("outputs")
    if outputs:
        parts = []
        for item in outputs:
            if isinstance(item, dict):
                if "text" in item:
                    parts.append(str(item.get("text", "")))
                else:
                    parts.append(self._collect_from_content(item.get("content")))
        return "".join(parts)
    
    # Shape 4: Content block
    content = response_body.get("content")
    if content:
        return self._collect_from_content(content)
    
    # Shape 5: Message format
    message = response_body.get("message")
    if isinstance(message, dict):
        return self._collect_from_content(message.get("content"))
    
    # Shape 6: Messages array
    messages = response_body.get("messages")
    if isinstance(messages, list):
        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                return self._collect_from_content(msg.get("content"))
    
    return ""
```

**This flexible parser supports:**
- Llama3 native format (`generation`)
- Claude format (`content` array with text blocks)
- Legacy Bedrock formats (`generations`, `outputs`)
- Messages-based conversation format

#### 4.1.4 Echo Detection

**Anti-Echo Algorithm:**
```python
def _looks_like_prompt_echo(self, user_prompt: str, generation: str) -> bool:
    """Detect if model simply repeated the user's prompt verbatim."""
    
    user_prompt_clean = user_prompt.lower().strip()
    generation_clean = generation.lower().strip()
    
    # Check 1: Exact containment
    if user_prompt_clean in generation_clean or generation_clean in user_prompt_clean:
        # Use SequenceMatcher for fuzzy similarity
        ratio = SequenceMatcher(None, user_prompt_clean, generation_clean).ratio()
        if ratio >= 0.995:
            return True
    
    # Check 2: Token overlap analysis
    def _tokenize(text):
        return re.findall(r"\b\w+\b", text.lower())
    
    user_tokens = _tokenize(user_prompt)
    gen_tokens = _tokenize(generation)
    
    if not user_tokens or not gen_tokens:
        return False
    
    # Calculate token overlap
    user_counter = Counter(user_tokens)
    gen_counter = Counter(gen_tokens)
    
    overlap_count = sum((user_counter & gen_counter).values())
    user_total = sum(user_counter.values())
    gen_total = sum(gen_counter.values())
    
    overlap_ratio_user = overlap_count / user_total if user_total > 0 else 0
    overlap_ratio_gen = overlap_count / gen_total if gen_total > 0 else 0
    
    # Echo if 98%+ token overlap in both directions
    if overlap_ratio_user >= 0.98 and overlap_ratio_gen >= 0.98:
        return True
    
    # Check 3: Length ratio (suspiciously similar lengths)
    len_ratio = min(len(user_prompt_clean), len(generation_clean)) / max(len(user_prompt_clean), len(generation_clean))
    if len_ratio >= 0.92 and overlap_ratio_user >= 0.85:
        return True
    
    return False
```

**Echo Detection Criteria:**
1. **String Similarity**: SequenceMatcher ratio ≥ 0.995
2. **Token Overlap**: ≥98% tokens shared in both directions
3. **Length + Overlap**: Length ratio ≥92% AND overlap ≥85%

#### 4.1.5 Retry Strategy

**7-Attempt Escalation Plan:**

```python
def _build_attempt_plan(self, user_prompt, persona, language, 
                        base_temperature, base_top_p, attempt_limit):
    """Build progressive retry strategy with escalating parameters."""
    
    attempt_plan = []
    
    for attempt_index in range(attempt_limit):
        if attempt_index == 0:
            # Attempt 1: Clean baseline
            attempt_plan.append(VoiceoverAttempt(
                index=attempt_index + 1,
                label="primary",
                prompt=self._compose_prompt(user_prompt, persona, language),
                temperature=base_temperature,  # Default: 0.6
                top_p=base_top_p,             # Default: 0.9
                force=False,
                notes="initial generation"
            ))
        
        elif attempt_index == 1:
            # Attempt 2: Force speech + temp boost
            enhanced_prompt = (
                f"{user_prompt}\n\n"
                "Transform this into a fresh narration script with original phrasing, "
                "using expressive SSML tags. Deliver 4-6 sentences split across "
                "paragraphs with varied pacing cues."
            )
            attempt_plan.append(VoiceoverAttempt(
                index=attempt_index + 1,
                label="retry_force_speech",
                prompt=self._compose_prompt(enhanced_prompt, persona, language, True),
                temperature=min(1.0, base_temperature + 0.25),  # +0.25
                top_p=min(0.99, base_top_p + 0.06),            # +0.06
                force=True,
                notes="first retry with force_speech"
            ))
        
        elif attempt_index == 2:
            # Attempt 3: Story arc guidance + more temp
            arc_prompt = (
                f"{user_prompt}\n\n"
                "Craft a vivid voiceover with an opening hook, middle build, "
                "and closing call-to-action. Incorporate <p> sections, <break>, "
                "and <emphasis> tags. Avoid copying the input sentences directly."
            )
            attempt_plan.append(VoiceoverAttempt(
                index=attempt_index + 1,
                label="retry_story_arc",
                prompt=self._compose_prompt(arc_prompt, persona, language, True),
                temperature=min(1.0, base_temperature + 0.35),  # +0.35
                top_p=min(0.995, base_top_p + 0.08),           # +0.08
                force=True,
                notes="second retry with structured guidance"
            ))
        
        else:
            # Attempts 4-7: Progressive escalation
            escalation = attempt_index - 2
            escalated_prompt = (
                f"{user_prompt}\n\n"
                f"Attempt {attempt_index + 1}: Produce an entirely new narration "
                "with a cinematic arc, vivid sensory language, and varied pacing. "
                "Do not mirror the source sentences—paraphrase heavily and introduce "
                "fresh connective tissue.\nUse multiple <p> blocks, layer in "
                "<prosody rate=\"slow\"> and <emphasis> for key beats, and ensure "
                "at least five sentences total. Close with a motivating call-to-action."
            )
            attempt_plan.append(VoiceoverAttempt(
                index=attempt_index + 1,
                label=f"retry_escalation_{attempt_index + 1}",
                prompt=self._compose_prompt(escalated_prompt, persona, language, True),
                temperature=min(1.0, base_temperature + 0.25 + 0.1 * escalation),
                top_p=min(0.996, base_top_p + 0.06 + 0.02 * escalation),
                force=True,
                notes=f"escalation attempt {attempt_index + 1}"
            ))
    
    return attempt_plan
```

**Parameter Escalation Table:**

| Attempt | Label | Temperature | Top P | Force | Prompt Enhancement |
|---------|-------|-------------|-------|-------|--------------------|
| 1 | primary | 0.6 | 0.9 | No | Clean baseline |
| 2 | retry_force_speech | 0.85 | 0.96 | Yes | "Transform into fresh narration..." |
| 3 | retry_story_arc | 0.95 | 0.98 | Yes | "Opening hook, middle build, closing CTA..." |
| 4 | retry_escalation_4 | 1.0 | 0.98 | Yes | "Cinematic arc, sensory language..." |
| 5 | retry_escalation_5 | 1.0 | 1.0 | Yes | Same with escalation=2 |
| 6 | retry_escalation_6 | 1.0 | 1.0 | Yes | Same with escalation=3 |
| 7 | retry_escalation_7 | 1.0 | 1.0 | Yes | Same with escalation=4 |

**Retry Decision Logic:**
```python
def _should_retry(self, user_prompt: str, ssml: str) -> Tuple[bool, Optional[str]]:
    """Determine if generated SSML requires retry."""
    
    if not ssml:
        return True, "empty"
    
    if self._looks_like_prompt_echo(user_prompt, ssml):
        return True, "echo"
    
    return False, None  # Success
```

#### 4.1.6 Fallback SSML Generation

**Emergency Template When All Attempts Fail:**

```python
def _fallback_ssml(self, prompt: str) -> str:
    """Generate basic SSML template when LLM fails entirely."""
    
    clean_text = (prompt or "Narration coming up.").strip()
    clean_text = html.escape(clean_text[:500])  # Escape XML, limit length
    
    sentences = re.split(r"(?<=[.!?])\s+", clean_text)
    
    # Structure: intro + body + outro
    intro = sentences[0] if sentences else clean_text
    body_sentences = sentences[1:] if len(sentences) > 1 else []
    outro = "Thank you for watching." if body_sentences else ""
    
    parts = [f'<p><s>{intro}</s></p>']
    
    if body_sentences:
        body_text = " ".join(body_sentences[:3])  # Max 3 sentences
        parts.append(f'<break time="300ms"/>')
        parts.append(f'<p><s>{body_text}</s></p>')
    
    if outro:
        parts.append(f'<break time="500ms"/>')
        parts.append(f'<p><s>{outro}</s></p>')
    
    inner_ssml = "".join(parts)
    return f"<speak>{inner_ssml}</speak>"
```

**Fallback Response Metadata:**
```json
{
  "ssml": "<speak>...</speak>",
  "meta": {
    "fallback": true,
    "fallback_template": true,
    "fallback_reason": "Model response was empty or simply echoed the prompt.",
    "attempt_count": 7,
    "attempts": [...]
  }
}
```

---

*This document continues in the next part...*
# Synthetic Voiceover Service Reference - Part 2

*Continuation from Part 1...*

---

## 4.2 TTS Synthesis Pipeline

### 4.2.1 SSML Normalization

**Pre-Synthesis SSML Cleanup:**

```python
def _normalize_ssml(self, ssml: str) -> Tuple[str, bool, List[str]]:
    """Normalize SSML to meet Polly requirements. Returns (normalized, modified, notes)."""
    
    notes: List[str] = []
    original = (ssml or "").strip()
    candidate = original
    
    # Step 1: Handle empty input
    if not candidate:
        fallback = "<speak></speak>"
        notes.append("empty_input")
        return fallback, True, notes
    
    # Step 2: Remove XML declarations and DOCTYPE
    new_candidate = re.sub(r"<\?xml[^>]*>", "", candidate, flags=re.IGNORECASE)
    new_candidate = re.sub(r"<!DOCTYPE[^>]*>", "", new_candidate, flags=re.IGNORECASE)
    if new_candidate != candidate:
        notes.append("removed_xml_header")
        candidate = new_candidate.strip()
    
    # Step 3: Extract or add <speak> wrapper
    speak_match = re.search(
        r"<\s*speak\b[^>]*>(.*)</\s*speak\s*>",
        candidate,
        flags=re.IGNORECASE | re.DOTALL
    )
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
    
    # Step 4: Convert break time to milliseconds
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
        r'time="([0-9]*\.?[0-9]+)(s|ms)"',
        _convert_break,
        candidate,
        flags=re.IGNORECASE
    )
    if converted_candidate != candidate:
        notes.append("normalized_break_time")
        candidate = converted_candidate
    
    # Step 5: Convert decimal rate to percentage
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
    
    converted_rate = re.sub(
        r'rate="([0-9]*\.?[0-9]+)"',
        _convert_rate,
        candidate,
        flags=re.IGNORECASE
    )
    if converted_rate != candidate:
        notes.append("normalized_rate_decimal")
        candidate = converted_rate
    
    # Step 6: Escape unescaped ampersands
    escaped_candidate = re.sub(
        r"&(?![a-zA-Z]+;|#\d+;|#x[0-9A-Fa-f]+;)",
        "&amp;",
        candidate
    )
    if escaped_candidate != candidate:
        notes.append("escaped_ampersands")
        candidate = escaped_candidate
    
    # Step 7: Validate XML structure
    inner_text = self._strip_ssml_tags(candidate)
    if not inner_text:
        notes.append("empty_after_strip")
        candidate = "<speak></speak>"
    
    # Step 8: XML parsing validation
    try:
        from xml.etree import ElementTree as ET
        ET.fromstring(candidate)
    except ET.ParseError:
        # Fallback to escaped plain text
        safe_text = html.escape(inner_text or "Narration coming up.")
        candidate = f"<speak>{safe_text}</speak>"
        notes.append("parse_error_fallback")
    
    was_modified = candidate != original
    return candidate, was_modified, notes
```

**Normalization Examples:**

| Input | Output | Notes |
|-------|--------|-------|
| `<?xml version="1.0"?><speak>Hello</speak>` | `<speak>Hello</speak>` | `removed_xml_header` |
| `Hello world` | `<speak>Hello world</speak>` | `wrapped_in_speak` |
| `<break time="2s"/>` | `<break time="2000ms"/>` | `normalized_break_time` |
| `<prosody rate="1.5">Fast</prosody>` | `<prosody rate="150%">Fast</prosody>` | `normalized_rate_decimal` |
| `A & B` | `A &amp; B` | `escaped_ampersands` |

### 4.2.2 Neural Engine Sanitization

**Remove Unsupported Tags for Neural Voices:**

```python
@staticmethod
def _sanitize_ssml_for_neural(ssml: str) -> str:
    """Remove SSML features not supported by Polly neural engine."""
    
    # Remove Amazon-specific effects not supported in neural
    sanitized = re.sub(
        r"<\s*/?amazon:(?:effect|domain|auto-breaths)[^>]*>",
        "",
        ssml,
        flags=re.IGNORECASE
    )
    
    # Convert x-fast/x-slow to fast/slow
    sanitized = re.sub(
        r'rate="x-(fast|slow)"',
        r'rate="\1"',
        sanitized,
        flags=re.IGNORECASE
    )
    
    # Convert x-loud/x-soft to loud/soft
    sanitized = re.sub(
        r'volume="x-(loud|soft)"',
        r'volume="\1"',
        sanitized,
        flags=re.IGNORECASE
    )
    
    # Convert decimal rate to percentage (neural requirement)
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
    
    sanitized = re.sub(
        r'rate="([0-9]*\.?[0-9]+)"',
        _sanitize_rate_decimal,
        sanitized,
        flags=re.IGNORECASE
    )
    
    # Remove XML comments
    sanitized = re.sub(r"<!--.*?-->", "", sanitized, flags=re.DOTALL)
    
    return sanitized
```

**Unsupported Neural Features:**
- `<amazon:effect>` tags (whisper, drc)
- `<amazon:domain>` tags (news, conversational)
- `<amazon:auto-breaths>` tags
- `rate="x-fast"` / `rate="x-slow"` (use `fast`/`slow`)
- `volume="x-loud"` / `volume="x-soft"` (use `loud`/`soft`)

### 4.2.3 Polly Invocation with Multi-Stage Fallback

**Comprehensive Error Recovery Strategy:**

```python
def synthesize_speech(self, *, voice_id, ssml, output_format="mp3", sample_rate=None):
    """
    Synthesize speech with multi-stage fallback strategy:
    1. Try neural engine with normalized SSML
    2. If InvalidSsmlException (neural features), sanitize and retry
    3. If still failing, try standard engine
    4. If still failing, try plain text wrapped in <speak>
    5. If still failing, try text-only (no SSML)
    6. If still failing, try safe minimal SSML with both engines
    """
    
    # Validate inputs
    if not voice_id:
        raise ValueError("voiceId is required")
    if not ssml:
        raise ValueError("ssml content is required")
    fmt = output_format.lower()
    if fmt not in self.AUDIO_MIME:
        raise ValueError(f"Unsupported output format '{output_format}'")
    
    # Normalize SSML
    normalized_ssml, ssml_normalized, normalization_notes = self._normalize_ssml(ssml)
    original_plaintext = self._strip_ssml_tags(ssml)
    
    # Prepare request
    request_args = {
        "VoiceId": voice_id,
        "Text": normalized_ssml,
        "TextType": "ssml",
        "Engine": "neural",
        "OutputFormat": fmt,
    }
    if sample_rate:
        request_args["SampleRate"] = str(sample_rate)
    
    # Tracking variables
    engine_used = request_args["Engine"]
    sanitized_used = False
    sanitized_ssml = None
    plain_retry_used = False
    text_fallback_used = False
    safe_minimal_used = False
    response = None
    error_message = None
    audio_bytes = None
    
    # === STAGE 1: Primary neural attempt ===
    try:
        response = self.polly.synthesize_speech(**request_args)
        audio_bytes = response.get("AudioStream").read() if response else None
    
    except (BotoCoreError, ClientError) as aws_error:
        error_message = str(aws_error)
        error_code = None
        if isinstance(aws_error, ClientError):
            error_code = aws_error.response.get("Error", {}).get("Code")
            error_message = aws_error.response.get("Error", {}).get("Message", error_message)
        
        # === STAGE 2: Sanitize for neural ===
        if error_code == "InvalidSsmlException" and "unsupported neural feature" in error_message.lower():
            sanitized_candidate = self._sanitize_ssml_for_neural(normalized_ssml)
            if sanitized_candidate != normalized_ssml:
                try:
                    request_args["Text"] = sanitized_candidate
                    response = self.polly.synthesize_speech(**request_args)
                    sanitized_used = True
                    sanitized_ssml = sanitized_candidate
                    audio_bytes = response.get("AudioStream").read() if response else None
                    error_message = None
                except (BotoCoreError, ClientError) as retry_error:
                    request_args["Text"] = normalized_ssml
                    if isinstance(retry_error, ClientError):
                        error_message = retry_error.response.get("Error", {}).get("Message", str(retry_error))
                    else:
                        error_message = str(retry_error)
            
            # === STAGE 3: Fallback to standard engine ===
            if audio_bytes is None:
                supported_engines = self._voice_supported_engines(voice_id)
                if "standard" in supported_engines:
                    fallback_args = dict(request_args)
                    fallback_args["Engine"] = "standard"
                    engine_used = "standard"
                    try:
                        response = self.polly.synthesize_speech(**fallback_args)
                        audio_bytes = response.get("AudioStream").read() if response else None
                        error_message = None
                    except (BotoCoreError, ClientError) as fallback_error:
                        fallback_msg = (
                            fallback_error.response.get("Error", {}).get("Message", str(fallback_error))
                            if isinstance(fallback_error, ClientError)
                            else str(fallback_error)
                        )
                        # === STAGE 6a: Safe minimal with engine sequence ===
                        engine_sequence = ["neural", "standard"]
                        if not self._try_safe_minimal(engine_sequence):
                            raise RuntimeError(
                                "Voice synthesis failed: neural engine rejected SSML and standard "
                                f"fallback also failed ({fallback_msg})"
                            ) from fallback_error
                else:
                    # No standard engine available
                    detail = (
                        "Voice does not support the standard engine and neural synthesis rejected SSML. "
                        "Try simplifying SSML effects or choose another voice."
                    )
                    if error_message:
                        detail = f"{detail} (Last error: {error_message})"
                    engine_sequence = [request_args.get("Engine", "neural")]
                    if not self._try_safe_minimal(engine_sequence):
                        raise RuntimeError(detail)
        
        # === STAGE 4: Plain SSML retry (generic SSML error) ===
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
                    normalized_ssml = plain_candidate
                    audio_bytes = response.get("AudioStream").read() if response else None
                    error_message = None
                except (BotoCoreError, ClientError) as plain_error:
                    request_args["Text"] = normalized_ssml
                    
                    # === STAGE 5: Text-only (no SSML) ===
                    plain_text_payload = self._strip_ssml_tags(normalized_ssml) or "Narration coming up."
                    text_args = dict(request_args)
                    text_args["Text"] = plain_text_payload
                    text_args["TextType"] = "text"
                    try:
                        response = self.polly.synthesize_speech(**text_args)
                        normalized_ssml = plain_candidate
                        audio_bytes = response.get("AudioStream").read() if response else None
                        text_fallback_used = True
                        error_message = None
                    except (BotoCoreError, ClientError) as text_error:
                        # === STAGE 6b: Safe minimal ===
                        engine_sequence = [request_args.get("Engine", "neural")]
                        if not self._try_safe_minimal(engine_sequence):
                            raise RuntimeError(
                                "Voice synthesis failed: neural engine rejected SSML even after sanitization"
                            ) from text_error
        else:
            # === STAGE 6c: Safe minimal for other errors ===
            engine_sequence = [request_args.get("Engine", "neural")]
            if not self._try_safe_minimal(engine_sequence):
                raise RuntimeError(f"Voice synthesis failed: {error_message}") from aws_error
    
    except Exception:
        raise
    
    # Final check
    if response is None or audio_bytes is None:
        engine_sequence = [request_args.get("Engine", "neural"), "standard"]
        if not self._try_safe_minimal(engine_sequence):
            raise RuntimeError("Failed to synthesize speech; no audio stream received")
    
    # Return metadata + audio
    result_metadata = {
        "engine": engine_used,
        "normalized": ssml_normalized,
        "normalization_notes": normalization_notes,
        "sanitized": sanitized_used,
        "sanitized_ssml": sanitized_ssml,
        "plain_retry": plain_retry_used,
        "text_fallback": text_fallback_used,
        "safe_minimal": safe_minimal_used,
        "content_type": self.AUDIO_MIME[fmt],
    }
    return result_metadata, audio_bytes
```

**Safe Minimal Fallback:**
```python
def _try_safe_minimal(self, engine_sequence: List[str]) -> bool:
    """Last resort: minimal SSML with plain text."""
    
    safe_candidate_text = (
        original_plaintext or 
        self._strip_ssml_tags(normalized_ssml) or 
        "Narration coming up."
    )
    safe_candidate = f"<speak><s>{html.escape(safe_candidate_text[:320])}</s></speak>"
    
    # Try SSML with each engine
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
            audio_bytes = response.get("AudioStream").read() if response else None
            return audio_bytes is not None
        except (BotoCoreError, ClientError):
            continue
    
    # Try text-only with each engine
    for engine_option in engine_sequence:
        text_request = dict(request_args)
        text_request["Engine"] = engine_option
        text_request["Text"] = safe_candidate_text
        text_request["TextType"] = "text"
        try:
            response = self.polly.synthesize_speech(**text_request)
            engine_used = engine_option
            safe_minimal_used = True
            text_fallback_used = True
            audio_bytes = response.get("AudioStream").read() if response else None
            return audio_bytes is not None
        except (BotoCoreError, ClientError):
            continue
    
    return False
```

**Fallback Strategy Diagram:**

```
┌────────────────────────────────────────────────────────────┐
│               POLLY SYNTHESIS FALLBACK CHAIN               │
└────────────────────────────────────────────────────────────┘

1. Neural + Normalized SSML
   ↓ [InvalidSsmlException: unsupported neural feature]
   
2. Neural + Sanitized SSML (remove amazon: tags, fix rates)
   ↓ [Still failing]
   
3. Standard Engine + Sanitized SSML
   ↓ [Still failing OR no standard engine available]
   
4. Neural/Standard + Plain Text Wrapped in <speak>
   ↓ [Still failing]
   
5. Neural/Standard + Plain Text (TextType=text, no SSML)
   ↓ [Still failing]
   
6. Safe Minimal Fallback:
   a. Try Neural + <speak><s>{first 320 chars}</s></speak>
   b. Try Standard + <speak><s>{first 320 chars}</s></speak>
   c. Try Neural + Plain Text (TextType=text)
   d. Try Standard + Plain Text (TextType=text)
   ↓ [All failed]
   
7. RuntimeError with detailed message
```

### 4.2.4 Voice Catalog Management

**Neural Voice Discovery:**

```python
def _list_neural_voices(self) -> List[Dict[str, Any]]:
    """Fetch and cache all neural-capable voices from Polly."""
    
    if self._voice_cache is not None:
        return self._voice_cache
    
    paginator = self.polly.get_paginator("describe_voices")
    voices: List[Dict[str, Any]] = []
    
    for page in paginator.paginate(Engine="neural"):
        for voice in page.get("Voices", []):
            # Verify neural support in SupportedEngines array
            if "neural" in [engine.lower() for engine in voice.get("SupportedEngines", [])]:
                voices.append({
                    "id": voice.get("Id"),
                    "name": voice.get("Name"),
                    "language_code": voice.get("LanguageCode"),
                    "language_name": voice.get("LanguageName"),
                    "gender": voice.get("Gender"),
                    "style_list": voice.get("AdditionalLanguageCodes", []),
                })
    
    # Sort by language, then name
    voices.sort(key=lambda v: (v.get("language_name", ""), v.get("name", "")))
    
    # Cache at instance level
    self._voice_cache = voices
    return voices
```

**Voice Engine Support Query:**

```python
def _voice_supported_engines(self, voice_id: str) -> List[str]:
    """Check which engines (neural, standard) a voice supports."""
    
    if voice_id in self._voice_engine_cache:
        return self._voice_engine_cache[voice_id]
    
    try:
        response = self.polly.describe_voices(VoiceId=voice_id)
    except (BotoCoreError, ClientError):
        engines: List[str] = []
    else:
        voices = response.get("Voices", [])
        engines = [
            engine.lower() 
            for engine in (voices[0].get("SupportedEngines", []) if voices else [])
        ]
    
    self._voice_engine_cache[voice_id] = engines
    return engines
```

**Example Voice Catalog Entry:**
```json
{
  "id": "Joanna",
  "name": "Joanna",
  "language_code": "en-US",
  "language_name": "US English",
  "gender": "Female",
  "style_list": []
}
```

---

## 5. Frontend Architecture Deep Dive

### 5.1 Component Structure

**Main Component Hierarchy:**
```
SyntheticVoiceover (Root)
├── Step Wizard Progress Bar
│   ├── Step 1: Provide Content
│   ├── Step 2: Generate SSML
│   └── Step 3: Render Narration
├── Input Mode Selection Cards
│   ├── GenAI Card (default)
│   ├── Paste Card
│   └── Audio/Record Card
├── Content Input Section
│   ├── Prompt Textarea
│   ├── Recording Controls (if audio mode)
│   └── Mode-specific Help Text
├── Persona Selection Panel
│   ├── Persona Grid (4 presets)
│   └── Selected Persona Display
├── SSML Generation Section
│   ├── Generate Button
│   ├── SSML Editor (with expand/collapse)
│   └── Generation Status Display
├── Voice Selection Panel
│   ├── Voice Artist Grid (50+ voices)
│   ├── Voice Metadata (language, gender)
│   └── Audio Format Options
└── Audio Synthesis Section
    ├── Synthesize Button
    ├── Audio Player
    ├── Download Button
    └── Synthesis Status Display
```

### 5.2 State Management Strategy

**State Categories:**

1. **Input State**: User-provided content
   ```javascript
   const [prompt, setPrompt] = useState('')
   const [inputMode, setInputMode] = useState('genai')
   const [persona, setPersona] = useState('')
   ```

2. **Processing State**: Intermediate results
   ```javascript
   const [ssml, setSsml] = useState('')
   const [loadingSsml, setLoadingSsml] = useState(false)
   ```

3. **Output State**: Final artifacts
   ```javascript
   const [audioUrl, setAudioUrl] = useState('')
   const [audioFormat, setAudioFormat] = useState('mp3')
   ```

4. **UI State**: View control
   ```javascript
   const [currentStep, setCurrentStep] = useState(1)
   const [ssmlExpanded, setSsmlExpanded] = useState(false)
   const [status, setStatus] = useState('')
   ```

5. **Catalog State**: External data
   ```javascript
   const [voices, setVoices] = useState([])
   const [selectedVoice, setSelectedVoice] = useState('')
   ```

6. **Recording State**: Browser API integration
   ```javascript
   const [isRecording, setIsRecording] = useState(false)
   const [canRecord, setCanRecord] = useState(false)
   const recognitionRef = useRef(null)
   ```

### 5.3 Speech Recognition Integration

**Web Speech API Setup:**

```javascript
useEffect(() => {
  if (typeof window === 'undefined') {
    setCanRecord(false)
    return
  }
  
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
  if (!SpeechRecognition) {
    setCanRecord(false)
    return
  }
  
  setCanRecord(true)
  const recognition = new SpeechRecognition()
  recognition.continuous = true
  recognition.interimResults = true
  recognition.lang = 'en-US'
  
  recognition.onresult = (event) => {
    let interimTranscript = ''
    let finalTranscript = recordedTextRef.current
    
    for (let i = event.resultIndex; i < event.results.length; i += 1) {
      const transcript = event.results[i][0].transcript
      if (event.results[i].isFinal) {
        finalTranscript += transcript
      } else {
        interimTranscript = `${interimTranscript}${transcript}`
      }
    }
    
    recordedTextRef.current = finalTranscript
    const combined = [preRecordPromptRef.current, finalTranscript, interimTranscript]
      .filter(Boolean)
      .join(' ')
      .replace(/\s+/g, ' ')
      .trim()
    setPrompt(combined)
  }
  
  recognition.onerror = (event) => {
    const errorMessage = event?.error === 'not-allowed'
      ? 'Microphone permission denied.'
      : `Recording error: ${event?.error || 'unknown'}.`
    setRecordingError(errorMessage)
    stopRecording()
  }
  
  recognition.onend = () => {
    setIsRecording(false)
  }
  
  recognitionRef.current = recognition
  
  return () => {
    try {
      recognition.stop()
    } catch (error) {
      // ignore stop errors on unmount
    }
    recognitionRef.current = null
  }
}, [setPrompt, stopRecording])
```

**Recording Controls:**

```javascript
const startRecording = useCallback(() => {
  if (!recognitionRef.current) {
    setRecordingError('Speech recognition is not available in this browser.')
    return
  }
  try {
    preRecordPromptRef.current = prompt.trim()
    recordedTextRef.current = ''
    setRecordingError('')
    recognitionRef.current.start()
    setIsRecording(true)
  } catch (error) {
    setRecordingError('Unable to start recording. Confirm microphone permissions and try again.')
  }
}, [prompt])

const stopRecording = useCallback(() => {
  if (recognitionRef.current) {
    try {
      recognitionRef.current.stop()
    } catch (error) {
      // ignore stop errors
    }
  }
  recordedTextRef.current = ''
  setIsRecording(false)
}, [])
```

**Key Features:**
- **Continuous Recognition**: Captures full sentences without restart
- **Interim Results**: Shows real-time transcription as user speaks
- **Text Preservation**: Preserves existing prompt text before recording starts
- **Auto-Stop on Mode Change**: Stops recording if user switches input mode

### 5.4 API Integration Layer

**SSML Generation Request:**

```javascript
const handleGenerateSsml = async () => {
  if (!hasPrompt) {
    setStatus('Enter content to generate SSML.')
    setStatusError(true)
    return
  }
  
  setLoadingSsml(true)
  setStatus('Generating expressive SSML script...')
  setStatusError(false)
  
  try {
    const payload = {
      prompt: prompt.trim(),
    }
    
    if (persona) {
      payload.persona = activePersona?.description || persona
    }
    
    const response = await axios.post(
      `${VOICE_API_BASE}/generate-ssml`,
      payload,
      {
        headers: { 'Content-Type': 'application/json' },
        timeout: 90000, // 90s timeout for LLM generation
      }
    )
    
    const ssmlData = response?.data?.ssml
    if (!ssmlData) {
      throw new Error('No SSML returned from service')
    }
    
    const normalized = persistSsml(ssmlData)
    
    const meta = response?.data?.meta || {}
    const attemptCount = meta.attempt_count || 1
    const wasFallback = meta.fallback || false
    
    if (wasFallback) {
      setStatus(
        `SSML generated using fallback template after ${attemptCount} attempts. ` +
        `Reason: ${meta.fallback_reason || 'Model response failed validation.'}`
      )
      setStatusError(true)
    } else {
      setStatus(`SSML generated successfully in ${attemptCount} attempt(s).`)
      setStatusError(false)
    }
    
    if (normalized.trim()) {
      setCurrentStep(3) // Advance to synthesis step
      setSsmlExpanded(true)
    }
  } catch (error) {
    console.error('SSML generation failed:', error)
    setStatus(
      error.response?.data?.error ||
      error.message ||
      'SSML generation failed. Check service logs.'
    )
    setStatusError(true)
  } finally {
    setLoadingSsml(false)
  }
}
```

**Voice Catalog Fetch:**

```javascript
useEffect(() => {
  let active = true
  
  const loadVoices = async () => {
    try {
      const response = await axios.get(`${VOICE_API_BASE}/voices`)
      if (!active) return
      
      const voiceList = response?.data?.voices || []
      setVoices(voiceList)
      
      if (voiceList.length) {
        setSelectedVoice(voiceList[0].id)
      }
    } catch (error) {
      console.error('Failed to fetch voices', error)
      if (!active) return
      setStatusError(true)
      setStatus('Unable to load voice catalog. Verify service credentials and regional access.')
    } finally {
      if (active) setVoicesLoading(false)
    }
  }
  
  loadVoices()
  
  return () => {
    active = false
  }
}, [])
```

**Audio Synthesis Request:**

```javascript
const handleSynthesize = async () => {
  if (!hasSsml) {
    setStatus('Generate SSML before synthesizing audio.')
    setStatusError(true)
    return
  }
  
  if (!selectedVoice) {
    setStatus('Select a voice artist before synthesizing.')
    setStatusError(true)
    return
  }
  
  setSynthLoading(true)
  setStatus('Synthesizing neural audio...')
  setStatusError(false)
  
  // Revoke previous audio URL
  if (audioUrl) {
    URL.revokeObjectURL(audioUrl)
    setAudioUrl('')
  }
  
  try {
    const payload = {
      voiceId: selectedVoice,
      ssml: ssmlText,
      outputFormat: audioFormat,
    }
    
    if (sampleRate) {
      payload.sampleRate = sampleRate
    }
    
    const response = await axios.post(
      `${VOICE_API_BASE}/synthesize`,
      payload,
      {
        headers: { 'Content-Type': 'application/json' },
        timeout: 60000, // 60s timeout for TTS
      }
    )
    
    const audioBase64 = response?.data?.audio
    if (!audioBase64) {
      throw new Error('No audio data returned from service')
    }
    
    // Decode base64 to binary
    const binaryString = base64Decode(audioBase64)
    const bytes = new Uint8Array(binaryString.length)
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i)
    }
    
    // Create blob and object URL
    const meta = response?.data?.meta || {}
    const mimeType = meta.content_type || 'audio/mpeg'
    const blob = new Blob([bytes], { type: mimeType })
    const url = URL.createObjectURL(blob)
    
    setAudioUrl(url)
    setEngineUsed(meta.engine || 'neural')
    
    const engineLabel = meta.engine === 'standard' ? 'standard' : 'neural'
    const normalizedLabel = meta.normalized ? ' (normalized)' : ''
    const sanitizedLabel = meta.sanitized ? ' + sanitized' : ''
    const fallbackLabel = meta.text_fallback ? ' (text fallback)' : ''
    
    setStatus(
      `Audio synthesized with ${engineLabel} engine${normalizedLabel}${sanitizedLabel}${fallbackLabel}.`
    )
    setStatusError(false)
  } catch (error) {
    console.error('Synthesis failed:', error)
    setStatus(
      error.response?.data?.error ||
      error.message ||
      'Audio synthesis failed. Check service logs.'
    )
    setStatusError(true)
  } finally {
    setSynthLoading(false)
  }
}
```

**Audio Download Handler:**

```javascript
const handleDownload = () => {
  if (!audioUrl) return
  
  const link = document.createElement('a')
  link.href = audioUrl
  
  const extension = audioFormat === 'ogg_vorbis' ? 'ogg' : audioFormat
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5)
  link.download = `voiceover-${timestamp}.${extension}`
  
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}
```

### 5.5 Step Wizard Navigation

**Step State Management:**

```javascript
// Step configuration
const stepItems = [
  {
    number: 1,
    title: 'Provide content',
    caption: 'Choose a capture method and prepare your base script.',
    completed: hasPrompt || currentStep > 1 || hasSsml || hasAudio,
    active: currentStep === 1,
  },
  {
    number: 2,
    title: 'Generate SSML',
    caption: 'Apply tone guidance and convert the text into an SSML blueprint.',
    completed: hasSsml || currentStep === 3 || hasAudio,
    active: currentStep === 2,
  },
  {
    number: 3,
    title: 'Render narration',
    caption: 'Select a voice artist and synthesize the final audio.',
    completed: hasAudio,
    active: currentStep === 3,
  },
]

// Constrained navigation
const goToStep = (stepNumber) => {
  const clamped = Math.max(1, Math.min(stepNumber, 3))
  
  // Can't skip to step 2 without prompt
  if (clamped === 2 && !hasPrompt) {
    setStatus('Provide content before generating SSML.')
    setStatusError(true)
    return
  }
  
  // Can't skip to step 3 without SSML
  if (clamped === 3 && !hasSsml) {
    setStatus('Generate SSML before rendering narration.')
    setStatusError(true)
    return
  }
  
  setCurrentStep(clamped)
}

// Auto-advance after SSML generation
useEffect(() => {
  if (hasSsml && currentStep === 2) {
    setCurrentStep(3)
  }
}, [hasSsml, currentStep])

// Auto-scroll to active step
useEffect(() => {
  const refMap = {
    1: scriptSectionRef,
    2: ssmlSectionRef,
    3: voiceSectionRef,
  }
  const targetRef = refMap[currentStep]
  if (targetRef?.current) {
    targetRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}, [currentStep])
```

**Step Validation Rules:**
- Step 1 → 2: Requires `prompt` (non-empty text)
- Step 2 → 3: Requires `ssml` (generated or manually edited)
- Backward navigation: Always allowed
- Forward navigation: Blocked if prerequisites not met

---

*This document continues in Part 3...*
# Synthetic Voiceover Service Reference - Part 3

*Continuation from Part 2...*

---

## 6. Data Flow & Processing Pipeline

### 6.1 End-to-End Voiceover Generation Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    USER INTERACTION FLOW                             │
└─────────────────────────────────────────────────────────────────────┘

Step 1: Content Provision
   User selects input mode: GenAI | Paste | Audio
   │
   ├─> GenAI Mode: User describes scenario/audience/goals
   ├─> Paste Mode: User pastes existing script
   └─> Audio Mode: User speaks into microphone
   │
   └─> Text captured in prompt state
   
Step 2: SSML Generation
   User clicks "Generate SSML"
   │
   └─> Frontend sends POST /generate-ssml
       {
         "prompt": "...",
         "persona": "warm-guide",
         "language": "English"
       }
       │
       ↓
       ┌────────────────────────────────────┐
       │   BACKEND SSML GENERATION          │
       ├────────────────────────────────────┤
       │ 1. Compose Llama3 prompt           │
       │ 2. Build 7-attempt retry plan      │
       │ 3. Loop through attempts:          │
       │    a. Invoke Bedrock               │
       │    b. Extract generation text      │
       │    c. Check for echo               │
       │    d. If valid, break              │
       │    e. If invalid, escalate params  │
       │ 4. If all fail, use fallback SSML  │
       │ 5. Return SSML + metadata          │
       └────────────────────────────────────┘
       │
       ↓
   Frontend receives SSML
   │
   └─> SSML displayed in editor (expandable)
       User can manually edit SSML if desired
       Auto-advance to Step 3

Step 3: Audio Synthesis
   User selects voice from catalog
   User clicks "Synthesize"
   │
   └─> Frontend sends POST /synthesize
       {
         "voiceId": "Joanna",
         "ssml": "<speak>...</speak>",
         "outputFormat": "mp3"
       }
       │
       ↓
       ┌────────────────────────────────────┐
       │   BACKEND TTS SYNTHESIS            │
       ├────────────────────────────────────┤
       │ 1. Normalize SSML                  │
       │    - Add <speak> wrapper           │
       │    - Convert break times to ms     │
       │    - Escape ampersands             │
       │    - Validate XML structure        │
       │ 2. Try neural engine               │
       │ 3. If InvalidSsmlException:        │
       │    a. Sanitize for neural          │
       │    b. Try standard engine          │
       │    c. Try plain text SSML          │
       │    d. Try text-only (no SSML)      │
       │    e. Try safe minimal fallback    │
       │ 4. Stream audio bytes              │
       │ 5. Return base64 audio + metadata  │
       └────────────────────────────────────┘
       │
       ↓
   Frontend receives audio (base64)
   │
   ├─> Decode base64 to binary
   ├─> Create Blob
   ├─> Generate Object URL
   └─> Display audio player + download button
```

### 6.2 SSML Generation Sequence Diagram

```
Frontend                Flask API              Service Layer           AWS Bedrock
   │                       │                        │                      │
   │ POST /generate-ssml   │                        │                      │
   ├──────────────────────>│                        │                      │
   │  {prompt, persona}    │                        │                      │
   │                       │ generate_ssml()        │                      │
   │                       ├───────────────────────>│                      │
   │                       │                        │ _compose_prompt()    │
   │                       │                        ├──────────┐           │
   │                       │                        │          │           │
   │                       │                        │<─────────┘           │
   │                       │                        │ _build_attempt_plan()│
   │                       │                        ├──────────┐           │
   │                       │                        │          │           │
   │                       │                        │<─────────┘           │
   │                       │                        │                      │
   │                       │                        │ [Loop: Attempts 1-7] │
   │                       │                        │                      │
   │                       │                        │ _invoke_bedrock()    │
   │                       │                        ├─────────────────────>│
   │                       │                        │  {prompt, temp, top_p}│
   │                       │                        │                      │
   │                       │                        │ <response_body>      │
   │                       │                        │<─────────────────────┤
   │                       │                        │                      │
   │                       │                        │ _extract_generation()│
   │                       │                        ├──────────┐           │
   │                       │                        │          │           │
   │                       │                        │<─────────┘           │
   │                       │                        │ _looks_like_echo()   │
   │                       │                        ├──────────┐           │
   │                       │                        │          │           │
   │                       │                        │<─────────┘           │
   │                       │                        │                      │
   │                       │                        │ [If echo/empty:      │
   │                       │                        │  Continue to next    │
   │                       │                        │  attempt with higher │
   │                       │                        │  temp/top_p]         │
   │                       │                        │                      │
   │                       │                        │ [If valid: break]    │
   │                       │                        │                      │
   │                       │                        │ [If all fail:        │
   │                       │                        │  _fallback_ssml()]   │
   │                       │                        │                      │
   │                       │ <return SSML + meta>   │                      │
   │                       │<───────────────────────┤                      │
   │                       │                        │                      │
   │ {ssml, meta}          │                        │                      │
   │<──────────────────────┤                        │                      │
   │                       │                        │                      │
```

### 6.3 TTS Synthesis Sequence Diagram

```
Frontend                Flask API              Service Layer           AWS Polly
   │                       │                        │                      │
   │ POST /synthesize      │                        │                      │
   ├──────────────────────>│                        │                      │
   │  {voiceId, ssml}      │                        │                      │
   │                       │ synthesize_speech()    │                      │
   │                       ├───────────────────────>│                      │
   │                       │                        │ _normalize_ssml()    │
   │                       │                        ├──────────┐           │
   │                       │                        │          │           │
   │                       │                        │<─────────┘           │
   │                       │                        │                      │
   │                       │                        │ polly.synthesize()   │
   │                       │                        ├─────────────────────>│
   │                       │                        │  {neural, SSML}      │
   │                       │                        │                      │
   │                       │                        │ [InvalidSsmlException]│
   │                       │                        │<─────────────────────┤
   │                       │                        │                      │
   │                       │                        │ _sanitize_for_neural()│
   │                       │                        ├──────────┐           │
   │                       │                        │          │           │
   │                       │                        │<─────────┘           │
   │                       │                        │                      │
   │                       │                        │ polly.synthesize()   │
   │                       │                        ├─────────────────────>│
   │                       │                        │  {neural, sanitized} │
   │                       │                        │                      │
   │                       │                        │ [Still failing]      │
   │                       │                        │<─────────────────────┤
   │                       │                        │                      │
   │                       │                        │ polly.synthesize()   │
   │                       │                        ├─────────────────────>│
   │                       │                        │  {standard, sanitized}│
   │                       │                        │                      │
   │                       │                        │ <AudioStream>        │
   │                       │                        │<─────────────────────┤
   │                       │                        │                      │
   │                       │                        │ audio_bytes.read()   │
   │                       │                        ├──────────┐           │
   │                       │                        │          │           │
   │                       │                        │<─────────┘           │
   │                       │                        │                      │
   │                       │ <audio_bytes + meta>   │                      │
   │                       │<───────────────────────┤                      │
   │                       │                        │                      │
   │ {audio (base64), meta}│                        │                      │
   │<──────────────────────┤                        │                      │
   │                       │                        │                      │
```

### 6.4 Voice Catalog Caching Flow

```
┌────────────────────────────────────────────────────────────┐
│              VOICE CATALOG CACHING STRATEGY                │
└────────────────────────────────────────────────────────────┘

Frontend Startup
   │
   └─> useEffect(() => { loadVoices() })
       │
       └─> GET /voices
           │
           ↓
       ┌─────────────────────────────────────┐
       │   Backend Voice Cache Check          │
       ├─────────────────────────────────────┤
       │ if _voice_cache is not None:        │
       │    return _voice_cache (cached)     │
       │                                      │
       │ else:                                │
       │    paginator = polly.paginate()     │
       │    for page in pages:               │
       │       filter neural voices          │
       │       append to voices[]            │
       │    voices.sort(by language, name)   │
       │    _voice_cache = voices            │
       │    return voices                    │
       └─────────────────────────────────────┘
           │
           ↓
       Frontend receives voice list
       │
       ├─> setVoices(voiceList)
       ├─> setSelectedVoice(voiceList[0].id) // Default to first voice
       └─> setVoicesLoading(false)

Cache Lifetime:
- Instance-level: Cached for life of Flask process
- Frontend-level: Fetched once on component mount
- Invalidation: Requires Flask process restart or browser refresh
```

### 6.5 Error Propagation Flow

**SSML Generation Error Path:**
```
Bedrock API Error
   │
   ├─> BotoCoreError (network, config)
   │   └─> Log attempt as "error"
   │       Continue to next attempt
   │
   ├─> ClientError (throttling, auth)
   │   └─> Log attempt as "error"
   │       Continue to next attempt
   │
   └─> Unexpected Exception
       └─> Log attempt as "error"
           Continue to next attempt

[After all attempts exhausted]
   │
   └─> Generate fallback SSML
       Return {ssml, meta: {fallback: true, fallback_reason}}

Frontend receives response
   │
   ├─> If meta.fallback === true
   │   └─> Display warning status
   │       SSML still usable but template-based
   │
   └─> If no SSML returned at all
       └─> Display error status
           Block synthesis step
```

**TTS Synthesis Error Path:**
```
Polly API Error
   │
   ├─> InvalidSsmlException + "unsupported neural feature"
   │   └─> Sanitize SSML (remove amazon: tags)
   │       Retry neural
   │       │
   │       ├─> Success: Return audio
   │       └─> Fail: Try standard engine
   │           │
   │           ├─> Success: Return audio
   │           └─> Fail: Try safe minimal fallback
   │
   ├─> InvalidSsmlException (generic)
   │   └─> Sanitize SSML
   │       Retry neural
   │       │
   │       ├─> Success: Return audio
   │       └─> Fail: Try plain text in <speak>
   │           │
   │           ├─> Success: Return audio
   │           └─> Fail: Try text-only (no SSML)
   │               │
   │               ├─> Success: Return audio
   │               └─> Fail: Try safe minimal fallback
   │
   ├─> BotoCoreError / ClientError (other)
   │   └─> Try safe minimal fallback
   │       │
   │       └─> Fail: Raise RuntimeError
   │
   └─> Unexpected Exception
       └─> Re-raise (Flask error handler catches)

Frontend receives error response
   │
   └─> Display error.response?.data?.error || error.message
       Set statusError = true
       Audio player disabled
```

---

## 7. AWS Integration

### 7.1 AWS Bedrock Integration

**Service**: Amazon Bedrock Runtime  
**Model**: `meta.llama3-70b-instruct-v1:0` (default)  
**Region**: Configured via `BEDROCK_REGION` (defaults to `AWS_REGION`)

**Client Initialization:**
```python
bedrock_runtime = boto3.client(
    "bedrock-runtime",
    region_name=os.environ.get("BEDROCK_REGION", "us-east-1")
)
```

**API Operations:**

1. **InvokeModel** (Primary)
   ```python
   response = bedrock_runtime.invoke_model(
       modelId="meta.llama3-70b-instruct-v1:0",
       contentType="application/json",
       accept="application/json",
       body=json.dumps({
           "prompt": "<s>[INST] ... [/INST]",
           "max_gen_len": 900,
           "temperature": 0.6,
           "top_p": 0.9
       }).encode("utf-8")
   )
   
   response_body = json.loads(response["body"].read())
   # {"generation": "...", "prompt_token_count": 123, "generation_token_count": 456}
   ```

**Model-Specific Parameters:**

| Parameter | Type | Range | Purpose |
|-----------|------|-------|---------|
| `prompt` | string | - | Llama3 instruction format with system/user messages |
| `max_gen_len` | integer | 1-2048 | Maximum tokens to generate (default: 900) |
| `temperature` | float | 0.0-1.0 | Sampling randomness (escalates 0.6→1.0) |
| `top_p` | float | 0.0-1.0 | Nucleus sampling threshold (escalates 0.9→0.996) |

**Response Formats Supported:**

```python
# Format 1: Simple generation field (Llama native)
{
  "generation": "string",
  "prompt_token_count": integer,
  "generation_token_count": integer
}

# Format 2: Generations array
{
  "generations": [
    {"text": "string"}
  ]
}

# Format 3: Outputs array
{
  "outputs": [
    {"text": "string"}
  ]
}

# Format 4: Content block (Claude format)
{
  "content": [
    {"type": "text", "text": "string"}
  ]
}

# Format 5: Message format
{
  "message": {
    "content": [
      {"type": "text", "text": "string"}
    ]
  }
}
```

**IAM Permissions Required:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/meta.llama3-70b-instruct-v1:0"
      ]
    }
  ]
}
```

**Rate Limits:**
- **Requests per minute**: Varies by region and account (typically 50-500)
- **Tokens per minute**: Model-specific (Llama3-70B: ~50K tokens/min)
- **Concurrent requests**: Typically 5-10 per model

**Cost Estimation (us-east-1, as of Oct 2025):**
- **Llama3-70B**: $0.00265/1K input tokens, $0.00354/1K output tokens
- **Average SSML generation**: ~200 input tokens, ~300 output tokens
- **Cost per generation**: ~$0.0016

### 7.2 AWS Polly Integration

**Service**: Amazon Polly  
**Engine**: Neural (primary), Standard (fallback)  
**Region**: Configured via `POLLY_REGION` (defaults to `BEDROCK_REGION`)

**Client Initialization:**
```python
polly = boto3.client(
    "polly",
    region_name=os.environ.get("POLLY_REGION", "us-east-1")
)
```

**API Operations:**

1. **SynthesizeSpeech** (Primary)
   ```python
   response = polly.synthesize_speech(
       VoiceId="Joanna",
       Text="<speak>Hello world</speak>",
       TextType="ssml",
       Engine="neural",
       OutputFormat="mp3",
       SampleRate="24000"  # Optional
   )
   
   audio_stream = response["AudioStream"]
   audio_bytes = audio_stream.read()
   ```

2. **DescribeVoices** (Voice Catalog)
   ```python
   paginator = polly.get_paginator("describe_voices")
   for page in paginator.paginate(Engine="neural"):
       for voice in page["Voices"]:
           # Filter neural-capable voices
           if "neural" in voice["SupportedEngines"]:
               voice_data = {
                   "id": voice["Id"],
                   "name": voice["Name"],
                   "language_code": voice["LanguageCode"],
                   "gender": voice["Gender"]
               }
   ```

**SynthesizeSpeech Parameters:**

| Parameter | Type | Required | Values |
|-----------|------|----------|--------|
| `VoiceId` | string | Yes | Joanna, Matthew, Salli, etc. (50+ voices) |
| `Text` | string | Yes | SSML or plain text (max 3000 chars for neural) |
| `TextType` | string | Yes | `ssml` or `text` |
| `Engine` | string | Yes | `neural` or `standard` |
| `OutputFormat` | string | Yes | `mp3`, `ogg_vorbis`, `pcm` |
| `SampleRate` | string | No | `8000`, `16000`, `22050`, `24000` (mp3/ogg) |

**Supported Output Formats:**

| Format | MIME Type | Sample Rates | Use Case |
|--------|-----------|--------------|----------|
| `mp3` | audio/mpeg | 8000, 16000, 22050, 24000 | Default, best compatibility |
| `ogg_vorbis` | audio/ogg | 8000, 16000, 22050 | Open source, smaller files |
| `pcm` | audio/wav | 8000, 16000 | Uncompressed, editing |

**Neural Voice Capabilities:**

| Language | Neural Voices | Standard Voices |
|----------|---------------|-----------------|
| English (US) | 24 | 16 |
| English (British) | 6 | 5 |
| Spanish | 8 | 5 |
| French | 6 | 4 |
| German | 5 | 3 |
| Others | 20+ | 30+ |

**SSML Tag Support (Neural Engine):**

| Tag | Supported | Notes |
|-----|-----------|-------|
| `<speak>` | ✅ | Required wrapper |
| `<p>` | ✅ | Paragraph break |
| `<s>` | ✅ | Sentence break |
| `<break>` | ✅ | Pause (time in ms) |
| `<emphasis>` | ✅ | Stress on words |
| `<prosody>` | ✅ | Rate, pitch, volume |
| `<say-as>` | ✅ | Number formatting |
| `<sub>` | ✅ | Phonetic substitution |
| `<amazon:effect>` | ❌ | Not supported in neural |
| `<amazon:domain>` | ❌ | Not supported in neural |
| `<amazon:auto-breaths>` | ❌ | Not supported in neural |

**IAM Permissions Required:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "polly:SynthesizeSpeech",
        "polly:DescribeVoices"
      ],
      "Resource": "*"
    }
  ]
}
```

**Rate Limits:**
- **Requests per second**: 100 (can request increase)
- **Concurrent requests**: 10
- **Character limits**: 
  - Neural: 3,000 characters per request
  - Standard: 6,000 characters per request

**Cost Estimation (us-east-1, as of Oct 2025):**
- **Neural voices**: $16.00 per 1M characters
- **Standard voices**: $4.00 per 1M characters
- **Average voiceover**: ~500 characters
- **Cost per synthesis**: ~$0.008 (neural) or ~$0.002 (standard)

### 7.3 Region Selection Strategy

**Configuration Priority:**
1. `POLLY_REGION` environment variable
2. `BEDROCK_REGION` environment variable
3. `AWS_REGION` environment variable (default: `us-east-1`)

**Regional Availability:**

| Region | Bedrock (Llama3) | Polly Neural | Polly Standard |
|--------|------------------|--------------|----------------|
| us-east-1 | ✅ | ✅ | ✅ |
| us-west-2 | ✅ | ✅ | ✅ |
| eu-west-1 | ✅ | ✅ | ✅ |
| ap-southeast-1 | ✅ | ✅ | ✅ |
| ap-northeast-1 | ✅ | ✅ | ✅ |

**Best Practices:**
- **Same region for both services**: Reduces latency
- **Use us-east-1 for development**: Most comprehensive service availability
- **Production**: Choose region closest to users
- **Multi-region**: Consider regional failover for high availability

### 7.4 Credential Management

**Credential Sources (in order of precedence):**

1. **Environment Variables:**
   ```bash
   export AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
   export AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
   export AWS_SESSION_TOKEN=... # Optional for temporary credentials
   ```

2. **AWS Credentials File** (`~/.aws/credentials`):
   ```ini
   [default]
   aws_access_key_id = AKIAIOSFODNN7EXAMPLE
   aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
   ```

3. **IAM Role** (EC2/ECS/Lambda):
   - Automatically provided by AWS runtime
   - No explicit credentials needed in code
   - Rotates automatically

4. **AWS SSO** (Single Sign-On):
   ```bash
   aws sso login --profile my-profile
   export AWS_PROFILE=my-profile
   ```

**Security Best Practices:**
- ✅ Use IAM roles when running on AWS infrastructure
- ✅ Use temporary credentials (STS) for developers
- ✅ Enable MFA for production credentials
- ✅ Rotate access keys every 90 days
- ❌ Never commit credentials to version control
- ❌ Never use root account credentials

---

## 8. API Reference

### 8.1 Endpoint: POST /generate-ssml

**Description**: Generate expressive SSML script from text prompt using LLM.

**URL**: `/generate-ssml`  
**Method**: `POST`  
**Content-Type**: `application/json`

**Request Body:**
```json
{
  "prompt": "string (required)",
  "persona": "string (optional)",
  "language": "string (optional)",
  "temperature": "float (optional, default 0.6)",
  "top_p": "float (optional, default 0.9)"
}
```

**Request Schema:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `prompt` | string | Yes | - | User's text input describing the voiceover content |
| `persona` | string | No | null | Tone guidance (e.g., "Friendly mentor", "Energetic announcer") |
| `language` | string | No | null | Target language (e.g., "English", "Spanish") |
| `temperature` | float | No | 0.6 | Base sampling temperature (0.0-1.0) |
| `top_p` | float | No | 0.9 | Base nucleus sampling threshold (0.0-1.0) |

**Success Response:**

**Code**: `200 OK`

```json
{
  "ssml": "<speak><p><s>Welcome to our platform.</s></p><break time=\"500ms\"/><p><s>Discover powerful features designed to elevate your experience.</s></p></speak>",
  "meta": {
    "prompt_tokens": 187,
    "generation_tokens": 312,
    "attempt_count": 1,
    "attempts": [
      {
        "attempt": 1,
        "label": "primary",
        "status": "ok",
        "reason": null,
        "notes": "initial generation",
        "generation_length": 245,
        "temperature": 0.6,
        "top_p": 0.9,
        "inference_variant": "prompt"
      }
    ]
  }
}
```

**Fallback Response (when all attempts fail):**

**Code**: `200 OK`

```json
{
  "ssml": "<speak><p><s>Welcome to our platform.</s></p><break time=\"300ms\"/><p><s>Discover powerful features.</s></p><break time=\"500ms\"/><p><s>Thank you for watching.</s></p></speak>",
  "meta": {
    "prompt_tokens": null,
    "generation_tokens": null,
    "fallback": true,
    "fallback_template": true,
    "fallback_reason": "Model response was empty or simply echoed the prompt.",
    "attempt_count": 7,
    "attempts": [
      {
        "attempt": 1,
        "label": "primary",
        "status": "retry",
        "reason": "echo",
        "notes": "initial generation",
        "generation_length": 156,
        "temperature": 0.6,
        "top_p": 0.9
      },
      ...
    ]
  }
}
```

**Error Responses:**

**Code**: `400 Bad Request`
```json
{
  "error": "Prompt is required."
}
```

**Code**: `500 Internal Server Error`
```json
{
  "error": "Model invocation failed: <details>"
}
```

**Example cURL Request:**
```bash
curl -X POST http://localhost:5003/generate-ssml \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Introduce our new AI-powered video editing suite. Target audience: content creators.",
    "persona": "Energetic announcer with upbeat pacing",
    "language": "English"
  }'
```

**Response Time**: 5-30 seconds (depends on attempt count and Bedrock latency)

---

### 8.2 Endpoint: GET /voices

**Description**: Retrieve catalog of available neural voices.

**URL**: `/voices`  
**Method**: `GET`  
**Content-Type**: `application/json`

**Request**: No body required

**Success Response:**

**Code**: `200 OK`

```json
{
  "voices": [
    {
      "id": "Joanna",
      "name": "Joanna",
      "language_code": "en-US",
      "language_name": "US English",
      "gender": "Female",
      "style_list": []
    },
    {
      "id": "Matthew",
      "name": "Matthew",
      "language_code": "en-US",
      "language_name": "US English",
      "gender": "Male",
      "style_list": []
    },
    {
      "id": "Lucia",
      "name": "Lucia",
      "language_code": "es-ES",
      "language_name": "Spanish",
      "gender": "Female",
      "style_list": ["es-MX"]
    }
  ]
}
```

**Response Schema:**

| Field | Type | Description |
|-------|------|-------------|
| `voices` | array | List of voice objects |
| `voices[].id` | string | Polly voice ID (use for synthesis) |
| `voices[].name` | string | Display name |
| `voices[].language_code` | string | ISO language code (e.g., en-US) |
| `voices[].language_name` | string | Human-readable language name |
| `voices[].gender` | string | Male, Female, or Neutral |
| `voices[].style_list` | array | Additional supported language codes |

**Error Responses:**

**Code**: `500 Internal Server Error`
```json
{
  "error": "Failed to fetch voice catalog: <details>"
}
```

**Example cURL Request:**
```bash
curl http://localhost:5003/voices
```

**Response Time**: <1 second (cached after first request)

**Caching**: Voice catalog is cached in memory for the lifetime of the Flask process.

---

### 8.3 Endpoint: POST /synthesize

**Description**: Synthesize audio from SSML using Polly neural voices.

**URL**: `/synthesize`  
**Method**: `POST`  
**Content-Type**: `application/json`

**Request Body:**
```json
{
  "voiceId": "string (required)",
  "ssml": "string (required)",
  "outputFormat": "string (optional, default 'mp3')",
  "sampleRate": "string (optional)"
}
```

**Request Schema:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `voiceId` | string | Yes | - | Polly voice ID (get from /voices endpoint) |
| `ssml` | string | Yes | - | SSML content (will be normalized if needed) |
| `outputFormat` | string | No | "mp3" | Audio format: mp3, ogg_vorbis, pcm |
| `sampleRate` | string | No | null | Sample rate in Hz: 8000, 16000, 22050, 24000 |

**Success Response:**

**Code**: `200 OK`

```json
{
  "audio": "//uQx...base64_encoded_audio_bytes...AAAA",
  "meta": {
    "engine": "neural",
    "normalized": true,
    "normalization_notes": ["wrapped_in_speak", "normalized_break_time"],
    "sanitized": false,
    "sanitized_ssml": null,
    "plain_retry": false,
    "plain_retry_ssml": null,
    "text_fallback": false,
    "text_fallback_text": null,
    "safe_minimal": false,
    "safe_minimal_ssml": null,
    "safe_minimal_engine": null,
    "safe_minimal_mode": null,
    "content_type": "audio/mpeg"
  }
}
```

**Response Schema:**

| Field | Type | Description |
|-------|------|-------------|
| `audio` | string | Base64-encoded audio bytes |
| `meta.engine` | string | Engine used: neural or standard |
| `meta.normalized` | boolean | Whether SSML was modified during normalization |
| `meta.normalization_notes` | array | List of normalization operations applied |
| `meta.sanitized` | boolean | Whether SSML was sanitized for neural compatibility |
| `meta.plain_retry` | boolean | Whether plain text SSML retry was used |
| `meta.text_fallback` | boolean | Whether text-only synthesis was used |
| `meta.safe_minimal` | boolean | Whether safe minimal fallback was triggered |
| `meta.content_type` | string | MIME type of audio (audio/mpeg, audio/ogg, audio/wav) |

**Error Responses:**

**Code**: `400 Bad Request`
```json
{
  "error": "voiceId is required"
}
```

**Code**: `500 Internal Server Error`
```json
{
  "error": "Voice synthesis failed: <details>"
}
```

**Example cURL Request:**
```bash
curl -X POST http://localhost:5003/synthesize \
  -H "Content-Type: application/json" \
  -d '{
    "voiceId": "Joanna",
    "ssml": "<speak><p>Hello world</p></speak>",
    "outputFormat": "mp3",
    "sampleRate": "24000"
  }'
```

**Response Time**: 2-10 seconds (depends on SSML length and fallback stages)

**Decoding Audio (Frontend):**
```javascript
const audioBase64 = response.data.audio
const binaryString = atob(audioBase64)
const bytes = new Uint8Array(binaryString.length)
for (let i = 0; i < binaryString.length; i++) {
  bytes[i] = binaryString.charCodeAt(i)
}
const blob = new Blob([bytes], { type: 'audio/mpeg' })
const url = URL.createObjectURL(blob)
// Use url in <audio> element
```

---

### 8.4 Endpoint: GET /health

**Description**: Health check endpoint for service monitoring.

**URL**: `/health`  
**Method**: `GET`  
**Content-Type**: `application/json`

**Request**: No body required

**Success Response:**

**Code**: `200 OK`

```json
{
  "status": "ok",
  "model": "meta.llama3-70b-instruct-v1:0",
  "bedrock_region": "us-east-1",
  "polly_region": "us-east-1"
}
```

**Example cURL Request:**
```bash
curl http://localhost:5003/health
```

**Response Time**: <100ms

**Use Cases:**
- Load balancer health checks
- Service discovery registration
- Monitoring/alerting systems
- Deployment validation

---

*This document continues in Part 4 (final part)...*
# Synthetic Voiceover Service Reference - Part 4 (Final)

*Continuation from Part 3...*

---

## 9. Configuration Management

### 9.1 Environment Variables

**Required Variables:**
```bash
# AWS Credentials (if not using IAM roles)
AWS_ACCESS_KEY_ID=<your_access_key>
AWS_SECRET_ACCESS_KEY=<your_secret_key>

# Optional: AWS Session Token for temporary credentials
AWS_SESSION_TOKEN=<session_token>
```

**Optional Variables with Defaults:**
```bash
# Regional Configuration
AWS_REGION=us-east-1                    # Default region for AWS services
BEDROCK_REGION=us-east-1                # Override for Bedrock service
POLLY_REGION=us-east-1                  # Override for Polly service

# Model Configuration
VOICEOVER_MODEL_ID=meta.llama3-70b-instruct-v1:0  # Bedrock model to use

# Generation Parameters
VOICEOVER_MAX_TOKENS=900                # Max tokens per LLM generation
VOICEOVER_TEMPERATURE=0.6               # Base temperature for sampling
VOICEOVER_TOP_P=0.9                     # Base top_p for sampling
VOICEOVER_MAX_ATTEMPTS=7                # Maximum retry attempts

# System Prompt Override
VOICEOVER_SYSTEM_PROMPT="You are an expert voice director..."
```

**Frontend Variables:**
```bash
# API endpoint configuration
REACT_APP_VOICE_API_BASE=http://localhost:5003

# Build configuration
NODE_ENV=development|production
```

### 9.2 Configuration Files

**Backend: `.env` File (Optional)**
```bash
# .env file in syntheticVoiceover/ directory
AWS_REGION=us-east-1
BEDROCK_REGION=us-east-1
POLLY_REGION=us-east-1
VOICEOVER_MODEL_ID=meta.llama3-70b-instruct-v1:0
VOICEOVER_MAX_TOKENS=900
VOICEOVER_TEMPERATURE=0.6
VOICEOVER_TOP_P=0.9
VOICEOVER_MAX_ATTEMPTS=7
```

**Frontend: `.env` File (Development)**
```bash
# .env file in frontend/ directory
REACT_APP_VOICE_API_BASE=http://localhost:5003
NODE_ENV=development
```

**Frontend: `.env.production` File**
```bash
# .env.production file in frontend/ directory
REACT_APP_VOICE_API_BASE=https://api.yourdomain.com/voiceover
NODE_ENV=production
```

### 9.3 Runtime Configuration

**Flask App Configuration:**
```python
# app.py
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

**Service Layer Configuration:**
```python
# When instantiating service
service = SyntheticVoiceoverService(
    bedrock_runtime=bedrock_runtime,
    polly=polly,
    model_id=os.environ.get("VOICEOVER_MODEL_ID", "meta.llama3-70b-instruct-v1:0"),
    system_prompt=os.environ.get("VOICEOVER_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT),
    max_tokens=int(os.environ.get("VOICEOVER_MAX_TOKENS", "900"))
)
```

### 9.4 Configuration Best Practices

**Development:**
- Use `.env` files for local configuration
- Store credentials in `~/.aws/credentials` (not in .env)
- Use `us-east-1` for comprehensive service availability
- Enable debug logging: `FLASK_DEBUG=1`

**Production:**
- Use environment variables (not .env files)
- Use IAM roles for EC2/ECS deployments
- Enable only ERROR/WARNING logging
- Use region closest to users
- Set appropriate timeout values

**Security:**
- ✅ Never commit `.env` to version control
- ✅ Add `.env` to `.gitignore`
- ✅ Use AWS Secrets Manager for sensitive config
- ✅ Rotate credentials regularly
- ✅ Use least-privilege IAM policies

---

## 10. Deployment & Operations

### 10.1 Local Development Setup

**Prerequisites:**
- Python 3.8+ installed
- Node.js 16+ installed
- AWS credentials configured
- Access to Bedrock and Polly services

**Backend Setup:**
```bash
# Navigate to service directory
cd syntheticVoiceover

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
AWS_REGION=us-east-1
BEDROCK_REGION=us-east-1
POLLY_REGION=us-east-1
EOF

# Start Flask server
python app.py
# Server runs on http://localhost:5003
```

**Frontend Setup:**
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Create .env file
cat > .env << EOF
REACT_APP_VOICE_API_BASE=http://localhost:5003
EOF

# Start development server
npm start
# Frontend runs on http://localhost:3000
```

### 10.2 Production Deployment

**Backend Deployment (Standalone Flask):**

```bash
# Install production WSGI server
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5003 app:app --timeout 120 --log-level info

# With systemd service
sudo tee /etc/systemd/system/voiceover.service << EOF
[Unit]
Description=Synthetic Voiceover Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/mediagenai/syntheticVoiceover
Environment="PATH=/opt/mediagenai/syntheticVoiceover/venv/bin"
Environment="AWS_REGION=us-east-1"
ExecStart=/opt/mediagenai/syntheticVoiceover/venv/bin/gunicorn -w 4 -b 0.0.0.0:5003 app:app --timeout 120
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable voiceover
sudo systemctl start voiceover
```

**Backend Deployment (Docker):**

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5003

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5003", "app:app", "--timeout", "120"]
```

```bash
# Build and run
docker build -t voiceover-service .
docker run -d -p 5003:5003 \
  -e AWS_REGION=us-east-1 \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  --name voiceover \
  voiceover-service
```

**Frontend Deployment:**

```bash
# Build production bundle
cd frontend
npm run build

# Serve with Nginx
sudo tee /etc/nginx/sites-available/mediagenai << EOF
server {
    listen 80;
    server_name yourdomain.com;
    
    root /var/www/mediagenai/frontend/build;
    index index.html;
    
    location / {
        try_files \$uri /index.html;
    }
    
    location /api/voiceover/ {
        proxy_pass http://localhost:5003/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_read_timeout 120s;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/mediagenai /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 10.3 Process Management Scripts

**Start Script (`start-backend.sh`):**
```bash
#!/bin/bash
cd "$(dirname "$0")/syntheticVoiceover"

# Activate virtual environment
source venv/bin/activate

# Start Flask app in background
nohup python app.py > ../synthetic-voiceover.log 2>&1 &

# Save PID
echo $! > ../synthetic-voiceover.pid

echo "Synthetic Voiceover service started (PID: $(cat ../synthetic-voiceover.pid))"
```

**Stop Script (`stop-backend.sh`):**
```bash
#!/bin/bash
PID_FILE="synthetic-voiceover.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null; then
        kill $PID
        echo "Synthetic Voiceover service stopped (PID: $PID)"
    else
        echo "Process $PID not found (stale PID file)"
    fi
    rm "$PID_FILE"
else
    echo "PID file not found"
fi
```

### 10.4 Monitoring & Health Checks

**Health Check Endpoint:**
```bash
# Simple health check
curl http://localhost:5003/health

# Expected response
{
  "status": "ok",
  "model": "meta.llama3-70b-instruct-v1:0",
  "bedrock_region": "us-east-1",
  "polly_region": "us-east-1"
}
```

**Monitoring Script:**
```bash
#!/bin/bash
# monitor-voiceover.sh

HEALTH_URL="http://localhost:5003/health"
ALERT_EMAIL="admin@yourdomain.com"

while true; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)
    
    if [ "$STATUS" != "200" ]; then
        echo "$(date): Voiceover service unhealthy (HTTP $STATUS)" >> voiceover-monitor.log
        # Send alert (configure mail command)
        # echo "Service down" | mail -s "Voiceover Alert" $ALERT_EMAIL
    fi
    
    sleep 60  # Check every minute
done
```

**CloudWatch Metrics (if on AWS):**
```python
# Add to app.py
import boto3
from datetime import datetime

cloudwatch = boto3.client('cloudwatch')

@app.after_request
def log_request_metrics(response):
    if request.endpoint:
        cloudwatch.put_metric_data(
            Namespace='MediaGenAI/Voiceover',
            MetricData=[
                {
                    'MetricName': 'RequestCount',
                    'Timestamp': datetime.utcnow(),
                    'Value': 1,
                    'Unit': 'Count',
                    'Dimensions': [
                        {'Name': 'Endpoint', 'Value': request.endpoint},
                        {'Name': 'StatusCode', 'Value': str(response.status_code)}
                    ]
                }
            ]
        )
    return response
```

### 10.5 Logging Strategy

**Backend Logging Configuration:**
```python
# app.py
import logging
from logging.handlers import RotatingFileHandler

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# File handler with rotation
file_handler = RotatingFileHandler(
    'voiceover-service.log',
    maxBytes=10485760,  # 10MB
    backupCount=10
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))

app.logger.addHandler(file_handler)

# Example usage
@app.route("/generate-ssml", methods=["POST"])
def generate_ssml():
    app.logger.info(f"SSML generation request from {request.remote_addr}")
    # ... processing ...
    app.logger.info(f"SSML generated in {attempt_count} attempts")
    return response
```

**Log Levels:**
- **DEBUG**: Detailed diagnostic info (development only)
- **INFO**: General operational events (default)
- **WARNING**: Non-critical issues (e.g., fallback used)
- **ERROR**: Critical failures requiring attention

**Log Aggregation (Production):**
```bash
# Install filebeat for log shipping to ELK/CloudWatch
sudo apt-get install filebeat

# Configure filebeat.yml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /var/log/voiceover-service.log
  fields:
    service: voiceover
    environment: production

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
```

---

## 11. Troubleshooting Guide

### 11.1 Common Issues

#### Issue 1: "Prompt is required" Error

**Symptoms:**
- Frontend shows "Prompt is required" message
- SSML generation button doesn't work

**Causes:**
- Empty prompt text
- Whitespace-only input
- State not updated after clearing textarea

**Solutions:**
```javascript
// Ensure prompt is trimmed and non-empty
if (!prompt.trim()) {
  setStatus('Enter content to generate SSML.')
  return
}
```

**Verification:**
```bash
# Test with curl
curl -X POST http://localhost:5003/generate-ssml \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Test narration"}'
```

---

#### Issue 2: SSML Generation Returns Fallback Template

**Symptoms:**
- SSML generated but generic/template-like
- Status shows "using fallback template"
- `meta.fallback: true` in response

**Causes:**
- Model repeatedly echoes prompt
- Model returns empty generations
- All 7 attempts failed validation

**Solutions:**

1. **Check Prompt Quality:**
   ```
   ❌ Bad: "product"
   ✅ Good: "Introduce our new AI-powered video editing suite for content creators."
   ```

2. **Adjust Temperature:**
   ```json
   {
     "prompt": "...",
     "temperature": 0.8
   }
   ```

3. **Review Attempt Logs:**
   ```python
   # Check meta.attempts array in response
   for attempt in response["meta"]["attempts"]:
       print(f"Attempt {attempt['attempt']}: {attempt['status']} - {attempt.get('reason')}")
   ```

4. **Check Bedrock Access:**
   ```bash
   aws bedrock list-foundation-models --region us-east-1
   ```

---

#### Issue 3: "InvalidSsmlException" During Synthesis

**Symptoms:**
- Audio synthesis fails
- Error: "InvalidSsmlException"
- Neural engine rejects SSML

**Causes:**
- Unsupported SSML tags for neural engine
- Malformed XML structure
- Unsupported rate/volume values

**Solutions:**

1. **Automatic Sanitization:**
   - Service automatically sanitizes SSML
   - Check `meta.sanitized: true` in response

2. **Manual SSML Validation:**
   ```python
   from xml.etree import ElementTree as ET
   
   try:
       ET.fromstring(ssml)
       print("Valid XML")
   except ET.ParseError as e:
       print(f"Invalid XML: {e}")
   ```

3. **Remove Unsupported Tags:**
   ```xml
   <!-- ❌ Not supported in neural -->
   <amazon:effect name="whispered">Hello</amazon:effect>
   
   <!-- ✅ Supported in neural -->
   <emphasis level="moderate">Hello</emphasis>
   ```

4. **Check Response Metadata:**
   ```json
   {
     "meta": {
       "engine": "standard",  // Fell back to standard
       "sanitized": true,
       "sanitized_ssml": "<speak>...</speak>"
     }
   }
   ```

---

#### Issue 4: Voice Catalog Empty or Fails to Load

**Symptoms:**
- Frontend shows "Unable to load voice catalog"
- `/voices` endpoint returns empty array
- Voice selection disabled

**Causes:**
- Missing Polly permissions
- Invalid AWS credentials
- Regional limitations
- Network connectivity issues

**Solutions:**

1. **Verify AWS Credentials:**
   ```bash
   aws sts get-caller-identity
   # Should return your account info
   ```

2. **Test Polly Access:**
   ```bash
   aws polly describe-voices --engine neural --region us-east-1
   ```

3. **Check IAM Permissions:**
   ```json
   {
     "Effect": "Allow",
     "Action": [
       "polly:DescribeVoices",
       "polly:SynthesizeSpeech"
     ],
     "Resource": "*"
   }
   ```

4. **Review Backend Logs:**
   ```bash
   tail -f synthetic-voiceover.log | grep "voices"
   ```

5. **Manual Endpoint Test:**
   ```bash
   curl http://localhost:5003/voices
   ```

---

#### Issue 5: Audio Playback Fails in Browser

**Symptoms:**
- Audio player shows "Failed to load"
- No sound when clicking play
- Download works but playback doesn't

**Causes:**
- Invalid base64 decoding
- MIME type mismatch
- CORS issues
- Browser codec support

**Solutions:**

1. **Verify Base64 Encoding:**
   ```javascript
   const audioBase64 = response.data.audio
   console.log('Audio length:', audioBase64.length)
   console.log('First 50 chars:', audioBase64.substring(0, 50))
   ```

2. **Check MIME Type:**
   ```javascript
   const mimeType = response.data.meta.content_type
   console.log('MIME type:', mimeType)
   
   const blob = new Blob([bytes], { type: mimeType })
   ```

3. **Test with Different Format:**
   ```json
   {
     "voiceId": "Joanna",
     "ssml": "...",
     "outputFormat": "ogg_vorbis"
   }
   ```

4. **Check Browser Console:**
   - Open DevTools (F12)
   - Look for codec errors
   - Check Network tab for failed requests

5. **Manual Audio Test:**
   ```bash
   # Decode base64 to file
   echo "<base64_string>" | base64 -d > test.mp3
   
   # Play with ffplay (if ffmpeg installed)
   ffplay test.mp3
   ```

---

#### Issue 6: Speech Recognition Not Available

**Symptoms:**
- "Speech recognition is not available" message
- Recording controls disabled
- `canRecord` state is false

**Causes:**
- Browser doesn't support Web Speech API
- HTTPS required (not localhost)
- Microphone permissions denied

**Solutions:**

1. **Check Browser Support:**
   ```javascript
   const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
   console.log('SpeechRecognition available:', !!SpeechRecognition)
   ```

   **Supported Browsers:**
   - ✅ Chrome/Edge (desktop & mobile)
   - ✅ Safari (desktop & mobile)
   - ❌ Firefox (limited support)

2. **Ensure HTTPS:**
   - Web Speech API requires HTTPS (except localhost)
   - Use `https://` or `localhost` for testing

3. **Grant Microphone Permissions:**
   - Browser will prompt on first use
   - Check site settings if blocked
   - Chrome: `chrome://settings/content/microphone`

4. **Fallback to Manual Input:**
   - Use "Paste" or "GenAI" input modes
   - Speech recognition is optional feature

---

#### Issue 7: Service Crashes or Becomes Unresponsive

**Symptoms:**
- Health check fails
- Requests timeout
- Process exits unexpectedly

**Causes:**
- Memory exhaustion
- Unhandled exceptions
- AWS API throttling
- Long-running requests blocking workers

**Solutions:**

1. **Check Process Status:**
   ```bash
   # Check if process is running
   ps aux | grep "app.py"
   
   # Check PID file
   cat synthetic-voiceover.pid
   ```

2. **Review Error Logs:**
   ```bash
   tail -n 100 synthetic-voiceover.log
   
   # Check system logs
   sudo journalctl -u voiceover -n 100
   ```

3. **Monitor Memory Usage:**
   ```bash
   # Check memory
   free -h
   
   # Check process memory
   ps -p <PID> -o %mem,rss,vsz
   ```

4. **Increase Worker Timeout:**
   ```bash
   # Gunicorn with longer timeout
   gunicorn -w 4 -b 0.0.0.0:5003 app:app --timeout 180 --graceful-timeout 60
   ```

5. **Implement Rate Limiting:**
   ```python
   from flask_limiter import Limiter
   
   limiter = Limiter(
       app,
       key_func=lambda: request.remote_addr,
       default_limits=["100 per hour"]
   )
   
   @app.route("/generate-ssml", methods=["POST"])
   @limiter.limit("10 per minute")
   def generate_ssml():
       # ...
   ```

6. **Add Circuit Breaker:**
   ```python
   from pybreaker import CircuitBreaker
   
   bedrock_breaker = CircuitBreaker(
       fail_max=5,
       timeout_duration=60
   )
   
   @bedrock_breaker
   def _invoke_bedrock(self, body):
       # ... existing code ...
   ```

---

### 11.2 Debugging Techniques

**Enable Debug Logging:**
```python
# app.py
import logging
logging.basicConfig(level=logging.DEBUG)

@app.route("/generate-ssml", methods=["POST"])
def generate_ssml():
    app.logger.debug(f"Request payload: {request.get_json()}")
    # ... processing ...
    app.logger.debug(f"Attempt logs: {attempt_logs}")
    app.logger.debug(f"Final SSML length: {len(generation)}")
```

**Trace Request Flow:**
```python
import uuid
from flask import g

@app.before_request
def before_request():
    g.request_id = str(uuid.uuid4())
    app.logger.info(f"[{g.request_id}] {request.method} {request.path}")

@app.after_request
def after_request(response):
    app.logger.info(f"[{g.request_id}] Response: {response.status_code}")
    return response
```

**Test Individual Components:**
```python
# test_service.py
from synthetic_voiceover_service import SyntheticVoiceoverService
import boto3

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
polly = boto3.client("polly", region_name="us-east-1")

service = SyntheticVoiceoverService(bedrock, polly, "meta.llama3-70b-instruct-v1:0", "...", 900)

# Test SSML generation
ssml, meta = service.generate_ssml("Test prompt", temperature=0.7)
print(f"Generated SSML: {ssml}")
print(f"Metadata: {meta}")

# Test voice listing
voices = service.list_voices()
print(f"Found {len(voices)} voices")

# Test synthesis
audio_meta, audio_bytes = service.synthesize_speech(
    voice_id="Joanna",
    ssml="<speak>Hello</speak>"
)
print(f"Audio size: {len(audio_bytes)} bytes")
```

---

## 12. Performance Optimization

### 12.1 Backend Optimizations

**1. Voice Catalog Caching**
```python
# Already implemented - voice catalog cached in memory
@lru_cache(maxsize=1)
def _list_neural_voices():
    # Fetched once, cached forever (until process restart)
    pass
```

**2. Connection Pooling**
```python
# Use boto3 session with connection pooling
from botocore.config import Config

config = Config(
    max_pool_connections=50,
    retries={'max_attempts': 3}
)

bedrock_runtime = boto3.client(
    "bedrock-runtime",
    region_name=BEDROCK_REGION,
    config=config
)
```

**3. Async Processing (Optional)**
```python
# For high-load scenarios, consider async
from flask import Flask
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=10)

@app.route("/generate-ssml", methods=["POST"])
def generate_ssml():
    # Submit to thread pool
    future = executor.submit(service.generate_ssml, prompt, persona, language)
    
    # Wait with timeout
    try:
        ssml, meta = future.result(timeout=90)
    except TimeoutError:
        return jsonify({"error": "Generation timeout"}), 504
```

**4. Response Compression**
```python
from flask_compress import Compress

compress = Compress()
compress.init_app(app)

# Automatically compresses responses > 500 bytes
```

**5. Reduce Retry Attempts (if needed)**
```bash
# Set lower max attempts for faster failures
export VOICEOVER_MAX_ATTEMPTS=4
```

### 12.2 Frontend Optimizations

**1. Debounce Prompt Input**
```javascript
import { debounce } from 'lodash'

const debouncedSetPrompt = useCallback(
  debounce((value) => setPrompt(value), 300),
  []
)
```

**2. Lazy Load Voice Catalog**
```javascript
// Only load voices when user reaches Step 3
useEffect(() => {
  if (currentStep === 3 && voices.length === 0) {
    loadVoices()
  }
}, [currentStep])
```

**3. Audio Blob Cleanup**
```javascript
useEffect(() => {
  // Revoke old blob URLs to prevent memory leaks
  return () => {
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl)
    }
  }
}, [audioUrl])
```

**4. Optimize Re-renders**
```javascript
// Memoize expensive computations
const hasPrompt = useMemo(() => prompt.trim().length > 0, [prompt])
const hasSsml = useMemo(() => ssmlText.trim().length > 0, [ssmlText])

// Memoize callbacks
const handleGenerateSsml = useCallback(async () => {
  // ... generation logic ...
}, [prompt, persona, VOICE_API_BASE])
```

**5. Code Splitting**
```javascript
// Lazy load SyntheticVoiceover component
import React, { lazy, Suspense } from 'react'

const SyntheticVoiceover = lazy(() => import('./SyntheticVoiceover'))

function App() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <SyntheticVoiceover />
    </Suspense>
  )
}
```

### 12.3 AWS Cost Optimization

**1. Model Selection**
```bash
# Use smaller models for simpler tasks
export VOICEOVER_MODEL_ID=meta.llama3-8b-instruct-v1:0  # Cheaper alternative
```

**2. Token Limits**
```bash
# Reduce max tokens if voiceovers are typically short
export VOICEOVER_MAX_TOKENS=500
```

**3. Reduce Retry Attempts**
```bash
# Fewer attempts = lower cost, faster failures
export VOICEOVER_MAX_ATTEMPTS=3
```

**4. Use Standard Polly Engine (if acceptable)**
```python
# Modify synthesize_speech to prefer standard
request_args["Engine"] = "standard"  # 4x cheaper than neural
```

**5. Batch Processing**
```python
# If generating multiple voiceovers, batch requests
# (Not directly applicable to current architecture, but consider for future)
```

### 12.4 Monitoring & Metrics

**Key Metrics to Track:**

1. **SSML Generation:**
   - Average attempt count
   - Fallback rate (%)
   - Generation time (p50, p95, p99)
   - Token usage (input/output)

2. **TTS Synthesis:**
   - Neural vs standard engine usage
   - Normalization/sanitization rate
   - Synthesis time (p50, p95, p99)
   - Character count processed

3. **Error Rates:**
   - HTTP 4xx rate
   - HTTP 5xx rate
   - AWS API throttling rate
   - Timeout rate

4. **Resource Usage:**
   - CPU utilization
   - Memory usage
   - Network I/O
   - Request rate (RPM)

**CloudWatch Dashboard Example:**
```python
# Put custom metrics to CloudWatch
import boto3
from datetime import datetime

cloudwatch = boto3.client('cloudwatch')

def log_generation_metrics(attempt_count, fallback_used, duration_ms):
    cloudwatch.put_metric_data(
        Namespace='MediaGenAI/Voiceover',
        MetricData=[
            {
                'MetricName': 'GenerationAttempts',
                'Value': attempt_count,
                'Unit': 'Count',
                'Timestamp': datetime.utcnow()
            },
            {
                'MetricName': 'FallbackUsed',
                'Value': 1 if fallback_used else 0,
                'Unit': 'Count',
                'Timestamp': datetime.utcnow()
            },
            {
                'MetricName': 'GenerationDuration',
                'Value': duration_ms,
                'Unit': 'Milliseconds',
                'Timestamp': datetime.utcnow()
            }
        ]
    )
```

---

## 13. Appendix

### 13.1 SSML Reference

**Commonly Used Tags:**

```xml
<!-- Paragraph -->
<p>This is a paragraph with a natural pause after.</p>

<!-- Sentence -->
<s>This is a sentence.</s>

<!-- Break (pause) -->
<break time="500ms"/>
<break strength="medium"/>  <!-- weak, medium, strong, x-strong -->

<!-- Emphasis -->
<emphasis level="strong">important word</emphasis>
<emphasis level="moderate">notable word</emphasis>

<!-- Prosody (rate, pitch, volume) -->
<prosody rate="slow">Speak slowly here.</prosody>
<prosody rate="120%">Speak 20% faster.</prosody>
<prosody pitch="high">Higher pitch.</prosody>
<prosody volume="loud">Louder volume.</prosody>

<!-- Say-as (number interpretation) -->
<say-as interpret-as="cardinal">12345</say-as>  <!-- twelve thousand three hundred forty-five -->
<say-as interpret-as="ordinal">3</say-as>  <!-- third -->
<say-as interpret-as="digits">123</say-as>  <!-- one two three -->
<say-as interpret-as="date" format="mdy">10/21/2025</say-as>

<!-- Phonetic substitution -->
<sub alias="World Wide Web Consortium">W3C</sub>

<!-- Phoneme (IPA pronunciation) -->
<phoneme alphabet="ipa" ph="təˈmeɪtoʊ">tomato</phoneme>
```

**Complete Example:**
```xml
<speak>
  <p>
    <s>Welcome to <emphasis level="strong">MediaGenAI</emphasis>, the future of content creation.</s>
    <break time="500ms"/>
    <s>Our platform combines <prosody rate="slow">cutting-edge AI</prosody> with intuitive design.</s>
  </p>
  
  <break time="800ms"/>
  
  <p>
    <s>Join over <say-as interpret-as="cardinal">10000</say-as> creators worldwide.</s>
    <s><prosody volume="loud">Start your free trial today!</prosody></s>
  </p>
</speak>
```

### 13.2 Persona Preset Examples

**Warm Guide:**
```
Adopt a friendly, reassuring tone like a mentor guiding someone through a new experience.
Use moderate pacing with gentle emphasis on key concepts. Include occasional pauses
for reflection. Speak as if you're having a one-on-one conversation.
```

**Energetic Launch:**
```
Deliver with high energy and excitement, like an announcer at a product reveal event.
Use dynamic prosody with faster pacing and strong emphasis on benefits. Build momentum
toward a motivating call-to-action. Make it feel like something big is happening.
```

**News Brief:**
```
Adopt a confident, authoritative news anchor cadence. Use crisp, clear pronunciation
with measured pacing. Emphasize key facts and figures. Maintain professional neutrality
while ensuring information is engaging and easy to follow.
```

**Storyteller:**
```
Craft a narrative flow with deliberate pauses for dramatic effect. Vary pacing to
match the emotional arc—slow and contemplative for setup, building tension in the
middle, resolving with a satisfying conclusion. Use vivid sensory language.
```

### 13.3 Troubleshooting Checklist

**Before Reporting Issues:**

- [ ] Health check endpoint returns 200 OK
- [ ] AWS credentials are valid (`aws sts get-caller-identity`)
- [ ] Bedrock access confirmed (`aws bedrock list-foundation-models`)
- [ ] Polly access confirmed (`aws polly describe-voices`)
- [ ] Backend logs reviewed (`tail -f synthetic-voiceover.log`)
- [ ] Frontend console checked for errors (F12 DevTools)
- [ ] Network tab shows requests completing
- [ ] Environment variables are set correctly
- [ ] Dependencies are up to date (`pip list`, `npm list`)
- [ ] Service is running on correct port (5003)
- [ ] CORS is enabled (check response headers)
- [ ] Request/response payloads are valid JSON
- [ ] Timeout values are sufficient (90s+ for LLM)

---

## 14. Conclusion

The Synthetic Voiceover Service represents a sophisticated integration of LLM-based script generation and neural text-to-speech synthesis. This document has covered:

✅ **Architecture**: Dual-engine pipeline with Flask orchestration  
✅ **Backend**: SSML generation with 7-attempt retry strategy and echo detection  
✅ **Frontend**: Step wizard with speech recognition and voice catalog  
✅ **AWS Integration**: Bedrock (Llama3-70B) and Polly (neural voices)  
✅ **Error Handling**: Multi-stage fallback for robust TTS synthesis  
✅ **Configuration**: Environment-driven setup for flexibility  
✅ **Deployment**: Docker, systemd, and process management scripts  
✅ **Troubleshooting**: Common issues and debugging techniques  
✅ **Optimization**: Performance tuning and cost reduction strategies

**Key Takeaways:**

1. **Resilient Design**: Multiple fallback strategies ensure voiceover generation succeeds even when optimal paths fail
2. **User Experience**: Three input modes (GenAI, Paste, Record) accommodate different workflows
3. **Quality Control**: Echo detection and retry escalation prevent low-quality outputs
4. **Production-Ready**: Comprehensive error handling, logging, and monitoring capabilities
5. **Cost-Effective**: Configurable retry limits and model selection for budget control

**Next Steps:**

- Explore other microservices: Movie Script Creation, Scene Summarization
- Implement rate limiting and caching for production scale
- Add user authentication and project management
- Integrate with other MediaGenAI services for complete workflows

---

**Document Metadata:**
- **Service**: Synthetic Voiceover Service (Port 5003)
- **Version**: 1.0
- **Last Updated**: October 21, 2025
- **Author**: MediaGenAI Platform Team
- **Related Documents**: 
  - AI_SUBTITLE_SERVICE_REFERENCE.md
  - IMAGE_CREATION_SERVICE_REFERENCE.md
  - SERVICES_README.md

---

**End of Synthetic Voiceover Service Reference Documentation**

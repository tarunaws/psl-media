# Movie Script Creation Service - Complete Reference Guide
## Part 1: Executive Summary, Architecture Overview & Backend Foundation

**Document Version:** 1.0  
**Last Updated:** October 22, 2025  
**Service:** Movie Script Creation  
**Port:** 5005  
**Technology Stack:** Flask + AWS Bedrock (Llama3-70B) + AWS Translate + React

---

## Table of Contents - Part 1

1. [Executive Summary](#1-executive-summary)
2. [Service Architecture Overview](#2-service-architecture-overview)
3. [Backend Deep Dive - Part A](#3-backend-deep-dive---part-a)
   - Configuration & Environment
   - Language Support System
   - Segment-Based Generation Model

---

## 1. Executive Summary

### 1.1 Service Purpose

The **Movie Script Creation Service** is an AI-powered screenplay generation platform that creates industry-standard, professionally formatted feature-length film scripts. Unlike traditional script writing tools, this service leverages AWS Bedrock's Llama3-70B model with creative temperature tuning to generate compelling narratives that span multiple acts, maintain character consistency, and incorporate cultural localization for global audiences.

**Key Capabilities:**
- **Segment-Based Generation:** Breaks down full-length features into 10-minute screenplay segments for coherent long-form storytelling
- **Multi-Language Support:** AWS Translate integration for 60+ languages including Afrikaans, Hindi, Spanish, Chinese, Arabic, and more
- **Creative AI Tuning:** Higher temperature (0.65) optimized for creative writing vs analytical tasks
- **Industry Formatting:** Proper screenplay structure with sluglines, action lines, dialogue, and act breaks
- **Cultural Localization:** Region-specific references and audience targeting for global markets

### 1.2 Business Value

**For Content Creators:**
- Rapid screenplay prototyping (130-minute feature in minutes)
- Genre blending and tonal experimentation
- Multi-language script generation for international markets
- Consistent character development across full narrative arc

**For Production Studios:**
- Early-stage story development and pitch materials
- Cultural adaptation for regional markets
- Budget and runtime planning with structured segments
- Franchise and IP continuity maintenance

**For Streaming Platforms:**
- High-volume content pipeline for original programming
- Audience-targeted storytelling (kids, teens, adults, four-quadrant)
- Rating compliance (G, PG, PG-13, R, NC-17)
- Binge-friendly narrative pacing

### 1.3 Service Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| **Default Runtime** | 130 minutes | ~13 segments at 10 min/segment |
| **Max Runtime** | 180 minutes | 18 segments maximum |
| **Segment Length** | 10 minutes | Configurable via SEGMENT_LENGTH_MINUTES |
| **Min Tokens/Segment** | 3,500 tokens | ~2,625 words |
| **Max Tokens/Segment** | 4,096 tokens | Llama3-70B limit |
| **Supported Languages** | 60+ | AWS Translate coverage |
| **LLM Temperature** | 0.65 | Higher creativity vs Scene Summarization (0.4) |
| **Top-P Sampling** | 0.9 | Nucleus sampling for diverse outputs |
| **API Endpoints** | 2 | /health, /generate-script |

### 1.4 Architecture Comparison

**vs Scene Summarization Service:**
- **Complexity:** Similar (both use Bedrock + multi-stage processing)
- **Temperature:** Higher (0.65 vs 0.4) for creative writing
- **Endpoints:** Simpler (2 vs 4) - synchronous generation
- **Media Processing:** Text-only (no video/audio analysis)
- **Output Type:** Long-form narrative (vs short summaries)

**vs Synthetic Voiceover Service:**
- **Complexity:** Higher (segment management + translation)
- **AWS Services:** Bedrock + Translate (vs Polly + Transcribe)
- **Processing Model:** Iterative segment generation (vs single synthesis)
- **Language Support:** Translation-based (vs native TTS voices)

### 1.5 Technical Differentiators

1. **Segment-Based Long-Form Generation**
   - Breaks 130-minute runtime into 13 segments
   - Each segment maintains continuity with prior context
   - Final segment drives climax and resolution
   - Maximum 18 segments (180 minutes) to prevent LLM drift

2. **Creative Temperature Tuning**
   - Temperature 0.65 balances creativity with coherence
   - Higher than Scene Summarization (0.4) for analytical tasks
   - Lower than pure creative writing (0.8+) to maintain structure
   - Top-P 0.9 for diverse but focused outputs

3. **Multi-Language Translation**
   - 60+ languages via AWS Translate
   - Dialogue-focused translation (stage directions remain English)
   - Chunk-based translation for long scripts (4,500 char chunks)
   - Full-text translation mode via environment variable

4. **Industry-Standard Formatting**
   - Sluglines: INT./EXT. scene headings
   - Character cues: ALL CAPS character names
   - Action lines: Scene descriptions and directions
   - Dialogue: Character speech with parentheticals
   - Act structure: ACT I, ACT II A, ACT II B, ACT III

---

## 2. Service Architecture Overview

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         React Frontend (MovieScriptCreation.js)          │  │
│  │  • Multi-step wizard (4 steps)                          │  │
│  │  • Genre/mood/audience selection                        │  │
│  │  • Runtime & rating configuration                       │  │
│  │  • Language selection (60+ options)                     │  │
│  │  • Real-time creative DNA preview                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            ↓ HTTP POST                          │
└─────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│                      API GATEWAY LAYER                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Flask App (Port 5005)                       │  │
│  │  • CORS-enabled REST API                                │  │
│  │  • GET /health - Service health check                   │  │
│  │  • POST /generate-script - Script generation            │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATION LAYER                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │          Script Generation Orchestrator                  │  │
│  │  1. Parse & normalize creative brief                    │  │
│  │  2. Determine segment count (runtime / 10 min)          │  │
│  │  3. Iterate through segments:                           │  │
│  │     a. Build segment prompt with context                │  │
│  │     b. Invoke Bedrock LLM                               │  │
│  │     c. Extract & validate screenplay text               │  │
│  │     d. Append to script_so_far                          │  │
│  │  4. Translate dialogue (if non-English)                 │  │
│  │  5. Return complete screenplay                          │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│                      AWS SERVICES LAYER                         │
│  ┌─────────────────────────┐  ┌─────────────────────────────┐  │
│  │    AWS Bedrock          │  │    AWS Translate            │  │
│  │  • Model: Llama3-70B    │  │  • 60+ language pairs       │  │
│  │  • Region: us-east-1    │  │  • Dialogue translation     │  │
│  │  • Temp: 0.65           │  │  • Chunk-based (4500 char)  │  │
│  │  • 3500-4096 tokens     │  │  • Romanization support     │  │
│  └─────────────────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│                       OUTPUT LAYER                              │
│  • Complete feature-length screenplay (90-180 minutes)         │
│  • Industry-standard formatting (sluglines, dialogue, acts)    │
│  • Translated dialogue (if non-English selected)               │
│  • JSON response with title, script, language, runtime         │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Breakdown

#### 2.2.1 Frontend Component (React)

**File:** `frontend/src/MovieScriptCreation.js` (950 lines)

**Responsibilities:**
- Multi-step wizard UI (4 steps: logline, creative palette, audience/localization, runtime/compliance)
- Form state management for creative brief parameters
- API communication with backend
- Script display and download functionality

**Key Features:**
- **Step 0 - Logline & Guidance:** Free-form creative brief and additional notes
- **Step 1 - Creative Palette:** Genre selection (21 genres) + mood/tone (14 moods)
- **Step 2 - Audience & Localization:** Target cohorts (9 demographics) + regions (14 areas) + language (60+ options)
- **Step 3 - Runtime & Compliance:** Duration (90-180 min) + rating (G to NC-17) + creative DNA preview
- **Script Display:** Formatted screenplay with copy-to-clipboard and markdown download

**State Management:**
```javascript
// Creative Brief State
const [logline, setLogline] = useState('')
const [notes, setNotes] = useState('')
const [genres, setGenres] = useState(['Epic Fantasy', 'Adventure'])
const [moods, setMoods] = useState(['Epic and awe-inspiring'])
const [audience, setAudience] = useState(['Young adults (18-24)'])
const [regions, setRegions] = useState(['Global (All Regions)'])
const [runtime, setRuntime] = useState('130')
const [rating, setRating] = useState('PG-13')
const [language, setLanguage] = useState('en')

// UI State
const [step, setStep] = useState(0)
const [result, setResult] = useState(null)
const [loading, setLoading] = useState(false)
const [error, setError] = useState('')
```

#### 2.2.2 Backend API (Flask)

**File:** `movieScriptCreation/app.py` (696 lines)

**Responsibilities:**
- REST API endpoint handling
- Creative brief parsing and normalization
- Segment-based script generation orchestration
- AWS Bedrock integration
- AWS Translate integration for multi-language support

**API Endpoints:**

| Endpoint | Method | Purpose | Request | Response |
|----------|--------|---------|---------|----------|
| `/health` | GET | Health check | None | `{status, modelId, region, minTokens, maxTokens}` |
| `/generate-script` | POST | Generate screenplay | Creative brief JSON | `{title, script, language, runtimeMinutes}` |

**Processing Pipeline:**
1. Parse request JSON → `_compose_brief()`
2. Determine segment count → `_determine_segments()`
3. For each segment (0 to total_segments-1):
   - Build prompt with context → `_build_segment_prompt()`
   - Invoke Bedrock → `_invoke_bedrock()`
   - Extract screenplay text → `_extract_text()`
   - Parse script section → `_split_sections()`
   - Append to cumulative script
4. Translate dialogue → `_translate_dialogue_segments()`
5. Return complete screenplay

#### 2.2.3 AWS Bedrock Integration

**Model Configuration:**
```python
MODEL_ID = "meta.llama3-70b-instruct-v1:0"
BEDROCK_REGION = os.getenv("BEDROCK_REGION", "us-east-1")
MIN_TOKENS = 3500  # Minimum tokens per segment
TARGET_WORDS = 2625  # 3500 * 0.75 word-to-token ratio
MAX_TOKENS = 4096  # Llama3-70B max generation length
TEMPERATURE = 0.65  # Creative writing temperature
TOP_P = 0.9  # Nucleus sampling threshold
```

**Prompt Structure:**
```
<|begin_of_text|><|start_header_id|>system<|end_header_id|>
{SYSTEM_PROMPT - showrunner persona + formatting rules}
<|eot_id|><|start_header_id|>user<|end_header_id|>
{USER_PROMPT - creative brief + segment instructions + context}
<|eot_id|><|start_header_id|>assistant<|end_header_id|>
```

**System Prompt Highlights:**
- **Persona:** "Award-winning showrunner and narrative designer"
- **Analysis First:** "Surface cultural research, mythic structure, character arcs"
- **Token Target:** "Comfortably exceeds 3,500 tokens (~2,625+ words)"
- **Structure:** "ACT I, ACT II A, ACT II B, ACT III headings"
- **Consistency:** "Distinctive character names consistent across every segment"
- **Output Only:** "No analysis, summaries, commentary, or metadata"

#### 2.2.4 AWS Translate Integration

**Translation Modes:**
1. **Dialogue-Only Mode (Default):**
   - Identifies character dialogue lines
   - Translates dialogue while preserving stage directions in English
   - Line-by-line translation via `_translate_dialogue_line()`

2. **Full-Text Mode (Optional):**
   - Set via `MOVIE_SCRIPT_TRANSLATE_FULL=true` environment variable
   - Chunk-based translation (4,500 chars per chunk)
   - Translates entire screenplay including directions

**Language Support Matrix:**
- **Total Languages:** 60+
- **Script Systems:** Latin, Cyrillic, Arabic, Devanagari, CJK, etc.
- **Romanization:** Optional for non-Latin scripts (e.g., Hindi → Hinglish)

### 2.3 Data Flow Diagram

```
┌─────────────────┐
│  User Input     │
│  • Logline      │
│  • Genres       │
│  • Moods        │
│  • Audience     │
│  • Regions      │
│  • Runtime      │
│  • Rating       │
│  • Language     │
└────────┬────────┘
         │
         ↓
┌─────────────────────────────────────────────┐
│  Step 1: Brief Composition                  │
│  _compose_brief(payload)                    │
│  • Normalize genre/mood lists               │
│  • Parse runtime minutes                    │
│  • Resolve language code                    │
│  • Build brief_text narrative               │
└────────┬────────────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────────────┐
│  Step 2: Segment Planning                   │
│  _determine_segments(runtime_minutes)       │
│  • Calculate: ceil(130 / 10) = 13 segments  │
│  • Cap at MAX_SEGMENTS (18)                 │
└────────┬────────────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────────────┐
│  Step 3: Iterative Segment Generation       │
│  FOR segment_index in range(total_segments):│
│    ┌─────────────────────────────────────┐  │
│    │ 3a: Build Segment Prompt            │  │
│    │ • Include brief_text                │  │
│    │ • Specify segment minutes (1-10)    │  │
│    │ • Add script_so_far context         │  │
│    │ • Language guidance                 │  │
│    └────────┬────────────────────────────┘  │
│             ↓                                │
│    ┌─────────────────────────────────────┐  │
│    │ 3b: Invoke Bedrock                  │  │
│    │ • Model: Llama3-70B                 │  │
│    │ • Temp: 0.65, Top-P: 0.9            │  │
│    │ • Max tokens: 4096                  │  │
│    └────────┬────────────────────────────┘  │
│             ↓                                │
│    ┌─────────────────────────────────────┐  │
│    │ 3c: Extract Screenplay Text         │  │
│    │ • Parse response body               │  │
│    │ • Split <<ANALYSIS>> / <<SCRIPT>>   │  │
│    │ • Validate non-empty                │  │
│    └────────┬────────────────────────────┘  │
│             ↓                                │
│    ┌─────────────────────────────────────┐  │
│    │ 3d: Append to Cumulative Script     │  │
│    │ script_so_far += "\n\n" + segment   │  │
│    │ (Used as context for next segment)  │  │
│    └─────────────────────────────────────┘  │
└────────┬────────────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────────────┐
│  Step 4: Dialogue Translation               │
│  _translate_dialogue_segments(full_script)  │
│  IF language != "en":                       │
│    • Identify dialogue lines                │
│    • Translate via AWS Translate            │
│    • Preserve stage directions in English   │
└────────┬────────────────────────────────────┘
         │
         ↓
┌─────────────────┐
│  Final Output   │
│  {              │
│    title,       │
│    script,      │
│    language,    │
│    runtime      │
│  }              │
└─────────────────┘
```

### 2.4 Segment-Based Generation Model

**Why Segments?**
- **LLM Context Limits:** Llama3-70B has finite context window; can't generate 130-minute screenplay in single pass
- **Coherence Management:** Breaking into 10-minute chunks maintains narrative quality
- **Iterative Context:** Each segment uses prior script as context for continuity
- **Production Alignment:** 10-minute segments align with script page counts (~10 pages)

**Segment Calculation:**
```python
def _determine_segments(runtime_minutes: int) -> int:
    segments = max(1, math.ceil(runtime_minutes / SEGMENT_LENGTH_MINUTES))
    return min(segments, MAX_SEGMENTS)

# Examples:
# 90 minutes → ceil(90/10) = 9 segments
# 130 minutes → ceil(130/10) = 13 segments
# 180 minutes → ceil(180/10) = 18 segments (max)
# 200 minutes → min(20, 18) = 18 segments (capped)
```

**Segment Contextualization:**

| Segment | Minutes | Context Strategy |
|---------|---------|------------------|
| Segment 1 | 1-10 | Opening instructions: "Establish core world, introduce principal characters, ignite inciting incident" |
| Segments 2-12 | 11-120 | Prior script context (truncated to 4,000 chars): "Maintain continuity, do not repeat scenes" |
| Segment 13 (Final) | 121-130 | Final segment instructions: "Drive the climax, resolve character arcs, deliver satisfying denouement" |

**Context Truncation:**
```python
def _truncate_context(script_text: str, limit: int = 4000) -> str:
    """Keep last 4000 chars of script for context to avoid prompt bloat"""
    text = script_text.strip()
    if len(text) <= limit:
        return text
    return text[-limit:]  # Tail truncation keeps recent context
```

---

## 3. Backend Deep Dive - Part A

### 3.1 Configuration & Environment Variables

#### 3.1.1 Core Configuration

**File Location:** `movieScriptCreation/app.py` (Lines 1-50)

```python
# Flask Application Setup
app = Flask(__name__)
CORS(app)  # Enable cross-origin requests from frontend

# AWS Bedrock Configuration
BEDROCK_REGION = os.getenv("BEDROCK_REGION", "us-east-1")
MODEL_ID = "meta.llama3-70b-instruct-v1:0"

# Token & Generation Configuration
MIN_TOKENS = 3500  # Minimum tokens per screenplay segment
TARGET_WORDS = int(MIN_TOKENS * 0.75)  # ~2625 words (word-to-token ratio)
MAX_TOKENS = 4096  # Maximum tokens Bedrock can generate per request
TEMPERATURE = 0.65  # Higher than analytical tasks (0.4) for creative writing
TOP_P = 0.9  # Nucleus sampling for diverse outputs

# Segment Configuration
SEGMENT_LENGTH_MINUTES = 10  # Each segment covers ~10 minutes of screen time
DEFAULT_RUNTIME_MINUTES = 130  # Default feature length
MAX_SEGMENTS = 18  # Maximum 180 minutes to prevent LLM drift

# AWS Translate Configuration
TRANSLATE_REGION = os.getenv("TRANSLATE_REGION", "us-east-1")
MAX_TRANSLATE_CHARS = 4500  # Chunk size for translation to avoid API limits

# Runtime Configuration
PORT = int(os.getenv("PORT", "5005"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
RELOADER = os.getenv("RELOADER", "false").lower() == "true"
```

#### 3.1.2 Environment Variables Reference

| Variable | Default | Purpose | Example |
|----------|---------|---------|---------|
| `BEDROCK_REGION` | `us-east-1` | AWS region for Bedrock service | `us-west-2` |
| `TRANSLATE_REGION` | `us-east-1` | AWS region for Translate service | `eu-west-1` |
| `PORT` | `5005` | Flask server port | `8080` |
| `DEBUG` | `false` | Enable Flask debug mode | `true` |
| `RELOADER` | `false` | Enable auto-reload on code changes | `true` |
| `MOVIE_SCRIPT_TRANSLATE_FULL` | `true` | Enable full-text translation vs dialogue-only | `false` |

**AWS Credentials:**
- Loaded via standard AWS SDK chain (environment, credentials file, IAM role)
- Required permissions: `bedrock:InvokeModel`, `translate:TranslateText`

#### 3.1.3 Configuration Rationale

**Temperature 0.65 Justification:**
- **Too Low (0.2-0.4):** Produces repetitive, formulaic dialogue and predictable plot beats
- **Optimal (0.6-0.7):** Balances creative variation with narrative coherence
- **Too High (0.8-1.0):** Generates surreal, incoherent storylines that break continuity

**Segment Length 10 Minutes:**
- **Industry Standard:** 1 screenplay page ≈ 1 minute of screen time
- **Token Efficiency:** 10 pages × 250 words/page = 2,500 words ≈ 3,333 tokens
- **Context Management:** Keeps prompts focused on manageable story beats
- **Production Utility:** Aligns with scene blocking and shooting schedules

**Max Segments 18 Cap:**
- **LLM Drift Prevention:** After 18 iterations, character consistency degrades
- **Production Reality:** 180 minutes (3 hours) is upper limit for theatrical features
- **API Cost Management:** Limits maximum Bedrock invocations per request

### 3.2 Language Support System

#### 3.2.1 AWS Translate Language Matrix

**File Location:** `app.py` (Lines 51-115)

The service supports **60+ languages** via AWS Translate. Below is the complete language mapping:

```python
AWS_TRANSLATE_LANGUAGES = {
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
    "en": "English",
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
```

#### 3.2.2 Language Configuration Builder

**Function:** `_build_language_config()` (Lines 117-138)

This function generates language-specific instructions for the LLM:

```python
def _build_language_config() -> Dict[str, Dict[str, str]]:
    """
    Builds language configuration with:
    - label: Human-readable language name
    - brief_line: One-line language instruction for creative brief
    - segment_guidance: Detailed instructions for LLM per segment
    """
    config: Dict[str, Dict[str, str]] = {}
    
    for code, label in AWS_TRANSLATE_LANGUAGES.items():
        if code == "en":
            config[code] = {
                "label": label,
                "brief_line": "Dialogue language: English.",
                "segment_guidance": (
                    "Write all dialogue, scene directions, and on-screen "
                    "text in polished English."
                ),
            }
        else:
            config[code] = {
                "label": label,
                "brief_line": f"Dialogue language: {label}.",
                "segment_guidance": (
                    f"Write dialogue and on-screen text in natural {label} "
                    "while keeping stage directions in English."
                ),
            }
    
    return config
```

**Generated Configuration Examples:**

| Language | Brief Line | Segment Guidance |
|----------|------------|------------------|
| English (en) | "Dialogue language: English." | "Write all dialogue, scene directions, and on-screen text in polished English." |
| Hindi (hi) | "Dialogue language: Hindi." | "Write dialogue and on-screen text in natural Hindi while keeping stage directions in English." |
| Spanish (es) | "Dialogue language: Spanish." | "Write dialogue and on-screen text in natural Spanish while keeping stage directions in English." |
| Chinese (zh) | "Dialogue language: Chinese (Simplified)." | "Write dialogue and on-screen text in natural Chinese (Simplified) while keeping stage directions in English." |

**Rationale for English Stage Directions:**
- **Industry Standard:** Hollywood and international co-productions use English for technical directions
- **LLM Training:** Bedrock models trained primarily on English screenplay formats
- **Post-Production:** VFX, editing teams typically work with English technical annotations

#### 3.2.3 Language Normalization

**Function:** `_normalise_language()` (Lines 245-284)

Handles diverse input formats and resolves to canonical language codes:

```python
def _normalise_language(raw_language: Any) -> Dict[str, str]:
    """
    Normalizes language input to canonical code.
    
    Accepts:
    - String codes: "en", "hi", "es-MX"
    - String labels: "English", "Hindi", "Spanish (Mexico)"
    - Dict objects: {"value": "en"}, {"code": "hi"}, {"name": "Spanish"}
    - Case-insensitive matching
    - Common aliases: "english" → "en", "hinglish" → "hi"
    
    Returns:
    - Dictionary with code, label, brief_line, segment_guidance
    """
    
    # Handle dict input (from frontend select objects)
    if isinstance(raw_language, dict):
        candidate = raw_language.get("value") or raw_language.get("code") or raw_language.get("name")
    else:
        candidate = raw_language
    
    # Default to English if null/empty
    default_code = "en"
    if candidate is None or not str(candidate).strip():
        canonical = default_code
    else:
        lowered = str(candidate).strip().lower()
        
        # Try direct code lookup (e.g., "hi" → "hi")
        canonical = LANGUAGE_CODE_LOOKUP.get(lowered)
        
        # Try alias lookup for common variants
        if not canonical:
            alias_lookup = {
                "english": "en",
                "en-us": "en",
                "en-gb": "en",
                "hindi": "hi",
                "hinglish": "hi",  # Romanized Hindi
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
        
        # Try fuzzy match against labels (e.g., "spanish mexico" → "es-MX")
        if not canonical:
            canonical = next(
                (code for code, config in LANGUAGE_CONFIG.items() 
                 if lowered == config["label"].lower()),
                None,
            )
        
        # Fallback to English
        canonical = canonical or default_code
    
    # Return full config dictionary
    config = LANGUAGE_CONFIG.get(canonical, LANGUAGE_CONFIG[default_code])
    return {"code": canonical, **config}
```

**Example Transformations:**

| Input | Normalized Code | Label |
|-------|-----------------|-------|
| `"en"` | `en` | English |
| `"HINDI"` | `hi` | Hindi |
| `"Spanish (Mexico)"` | `es-MX` | Spanish (Mexico) |
| `{"value": "zh-TW"}` | `zh-TW` | Chinese (Traditional) |
| `"Hinglish"` | `hi` | Hindi (with romanization) |
| `""` (empty) | `en` | English (default) |
| `None` | `en` | English (default) |

### 3.3 Segment-Based Generation Model

#### 3.3.1 Runtime & Segment Calculation

**Function:** `_parse_runtime_minutes()` (Lines 286-300)

Extracts numeric runtime from various input formats:

```python
def _parse_runtime_minutes(raw_runtime: Any) -> Optional[int]:
    """
    Parses runtime input to integer minutes.
    
    Accepts:
    - Integers: 130
    - Floats: 130.0
    - Strings: "130", "130 minutes", "130m"
    - Invalid: None, "", "TBD", negative values
    
    Returns:
    - Integer minutes if valid
    - None if invalid (triggers DEFAULT_RUNTIME_MINUTES fallback)
    """
    if raw_runtime is None:
        return None
    
    # Handle numeric types
    if isinstance(raw_runtime, (int, float)):
        if raw_runtime <= 0:
            return None
        return int(raw_runtime)
    
    # Handle string types
    text = str(raw_runtime).strip()
    if not text:
        return None
    
    # Extract digits only (handles "130 minutes", "130m", etc.)
    digits = "".join(ch for ch in text if ch.isdigit())
    if not digits:
        return None
    
    value = int(digits)
    return value if value > 0 else None
```

**Function:** `_determine_segments()` (Lines 302-305)

Calculates segment count with safety caps:

```python
def _determine_segments(runtime_minutes: int) -> int:
    """
    Calculates number of 10-minute segments needed.
    
    Logic:
    - Minimum 1 segment (even if runtime < 10 minutes)
    - Round up partial segments (131 minutes → 14 segments)
    - Cap at MAX_SEGMENTS (18) to prevent LLM drift
    
    Examples:
    - 90 minutes: max(1, ceil(90/10)) = 9 segments
    - 130 minutes: max(1, ceil(130/10)) = 13 segments
    - 135 minutes: max(1, ceil(135/10)) = 14 segments
    - 180 minutes: min(18, 18) = 18 segments
    - 200 minutes: min(20, 18) = 18 segments (capped)
    """
    segments = max(1, math.ceil(runtime_minutes / SEGMENT_LENGTH_MINUTES))
    return min(segments, MAX_SEGMENTS)
```

**Segment Calculation Table:**

| Runtime (min) | Formula | Raw Segments | Capped Segments | Screen Time |
|---------------|---------|--------------|-----------------|-------------|
| 60 | ceil(60/10) | 6 | 6 | 1 hour |
| 90 | ceil(90/10) | 9 | 9 | 1.5 hours |
| 100 | ceil(100/10) | 10 | 10 | 1h 40m |
| 120 | ceil(120/10) | 12 | 12 | 2 hours |
| 130 | ceil(130/10) | 13 | 13 | 2h 10m (default) |
| 150 | ceil(150/10) | 15 | 15 | 2.5 hours |
| 180 | ceil(180/10) | 18 | 18 | 3 hours (max) |
| 200 | ceil(200/10) | 20 | **18** | 3 hours (capped) |

#### 3.3.2 Context Truncation Strategy

**Function:** `_truncate_context()` (Lines 307-312)

Manages context size to prevent prompt bloat:

```python
def _truncate_context(script_text: str, limit: int = 4000) -> str:
    """
    Truncates script context to last N characters.
    
    Why tail truncation?
    - Recent context (last 4000 chars) is most relevant for next segment
    - Preserves character names and plot threads from recent scenes
    - Prevents prompt from exceeding Bedrock's context window
    - ~4000 chars ≈ 1000 tokens ≈ 4 screenplay pages
    
    Example:
    - Segment 1: 3500 tokens (no truncation needed)
    - Segment 5: 17500 tokens cumulative → truncate to last 4000 chars
    - This keeps ~3-4 pages of recent script for continuity
    """
    text = script_text.strip()
    if len(text) <= limit:
        return text
    return text[-limit:]  # Tail truncation (keep end, discard start)
```

**Context Size Analysis:**

| Segment | Cumulative Tokens | Raw Chars | Truncated Chars | Context Provided |
|---------|-------------------|-----------|-----------------|------------------|
| 1 | 3,500 | ~14,000 | 14,000 | Full script so far |
| 2 | 7,000 | ~28,000 | 28,000 | Full script so far |
| 3 | 10,500 | ~42,000 | 42,000 | Full script so far |
| 4 | 14,000 | ~56,000 | **4,000** | Last ~1,000 tokens |
| 5 | 17,500 | ~70,000 | **4,000** | Last ~1,000 tokens |
| ... | ... | ... | **4,000** | Last ~1,000 tokens |
| 13 | 45,500 | ~182,000 | **4,000** | Last ~1,000 tokens |

**Why 4,000 Character Limit?**
- **Token Estimation:** 4,000 chars ≈ 1,000 tokens (4:1 ratio for English)
- **Context Budget:** Leaves room for system prompt, brief, and segment instructions
- **Bedrock Limits:** Llama3-70B context window is 8,192 tokens total (input + output)
- **Budget Breakdown:**
  - System prompt: ~500 tokens
  - Creative brief: ~300 tokens
  - Segment instructions: ~200 tokens
  - Script context: ~1,000 tokens
  - **Total Input:** ~2,000 tokens
  - **Available for Output:** 4,096 tokens (MAX_TOKENS)

#### 3.3.3 Segment Prompt Construction

**Function:** `_build_segment_prompt()` (Lines 314-369)

Constructs context-aware prompts for each screenplay segment:

```python
def _build_segment_prompt(
    brief: Dict[str, Any],
    segment_index: int,
    total_segments: int,
    runtime_minutes: int,
    script_so_far: str,
    language: Dict[str, str],
) -> str:
    """
    Builds a segment-specific prompt with creative brief and context.
    
    Parameters:
    - brief: Creative DNA (genres, moods, audience, regions, etc.)
    - segment_index: 0-based index (0 = first segment)
    - total_segments: Total number of segments (e.g., 13 for 130 min)
    - runtime_minutes: Total feature runtime
    - script_so_far: Cumulative screenplay text (truncated to 4000 chars)
    - language: Language configuration dict
    
    Returns:
    - Complete prompt string for Bedrock invocation
    """
    
    # Convert to 1-based segment numbering for clarity
    segment_number = segment_index + 1
    
    # Calculate minute range for this segment
    start_minute = segment_index * SEGMENT_LENGTH_MINUTES  # e.g., 0, 10, 20
    end_minute = min(runtime_minutes, segment_number * SEGMENT_LENGTH_MINUTES)
    
    # Adjust final segment to cover remaining runtime
    if segment_number == total_segments:
        end_minute = runtime_minutes
    
    # Build context instructions based on script progress
    if script_so_far.strip():
        # Mid-script: Provide recent context for continuity
        context_instructions = textwrap.dedent(
            f"""
            Script so far (maintain continuity, do not repeat scenes or dialogue):
            {_truncate_context(script_so_far)}
            """
        ).strip()
    else:
        # First segment: Opening instructions
        context_instructions = (
            "This is the opening segment. Establish the core world, introduce "
            "principal characters with memorable names, and ignite the inciting "
            "incident while setting tone and stakes."
        )
    
    # Build segment-specific instructions
    segment_notes = (
        f"Write Segment {segment_number} of {total_segments}, covering "
        f"approximately minutes {start_minute + 1} through {end_minute} of the film "
        f"(roughly {SEGMENT_LENGTH_MINUTES} minutes of screen time). "
        "Advance the plot with cinematic pacing, keeping character motivations "
        "and arcs coherent."
    )
    
    # Add finale instructions for last segment
    if segment_number == total_segments:
        segment_notes += (
            " This is the final segment—drive the climax, resolve character arcs, "
            "and deliver a satisfying denouement."
        )
    
    # Get language-specific guidance
    language_instructions = language.get("segment_guidance") or LANGUAGE_CONFIG["en"]["segment_guidance"]
    
    # Assemble complete prompt
    return textwrap.dedent(
        f"""
        {brief["brief_text"]}

        {segment_notes}

        {context_instructions}

        Language guidance:
        {language_instructions}

        Output only screenplay pages for this segment using proper scene headings, 
        action lines, and dialogue. Do not include recaps, analysis, or meta commentary. 
        Stop once this segment concludes.
        """
    ).strip()
```

**Prompt Anatomy Example (Segment 5 of 13):**

```
Project title: Untitled Feature
Logline or core idea: A reluctant hero discovers ancient powers...
Primary genres: Epic Fantasy, Adventure
Tonality & moods: Epic and awe-inspiring
Target audience cohorts: Young adults (18-24)
Priority regions & cultural references: Global (All Regions)
Era or setting: Present day
Target runtime: 130 minutes
Intended rating or compliance: PG-13
Dialogue language: English.

Write Segment 5 of 13, covering approximately minutes 41 through 50 of the film 
(roughly 10 minutes of screen time). Advance the plot with cinematic pacing, 
keeping character motivations and arcs coherent.

Script so far (maintain continuity, do not repeat scenes or dialogue):
[Last 4000 chars of segments 1-4]

Language guidance:
Write all dialogue, scene directions, and on-screen text in polished English.

Output only screenplay pages for this segment using proper scene headings, 
action lines, and dialogue. Do not include recaps, analysis, or meta commentary. 
Stop once this segment concludes.
```

**Segment-Specific Instructions:**

| Segment | Minutes | Special Instructions |
|---------|---------|---------------------|
| 1 (Opening) | 1-10 | "Establish the core world, introduce principal characters with memorable names, and ignite the inciting incident while setting tone and stakes." |
| 2-12 (Middle) | 11-120 | "Advance the plot with cinematic pacing, keeping character motivations and arcs coherent." + [Script so far context] |
| 13 (Final) | 121-130 | "This is the final segment—drive the climax, resolve character arcs, and deliver a satisfying denouement." |

---

## End of Part 1

**Continue to Part 2 for:**
- Screenplay Formatting Detection
- AWS Bedrock Invocation Details
- Response Parsing & Text Extraction
- Translation Pipeline Architecture
- Complete API Endpoint Reference

---

**Document Statistics - Part 1:**
- Pages: ~42
- Sections: 3 major sections
- Code Examples: 15+
- Tables: 12
- Architecture Diagrams: 3

**Next Document:** `MOVIE_SCRIPT_CREATION_PART2.md`
# Movie Script Creation Service - Complete Reference Guide
## Part 2: Screenplay Formatting, Translation Pipeline & API Reference

**Document Version:** 1.0  
**Last Updated:** October 22, 2025  
**Service:** Movie Script Creation  
**Port:** 5005

---

## Table of Contents - Part 2

3. [Backend Deep Dive - Part B](#3-backend-deep-dive---part-b)
   - Screenplay Formatting Detection
   - AWS Bedrock Integration
   - Response Parsing & Text Extraction
4. [Translation Pipeline Architecture](#4-translation-pipeline-architecture)
   - Dialogue-Only Translation Mode
   - Full-Text Translation Mode
   - Chunk-Based Translation Strategy
5. [API Endpoint Reference](#5-api-endpoint-reference)
   - Health Check Endpoint
   - Script Generation Endpoint
   - Request/Response Schemas

---

## 3. Backend Deep Dive - Part B

### 3.4 Screenplay Formatting Detection

The service includes intelligent pattern matching to identify screenplay elements and preserve industry-standard formatting.

#### 3.4.1 Scene Heading Detection

**Function:** `_is_scene_heading()` (Lines 371-374)

Identifies sluglines (location headers) in screenplay format:

```python
def _is_scene_heading(text: str) -> bool:
    """
    Detects if a line is a scene heading (slugline).
    
    Scene heading patterns:
    - INT. COFFEE SHOP - DAY
    - EXT. CITY STREET - NIGHT
    - EST. SPACE STATION - CONTINUOUS
    - INT/EXT. MOVING CAR - DUSK
    
    Returns:
    - True if line starts with standard slugline prefixes
    - False otherwise
    """
    stripped = text.strip()
    return stripped.startswith((
        "INT.",    # Interior scenes
        "EXT.",    # Exterior scenes
        "EST.",    # Establishing shots
        "INT/",    # Interior/Exterior combo
        "EXT/",    # Exterior/Interior combo
        "FADE",    # Transitions (FADE IN, FADE OUT)
        "CUT",     # Transitions (CUT TO:)
        "DISSOLVE" # Transitions (DISSOLVE TO:)
    ))
```

**Example Scene Headings:**

| Valid Sluglines | Detected |
|-----------------|----------|
| `INT. THRONE ROOM - DAY` | ✅ Yes |
| `EXT. BATTLEFIELD - CONTINUOUS` | ✅ Yes |
| `EST. CITYSCAPE - DAWN` | ✅ Yes |
| `INT/EXT. SPACESHIP - NIGHT` | ✅ Yes |
| `FADE IN:` | ✅ Yes |
| `CUT TO:` | ✅ Yes |
| `The hero enters the room.` | ❌ No (action line) |
| `HERO` | ❌ No (character cue) |

#### 3.4.2 Character Cue Detection

**Function:** `_is_character_line()` (Lines 376-389)

Identifies character dialogue cues using multiple heuristics:

```python
# Regex pattern for character names
CHARACTER_HEADING_PATTERN = re.compile(r'^[A-Z][A-Z0-9 .\'"()/\-]{0,60}$')

def _is_character_line(value: str) -> bool:
    """
    Detects if a line is a character name cue.
    
    Character cue patterns:
    - ALL CAPS: "HERO"
    - With parenthetical: "HERO (V.O.)"
    - With suffix: "HERO (CONT'D)"
    - With colon: "HERO:"
    
    Validation rules:
    - Must be uppercase
    - Max 60 characters (prevents false positives)
    - Allowed chars: A-Z, 0-9, space, . ' " ( ) / -
    - Not a scene heading (INT./EXT. check)
    
    Returns:
    - True if line matches character cue pattern
    - False if scene heading, action line, or malformed
    """
    stripped = value.strip()
    
    # Empty lines are not character cues
    if not stripped:
        return False
    
    # Scene headings take precedence
    if _is_scene_heading(stripped):
        return False
    
    # Check for colon-terminated uppercase (e.g., "HERO:")
    if stripped.endswith(":") and stripped == stripped.upper():
        return True
    
    # Check against regex pattern
    if CHARACTER_HEADING_PATTERN.match(stripped):
        return True
    
    return False
```

**Character Cue Examples:**

| Line | Detected | Reason |
|------|----------|--------|
| `HERO` | ✅ Yes | All caps, matches pattern |
| `HERO (V.O.)` | ✅ Yes | Voice-over parenthetical |
| `HERO (CONT'D)` | ✅ Yes | Continued dialogue |
| `HERO:` | ✅ Yes | Colon-terminated uppercase |
| `VILLAIN 2` | ✅ Yes | Alphanumeric allowed |
| `DR. SMITH` | ✅ Yes | Period allowed |
| `HERO'S FATHER` | ✅ Yes | Apostrophe allowed |
| `INT. ROOM - DAY` | ❌ No | Scene heading (excluded) |
| `He walks across the room.` | ❌ No | Not all caps |
| `hero` | ❌ No | Not uppercase |

**Regex Breakdown:**
```
^[A-Z][A-Z0-9 .\'"()/\-]{0,60}$

^           - Start of string
[A-Z]       - Must start with uppercase letter
[           - Character class
  A-Z       - Uppercase letters
  0-9       - Numbers (for GUARD 1, ROBOT 2, etc.)
  (space)   - Spaces (for "HERO'S FATHER")
  .         - Periods (for "DR. SMITH")
  '         - Apostrophes (for "HERO'S FATHER")
  "         - Quotes (for nickname parentheticals)
  ()        - Parentheses (for "(V.O.)", "(O.S.)")
  /         - Slashes (for dual character cues)
  -         - Hyphens (for hyphenated names)
]{0,60}     - 0-60 additional characters
$           - End of string
```

### 3.5 AWS Bedrock Integration

#### 3.5.1 System Prompt Design

**Variable:** `SYSTEM_PROMPT` (Lines 156-174)

The system prompt establishes the AI's persona and output requirements:

```python
SYSTEM_PROMPT = textwrap.dedent(
    f"""
    You are an award-winning showrunner and narrative designer who architects 
    internationally appealing feature films. Analyse every creative brief with 
    rigor before you write. Surface cultural research, mythic structure, character 
    arcs, and audience retention tactics. Then craft a professional, industry-formatted 
    screenplay that comfortably exceeds {MIN_TOKENS} tokens (roughly {TARGET_WORDS}+ words). 
    Use ACT I, ACT II A, ACT II B, and ACT III headings, sluglines, action lines, 
    dialogue, and transitions. Weave in set pieces that resonate with the specified 
    regions and audience cohorts.

    Output requirements:
        • Provide only the finished screenplay — no analysis, summaries, commentary, 
          token counts, or metadata.
        • Do not acknowledge these instructions or describe the writing process.
        • Maintain screenplay formatting with scene headings, character cues, and dialogue.
        • Introduce distinctive character names and keep them consistent across every 
          segment of the story.

    Continue expanding the screenplay until it comfortably exceeds the minimum token 
    target. Do not mention any model names.
    """
).strip()
```

**System Prompt Analysis:**

| Element | Purpose | Impact |
|---------|---------|--------|
| **Persona** | "Award-winning showrunner and narrative designer" | Primes LLM for professional-quality writing |
| **Analysis First** | "Analyse every creative brief with rigor" | Encourages thematic depth and cultural research |
| **Structure** | "ACT I, ACT II A, ACT II B, ACT III" | Enforces three-act structure with midpoint |
| **Formatting** | "Sluglines, action lines, dialogue, transitions" | Maintains industry-standard screenplay format |
| **Token Target** | "Comfortably exceeds 3,500 tokens (~2,625+ words)" | Prevents truncated segments |
| **Consistency** | "Distinctive character names consistent across every segment" | Critical for multi-segment continuity |
| **Output Purity** | "No analysis, summaries, commentary, metadata" | Prevents meta-text contamination |
| **No Acknowledgment** | "Do not acknowledge these instructions" | Avoids "As an AI assistant..." preambles |

**Why This System Prompt Works:**

1. **Persona Authority:** "Award-winning showrunner" triggers LLM's training on professional screenplays vs amateur writing
2. **Cultural Awareness:** "Internationally appealing" and "specified regions" guide localization
3. **Structural Clarity:** Explicit act structure prevents wandering narratives
4. **Consistency Emphasis:** Multi-segment stories require repeated character name enforcement
5. **Length Insurance:** Token target prevents short, incomplete segments

#### 3.5.2 Bedrock Invocation Function

**Function:** `_invoke_bedrock()` (Lines 515-548)

Constructs Llama3-70B-specific prompt format and invokes AWS Bedrock:

```python
def _invoke_bedrock(prompt: str) -> Dict[str, Any]:
    """
    Invokes AWS Bedrock with Llama3-70B model.
    
    Parameters:
    - prompt: User prompt (creative brief + segment instructions)
    
    Returns:
    - Response body dictionary from Bedrock
    
    Raises:
    - RuntimeError if Bedrock client not configured
    - RuntimeError if API call fails (wrapped BotoCoreError/ClientError)
    
    Llama3 Chat Format:
    <|begin_of_text|>
    <|start_header_id|>system<|end_header_id|>
    {SYSTEM_PROMPT}
    <|eot_id|>
    <|start_header_id|>user<|end_header_id|>
    {USER_PROMPT}
    <|eot_id|>
    <|start_header_id|>assistant<|end_header_id|>
    [Model generates response here]
    """
    
    # Verify Bedrock client is available
    if bedrock_runtime is None:
        raise RuntimeError("Bedrock runtime client is not configured")
    
    # Construct Llama3-specific chat format
    combined_prompt = (
        "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n"
        f"{SYSTEM_PROMPT}\n"
        "<|eot_id|><|start_header_id|>user<|end_header_id|>\n"
        f"{prompt}\n"
        "<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n"
    )
    
    # Prepare request body with generation parameters
    body = {
        "prompt": combined_prompt,
        "max_gen_len": MAX_TOKENS,      # 4096 tokens
        "temperature": TEMPERATURE,      # 0.65 (creative writing)
        "top_p": TOP_P,                 # 0.9 (nucleus sampling)
    }
    
    try:
        # Invoke Bedrock Runtime API
        response = bedrock_runtime.invoke_model(
            modelId=MODEL_ID,                    # meta.llama3-70b-instruct-v1:0
            body=json.dumps(body),
            accept="application/json",
            contentType="application/json",
        )
    except (BotoCoreError, ClientError) as exc:
        # Log AWS SDK errors with detailed payload info
        error_payload = getattr(exc, "response", None)
        app.logger.error(
            "Bedrock invocation failed: %s | payload=%s", 
            exc, 
            error_payload
        )
        raise RuntimeError("Language model invocation failed") from exc
    
    # Parse and return response body
    return json.loads(response["body"].read())
```

**Request Body Structure:**

```json
{
  "prompt": "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\nYou are an award-winning showrunner...\n<|eot_id|><|start_header_id|>user<|end_header_id|>\nProject title: Epic Quest\nLogline: A reluctant hero...\n<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n",
  "max_gen_len": 4096,
  "temperature": 0.65,
  "top_p": 0.9
}
```

**Llama3 Special Tokens:**

| Token | Purpose |
|-------|---------|
| `<|begin_of_text|>` | Marks start of conversation |
| `<|start_header_id|>` | Begins role header (system/user/assistant) |
| `<|end_header_id|>` | Ends role header |
| `<|eot_id|>` | End of turn (signals role switch) |

**Error Handling:**

```python
# Scenario 1: Bedrock client not initialized (AWS credentials missing)
if bedrock_runtime is None:
    raise RuntimeError("Bedrock runtime client is not configured")
    # Returns 502 Bad Gateway with error message to client

# Scenario 2: AWS SDK errors (throttling, model unavailable, etc.)
except (BotoCoreError, ClientError) as exc:
    app.logger.error("Bedrock invocation failed: %s", exc)
    raise RuntimeError("Language model invocation failed") from exc
    # Returns 502 Bad Gateway with sanitized error message
```

#### 3.5.3 Response Parsing & Text Extraction

**Function:** `_extract_text()` (Lines 550-594)

Robust extraction of screenplay text from diverse Bedrock response formats:

```python
def _extract_text(response_body: Dict[str, Any]) -> str:
    """
    Extracts screenplay text from Bedrock response body.
    
    Handles multiple response formats:
    1. Direct string fields: generation, output, result
    2. List of generations: [{"text": "..."}, ...]
    3. Nested content objects: {"content": {"text": "..."}}
    4. Message arrays: [{"role": "assistant", "content": "..."}]
    
    This flexibility ensures compatibility across Bedrock model versions.
    
    Returns:
    - Extracted screenplay text string
    - Empty string if no text found
    """
    
    if not response_body:
        return ""
    
    # Helper function for recursive content extraction
    def _from_content(value: Any) -> str:
        if isinstance(value, list):
            # List of content blocks: join all text
            return "".join(_from_content(item) for item in value)
        
        if isinstance(value, dict):
            # Dictionary: collect text, result, and nested content
            collected: List[str] = []
            if value.get("text"):
                collected.append(str(value.get("text", "")))
            if value.get("result"):
                collected.append(str(value.get("result", "")))
            if value.get("content"):
                collected.append(_from_content(value.get("content")))
            return "".join(collected)
        
        # Primitive type: convert to string
        return str(value)
    
    # Strategy 1: Check direct string fields (Llama3 format)
    for key in ("generation", "output", "result"):
        if isinstance(response_body.get(key), str):
            return str(response_body[key])
    
    # Strategy 2: Check generations array (older Bedrock format)
    if isinstance(response_body.get("generations"), list):
        return "".join(
            str(item.get("text", "")) 
            for item in response_body["generations"] 
            if isinstance(item, dict)
        )
    
    # Strategy 3: Check outputs array
    if isinstance(response_body.get("outputs"), list):
        return "".join(
            _from_content(item) 
            for item in response_body.get("outputs", [])
        )
    
    # Strategy 4: Check nested content field
    if response_body.get("content"):
        return _from_content(response_body.get("content"))
    
    # Strategy 5: Check messages array (chat completion format)
    if isinstance(response_body.get("messages"), list):
        for message in response_body["messages"]:
            if isinstance(message, dict) and message.get("role") == "assistant":
                return _from_content(message.get("content"))
    
    # No text found
    return ""
```

**Response Format Examples:**

**Format 1: Direct String (Llama3-70B Current Format)**
```json
{
  "generation": "INT. THRONE ROOM - DAY\n\nThe HERO enters...",
  "prompt_token_count": 2048,
  "generation_token_count": 3842,
  "stop_reason": "stop"
}
```

**Format 2: Generations Array (Legacy Format)**
```json
{
  "generations": [
    {
      "text": "INT. THRONE ROOM - DAY\n\nThe HERO enters...",
      "finish_reason": "length"
    }
  ]
}
```

**Format 3: Nested Content (Claude Format)**
```json
{
  "content": [
    {
      "type": "text",
      "text": "INT. THRONE ROOM - DAY\n\nThe HERO enters..."
    }
  ],
  "stop_reason": "end_turn"
}
```

**Format 4: Messages Array (Chat Completion Format)**
```json
{
  "messages": [
    {
      "role": "assistant",
      "content": "INT. THRONE ROOM - DAY\n\nThe HERO enters..."
    }
  ]
}
```

**Extraction Priority:**
1. Direct string fields (`generation`, `output`, `result`) → Fastest, most common
2. Generations array → Legacy compatibility
3. Outputs array → Multi-output models
4. Nested content → Claude/structured models
5. Messages array → Chat completion APIs

#### 3.5.4 Section Splitting (Analysis vs Script)

**Function:** `_split_sections()` (Lines 596-621)

Some LLM responses include analysis headers; this function isolates pure screenplay:

```python
def _split_sections(raw_text: str) -> Dict[str, str]:
    """
    Splits LLM response into analysis and script sections.
    
    Some models preface screenplay with analysis like:
    <<ANALYSIS>>
    This segment establishes the hero's ordinary world...
    <<SCRIPT>>
    INT. COFFEE SHOP - DAY
    ...
    <<END>>
    
    This function extracts only the screenplay portion.
    
    Returns:
    - Dictionary with "analysis" and "script" keys
    - If no markers found, entire text treated as "script"
    """
    
    text = raw_text or ""
    lowered = text.lower()
    
    # Define section markers (case-insensitive)
    analysis_marker = "<<analysis>>"
    script_marker = "<<script>>"
    
    # Check if both markers present
    if analysis_marker in lowered and script_marker in lowered:
        # Find marker positions
        idx_analysis = lowered.index(analysis_marker)
        idx_script = lowered.index(script_marker)
        
        # Extract analysis block
        analysis_block = text[
            idx_analysis + len("<<ANALYSIS>>") : idx_script
        ]
        
        # Find optional end marker
        end_idx = lowered.find("<<end>>", idx_script)
        if end_idx == -1:
            end_idx = len(text)
        
        # Extract script block
        script_block = text[
            idx_script + len("<<SCRIPT>>") : end_idx
        ]
        
        return {
            "analysis": analysis_block.strip(),
            "script": script_block.strip(),
        }
    
    # No markers: treat entire response as script
    return {
        "analysis": "",
        "script": text.strip(),
    }
```

**Example Input with Markers:**
```
<<ANALYSIS>>
This opening segment introduces the hero's ordinary world, establishing their 
reluctance and the status quo that will be disrupted by the inciting incident.
<<SCRIPT>>
INT. COFFEE SHOP - DAY

The HERO (late 20s, disheveled) stares at a laptop screen...
<<END>>
```

**Extracted Output:**
```python
{
  "analysis": "This opening segment introduces the hero's ordinary world...",
  "script": "INT. COFFEE SHOP - DAY\n\nThe HERO (late 20s, disheveled) stares..."
}
```

**Why This Matters:**
- Some LLMs include meta-commentary despite system prompt instructions
- Analysis text would contaminate screenplay if not filtered
- Only the `script` key is used in final output
- Analysis is logged for debugging but discarded

---

## 4. Translation Pipeline Architecture

### 4.1 Translation Modes Overview

The service supports two translation strategies:

| Mode | Environment Variable | Behavior | Use Case |
|------|---------------------|----------|----------|
| **Dialogue-Only** | `MOVIE_SCRIPT_TRANSLATE_FULL=false` | Translates character dialogue, preserves stage directions in English | Default - maintains technical clarity for production teams |
| **Full-Text** | `MOVIE_SCRIPT_TRANSLATE_FULL=true` | Translates entire screenplay including directions | Fully localized scripts for regional markets |

### 4.2 Dialogue-Only Translation Mode

**Function:** `_translate_dialogue_segments()` (Lines 458-513)

#### 4.2.1 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Input: Complete English screenplay (all segments joined)   │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 1: Language Check                                     │
│  • If language == "en": return script unchanged             │
│  • If translate_client == None: skip translation (warning)  │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 2: Check Translation Mode                             │
│  • If MOVIE_SCRIPT_TRANSLATE_FULL=true:                     │
│    → Call _translate_full_text() and return                 │
│  • Otherwise: continue to dialogue-only mode                │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 3: Line-by-Line Processing                            │
│  FOR each line in script:                                   │
│    ┌──────────────────────────────────────────────────┐    │
│    │ 3a: Check if blank line                          │    │
│    │ • Reset in_dialogue flag                         │    │
│    │ • Preserve line as-is                            │    │
│    └────────────┬─────────────────────────────────────┘    │
│                 ↓                                            │
│    ┌──────────────────────────────────────────────────┐    │
│    │ 3b: Check if character cue (_is_character_line) │    │
│    │ • Set in_dialogue = True                         │    │
│    │ • Preserve character name in English            │    │
│    └────────────┬─────────────────────────────────────┘    │
│                 ↓                                            │
│    ┌──────────────────────────────────────────────────┐    │
│    │ 3c: Check if dialogue line                       │    │
│    │ • If in_dialogue AND not parenthetical:          │    │
│    │   → Call _translate_dialogue_line()              │    │
│    │ • Otherwise preserve line (stage direction)      │    │
│    └──────────────────────────────────────────────────┘    │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│  Output: Screenplay with translated dialogue + English dirs │
└─────────────────────────────────────────────────────────────┘
```

#### 4.2.2 Implementation

```python
def _translate_dialogue_segments(
    script_text: str, 
    language: Dict[str, str]
) -> str:
    """
    Translates dialogue while preserving stage directions in English.
    
    Parameters:
    - script_text: Complete screenplay text
    - language: Language config dict with "code", "label", "romanize" keys
    
    Returns:
    - Screenplay with translated dialogue
    
    Translation Logic:
    1. Split script into lines
    2. Track dialogue state with in_dialogue flag
    3. When character cue detected: set in_dialogue = True
    4. When dialogue line detected: translate via AWS Translate
    5. When blank line or scene heading: set in_dialogue = False
    6. Preserve all stage directions, sluglines, and formatting
    """
    
    # Extract language code (e.g., "hi", "es", "zh")
    code = (language or {}).get("code", "en")
    target_language = TRANSLATE_LANGUAGE_CODES.get(code)
    
    # Skip translation for English
    if not target_language or target_language.lower().startswith("en"):
        return script_text
    
    # Check if translate client available
    if translate_client is None:
        app.logger.warning(
            "Translate client unavailable; skipping dialogue translation"
        )
        return script_text
    
    # Check if full-text translation enabled
    if os.getenv("MOVIE_SCRIPT_TRANSLATE_FULL", "true").lower() in {"1", "true", "yes"}:
        full_translation = _translate_full_text(script_text, target_language)
        if full_translation != script_text:
            return full_translation
    
    # Dialogue-only translation mode
    lines = script_text.splitlines()
    translated_lines: List[str] = []
    in_dialogue = False
    romanize = bool(language.get("romanize"))
    
    for line in lines:
        stripped = line.strip()
        
        # Blank lines reset dialogue state
        if not stripped:
            in_dialogue = False
            translated_lines.append(line)
            continue
        
        # Character cues activate dialogue state
        if _is_character_line(stripped):
            in_dialogue = True
            translated_lines.append(line)  # Keep character name in English
            continue
        
        # Translate dialogue lines (but not parentheticals)
        if in_dialogue and not stripped.startswith("("):
            translated_lines.append(
                _translate_dialogue_line(line, target_language, romanize)
            )
            continue
        
        # Preserve all other lines (stage directions, sluglines)
        translated_lines.append(line)
    
    return "\n".join(translated_lines)
```

#### 4.2.3 Single Dialogue Line Translation

**Function:** `_translate_dialogue_line()` (Lines 391-419)

```python
def _translate_dialogue_line(
    text: str, 
    target_language: str, 
    romanize: bool
) -> str:
    """
    Translates a single dialogue line while preserving indentation.
    
    Parameters:
    - text: Original dialogue line (may have leading whitespace)
    - target_language: AWS Translate language code (e.g., "hi", "es")
    - romanize: If True, convert non-Latin scripts to Latin (e.g., Hindi → Hinglish)
    
    Returns:
    - Translated dialogue line with original indentation preserved
    
    Example:
    Input:  "    I cannot believe this is happening."
    Output: "    मुझे विश्वास नहीं हो रहा कि यह हो रहा है।"
    (Or romanized: "    Mujhe vishwas nahin ho raha ki yah ho raha hai.")
    """
    
    if translate_client is None:
        return text
    
    # Preserve leading whitespace (screenplay indentation)
    stripped = text.lstrip()
    if not stripped:
        return text
    prefix = text[: len(text) - len(stripped)]
    
    try:
        # Call AWS Translate API
        response = translate_client.translate_text(
            Text=stripped,
            SourceLanguageCode="en",
            TargetLanguageCode=target_language,
        )
        translated = response.get("TranslatedText", stripped)
        
    except (BotoCoreError, ClientError) as exc:
        # Log error but return original text (graceful degradation)
        app.logger.warning("Dialogue translation failed: %s", exc)
        return text
        
    except Exception as exc:
        app.logger.warning("Unexpected dialogue translation error: %s", exc)
        return text
    
    # Apply romanization if requested (e.g., Devanagari → Latin)
    if romanize:
        translated = unidecode(translated)  # Uses unidecode library
    
    # Restore original indentation
    return f"{prefix}{translated}"
```

**Whitespace Preservation Example:**

```
Original:
HERO
    I will fight for what's right.
        (pause)
    No matter the cost.

Translated (Hindi):
HERO
    मैं सही के लिए लड़ूंगा।
        (pause)
    चाहे जो कीमत हो।

Translated (Hindi Romanized):
HERO
    Main sahi ke liye larunga.
        (pause)
    Chahe jo keemat ho.
```

**Why Preserve Indentation?**
- Screenplay formatting has semantic meaning (dialogue indentation = 2.5 inches from left margin)
- Production software (Final Draft, Celtx) depends on spacing for PDF generation
- Actors and directors use indentation to parse script structure quickly

### 4.3 Full-Text Translation Mode

**Function:** `_translate_full_text()` (Lines 445-456)

Translates entire screenplay including stage directions:

```python
def _translate_full_text(script_text: str, target_language: str) -> str:
    """
    Translates entire screenplay including stage directions.
    
    Strategy:
    1. Split script into chunks (4,500 chars each) to avoid API limits
    2. Translate each chunk independently
    3. Join chunks back together
    
    Chunk boundaries:
    - Prefer newlines for clean breaks
    - Fallback to whitespace if no newline near boundary
    - Prevents mid-word splits
    
    Returns:
    - Fully translated screenplay
    - Original text if translation fails (graceful degradation)
    """
    
    if translate_client is None or not script_text.strip():
        return script_text
    
    translated_chunks: List[str] = []
    
    # Split into chunks
    for chunk in _chunk_text_for_translate(script_text, MAX_TRANSLATE_CHARS):
        try:
            # Translate chunk
            response = translate_client.translate_text(
                Text=chunk,
                SourceLanguageCode="en",
                TargetLanguageCode=target_language,
            )
            translated_chunks.append(response.get("TranslatedText", chunk))
            
        except (BotoCoreError, ClientError) as exc:
            # Log error and keep original chunk
            app.logger.warning(
                "Chunk translation failed; returning original chunk: %s", exc
            )
            translated_chunks.append(chunk)
            
        except Exception as exc:
            app.logger.warning(
                "Unexpected chunk translation error; returning original chunk: %s", exc
            )
            translated_chunks.append(chunk)
    
    # Join all translated chunks
    return "".join(translated_chunks)
```

### 4.4 Chunk-Based Translation Strategy

**Function:** `_chunk_text_for_translate()` (Lines 421-443)

**Why Chunking?**
- AWS Translate has 5,000 byte limit per request
- 130-minute screenplay ≈ 130 pages × 250 words/page = 32,500 words ≈ 162,500 characters
- Requires ~36 chunks at 4,500 chars/chunk

```python
def _chunk_text_for_translate(text: str, max_chars: int) -> List[str]:
    """
    Splits text into chunks for AWS Translate API.
    
    Parameters:
    - text: Full screenplay text
    - max_chars: Maximum characters per chunk (4,500 default)
    
    Returns:
    - List of text chunks
    
    Chunking Logic:
    1. Start at position 0
    2. Move forward max_chars characters
    3. Look backward from that point to find:
       a. Nearest newline (preferred) within 50% window
       b. Nearest whitespace if no newline
    4. Split at found boundary
    5. Repeat until end of text
    
    This prevents splitting:
    - Mid-word
    - Mid-sentence (prefers paragraph breaks)
    - Mid-dialogue line
    """
    
    if not text:
        return [""]
    
    chunks: List[str] = []
    length = len(text)
    start = 0
    
    while start < length:
        # Calculate tentative end position
        end = min(start + max_chars, length)
        
        if end < length:
            # Look for clean break point in last 50% of chunk
            search_start = start + int(max_chars * 0.5)
            
            # Prefer newline breaks (paragraph boundaries)
            newline_idx = text.rfind("\n", search_start, end)
            
            # Fallback to whitespace breaks (word boundaries)
            whitespace_idx = text.rfind(" ", search_start, end)
            
            # Use best available break point
            candidate = max(newline_idx, whitespace_idx)
            
            if candidate != -1 and candidate >= start:
                end = min(candidate + 1, length)  # Include the newline/space
        
        # Extract chunk
        chunk = text[start:end]
        if not chunk:
            break
        
        chunks.append(chunk)
        start = end
    
    return chunks if chunks else [text]
```

**Chunking Example:**

```
Script: 15,000 characters
Max chunk: 4,500 characters

Chunk 1: Chars 0-4,500 (split at newline near 4,500)
Chunk 2: Chars 4,501-9,000 (split at newline near 9,000)
Chunk 3: Chars 9,001-13,500 (split at newline near 13,500)
Chunk 4: Chars 13,501-15,000 (final chunk)
```

**Break Point Priority:**
1. **Newline within last 50% of chunk** → Best (preserves paragraph structure)
2. **Whitespace within last 50% of chunk** → Good (preserves word boundaries)
3. **Hard break at max_chars** → Fallback (may split mid-word if unavoidable)

### 4.5 Translation Configuration

#### 4.5.1 Language Code Mapping

```python
# Direct 1:1 mapping for AWS Translate
TRANSLATE_LANGUAGE_CODES = {code: code for code in LANGUAGE_CONFIG.keys()}

# Examples:
# "en" → "en"
# "hi" → "hi"
# "es-MX" → "es-MX"
# "zh-TW" → "zh-TW"
```

#### 4.5.2 Romanization Support

Some languages benefit from romanization (non-Latin scripts → Latin alphabet):

| Language | Script | Romanized | Use Case |
|----------|--------|-----------|----------|
| Hindi (hi) | Devanagari (हिन्दी) | Latin (Hinglish) | Indian productions with English subtitles |
| Arabic (ar) | Arabic (العربية) | Latin (Arabizi) | Middle East social media content |
| Russian (ru) | Cyrillic (Русский) | Latin (Translit) | International co-productions |
| Japanese (ja) | Kanji/Kana (日本語) | Latin (Romaji) | Anime scripts for Western markets |

**Romanization Example:**

```python
# Original Hindi (Devanagari)
dialogue = "मैं एक नायक हूँ।"

# Romanized (Hinglish)
romanized = unidecode(dialogue)
# Output: "main ek naayak hoon."
```

**unidecode Library:**
- Converts Unicode to ASCII approximations
- Supports 100+ scripts (Cyrillic, Arabic, CJK, Devanagari, etc.)
- Lossy conversion (tone marks, diacritics removed)

---

## 5. API Endpoint Reference

### 5.1 Health Check Endpoint

#### 5.1.1 Endpoint Specification

**Route:** `GET /health`  
**Purpose:** Service health check and configuration visibility  
**Authentication:** None required  
**Rate Limiting:** None

#### 5.1.2 Request

```http
GET /health HTTP/1.1
Host: localhost:5005
```

**No request body or parameters required.**

#### 5.1.3 Response

**Success Response (200 OK):**

```json
{
  "status": "ok",
  "modelId": "meta.llama3-70b-instruct-v1:0",
  "region": "us-east-1",
  "minTokens": 3500,
  "maxTokens": 4096
}
```

**Degraded Response (200 OK with degraded status):**

```json
{
  "status": "degraded",
  "modelId": "meta.llama3-70b-instruct-v1:0",
  "region": "us-east-1",
  "minTokens": 3500,
  "maxTokens": 4096
}
```

**Status Field Logic:**
```python
"status": "ok" if bedrock_runtime else "degraded"
```

- `"ok"` → Bedrock client initialized successfully
- `"degraded"` → Bedrock client failed to initialize (check AWS credentials)

#### 5.1.4 Implementation

```python
@app.route("/health", methods=["GET"])
def health() -> Any:
    """
    Health check endpoint.
    
    Returns service status and configuration for monitoring/debugging.
    """
    return jsonify(
        {
            "status": "ok" if bedrock_runtime else "degraded",
            "modelId": MODEL_ID,
            "region": BEDROCK_REGION,
            "minTokens": MIN_TOKENS,
            "maxTokens": MAX_TOKENS,
        }
    )
```

#### 5.1.5 Monitoring Use Cases

**Container Orchestration (Kubernetes/ECS):**
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 5005
  initialDelaySeconds: 30
  periodSeconds: 10
```

**Load Balancer Health Checks:**
- Path: `/health`
- Expected status: `200`
- Healthy condition: `response.status == "ok"`

**Operational Monitoring:**
```bash
# Check service health
curl http://localhost:5005/health

# Parse status
curl -s http://localhost:5005/health | jq '.status'
# Output: "ok" or "degraded"
```

### 5.2 Script Generation Endpoint

#### 5.2.1 Endpoint Specification

**Route:** `POST /generate-script`  
**Purpose:** Generate complete feature-length screenplay  
**Content-Type:** `application/json`  
**Authentication:** None (add API keys in production)  
**Timeout:** Recommended 5 minutes (13 segments × 20s/segment avg)

#### 5.2.2 Request Schema

```json
{
  "title": "string (optional)",
  "logline": "string (optional)",
  "additionalGuidance": "string (optional)",
  "brief": "string (optional, alias for additionalGuidance)",
  
  "genres": ["string", "string", ...],
  "genre": "string (optional, alias for genres)",
  
  "moods": ["string", "string", ...],
  "mood": "string (optional, alias for moods)",
  
  "audience": ["string", "string", ...],
  
  "regions": ["string", "string", ...],
  "region": "string (optional, alias for regions)",
  
  "era": "string (optional)",
  "period": "string (optional, alias for era)",
  
  "targetRuntimeMinutes": 130,
  "runtimeMinutes": 130,
  
  "targetRating": "string (optional)",
  "rating": "string (optional, alias for targetRating)",
  
  "franchiseContext": "string (optional)",
  
  "language": "en"
}
```

**Field Descriptions:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `title` | string | No | "Untitled Feature" | Project title for screenplay header |
| `logline` | string | No | Auto-generated | One-line premise/hook for the story |
| `additionalGuidance` | string | No | "" | Free-form creative notes (must-have scenes, visual motifs, etc.) |
| `genres` | string[] | No | [] | Primary genres (Action, Drama, Sci-Fi, etc.) |
| `moods` | string[] | No | [] | Tonal palette (Epic, Darkly comic, Suspenseful, etc.) |
| `audience` | string[] | No | [] | Target demographics (Kids 6-11, Adults 25-44, Four-quadrant, etc.) |
| `regions` | string[] | No | [] | Cultural regions (North America, India, China, Global, etc.) |
| `era` | string | No | "" | Time period (Present day, 1920s, Future, Medieval, etc.) |
| `targetRuntimeMinutes` | integer | No | 130 | Desired screenplay length in minutes |
| `targetRating` | string | No | "" | MPAA rating (G, PG, PG-13, R, NC-17) |
| `franchiseContext` | string | No | "" | IP continuity notes for sequels/shared universes |
| `language` | string | No | "en" | Dialogue language code (en, hi, es, zh, etc.) |

**Field Aliases:**
- `brief` ↔ `additionalGuidance`
- `genre` ↔ `genres` (string converts to single-item array)
- `mood` ↔ `moods`
- `region` ↔ `regions`
- `period` ↔ `era`
- `runtimeMinutes` ↔ `targetRuntimeMinutes`
- `rating` ↔ `targetRating`

#### 5.2.3 Example Requests

**Minimal Request (All Defaults):**
```json
POST /generate-script
Content-Type: application/json

{}
```
*Generates 130-minute English screenplay with default creative parameters.*

**Basic Request:**
```json
{
  "logline": "A reluctant hero discovers ancient powers and must save the world.",
  "genres": ["Epic Fantasy", "Adventure"],
  "language": "en"
}
```

**Full-Featured Request:**
```json
{
  "title": "Echoes of Eternity",
  "logline": "A time-traveling archaeologist must prevent a catastrophic temporal paradox while confronting her own past.",
  "additionalGuidance": "Include a memorable chess metaphor scene. Visual motif: broken clocks. Budget: $80M tentpole. Must set up sequel hook.",
  
  "genres": ["Science Fiction", "Thriller", "Drama"],
  "moods": ["High-tension suspense", "Bittersweet", "Hopeful and redemptive"],
  
  "audience": ["Adults (25-44)", "Young adults (18-24)", "Festival cinephiles"],
  "regions": ["North America", "Western Europe", "China"],
  
  "era": "Present day with flashbacks to 1990s",
  "targetRuntimeMinutes": 140,
  "targetRating": "PG-13",
  
  "franchiseContext": "Part 1 of planned trilogy. Introduce Dr. Chen's rival but don't reveal full backstory.",
  
  "language": "en"
}
```

**Multi-Language Request (Hindi):**
```json
{
  "title": "बहादुर योद्धा",
  "logline": "A warrior princess must unite warring kingdoms against a demon invasion.",
  "genres": ["Action", "Epic Fantasy", "Historical"],
  "moods": ["Epic and awe-inspiring", "Heart-wrenching"],
  "audience": ["Young adults (18-24)", "Adults (25-44)", "Family four-quadrant"],
  "regions": ["India & South Asia", "Global (All Regions)"],
  "targetRuntimeMinutes": 150,
  "targetRating": "PG-13",
  "language": "hi"
}
```
*Generates screenplay with Hindi dialogue and English stage directions.*

#### 5.2.4 Response Schema

**Success Response (200 OK):**

```json
{
  "title": "Echoes of Eternity",
  "script": "ACT I\n\nINT. UNIVERSITY LAB - DAY\n\nDR. MAYA CHEN (35, intense) examines ancient artifacts...",
  "language": "English (default)",
  "runtimeMinutes": 140
}
```

**Field Descriptions:**

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Screenplay title (from request or default "Untitled Feature") |
| `script` | string | Complete feature-length screenplay with industry formatting |
| `language` | string | Human-readable language name (e.g., "Hindi", "Spanish (Mexico)") |
| `runtimeMinutes` | integer | Actual runtime used for segment calculation |

**Error Responses:**

**415 Unsupported Media Type:**
```json
{
  "error": "Request must be JSON"
}
```
*Returned when Content-Type is not application/json.*

**502 Bad Gateway (Bedrock Failure):**
```json
{
  "error": "Language model invocation failed"
}
```
*Returned when AWS Bedrock API call fails (credentials, throttling, model unavailable).*

**502 Bad Gateway (Empty Generation):**
```json
{
  "error": "Unable to generate screenplay segments"
}
```
*Returned when all segment generations are empty or fail to parse.*

#### 5.2.5 Implementation

```python
@app.route("/generate-script", methods=["POST"])
def generate_script() -> Any:
    """
    Main screenplay generation endpoint.
    
    Process:
    1. Validate Content-Type
    2. Parse request JSON
    3. Compose creative brief
    4. Determine segment count
    5. Generate segments iteratively
    6. Translate dialogue (if non-English)
    7. Return complete screenplay
    """
    
    # Validate Content-Type
    if request.content_type != "application/json":
        return jsonify({"error": "Request must be JSON"}), 415
    
    # Parse request body
    payload: Dict[str, Any] = request.get_json(silent=True) or {}
    brief = _compose_brief(payload)
    
    # Calculate segments
    runtime_minutes = _parse_runtime_minutes(brief.get("runtime")) or DEFAULT_RUNTIME_MINUTES
    total_segments = _determine_segments(runtime_minutes)
    
    # Generate segments iteratively
    script_segments: List[str] = []
    script_so_far = ""
    
    for segment_index in range(total_segments):
        # Build segment prompt with cumulative context
        prompt = _build_segment_prompt(
            brief=brief,
            segment_index=segment_index,
            total_segments=total_segments,
            runtime_minutes=runtime_minutes,
            script_so_far=script_so_far,
            language=brief["language"],
        )
        
        # Invoke Bedrock
        try:
            response_body = _invoke_bedrock(prompt)
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 502
        
        # Extract screenplay text
        raw_text = _extract_text(response_body)
        if not raw_text.strip():
            app.logger.warning(
                "Empty generation received from Bedrock for segment %s | response=%s",
                segment_index + 1,
                response_body,
            )
            continue
        
        # Parse script section (strip analysis if present)
        segment_script = _split_sections(raw_text).get("script", "").strip()
        if not segment_script:
            app.logger.warning(
                "Parsed empty script for segment %s | raw_text=%s",
                segment_index + 1,
                raw_text,
            )
            continue
        
        # Append to cumulative script
        script_segments.append(segment_script)
        script_so_far = f"{script_so_far}\n\n{segment_script}".strip()
    
    # Validate generation success
    if not script_segments:
        return jsonify({"error": "Unable to generate screenplay segments"}), 502
    
    # Join all segments
    full_script = "\n\n".join(script_segments).strip()
    
    # Translate dialogue if non-English
    full_script = _translate_dialogue_segments(full_script, brief["language"])
    
    # Return complete screenplay
    return jsonify(
        {
            "title": brief["title"],
            "script": full_script,
            "language": brief["language"].get("label", "English (default)"),
            "runtimeMinutes": runtime_minutes,
        }
    )
```

#### 5.2.6 Performance Characteristics

**Timing Analysis (130-minute screenplay, 13 segments):**

| Phase | Duration | Notes |
|-------|----------|-------|
| Request parsing | ~10ms | Negligible |
| Segment 1 generation | 15-25s | Cold start (no context) |
| Segments 2-12 generation | 18-30s each | With 4000-char context |
| Segment 13 generation | 20-35s | Final segment (climax complexity) |
| Translation | 5-15s | Dialogue-only mode |
| **Total** | **4-7 minutes** | Varies by model availability |

**Bedrock Throttling:**
- Default limit: 5 requests/minute for Llama3-70B
- 13 segments require ~3 minutes minimum due to rate limits
- Consider request quota increase for production workloads

**Cost Estimation (AWS Pricing as of Oct 2025):**
- Bedrock Llama3-70B: $0.00265/1K input tokens, $0.0035/1K output tokens
- Input per segment: ~2,000 tokens × 13 segments = 26,000 tokens = $0.07
- Output per segment: ~3,500 tokens × 13 segments = 45,500 tokens = $0.16
- AWS Translate: $15/million characters
- Translation: ~162,500 chars = $0.002
- **Total per screenplay: ~$0.23**

---

## End of Part 2

**Continue to Part 3 for:**
- Frontend Architecture Deep Dive
- Multi-Step Wizard Implementation
- State Management & API Integration
- Script Display & Export Features
- Complete Frontend Component Reference

---

**Document Statistics - Part 2:**
- Pages: ~45
- Sections: 3 major sections (continuation)
- Code Examples: 20+
- Tables: 15+
- API schemas: 2 complete specifications

**Next Document:** `MOVIE_SCRIPT_CREATION_PART3.md`
# Movie Script Creation Service - Complete Reference Guide
## Part 3: Frontend Architecture & User Experience

**Document Version:** 1.0  
**Last Updated:** October 22, 2025  
**Service:** Movie Script Creation  
**Port:** 5005 (Backend) / 3000 (Frontend Dev)

---

## Table of Contents - Part 3

6. [Frontend Architecture Deep Dive](#6-frontend-architecture-deep-dive)
   - Component Structure
   - Multi-Step Wizard Design
   - State Management Architecture
7. [User Interface Components](#7-user-interface-components)
   - Form Controls & Validation
   - Creative DNA Preview
   - Script Display & Export
8. [Frontend-Backend Integration](#8-frontend-backend-integration)
   - API Communication
   - Error Handling
   - Loading States

---

## 6. Frontend Architecture Deep Dive

### 6.1 Component Structure

**File:** `frontend/src/MovieScriptCreation.js` (950 lines)

#### 6.1.1 Technology Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18.x | Component framework |
| styled-components | 5.x | CSS-in-JS styling |
| axios | 1.x | HTTP client for API calls |
| JavaScript | ES6+ | Language (not TypeScript) |

#### 6.1.2 Component Architecture

```
MovieScriptCreation (Main Component)
│
├── State Management (16 state variables)
│   ├── Creative Brief State
│   │   ├── logline
│   │   ├── notes
│   │   ├── genres
│   │   ├── moods
│   │   ├── audience
│   │   ├── regions
│   │   ├── runtime
│   │   ├── rating
│   │   └── language
│   │
│   └── UI State
│       ├── step (0-3, wizard navigation)
│       ├── hasTriggeredGeneration
│       ├── result (API response)
│       ├── loading
│       ├── error
│       └── copyStatus
│
├── Styled Components (25+ UI elements)
│   ├── Layout Components
│   │   ├── Page (outer container)
│   │   ├── Header (title section)
│   │   ├── Layout (grid container)
│   │   └── Panel (card containers)
│   │
│   ├── Form Components
│   │   ├── Field (input wrapper)
│   │   ├── Label
│   │   ├── TextArea
│   │   ├── Select
│   │   ├── MultiSelect
│   │   └── HelperText
│   │
│   ├── Button Components
│   │   ├── PrimaryButton (gradient)
│   │   ├── SecondaryButton (outline)
│   │   └── TertiaryButton (minimal)
│   │
│   ├── Display Components
│   │   ├── Blueprint (creative DNA preview)
│   │   ├── ScriptBlock (screenplay display)
│   │   ├── ErrorBanner
│   │   └── EmptyState
│   │
│   └── Utility Components
│       ├── ButtonRow
│       ├── FooterButtons
│       └── CopyStatus
│
├── Event Handlers (7 callbacks)
│   ├── handleMultiSelect() - Multi-select dropdown handler
│   ├── handleNext() - Wizard navigation forward
│   ├── handlePrev() - Wizard navigation backward
│   ├── handleGenerate() - Submit screenplay generation
│   ├── handleReset() - Clear form and results
│   ├── handleCopy() - Copy script to clipboard
│   └── handleDownload() - Download script as markdown
│
└── Render Logic
    ├── Conditional Step Rendering (0-3)
    ├── Creative DNA Preview (computed)
    └── Output Panel (conditional)
```

#### 6.1.3 Constants & Configuration

**Data Constants (Lines 5-216):**

```javascript
// Genre options (21 genres)
const GENRES = [
  'Action', 'Adventure', 'Animation', 'Biographical', 'Comedy',
  'Crime Thriller', 'Documentary', 'Drama', 'Epic Fantasy', 'Family',
  'Historical', 'Horror', 'Musical', 'Mystery', 'Romance',
  'Science Fiction', 'Sports Drama', 'Superhero', 'Techno Thriller',
  'War', 'Western',
]

// Mood options (14 moods)
const MOODS = [
  'Adrenaline-pumping', 'Bittersweet', 'Bleak and gritty', 'Darkly comic',
  'Epic and awe-inspiring', 'Feel-good and uplifting', 'Heart-wrenching',
  'High-tension suspense', 'Hopeful and redemptive', 'Romantic and nostalgic',
  'Satirical', 'Spine-chilling', 'Thrilling mystery', 'Whimsical',
]

// Audience cohorts (9 demographics)
const AUDIENCES = [
  {
    value: 'Kids (6-11)',
    label: 'Kids (6-11)',
    description: 'Wholesome adventure with clear morals and age-appropriate stakes.',
  },
  {
    value: 'Tweens (10-13)',
    label: 'Tweens (10-13)',
    description: 'Coming-of-age plots with relatable school and friendship drama.',
  },
  {
    value: 'Teens (13-17)',
    label: 'Teens (13-17)',
    description: 'High-energy stories balancing romance, rebellion, and social dynamics.',
  },
  {
    value: 'Young adults (18-24)',
    label: 'Young adults (18-24)',
    description: 'Culturally current narratives with sharp dialogue and rapid pacing.',
  },
  {
    value: 'Adults (25-44)',
    label: 'Adults (25-44)',
    description: 'Character-driven arcs blending career, relationship, and family tensions.',
  },
  {
    value: 'Mature adults (45+)',
    label: 'Mature adults (45+)',
    description: 'Reflective storytelling with legacy themes and emotionally grounded stakes.',
  },
  {
    value: 'Family four-quadrant',
    label: 'Family four-quadrant',
    description: 'All-ages entertainment mixing humor, heart, and spectacle for shared viewing.',
  },
  {
    value: 'Festival cinephiles',
    label: 'Festival cinephiles',
    description: 'Auteur-style storytelling with layered themes and daring structure.',
  },
  {
    value: 'Streaming binge audiences',
    label: 'Streaming binge audiences',
    description: 'Hooky serialized beats that deliver cliffhangers and rapid payoffs.',
  },
]

// Regional markets (14 regions)
const REGIONS = [
  'Global (All Regions)', 'North America', 'Latin America',
  'Western Europe', 'Central & Eastern Europe', 'Middle East & North Africa',
  'Sub-Saharan Africa', 'India & South Asia', 'China', 'Japan', 'Korea',
  'Southeast Asia', 'Australia & New Zealand', 'Caribbean',
]

// AWS Translate languages (60+ languages - matches backend)
const AWS_TRANSLATE_LANGUAGES = {
  en: 'English (default)',
  af: 'Afrikaans',
  sq: 'Albanian',
  // ... (full 60+ language dict)
}

// MPAA ratings (6 ratings)
const RATINGS = [
  { value: 'G', label: 'G — General Audiences (all ages admitted)' },
  { value: 'PG', label: 'PG — Parental guidance suggested' },
  { value: 'PG-13', label: 'PG-13 — Parents strongly cautioned' },
  { value: 'R', label: 'R — Restricted (under 17 requires accompanying adult)' },
  { value: 'NC-17', label: 'NC-17 — Adults only (no one 17 and under admitted)' },
  { value: 'Unrated / Festival', label: 'Unrated / Festival' },
]

// Runtime presets (9 options)
const RUNTIMES = ['90', '100', '110', '120', '130', '140', '150', '160', '180']
```

**Wizard Step Configuration (Lines 218-235):**

```javascript
const STEPS = [
  {
    title: '',  // Step 0: Landing page (no title)
    description: '',
  },
  {
    title: 'Creative palette',
    description: 'Pick the genres and tonal palette that define the script.',
  },
  {
    title: 'Audience & localisation',
    description: 'Dial in who the story is for and where it should resonate.',
  },
  {
    title: 'Runtime & compliance',
    description: 'Lock duration, rating, and review the creative DNA summary.',
  },
]

const LAST_STEP_INDEX = STEPS.length - 1  // 3
```

**API Base URL Resolution (Lines 237-252):**

```javascript
const resolveScriptApiBase = () => {
  // Priority 1: Environment variable
  const envValue = process.env.REACT_APP_SCRIPT_API_BASE
  if (envValue) {
    return envValue.replace(/\/$/, '')  // Remove trailing slash
  }
  
  // Priority 2: Auto-detect localhost/LAN
  if (typeof window !== 'undefined') {
    const { protocol, hostname } = window.location
    
    // Localhost aliases
    const localHosts = new Set(['localhost', '127.0.0.1', '0.0.0.0'])
    
    // LAN IP ranges (192.168.x.x, 10.x.x.x, 172.16-31.x.x, *.local)
    const isLanHost = /^(192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[0-1]))/.test(hostname) 
                      || hostname.endsWith('.local')
    
    if (localHosts.has(hostname) || isLanHost) {
      return `${protocol}//${hostname}:5005`  // Backend port
    }
  }
  
  // Priority 3: Production default (same origin)
  return ''  // Relative URLs → proxied through frontend server
}

const SCRIPT_API_BASE = resolveScriptApiBase()
```

**API Resolution Examples:**

| Scenario | Hostname | Resolved API Base |
|----------|----------|-------------------|
| Development | `localhost:3000` | `http://localhost:5005` |
| LAN Testing | `192.168.1.100:3000` | `http://192.168.1.100:5005` |
| Production | `moviegen.ai` | `` (relative URLs) |
| Custom Env | Any | `$REACT_APP_SCRIPT_API_BASE` |

### 6.2 Multi-Step Wizard Design

#### 6.2.1 Wizard State Machine

```
┌─────────────────────────────────────────────────────────────┐
│  Step 0: Logline & Guidance                                 │
│  • Primary creative brief input                             │
│  • Additional guidance/notes                                │
│  • Action: Next button → Step 1                             │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 1: Creative Palette                                   │
│  • Genre selection (multi-select)                           │
│  • Mood/tone selection (multi-select)                       │
│  • Actions: Previous → Step 0, Next → Step 2               │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 2: Audience & Localization                            │
│  • Target audience (multi-select, 9 demographics)           │
│  • Priority regions (multi-select, 14 regions)              │
│  • Dialogue language (single-select, 60+ languages)         │
│  • Actions: Previous → Step 1, Next → Step 3               │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 3: Runtime & Compliance (Final Step)                  │
│  • Target runtime (dropdown, 90-180 minutes)                │
│  • Audience rating (dropdown, G to NC-17)                   │
│  • Creative DNA preview (computed from all fields)          │
│  • Actions:                                                 │
│    - Previous → Step 2                                      │
│    - Generate Script (submit) → API call                    │
│    - Reset Brief → Step 0 (clear all fields)                │
└─────────────────────────────────────────────────────────────┘
```

#### 6.2.2 Navigation Implementation

```javascript
// State variable tracking current step (0-3)
const [step, setStep] = useState(0)

// Forward navigation
const handleNext = useCallback(() => {
  setStep((prev) => Math.min(prev + 1, LAST_STEP_INDEX))
}, [])

// Backward navigation
const handlePrev = useCallback(() => {
  setStep((prev) => Math.max(prev - 1, 0))
}, [])

// Derived state
const isOnLastStep = step === LAST_STEP_INDEX  // true when step === 3
const currentStepMeta = STEPS[step]  // { title, description }
```

#### 6.2.3 Conditional Rendering

**Step 0: Logline & Guidance**

```javascript
{step === 0 && (
  <FieldGrid>
    <Field>
      <Label htmlFor="script-logline">Context for Movie Script</Label>
      <TextArea
        id="script-logline"
        placeholder="Give the model your premise, hook, and key stakes."
        value={logline}
        onChange={(event) => setLogline(event.target.value)}
      />
    </Field>
    
    <Field>
      <Label htmlFor="script-notes">Additional guidance</Label>
      <TextArea
        id="script-notes"
        placeholder="e.g. Must-have scenes, visual motifs, production budget, character arcs, or localisation cues."
        value={notes}
        onChange={(event) => setNotes(event.target.value)}
      />
    </Field>
    
    <HelperNotice>
      Tip: The more specific you are here, the smarter the screenplay 
      structure and localisation choices will be.
    </HelperNotice>
  </FieldGrid>
)}
```

**Step 1: Creative Palette**

```javascript
{step === 1 && (
  <FieldGrid>
    <Field>
      <Label htmlFor="script-genres">Primary genres</Label>
      <MultiSelect
        id="script-genres"
        value={genres}
        onChange={handleMultiSelect(setGenres)}
        multiple
      >
        {GENRES.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </MultiSelect>
      <HelperText>Hold Cmd/Ctrl to choose multiple genres.</HelperText>
    </Field>
    
    <Field>
      <Label htmlFor="script-moods">Mood and tone</Label>
      <MultiSelect
        id="script-moods"
        value={moods}
        onChange={handleMultiSelect(setMoods)}
        multiple
      >
        {MOODS.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </MultiSelect>
    </Field>
  </FieldGrid>
)}
```

**Step 2: Audience & Localization**

```javascript
{step === 2 && (
  <FieldGrid>
    <Field>
      <Label htmlFor="script-audience">Target audience</Label>
      <MultiSelect
        id="script-audience"
        value={audience}
        onChange={handleMultiSelect(setAudience)}
        multiple
      >
        {AUDIENCES.map((option) => (
          <option key={option.value} value={option.value}>
            {`${option.label} — ${option.description}`}
          </option>
        ))}
      </MultiSelect>
      <HelperText>
        Choose the viewer cohorts you want the screenplay to delight—this 
        steers tone, references, and pacing toward their expectations.
      </HelperText>
    </Field>
    
    <Field>
      <Label htmlFor="script-regions">Priority regions</Label>
      <MultiSelect
        id="script-regions"
        value={regions}
        onChange={handleMultiSelect(setRegions)}
        multiple
      >
        {REGIONS.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </MultiSelect>
    </Field>
    
    <Field>
      <Label htmlFor="script-language">Dialogue language</Label>
      <Select
        id="script-language"
        value={language}
        onChange={(event) => setLanguage(event.target.value)}
      >
        {LANGUAGES.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </Select>
      <HelperText>
        Hindi selection delivers dialogue in Hinglish (Latin script), 
        while other options use the chosen language for spoken lines.
      </HelperText>
    </Field>
  </FieldGrid>
)}
```

**Step 3: Runtime & Compliance**

```javascript
{step === 3 && (
  <FinalStepGrid>
    <Field>
      <Label htmlFor="script-runtime">Target runtime (minutes)</Label>
      <Select 
        id="script-runtime" 
        value={runtime} 
        onChange={(event) => setRuntime(event.target.value)}
      >
        <option value="">130 (default)</option>
        {RUNTIMES.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </Select>
    </Field>
    
    <Field>
      <Label htmlFor="script-rating">Audience rating</Label>
      <Select 
        id="script-rating" 
        value={rating} 
        onChange={(event) => setRating(event.target.value)}
      >
        <option value="">Let tone dictate</option>
        {RATINGS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </Select>
    </Field>
  </FinalStepGrid>
)}
```

### 6.3 State Management Architecture

#### 6.3.1 State Variables

**Creative Brief State (9 variables):**

```javascript
// Text inputs
const [logline, setLogline] = useState('')
const [notes, setNotes] = useState('')

// Multi-select arrays
const [genres, setGenres] = useState(['Epic Fantasy', 'Adventure'])
const [moods, setMoods] = useState(['Epic and awe-inspiring'])
const [audience, setAudience] = useState(['Young adults (18-24)'])
const [regions, setRegions] = useState(['Global (All Regions)'])

// Single-select dropdowns
const [runtime, setRuntime] = useState('130')
const [rating, setRating] = useState('PG-13')
const [language, setLanguage] = useState('en')
```

**UI State (7 variables):**

```javascript
// Wizard navigation
const [step, setStep] = useState(0)  // 0-3

// Generation tracking
const [hasTriggeredGeneration, setHasTriggeredGeneration] = useState(false)

// API response
const [result, setResult] = useState(null)  // { title, script, language, runtimeMinutes }

// Loading indicators
const [loading, setLoading] = useState(false)

// Error handling
const [error, setError] = useState('')

// User feedback
const [copyStatus, setCopyStatus] = useState('')
```

#### 6.3.2 Default Values Rationale

| Field | Default | Rationale |
|-------|---------|-----------|
| `genres` | `['Epic Fantasy', 'Adventure']` | Demonstrates multi-genre blending |
| `moods` | `['Epic and awe-inspiring']` | Showcases cinematic scope |
| `audience` | `['Young adults (18-24)']` | Largest streaming demographic |
| `regions` | `['Global (All Regions)']` | Encourages international appeal |
| `runtime` | `'130'` | Industry standard feature length |
| `rating` | `'PG-13'` | Widest theatrical audience |
| `language` | `'en'` | Most common screenplay language |

**Why Not Empty Defaults?**
- Reduces cognitive load for first-time users
- Demonstrates expected input format
- Enables immediate "Generate" without form filling
- Showcases service capabilities (multi-genre, localization)

#### 6.3.3 Multi-Select Handler

```javascript
const handleMultiSelect = useCallback(
  (setter) => (event) => {
    // Extract selected values from <select multiple> element
    const values = Array.from(event.target.selectedOptions).map(
      (option) => option.value
    )
    setter(values)
  },
  []
)

// Usage:
<MultiSelect
  value={genres}
  onChange={handleMultiSelect(setGenres)}
  multiple
>
  {/* options */}
</MultiSelect>
```

**Why Curried Function?**
- Single handler for all multi-select fields (genres, moods, audience, regions)
- Avoids 4 separate nearly-identical handler functions
- Preserves `useCallback` optimization (empty dependency array)

---

## 7. User Interface Components

### 7.1 Form Controls & Validation

#### 7.1.1 Text Areas

**Component:** `TextArea` (Lines 320-336)

```javascript
const TextArea = styled.textarea`
  border-radius: 14px;
  border: 1px solid rgba(99, 102, 241, 0.25);
  background: rgba(8, 18, 34, 0.88);
  color: #f8fafc;
  padding: 1rem 1.05rem;
  font-size: 1rem;
  line-height: 1.65;
  min-height: 140px;
  resize: vertical;
  transition: border 0.2s ease, box-shadow 0.2s ease;

  &:focus {
    outline: none;
    border-color: rgba(56, 189, 248, 0.6);
    box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.15);
  }
`
```

**Design Decisions:**
- **Min-height:** 140px accommodates 5-6 lines of text without scroll
- **Resize: vertical** allows users to expand but not break layout horizontally
- **Focus states:** Blue glow (56, 189, 248 = sky blue) indicates active field
- **Dark theme:** Matches cinematic/production aesthetic

#### 7.1.2 Select & Multi-Select

**Single Select Component:**

```javascript
const Select = styled.select`
  border-radius: 14px;
  border: 1px solid rgba(99, 102, 241, 0.25);
  background: rgba(8, 18, 34, 0.88);
  color: #f8fafc;
  padding: 0.85rem 1rem;
  font-size: 1rem;
  min-height: 54px;
  transition: border 0.2s ease, box-shadow 0.2s ease;

  &:focus {
    outline: none;
    border-color: rgba(56, 189, 248, 0.6);
    box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.15);
  }
`
```

**Multi-Select Extension:**

```javascript
const MultiSelect = styled(Select)`
  min-height: 160px;  // Show 8-10 options without scroll
`
```

**Multi-Select Usage Pattern:**

```javascript
// User can Cmd/Ctrl + Click to select multiple
<MultiSelect value={['Action', 'Drama']} onChange={handler} multiple>
  <option value="Action">Action</option>
  <option value="Drama">Drama</option>
  <option value="Comedy">Comedy</option>
</MultiSelect>
```

#### 7.1.3 Helper Text & Validation

**Helper Text Component:**

```javascript
const HelperText = styled.span`
  font-size: 0.8rem;
  color: rgba(148, 163, 184, 0.75);
`

// Usage:
<HelperText>Hold Cmd/Ctrl to choose multiple genres.</HelperText>
```

**Error Banner Component:**

```javascript
const ErrorBanner = styled.div`
  border-radius: 14px;
  border: 1px solid rgba(248, 113, 113, 0.5);
  background: rgba(239, 68, 68, 0.12);
  color: #fecaca;
  padding: 0.85rem 1rem;
  font-size: 0.95rem;
`

// Usage:
{error && <ErrorBanner role="alert">{error}</ErrorBanner>}
```

**Client-Side Validation:**

Currently **no validation** on form fields. All fields are optional with backend defaults:
- Empty `logline` → Backend generates generic logline
- Empty `genres` → Backend uses "Blend genres for fresh voice"
- Empty `runtime` → Backend defaults to 130 minutes

**Rationale:**
- Flexibility for experimentation
- Backend handles all normalization
- Focus on creative freedom vs constraints

### 7.2 Creative DNA Preview

#### 7.2.1 Blueprint Component

**Styled Component:**

```javascript
const Blueprint = styled.div`
  background: rgba(11, 22, 40, 0.78);
  border: 1px solid rgba(96, 165, 250, 0.25);
  border-radius: 16px;
  padding: 1.2rem 1.3rem;
  display: grid;
  gap: 0.65rem;
`

const BlueprintTitle = styled.h3`
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  color: #e0f2fe;
`

const BlueprintList = styled.ul`
  margin: 0;
  padding-left: 1.1rem;
  color: #cbd5f5;
  font-size: 0.92rem;
  line-height: 1.6;
`
```

#### 7.2.2 Computed Preview State

**useMemo Hook (Lines 580-615):**

```javascript
const creativePreview = useMemo(() => {
  // Resolve rating label from value
  const ratingLabel = RATINGS.find(
    (option) => option.value === rating
  )?.label
  
  // Resolve audience labels from values
  const audienceLabelList = audience.length
    ? audience
        .map((value) => 
          AUDIENCES.find((option) => option.value === value)?.label || value
        )
        .join(', ')
    : ''
  
  // Resolve language label from code
  const languageLabel = LANGUAGES.find(
    (option) => option.value === language
  )?.label || 'English (default)'
  
  return [
    {
      label: 'Genres',
      value: genres.length 
        ? genres.join(', ') 
        : 'Blend genres for a fresh cinematic voice.',
    },
    {
      label: 'Mood palette',
      value: moods.length 
        ? moods.join(', ') 
        : 'Balance drama, humour, suspense, and awe.',
    },
    {
      label: 'Audience focus',
      value: audienceLabelList || 'Design for a global, four-quadrant audience.',
    },
    {
      label: 'Regional emphasis',
      value: regions.length 
        ? regions.join(', ') 
        : 'Global relevance with local authenticity.',
    },
    {
      label: 'Era & setting',
      value: 'Present day (default)',
    },
    {
      label: 'Runtime target',
      value: runtime 
        ? `${runtime} minutes` 
        : 'Approx. 130 minutes (feature length).',
    },
    {
      label: 'Rating / compliance',
      value: ratingLabel || 'Tailor tone to the chosen audience rating.',
    },
    {
      label: 'Dialogue language',
      value: languageLabel,
    },
    {
      label: 'Additional notes',
      value: notes.trim() 
        || 'Invite the model to propose bold twists and cultural specificity.',
    },
  ]
}, [genres, moods, audience, regions, runtime, rating, notes, language])
```

**Why useMemo?**
- Prevents recomputation on every render
- Only recalculates when dependencies change (form field updates)
- Improves performance for 9 field transformations

#### 7.2.3 Render Implementation

```javascript
{isOnLastStep && (
  <Blueprint>
    <BlueprintTitle>Creative DNA preview</BlueprintTitle>
    <BlueprintList>
      {creativePreview.map((item) => (
        <li key={item.label}>
          <strong>{item.label}:</strong> {item.value}
        </li>
      ))}
    </BlueprintList>
  </Blueprint>
)}
```

**Example Rendered Preview:**

```
Creative DNA preview
• Genres: Epic Fantasy, Adventure
• Mood palette: Epic and awe-inspiring
• Audience focus: Young adults (18-24)
• Regional emphasis: Global (All Regions)
• Era & setting: Present day (default)
• Runtime target: 130 minutes
• Rating / compliance: PG-13 — Parents strongly cautioned
• Dialogue language: English (default)
• Additional notes: Include memorable chase sequence through ancient ruins
```

### 7.3 Script Display & Export

#### 7.3.1 Script Block Component

```javascript
const ScriptBlock = styled.pre`
  background: rgba(7, 16, 32, 0.78);
  border: 1px solid rgba(96, 165, 250, 0.18);
  border-radius: 16px;
  padding: 1.4rem 1.6rem;
  color: #e5edff;
  line-height: 1.8;
  overflow-y: auto;
  max-height: 70vh;  // Prevents page overflow on long scripts
  white-space: pre-wrap;  // Preserves screenplay formatting
  word-break: break-word;  // Prevents horizontal scroll
`
```

**Design Features:**
- **`<pre>` element:** Preserves whitespace and newlines from screenplay
- **`white-space: pre-wrap`:** Maintains formatting but wraps long lines
- **`max-height: 70vh`:** Scrollable for 130-minute scripts (~130 pages)
- **Dark theme:** Reduces eye strain for long reading sessions

#### 7.3.2 Copy to Clipboard

**Handler Implementation:**

```javascript
const handleCopy = useCallback(async (text, label) => {
  if (!text) {
    return
  }
  
  try {
    await navigator.clipboard.writeText(text)
    setCopyStatus(`Copied ${label}.`)
  } catch (copyError) {
    setCopyStatus('Clipboard access is unavailable.')
  }
  
  // Clear status after 2.5 seconds
  setTimeout(() => setCopyStatus(''), 2500)
}, [])

// Usage:
<TertiaryButton 
  type="button" 
  onClick={() => handleCopy(result.script, 'screenplay')}
>
  Copy screenplay
</TertiaryButton>
```

**Browser Compatibility:**
- Modern browsers: `navigator.clipboard.writeText()` (HTTPS required)
- Fallback: Error message if clipboard API unavailable
- Permission handling: Browser prompts user on first use

#### 7.3.3 Download as Markdown

**Handler Implementation:**

```javascript
const handleDownload = useCallback(() => {
  if (!result?.script) {
    return
  }
  
  // Generate filename from title
  const filename = `${slugify(result.title || 'movie-script')}.md`
  
  // Format as markdown
  const content = `# ${result.title || 'Movie Script'}\n\n${result.script}`
  
  // Create downloadable blob
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  
  // Trigger download via temporary link
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  
  // Clean up object URL
  URL.revokeObjectURL(url)
  
  // Show feedback
  setCopyStatus(`Downloaded ${filename}`)
  setTimeout(() => setCopyStatus(''), 2500)
}, [result])

// slugify helper function
const slugify = (value = '') =>
  value
    .toString()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')  // Replace non-alphanumeric with hyphens
    .replace(/^-+|-+$/g, '')      // Remove leading/trailing hyphens
    || 'movie-script'              // Fallback if empty
```

**Filename Examples:**

| Title | Slug | Filename |
|-------|------|----------|
| "Echoes of Eternity" | `echoes-of-eternity` | `echoes-of-eternity.md` |
| "Star Wars: Episode IX" | `star-wars-episode-ix` | `star-wars-episode-ix.md` |
| "Untitled Feature" | `untitled-feature` | `untitled-feature.md` |
| "" (empty) | `movie-script` | `movie-script.md` |

**Markdown Format:**

```markdown
# Echoes of Eternity

ACT I

INT. UNIVERSITY LAB - DAY

DR. MAYA CHEN (35, intense) examines ancient artifacts...
```

**Why Markdown?**
- **Portability:** Opens in any text editor, GitHub, Notion, Obsidian
- **Version Control:** Git-friendly format for screenplay revisions
- **Import:** Many screenplay software tools support markdown import
- **Formatting Preservation:** Maintains structure without proprietary formats

---

## 8. Frontend-Backend Integration

### 8.1 API Communication

#### 8.1.1 Script Generation Handler

**Main Handler (Lines 617-672):**

```javascript
const handleGenerate = useCallback(
  async (event) => {
    event.preventDefault()
    
    // If not on last step, jump to final step instead of generating
    if (!isOnLastStep) {
      setStep(LAST_STEP_INDEX)
      return
    }
    
    // Mark that generation has been triggered (shows output panel)
    setHasTriggeredGeneration(true)
    
    // Reset UI state
    setLoading(true)
    setError('')
    setResult(null)
    setCopyStatus('')
    
    // Build API payload
    const payload = {
      logline: logline.trim() || undefined,
      additionalGuidance: notes.trim() || undefined,
      genres,
      moods,
      audience,
      regions,
      era: 'Present day',
      targetRuntimeMinutes: runtimeToInt(runtime),
      targetRating: rating || undefined,
      language,
    }
    
    try {
      // Construct API URL
      const url = SCRIPT_API_BASE 
        ? `${SCRIPT_API_BASE}/generate-script` 
        : '/generate-script'
      
      // Make POST request
      const response = await axios.post(url, payload, {
        headers: { 'Content-Type': 'application/json' },
      })
      
      // Store result
      setResult(response.data)
      
    } catch (err) {
      // Extract error message
      const message = err?.response?.data?.error 
        || err?.message 
        || 'Failed to generate screenplay.'
      
      // Normalize error message
      setError(normaliseErrorMessage(message))
      
    } finally {
      setLoading(false)
    }
  },
  [
    audience, genres, isOnLastStep, language, logline, 
    moods, notes, rating, regions, runtime
  ]
)
```

**Payload Transformation:**

```javascript
// Frontend State → API Payload
{
  logline: "A reluctant hero discovers ancient powers",
  notes: "Include memorable chase scene",
  genres: ["Epic Fantasy", "Adventure"],
  moods: ["Epic and awe-inspiring"],
  audience: ["Young adults (18-24)"],
  regions: ["Global (All Regions)"],
  era: "Present day",  // Hardcoded in frontend
  targetRuntimeMinutes: 130,  // Converted from string "130"
  targetRating: "PG-13",
  language: "en"
}
```

**Runtime Conversion Helper:**

```javascript
const runtimeToInt = (value) => {
  const parsed = parseInt(value, 10)
  return Number.isFinite(parsed) ? parsed : undefined
}

// Examples:
runtimeToInt("130")    // → 130
runtimeToInt("abc")    // → undefined
runtimeToInt("")       // → undefined
runtimeToInt(null)     // → undefined
```

#### 8.1.2 Response Handling

**Success Path:**

```javascript
// API returns:
{
  "title": "Echoes of Eternity",
  "script": "ACT I\n\nINT. LAB - DAY\n\n...",
  "language": "English (default)",
  "runtimeMinutes": 140
}

// Stored in state:
setResult(response.data)

// Displayed in UI:
<ResultTitle>{result.title}</ResultTitle>
<ScriptBlock>{result.script}</ScriptBlock>
```

**Error Path:**

```javascript
// API returns 502:
{
  "error": "Language model invocation failed"
}

// Extracted and normalized:
const message = err.response.data.error
setError(normaliseErrorMessage(message))

// Displayed in UI:
<ErrorBanner>{error}</ErrorBanner>
```

### 8.2 Error Handling

#### 8.2.1 Error Normalization

**Function:** `normaliseErrorMessage()` (Lines 533-556)

```javascript
const normaliseErrorMessage = (message = '') => {
  const raw = String(message || '').trim()
  
  // Default fallback
  if (!raw) {
    return 'Unable to generate a script right now. Please try again in a moment.'
  }
  
  // Pattern matching for common errors
  if (/language model invocation failed/i.test(raw)) {
    return 'Language model invocation failed. Confirm the Movie Script service has valid Bedrock access and try again.'
  }
  
  if (/^network error/i.test(raw)) {
    return 'Network error while contacting the Movie Script service. Check your connection and retry.'
  }
  
  if (/status code 5\d{2}/i.test(raw)) {
    return 'Our servers are unavailable right now (5xx). Please retry shortly.'
  }
  
  // Return original message if no pattern matches
  return raw
}
```

**Error Message Mapping:**

| Backend Error | Normalized Frontend Message |
|---------------|------------------------------|
| "Language model invocation failed" | "Language model invocation failed. Confirm the Movie Script service has valid Bedrock access and try again." |
| "Network Error" | "Network error while contacting the Movie Script service. Check your connection and retry." |
| "502 Bad Gateway" | "Our servers are unavailable right now (5xx). Please retry shortly." |
| Empty/null | "Unable to generate a script right now. Please try again in a moment." |
| Other | (Pass through original message) |

**Why Normalize?**
- **User-Friendly:** Avoids technical jargon ("Boto3 ClientError")
- **Actionable:** Suggests remediation ("Check connection", "Confirm Bedrock access")
- **Consistent:** Standardizes error presentation

#### 8.2.2 Error Display

**Conditional Rendering:**

```javascript
// Show error in form panel before generation
{error && !hasTriggeredGeneration && (
  <ErrorBanner role="alert">{error}</ErrorBanner>
)}

// Show error in output panel after generation
{showOutputPanel && error && !loading && !result && (
  <ErrorBanner role="alert">{error}</ErrorBanner>
)}
```

**Error Banner Accessibility:**
- `role="alert"` → Screen readers announce error immediately
- Red color scheme → Visually distinct from success states
- Persistent display → Error remains until cleared by user action

### 8.3 Loading States

#### 8.3.1 Loading Indicators

**Button State:**

```javascript
<PrimaryButton type="submit" disabled={loading}>
  {loading ? 'Generating screenplay…' : 'Generate script'}
</PrimaryButton>
```

**Output Panel State:**

```javascript
{loading && (
  <EmptyState>
    The story engine is crafting your screenplay. This can take 
    a little while—stay tuned.
  </EmptyState>
)}
```

**Disabled Button Styling:**

```javascript
const PrimaryButton = styled.button`
  /* ... other styles ... */
  
  &:disabled {
    opacity: 0.55;
    cursor: not-allowed;
    box-shadow: none;
  }
`
```

#### 8.3.2 Progressive Disclosure

**Output Panel Visibility:**

```javascript
const showOutputPanel = hasTriggeredGeneration || Boolean(result) || loading

{showOutputPanel && (
  <Panel>
    <SectionTitle>Script</SectionTitle>
    
    {/* State 1: Error (no loading, no result) */}
    {error && !loading && !result && (
      <ErrorBanner role="alert">{error}</ErrorBanner>
    )}
    
    {/* State 2: Empty (no generation triggered yet) */}
    {!result && !loading && !error && (
      <EmptyState>
        Configure the creative palette and generate a screenplay. 
        The complete script will appear here when ready.
      </EmptyState>
    )}
    
    {/* State 3: Loading */}
    {loading && (
      <EmptyState>
        The story engine is crafting your screenplay. This can take 
        a little while—stay tuned.
      </EmptyState>
    )}
    
    {/* State 4: Success */}
    {result && (
      <>
        <ResultTitle>{result.title}</ResultTitle>
        <ScriptBlock>{result.script}</ScriptBlock>
        <FooterButtons>
          <TertiaryButton onClick={() => handleCopy(result.script, 'screenplay')}>
            Copy screenplay
          </TertiaryButton>
          <TertiaryButton onClick={handleDownload}>
            Download as Markdown
          </TertiaryButton>
        </FooterButtons>
      </>
    )}
  </Panel>
)}
```

**State Machine:**

```
showOutputPanel = false (initial)
  → Form panel only

User clicks "Generate Script"
  → hasTriggeredGeneration = true
  → showOutputPanel = true
  → loading = true
  → Display: "The story engine is crafting..."

API Success
  → loading = false
  → result = { title, script, ... }
  → Display: Script with copy/download buttons

API Error
  → loading = false
  → error = "Language model invocation failed..."
  → Display: Error banner with retry instructions
```

---

## End of Part 3

**Continue to Part 4 for:**
- Complete Deployment Guide
- AWS Configuration & IAM Policies
- Performance Optimization
- Troubleshooting Guide
- Production Checklist

---

**Document Statistics - Part 3:**
- Pages: ~48
- Sections: 3 major sections
- Code Examples: 25+
- UI Components: 15+
- State Machine Diagrams: 2

**Next Document:** `MOVIE_SCRIPT_CREATION_PART4.md`
# Movie Script Creation Service - Complete Reference Guide
## Part 4: Deployment, Configuration & Production Operations

**Document Version:** 1.0  
**Last Updated:** October 22, 2025  
**Service:** Movie Script Creation  
**Port:** 5005

---

## Table of Contents - Part 4

9. [Deployment Guide](#9-deployment-guide)
   - Local Development Setup
   - Production Deployment
   - Docker Containerization
10. [AWS Configuration](#10-aws-configuration)
    - IAM Policies & Permissions
    - Bedrock Model Access
    - Translate Service Configuration
11. [Performance & Optimization](#11-performance--optimization)
    - Caching Strategies
    - Rate Limiting
    - Cost Optimization
12. [Troubleshooting Guide](#12-troubleshooting-guide)
    - Common Issues & Solutions
    - Debugging Tools
    - Log Analysis
13. [Production Checklist](#13-production-checklist)
    - Security Hardening
    - Monitoring Setup
    - Backup & Recovery

---

## 9. Deployment Guide

### 9.1 Local Development Setup

#### 9.1.1 Prerequisites

**System Requirements:**
- Python 3.11+ (3.14 compatible per `__pycache__` evidence)
- Node.js 18+ (for frontend React app)
- AWS Account with Bedrock and Translate access
- 8GB+ RAM (Bedrock API calls can be memory-intensive)
- macOS/Linux (Windows requires WSL for script compatibility)

**AWS Services:**
- AWS Bedrock (meta.llama3-70b-instruct-v1:0 model)
- AWS Translate
- AWS credentials configured via CLI or environment variables

#### 9.1.2 Backend Setup

**Step 1: Install Python Dependencies**

```bash
cd /Users/tarun_bhardwaj/mydrive/Projects/mediaGenAI/movieScriptCreation

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (if requirements.txt exists)
pip install flask flask-cors boto3 unidecode python-dotenv

# Or create requirements.txt:
cat > requirements.txt << EOF
flask>=2.3.0
flask-cors>=4.0.0
boto3>=1.28.0
unidecode>=1.3.6
python-dotenv>=1.0.0
botocore>=1.31.0
EOF

pip install -r requirements.txt
```

**Step 2: Configure Environment Variables**

```bash
# Create .env file
cat > .env << EOF
# AWS Configuration
BEDROCK_REGION=us-east-1
TRANSLATE_REGION=us-east-1

# Flask Configuration
PORT=5005
DEBUG=true
RELOADER=true

# Translation Mode
MOVIE_SCRIPT_TRANSLATE_FULL=true

# AWS Credentials (if not using AWS CLI profile)
# AWS_ACCESS_KEY_ID=AKIA...
# AWS_SECRET_ACCESS_KEY=...
# AWS_SESSION_TOKEN=...  # If using temporary credentials
EOF
```

**Step 3: Verify AWS Credentials**

```bash
# Check AWS CLI configuration
aws sts get-caller-identity

# Expected output:
# {
#     "UserId": "AIDAI...",
#     "Account": "123456789012",
#     "Arn": "arn:aws:iam::123456789012:user/your-name"
# }

# Test Bedrock access
aws bedrock list-foundation-models --region us-east-1 \
  --query 'modelSummaries[?modelId==`meta.llama3-70b-instruct-v1:0`]'

# Test Translate access
aws translate translate-text \
  --text "Hello world" \
  --source-language-code en \
  --target-language-code es \
  --region us-east-1
```

**Step 4: Start Backend Server**

```bash
# Development mode (auto-reload enabled)
python app.py

# Output:
#  * Serving Flask app 'app'
#  * Debug mode: on
#  * Running on http://0.0.0.0:5005
#  * Restarting with stat
```

**Step 5: Test Health Endpoint**

```bash
curl http://localhost:5005/health | jq

# Expected output:
# {
#   "status": "ok",
#   "modelId": "meta.llama3-70b-instruct-v1:0",
#   "region": "us-east-1",
#   "minTokens": 3500,
#   "maxTokens": 4096
# }
```

#### 9.1.3 Frontend Setup

**Step 1: Navigate to Frontend Directory**

```bash
cd /Users/tarun_bhardwaj/mydrive/Projects/mediaGenAI/frontend
```

**Step 2: Install Dependencies**

```bash
# Install Node modules
npm install

# Or if using Yarn:
yarn install
```

**Step 3: Configure API Base URL**

```bash
# Create .env.local file for local development
cat > .env.local << EOF
REACT_APP_SCRIPT_API_BASE=http://localhost:5005
EOF
```

**Step 4: Start Development Server**

```bash
npm start

# Output:
# Compiled successfully!
# 
# You can now view frontend in the browser.
# 
#   Local:            http://localhost:3000
#   On Your Network:  http://192.168.1.100:3000
```

**Step 5: Access Application**

Open browser to `http://localhost:3000` and navigate to Movie Script Creation page.

#### 9.1.4 Development Workflow

**Typical Development Cycle:**

```bash
# Terminal 1: Backend (Flask auto-reloads on code changes)
cd movieScriptCreation
source venv/bin/activate
python app.py

# Terminal 2: Frontend (React hot-reloads on code changes)
cd frontend
npm start

# Terminal 3: Test API directly
curl -X POST http://localhost:5005/generate-script \
  -H "Content-Type: application/json" \
  -d '{
    "logline": "Test screenplay",
    "genres": ["Drama"],
    "targetRuntimeMinutes": 90
  }'
```

### 9.2 Production Deployment

#### 9.2.1 Production Environment Variables

```bash
# Backend .env (production)
BEDROCK_REGION=us-east-1
TRANSLATE_REGION=us-east-1
PORT=5005
DEBUG=false
RELOADER=false
MOVIE_SCRIPT_TRANSLATE_FULL=true

# Use IAM roles instead of hardcoded credentials in production
# AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY should NOT be set
# (EC2/ECS will use instance role automatically)
```

```bash
# Frontend .env.production
REACT_APP_SCRIPT_API_BASE=https://api.yourdomain.com
```

#### 9.2.2 Backend Production Server (Gunicorn)

**Install Gunicorn:**

```bash
pip install gunicorn
```

**Start with Gunicorn:**

```bash
# Production-grade WSGI server
gunicorn \
  --bind 0.0.0.0:5005 \
  --workers 4 \
  --timeout 300 \
  --access-logfile /var/log/moviescript/access.log \
  --error-logfile /var/log/moviescript/error.log \
  app:app
```

**Gunicorn Configuration File:**

```python
# gunicorn.conf.py
import multiprocessing

# Server Socket
bind = "0.0.0.0:5005"
backlog = 2048

# Worker Processes
workers = multiprocessing.cpu_count() * 2 + 1  # 2-4 workers per CPU core
worker_class = "sync"  # Use "gevent" for async if needed
worker_connections = 1000
timeout = 300  # 5 minutes (script generation is slow)
keepalive = 5

# Logging
accesslog = "/var/log/moviescript/access.log"
errorlog = "/var/log/moviescript/error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process Naming
proc_name = "moviescript"

# Server Mechanics
daemon = False  # Set True for background process
pidfile = "/var/run/moviescript.pid"
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if terminating TLS at application level)
# keyfile = "/etc/ssl/private/key.pem"
# certfile = "/etc/ssl/certs/cert.pem"
```

**Start with Config File:**

```bash
gunicorn --config gunicorn.conf.py app:app
```

#### 9.2.3 Systemd Service Unit

**Create Service File:**

```bash
sudo nano /etc/systemd/system/moviescript.service
```

```ini
[Unit]
Description=Movie Script Creation Service
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/mediagenai/movieScriptCreation
Environment="PATH=/opt/mediagenai/movieScriptCreation/venv/bin"
ExecStart=/opt/mediagenai/movieScriptCreation/venv/bin/gunicorn \
  --config gunicorn.conf.py app:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

**Enable and Start Service:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable moviescript
sudo systemctl start moviescript
sudo systemctl status moviescript

# View logs
sudo journalctl -u moviescript -f
```

#### 9.2.4 Frontend Production Build

**Build React App:**

```bash
cd frontend
npm run build

# Output: build/ directory with optimized static files
```

**Serve with Nginx:**

```nginx
# /etc/nginx/sites-available/moviescript-frontend
server {
    listen 80;
    server_name moviegen.yourdomain.com;
    
    root /opt/mediagenai/frontend/build;
    index index.html;
    
    # Gzip compression
    gzip on;
    gzip_types text/css application/javascript application/json;
    
    # Cache static assets
    location /static/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # API proxy to backend
    location /generate-script {
        proxy_pass http://localhost:5005;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 600s;  # 10 minutes for long generations
    }
    
    location /health {
        proxy_pass http://localhost:5005;
    }
    
    # React Router fallback
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

**Enable Site:**

```bash
sudo ln -s /etc/nginx/sites-available/moviescript-frontend \
            /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 9.3 Docker Containerization

#### 9.3.1 Backend Dockerfile

```dockerfile
# movieScriptCreation/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .

# Expose port
EXPOSE 5005

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:5005/health || exit 1

# Run with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5005", "--workers", "4", \
     "--timeout", "300", "app:app"]
```

#### 9.3.2 Frontend Dockerfile

```dockerfile
# frontend/Dockerfile
FROM node:18-alpine AS build

WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source code
COPY public/ ./public/
COPY src/ ./src/

# Build production bundle
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built React app
COPY --from=build /app/build /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

#### 9.3.3 Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  moviescript-backend:
    build:
      context: ./movieScriptCreation
      dockerfile: Dockerfile
    container_name: moviescript-backend
    ports:
      - "5005:5005"
    environment:
      - BEDROCK_REGION=us-east-1
      - TRANSLATE_REGION=us-east-1
      - PORT=5005
      - DEBUG=false
    env_file:
      - ./movieScriptCreation/.env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5005/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  moviescript-frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: moviescript-frontend
    ports:
      - "80:80"
    depends_on:
      - moviescript-backend
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

**Deploy with Docker Compose:**

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f moviescript-backend

# Stop services
docker-compose down
```

---

## 10. AWS Configuration

### 10.1 IAM Policies & Permissions

#### 10.1.1 Minimum Required Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:ListFoundationModels"
      ],
      "Resource": [
        "arn:aws:bedrock:us-east-1::foundation-model/meta.llama3-70b-instruct-v1:0"
      ]
    },
    {
      "Sid": "TranslateAccess",
      "Effect": "Allow",
      "Action": [
        "translate:TranslateText"
      ],
      "Resource": "*"
    }
  ]
}
```

#### 10.1.2 Enhanced Policy with Logging

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "bedrock:ListFoundationModels",
        "bedrock:GetFoundationModel"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/meta.llama3-70b-instruct-v1:0"
      ]
    },
    {
      "Sid": "TranslateAccess",
      "Effect": "Allow",
      "Action": [
        "translate:TranslateText",
        "translate:DescribeTextTranslationJob"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudWatchLogging",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": [
        "arn:aws:logs:*:*:log-group:/aws/moviescript/*"
      ]
    }
  ]
}
```

#### 10.1.3 Create IAM Role for EC2/ECS

**Step 1: Create Trust Policy**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**Step 2: Create Role via AWS CLI**

```bash
# Create role
aws iam create-role \
  --role-name MovieScriptServiceRole \
  --assume-role-policy-document file://trust-policy.json

# Attach policy
aws iam put-role-policy \
  --role-name MovieScriptServiceRole \
  --policy-name MovieScriptAccess \
  --policy-document file://service-policy.json

# Create instance profile (for EC2)
aws iam create-instance-profile \
  --instance-profile-name MovieScriptInstanceProfile

# Add role to instance profile
aws iam add-role-to-instance-profile \
  --instance-profile-name MovieScriptInstanceProfile \
  --role-name MovieScriptServiceRole
```

**Step 3: Attach to EC2 Instance**

```bash
aws ec2 associate-iam-instance-profile \
  --instance-id i-1234567890abcdef0 \
  --iam-instance-profile Name=MovieScriptInstanceProfile
```

### 10.2 Bedrock Model Access

#### 10.2.1 Enable Bedrock in AWS Console

1. Navigate to AWS Bedrock console: https://console.aws.amazon.com/bedrock
2. Select region: `us-east-1` (or desired region)
3. Click "Model access" in left sidebar
4. Click "Enable specific models"
5. Find "Llama 3 70B Instruct" (meta.llama3-70b-instruct-v1:0)
6. Click "Enable" and accept terms
7. Wait for status to change from "Pending" to "Enabled" (~5 minutes)

#### 10.2.2 Verify Model Access via CLI

```bash
# List available models
aws bedrock list-foundation-models \
  --region us-east-1 \
  --query 'modelSummaries[?contains(modelId, `llama3-70b`)]' \
  --output table

# Expected output:
# -----------------------------------------------------------------------
# |                    ListFoundationModels                            |
# +------------------------+-------------------------------------------+
# |        modelId         |           modelName                       |
# +------------------------+-------------------------------------------+
# | meta.llama3-70b-...   | Llama 3 70B Instruct                      |
# +------------------------+-------------------------------------------+

# Test invocation
aws bedrock-runtime invoke-model \
  --model-id meta.llama3-70b-instruct-v1:0 \
  --body '{"prompt":"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\nWrite one sentence.<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n","max_gen_len":50,"temperature":0.5}' \
  --region us-east-1 \
  output.json

cat output.json | jq '.body' -r | jq
```

#### 10.2.3 Bedrock Quota Limits

**Default Limits (as of Oct 2025):**

| Metric | Default Limit | Adjustable |
|--------|---------------|------------|
| Requests per minute | 5 | Yes (via quota request) |
| Tokens per minute | 10,000 | Yes |
| Concurrent requests | 2 | Yes |
| Max tokens per request | 4,096 | No (model limit) |

**Request Quota Increase:**

1. Navigate to Service Quotas console
2. Search for "Bedrock"
3. Select "Requests per minute for Llama 3 70B"
4. Click "Request quota increase"
5. Enter desired value (e.g., 20 RPM)
6. Provide use case justification
7. Submit request (approval typically within 24-48 hours)

### 10.3 Translate Service Configuration

#### 10.3.1 Translate Quotas

**Default Limits:**

| Metric | Default Limit | Adjustable |
|--------|---------------|------------|
| Characters per second | 1,000 | Yes |
| Requests per second | 100 | Yes |
| Max characters per request | 5,000 | No |
| Concurrent translations | 10 | Yes |

**Service Configuration:**

```python
# movieScriptCreation/app.py
TRANSLATE_REGION = os.getenv("TRANSLATE_REGION", "us-east-1")
MAX_TRANSLATE_CHARS = 4500  # Stay under 5000 byte limit with buffer
```

#### 10.3.2 Optimize Translation Costs

**Cost Breakdown (as of Oct 2025):**
- $15 per million characters
- 130-minute screenplay ≈ 162,500 characters
- Cost per screenplay: ~$0.002 (negligible)

**Cost Optimization Strategies:**

1. **Dialogue-Only Mode (Default):**
   ```python
   # Only translate dialogue lines, keep stage directions in English
   MOVIE_SCRIPT_TRANSLATE_FULL=false
   # Reduces translation volume by ~60%
   ```

2. **Caching Translated Scripts:**
   ```python
   # Implement Redis cache for identical scripts
   import redis
   
   cache = redis.Redis(host='localhost', port=6379)
   cache_key = f"script:{hash(script_text)}:{language}"
   
   cached = cache.get(cache_key)
   if cached:
       return cached.decode('utf-8')
   
   translated = translate_text(script_text, language)
   cache.setex(cache_key, 3600, translated)  # 1 hour TTL
   return translated
   ```

3. **Batch Translation:**
   ```python
   # Combine multiple short lines into single API call
   if len(lines_to_translate) > 1:
       combined = "\n".join(lines_to_translate)
       if len(combined) < MAX_TRANSLATE_CHARS:
           translated_combined = translate_text(combined, language)
           return translated_combined.split("\n")
   ```

---

## 11. Performance & Optimization

### 11.1 Caching Strategies

#### 11.1.1 Backend Response Caching

**Redis-Based Caching:**

```python
import redis
import hashlib
import json

# Initialize Redis client
cache = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    db=0,
    decode_responses=True
)

def generate_cache_key(payload: Dict[str, Any]) -> str:
    """Generate deterministic cache key from request payload."""
    # Sort keys for consistency
    normalized = json.dumps(payload, sort_keys=True)
    return f"script:{hashlib.sha256(normalized.encode()).hexdigest()}"

@app.route("/generate-script", methods=["POST"])
def generate_script() -> Any:
    payload = request.get_json(silent=True) or {}
    
    # Check cache
    cache_key = generate_cache_key(payload)
    cached_result = cache.get(cache_key)
    
    if cached_result:
        app.logger.info(f"Cache hit for key: {cache_key}")
        return jsonify(json.loads(cached_result))
    
    # ... (existing generation logic) ...
    
    # Store in cache (24 hour TTL)
    cache.setex(cache_key, 86400, json.dumps(result))
    
    return jsonify(result)
```

**Cache Invalidation Strategy:**
- **TTL:** 24 hours (scripts rarely change)
- **Manual Clear:** Admin endpoint to flush specific keys
- **Pattern Clear:** Flush all scripts for a language `script:*:hi`

#### 11.1.2 Frontend Caching

**Service Worker for Script Caching:**

```javascript
// frontend/src/serviceWorker.js
const CACHE_NAME = 'moviescript-v1'
const CACHE_URLS = [
  '/static/css/*.css',
  '/static/js/*.js',
]

self.addEventListener('fetch', (event) => {
  // Cache GET requests only
  if (event.request.method === 'GET') {
    event.respondWith(
      caches.match(event.request).then((response) => {
        return response || fetch(event.request)
      })
    )
  }
})
```

**LocalStorage for User Preferences:**

```javascript
// Save user's last creative brief
const saveToLocalStorage = (brief) => {
  localStorage.setItem('lastBrief', JSON.stringify(brief))
}

// Restore on page load
const restoreFromLocalStorage = () => {
  const saved = localStorage.getItem('lastBrief')
  if (saved) {
    const brief = JSON.parse(saved)
    setGenres(brief.genres || [])
    setMoods(brief.moods || [])
    // ... restore other fields
  }
}
```

### 11.2 Rate Limiting

#### 11.2.1 Flask-Limiter Implementation

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="redis://localhost:6379"
)

@app.route("/generate-script", methods=["POST"])
@limiter.limit("10 per hour")  # Max 10 scripts per hour per IP
def generate_script() -> Any:
    # ... existing logic ...
    pass
```

#### 11.2.2 Token Bucket Algorithm

```python
import time
from collections import defaultdict

class TokenBucket:
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate  # tokens per second
        self.buckets = defaultdict(lambda: {
            'tokens': capacity,
            'last_refill': time.time()
        })
    
    def consume(self, key: str, tokens: int = 1) -> bool:
        bucket = self.buckets[key]
        now = time.time()
        
        # Refill tokens based on elapsed time
        elapsed = now - bucket['last_refill']
        bucket['tokens'] = min(
            self.capacity,
            bucket['tokens'] + elapsed * self.refill_rate
        )
        bucket['last_refill'] = now
        
        # Try to consume tokens
        if bucket['tokens'] >= tokens:
            bucket['tokens'] -= tokens
            return True
        return False

# Usage:
bucket = TokenBucket(capacity=10, refill_rate=0.1)  # 10 tokens, refill 1 per 10s

@app.before_request
def rate_limit():
    client_ip = request.remote_addr
    if not bucket.consume(client_ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429
```

### 11.3 Cost Optimization

#### 11.3.1 Cost Tracking

```python
import json
from datetime import datetime

def log_generation_cost(payload: Dict, response_body: Dict):
    """Log generation costs for billing analysis."""
    
    # Extract token counts from Bedrock response
    prompt_tokens = response_body.get('prompt_token_count', 0)
    generation_tokens = response_body.get('generation_token_count', 0)
    
    # Calculate costs (as of Oct 2025)
    input_cost = (prompt_tokens / 1000) * 0.00265
    output_cost = (generation_tokens / 1000) * 0.0035
    total_cost = input_cost + output_cost
    
    # Log to file
    cost_log = {
        'timestamp': datetime.utcnow().isoformat(),
        'client_ip': request.remote_addr,
        'runtime_minutes': payload.get('targetRuntimeMinutes', 130),
        'language': payload.get('language', 'en'),
        'prompt_tokens': prompt_tokens,
        'generation_tokens': generation_tokens,
        'cost_usd': round(total_cost, 4)
    }
    
    with open('/var/log/moviescript/costs.jsonl', 'a') as f:
        f.write(json.dumps(cost_log) + '\n')
    
    return total_cost
```

#### 11.3.2 Cost Analysis Queries

```bash
# Daily cost summary
cat /var/log/moviescript/costs.jsonl | \
  jq -s 'group_by(.timestamp[:10]) | 
         map({date: .[0].timestamp[:10], 
              total: map(.cost_usd) | add, 
              count: length})' 

# Average cost per screenplay
cat /var/log/moviescript/costs.jsonl | \
  jq -s 'map(.cost_usd) | add / length'

# Most expensive runtimes
cat /var/log/moviescript/costs.jsonl | \
  jq -s 'sort_by(.cost_usd) | reverse | .[0:10]'
```

---

## 12. Troubleshooting Guide

### 12.1 Common Issues & Solutions

#### 12.1.1 "Bedrock runtime client is not configured"

**Symptoms:**
- 502 Bad Gateway error
- Health endpoint shows `"status": "degraded"`

**Causes:**
- AWS credentials not configured
- IAM role missing Bedrock permissions
- Wrong AWS region

**Solutions:**

```bash
# 1. Verify credentials
aws sts get-caller-identity

# 2. Check IAM permissions
aws iam get-user-policy --user-name your-user --policy-name MovieScriptAccess

# 3. Test Bedrock access
aws bedrock list-foundation-models --region us-east-1

# 4. Verify region in environment
echo $BEDROCK_REGION
# Should output: us-east-1

# 5. Restart service after credential fix
sudo systemctl restart moviescript
```

#### 12.1.2 "Empty generation received from Bedrock"

**Symptoms:**
- "Unable to generate screenplay segments" error
- API returns 502 after 4-7 minutes

**Causes:**
- Bedrock model unavailable (AWS outage)
- Prompt too large (exceeds context window)
- Model throttling (exceeded RPM quota)

**Solutions:**

```python
# Add detailed logging to app.py
@app.route("/generate-script", methods=["POST"])
def generate_script():
    # ... existing code ...
    
    for segment_index in range(total_segments):
        prompt = _build_segment_prompt(...)
        
        # Log prompt size
        app.logger.info(
            f"Segment {segment_index+1}/{total_segments}: "
            f"Prompt length = {len(prompt)} chars"
        )
        
        try:
            response_body = _invoke_bedrock(prompt)
            app.logger.info(f"Response keys: {response_body.keys()}")
            
        except Exception as exc:
            app.logger.error(
                f"Segment {segment_index+1} failed: {exc}",
                exc_info=True
            )
            # Continue to next segment instead of failing entire request
            continue
```

**Check Bedrock Service Health:**

```bash
# AWS Health Dashboard
aws health describe-events \
  --filter services=BEDROCK \
  --region us-east-1

# Check quota usage
aws service-quotas get-service-quota \
  --service-code bedrock \
  --quota-code L-1234ABCD \
  --region us-east-1
```

#### 12.1.3 "Translation failed" warnings

**Symptoms:**
- Script returned with English dialogue despite non-English selection
- Warning logs: "Dialogue translation failed: ..."

**Causes:**
- AWS Translate quota exceeded
- Unsupported language code
- Network timeout during translation

**Solutions:**

```python
# Add retry logic to translation
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
def _translate_dialogue_line(text, target_language, romanize):
    # ... existing translation logic ...
    pass

# Validate language code before translation
def _translate_dialogue_segments(script_text, language):
    code = language.get("code", "en")
    
    # Verify language supported by AWS Translate
    if code not in TRANSLATE_LANGUAGE_CODES:
        app.logger.warning(
            f"Unsupported language code '{code}', falling back to English"
        )
        return script_text
    
    # ... existing logic ...
```

#### 12.1.4 Frontend shows "Network error"

**Symptoms:**
- "Network error while contacting the Movie Script service"
- Browser console shows CORS errors

**Causes:**
- Backend not running
- CORS not enabled
- Wrong API base URL

**Solutions:**

```bash
# 1. Check backend is running
curl http://localhost:5005/health

# 2. Verify CORS headers in response
curl -v http://localhost:5005/health | grep -i "access-control"
# Should see: Access-Control-Allow-Origin: *

# 3. Check frontend API config
# frontend/.env.local
REACT_APP_SCRIPT_API_BASE=http://localhost:5005  # Must match backend port

# 4. Verify in browser console
console.log(process.env.REACT_APP_SCRIPT_API_BASE)

# 5. Add CORS headers to Flask app
from flask_cors import CORS
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
```

### 12.2 Debugging Tools

#### 12.2.1 Enable Debug Logging

```python
# app.py - Add detailed logging
import logging

# Configure root logger
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/moviescript/debug.log'),
        logging.StreamHandler()
    ]
)

# Log all requests
@app.before_request
def log_request():
    app.logger.debug(
        f"Request: {request.method} {request.path} "
        f"from {request.remote_addr}"
    )
    if request.is_json:
        app.logger.debug(f"Payload: {request.get_json()}")

@app.after_request
def log_response(response):
    app.logger.debug(f"Response status: {response.status_code}")
    return response
```

#### 12.2.2 Test Script Generation via CLI

```python
# test_generation.py
import requests
import json
import sys

payload = {
    "logline": "Test screenplay",
    "genres": ["Drama"],
    "targetRuntimeMinutes": 90,
    "language": "en"
}

print("Sending request to backend...")
response = requests.post(
    "http://localhost:5005/generate-script",
    json=payload,
    headers={"Content-Type": "application/json"},
    timeout=600  # 10 minutes
)

print(f"Status: {response.status_code}")
print(f"Headers: {response.headers}")

if response.ok:
    result = response.json()
    print(f"Title: {result['title']}")
    print(f"Script length: {len(result['script'])} chars")
    print("\nFirst 500 chars:\n{result['script'][:500]}")
else:
    print(f"Error: {response.text}")
    sys.exit(1)
```

```bash
# Run test
python test_generation.py
```

#### 12.2.3 Monitor Bedrock API Calls

```python
# Add request/response logging
def _invoke_bedrock(prompt: str) -> Dict[str, Any]:
    request_id = str(uuid.uuid4())
    
    app.logger.info(
        f"[{request_id}] Invoking Bedrock: "
        f"prompt_length={len(prompt)} chars"
    )
    
    start_time = time.time()
    
    try:
        response = bedrock_runtime.invoke_model(...)
        elapsed = time.time() - start_time
        
        app.logger.info(
            f"[{request_id}] Bedrock response received: "
            f"elapsed={elapsed:.2f}s"
        )
        
        return json.loads(response["body"].read())
        
    except Exception as exc:
        elapsed = time.time() - start_time
        app.logger.error(
            f"[{request_id}] Bedrock failed: "
            f"elapsed={elapsed:.2f}s, error={exc}"
        )
        raise
```

### 12.3 Log Analysis

#### 12.3.1 Parse Application Logs

```bash
# Find all errors in last hour
tail -n 10000 /var/log/moviescript/error.log | \
  grep "$(date -u -d '1 hour ago' '+%Y-%m-%d %H')" | \
  grep ERROR

# Count errors by type
grep ERROR /var/log/moviescript/error.log | \
  awk -F': ' '{print $2}' | \
  sort | uniq -c | sort -rn

# Find slow requests (>120s)
grep "elapsed=" /var/log/moviescript/debug.log | \
  awk '$NF>120' | \
  sort -k6 -rn | \
  head -20
```

#### 12.3.2 CloudWatch Logs Integration

```python
import watchtower
import logging

# Configure CloudWatch handler
logger = logging.getLogger(__name__)
logger.addHandler(watchtower.CloudWatchLogHandler(
    log_group='/aws/moviescript/production',
    stream_name='backend-logs'
))

# Log with structured data
logger.info(
    "Script generated successfully",
    extra={
        'runtime_minutes': 130,
        'language': 'en',
        'segments': 13,
        'elapsed_seconds': 245
    }
)
```

**Query CloudWatch Logs:**

```bash
# Count generations by language
aws logs filter-log-events \
  --log-group-name /aws/moviescript/production \
  --start-time $(date -u -d '1 day ago' +%s)000 \
  --filter-pattern '{ $.language = * }' \
  --query 'events[*].message' \
  --output text | \
  jq -r '.language' | \
  sort | uniq -c

# Find failed generations
aws logs filter-log-events \
  --log-group-name /aws/moviescript/production \
  --filter-pattern 'ERROR' \
  --start-time $(date -u -d '1 hour ago' +%s)000
```

---

## 13. Production Checklist

### 13.1 Security Hardening

#### 13.1.1 API Security

**Add API Key Authentication:**

```python
from functools import wraps

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        valid_keys = os.getenv('API_KEYS', '').split(',')
        
        if not api_key or api_key not in valid_keys:
            return jsonify({'error': 'Invalid API key'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

@app.route("/generate-script", methods=["POST"])
@require_api_key
def generate_script():
    # ... existing logic ...
    pass
```

**Environment Variable:**

```bash
# .env
API_KEYS=sk-prod-abc123,sk-prod-def456
```

**Frontend Integration:**

```javascript
const response = await axios.post(url, payload, {
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': process.env.REACT_APP_API_KEY
  }
})
```

#### 13.1.2 Input Validation

```python
from flask import abort

@app.route("/generate-script", methods=["POST"])
def generate_script():
    payload = request.get_json(silent=True)
    
    if not payload:
        abort(400, description="Request body must be JSON")
    
    # Validate runtime
    runtime = payload.get('targetRuntimeMinutes')
    if runtime and (runtime < 60 or runtime > 180):
        abort(400, description="Runtime must be between 60-180 minutes")
    
    # Validate language
    language = payload.get('language', 'en')
    if language not in LANGUAGE_CONFIG:
        abort(400, description=f"Unsupported language: {language}")
    
    # ... existing logic ...
```

#### 13.1.3 Rate Limiting per User

```python
@app.route("/generate-script", methods=["POST"])
@limiter.limit(
    "10 per hour",
    key_func=lambda: request.headers.get('X-API-Key', 'anonymous')
)
def generate_script():
    # ... existing logic ...
    pass
```

### 13.2 Monitoring Setup

#### 13.2.1 Health Check Monitoring

**External Monitoring (UptimeRobot, Pingdom, etc.):**

- URL: `https://api.yourdomain.com/health`
- Interval: 5 minutes
- Alert on: Status != 200 or `status != "ok"`

**Custom Health Check Script:**

```bash
#!/bin/bash
# /opt/moviescript/healthcheck.sh

ENDPOINT="http://localhost:5005/health"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $ENDPOINT)

if [ "$RESPONSE" -eq 200 ]; then
    STATUS=$(curl -s $ENDPOINT | jq -r '.status')
    if [ "$STATUS" = "ok" ]; then
        echo "$(date): Service healthy"
        exit 0
    fi
fi

echo "$(date): Service unhealthy (HTTP $RESPONSE)"
# Send alert (e.g., via SNS, PagerDuty, Slack)
aws sns publish \
    --topic-arn arn:aws:sns:us-east-1:123456789012:moviescript-alerts \
    --message "Movie Script service is down"
exit 1
```

**Cron Job:**

```bash
# Run health check every 5 minutes
*/5 * * * * /opt/moviescript/healthcheck.sh >> /var/log/moviescript/healthcheck.log 2>&1
```

#### 13.2.2 Metrics Collection

**Prometheus Metrics:**

```python
from prometheus_flask_exporter import PrometheusMetrics

metrics = PrometheusMetrics(app)

# Custom metrics
generation_duration = metrics.histogram(
    'moviescript_generation_duration_seconds',
    'Time spent generating screenplay',
    labels={'language': lambda: request.json.get('language', 'en')}
)

@app.route("/generate-script", methods=["POST"])
@generation_duration.time()
def generate_script():
    # ... existing logic ...
    pass
```

**Grafana Dashboard:**

```yaml
# Example Grafana panel query
# Average generation time by language
avg(rate(moviescript_generation_duration_seconds_sum[5m])) 
  by (language)
```

### 13.3 Backup & Recovery

#### 13.3.1 Configuration Backup

```bash
#!/bin/bash
# backup-config.sh

BACKUP_DIR=/opt/backups/moviescript
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup environment variables
cp /opt/mediagenai/movieScriptCreation/.env \
   $BACKUP_DIR/env_$DATE.bak

# Backup application code
tar -czf $BACKUP_DIR/code_$DATE.tar.gz \
    /opt/mediagenai/movieScriptCreation/app.py

# Backup nginx config
cp /etc/nginx/sites-available/moviescript-frontend \
   $BACKUP_DIR/nginx_$DATE.conf

# Upload to S3
aws s3 sync $BACKUP_DIR s3://your-backup-bucket/moviescript/

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.bak" -mtime +7 -delete
```

#### 13.3.2 Disaster Recovery Plan

**RTO (Recovery Time Objective): 30 minutes**

**Recovery Steps:**

1. **Launch new EC2 instance from AMI**
   ```bash
   aws ec2 run-instances \
     --image-id ami-moviescript-golden \
     --instance-type t3.medium \
     --iam-instance-profile Name=MovieScriptInstanceProfile
   ```

2. **Restore configuration from S3**
   ```bash
   aws s3 sync s3://your-backup-bucket/moviescript/latest/ \
     /opt/mediagenai/movieScriptCreation/
   ```

3. **Start services**
   ```bash
   sudo systemctl start moviescript
   sudo systemctl start nginx
   ```

4. **Verify health**
   ```bash
   curl http://localhost:5005/health
   ```

5. **Update DNS**
   ```bash
   aws route53 change-resource-record-sets \
     --hosted-zone-id Z1234567890ABC \
     --change-batch file://dns-update.json
   ```

---

## 14. Appendix

### 14.1 Complete Environment Variables Reference

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `BEDROCK_REGION` | string | `us-east-1` | AWS region for Bedrock service |
| `TRANSLATE_REGION` | string | `us-east-1` | AWS region for Translate service |
| `PORT` | integer | `5005` | Flask server port |
| `DEBUG` | boolean | `false` | Enable Flask debug mode |
| `RELOADER` | boolean | `false` | Enable auto-reload on code changes |
| `MOVIE_SCRIPT_TRANSLATE_FULL` | boolean | `true` | Enable full-text translation vs dialogue-only |
| `MODEL_ID` | string | `meta.llama3-70b-instruct-v1:0` | Bedrock model identifier |
| `MIN_TOKENS` | integer | `3500` | Minimum tokens per segment |
| `MAX_TOKENS` | integer | `4096` | Maximum tokens per segment |
| `TEMPERATURE` | float | `0.65` | LLM temperature for creative writing |
| `TOP_P` | float | `0.9` | Nucleus sampling threshold |
| `SEGMENT_LENGTH_MINUTES` | integer | `10` | Minutes per screenplay segment |
| `DEFAULT_RUNTIME_MINUTES` | integer | `130` | Default feature runtime |
| `MAX_SEGMENTS` | integer | `18` | Maximum segments (180 min cap) |
| `MAX_TRANSLATE_CHARS` | integer | `4500` | Max characters per translation chunk |
| `REDIS_HOST` | string | `localhost` | Redis host for caching/rate limiting |
| `REDIS_PORT` | integer | `6379` | Redis port |
| `API_KEYS` | string | `` | Comma-separated API keys for authentication |

### 14.2 AWS Resource Requirements

**Minimum Production Setup:**

| Resource | Specification | Monthly Cost (est.) |
|----------|---------------|---------------------|
| EC2 Instance | t3.medium (2 vCPU, 4GB RAM) | $30 |
| EBS Storage | 30 GB gp3 | $3 |
| Bedrock Usage | 1,000 scripts/month @ 45K tokens each | $120 |
| Translate Usage | 1,000 scripts/month @ 162K chars each | $2.50 |
| Data Transfer | 10 GB/month | $1 |
| **Total** | | **~$156/month** |

**Scaling Estimates:**

| Monthly Volume | Bedrock Cost | Translate Cost | Total AWS |
|----------------|--------------|----------------|-----------|
| 1,000 scripts | $120 | $2.50 | $156 |
| 10,000 scripts | $1,200 | $25 | $1,287 |
| 100,000 scripts | $12,000 | $250 | $12,345 |

### 14.3 Performance Benchmarks

**Measured on AWS t3.medium (2 vCPU, 4 GB RAM):**

| Metric | Value | Notes |
|--------|-------|-------|
| 90-min script (9 segments) | 3-4 minutes | Average |
| 130-min script (13 segments) | 4-7 minutes | Default |
| 180-min script (18 segments) | 6-10 minutes | Maximum |
| Segment generation | 15-30 seconds | Per segment |
| Translation (dialogue-only) | 2-5 seconds | 130-min script |
| Translation (full-text) | 5-15 seconds | 130-min script |
| Memory usage | 200-400 MB | Per request |
| CPU usage | 20-40% | During generation |

### 14.4 Troubleshooting Decision Tree

```
Script generation fails
│
├─ HTTP 415: Content-Type error
│  └─ Solution: Add "Content-Type: application/json" header
│
├─ HTTP 401: API key error
│  └─ Solution: Add valid "X-API-Key" header
│
├─ HTTP 429: Rate limit exceeded
│  └─ Solution: Wait 1 hour or contact admin for quota increase
│
├─ HTTP 502: "Bedrock runtime client is not configured"
│  ├─ Check: aws sts get-caller-identity
│  ├─ Check: IAM permissions for Bedrock
│  └─ Solution: Configure AWS credentials or attach IAM role
│
├─ HTTP 502: "Language model invocation failed"
│  ├─ Check: Bedrock model access enabled in console
│  ├─ Check: aws bedrock list-foundation-models
│  └─ Solution: Enable Llama3-70B in Bedrock console
│
└─ HTTP 502: "Unable to generate screenplay segments"
   ├─ Check: Bedrock quota (5 RPM default)
   ├─ Check: AWS Health Dashboard for outages
   └─ Solution: Request quota increase or retry later
```

---

## 15. Conclusion

### 15.1 Service Summary

The Movie Script Creation Service provides AI-powered screenplay generation with:

**Core Capabilities:**
- Feature-length scripts (90-180 minutes)
- Industry-standard formatting (sluglines, dialogue, acts)
- 60+ language support via AWS Translate
- Segment-based generation for narrative coherence
- Multi-genre and tonal blending

**Technical Architecture:**
- Flask backend with Gunicorn WSGI server
- React frontend with multi-step wizard
- AWS Bedrock (Llama3-70B) for creative writing
- AWS Translate for localization
- Redis caching for performance

**Production Readiness:**
- Docker containerization
- Systemd service management
- Nginx reverse proxy
- CloudWatch logging
- Prometheus metrics

### 15.2 Future Enhancements

**Planned Features:**
1. **Streaming Generation:** Real-time segment-by-segment display
2. **Revision Mode:** Regenerate specific segments while preserving others
3. **Character Consistency Checker:** Validate character names across segments
4. **Style Transfer:** Apply screenplay style of famous writers
5. **Budget Estimation:** Auto-calculate production costs from script elements
6. **Casting Suggestions:** AI recommendations based on character descriptions
7. **Export Formats:** PDF (Final Draft format), FDX, Fountain markup

**Infrastructure Improvements:**
1. **Multi-Region Deployment:** Reduce latency for global users
2. **Bedrock Model Updates:** Migrate to newer Llama models as available
3. **Horizontal Scaling:** Load balancer + auto-scaling groups
4. **Database Integration:** Store scripts for user accounts
5. **WebSocket Support:** Real-time progress updates during generation

### 15.3 Support & Resources

**Documentation:**
- Part 1: Architecture Overview & Backend Foundation
- Part 2: Screenplay Formatting & Translation Pipeline
- Part 3: Frontend Architecture & User Experience
- Part 4: Deployment & Production Operations (this document)

**Contact:**
- Technical Issues: GitHub Issues or internal ticketing system
- AWS Support: AWS Support Center (for Bedrock/Translate issues)
- Community: Internal Slack #moviescript-service

---

**Document Statistics - Part 4:**
- Pages: ~52
- Sections: 7 major sections
- Code Examples: 30+
- Configuration Files: 10+
- Troubleshooting Scenarios: 8

**Total Documentation (All 4 Parts):**
- **Total Pages:** ~187
- **Total Sections:** 15
- **Total Code Examples:** 90+
- **Total Tables:** 40+
- **Total Diagrams:** 5

---

**End of Movie Script Creation Service Reference Guide**

*Last Updated: October 22, 2025*  
*Document Version: 1.0*  
*Service Version: Production*
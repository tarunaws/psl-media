# Image Creation Service - Complete Reference Guide

**Version:** 1.0  
**Last Updated:** October 21, 2025  
**Service Port:** 5002  
**Technology Stack:** Python 3.11+, Flask, AWS Bedrock (Amazon Nova Canvas), Amazon S3, PIL/Pillow

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [System Components](#system-components)
3. [Backend Architecture](#backend-architecture)
4. [Frontend Architecture](#frontend-architecture)
5. [Data Flow & Processing Pipeline](#data-flow--processing-pipeline)
6. [AWS Integration](#aws-integration)
7. [Key Logic & Algorithms](#key-logic--algorithms)
8. [API Reference](#api-reference)
9. [Configuration](#configuration)
10. [Deployment](#deployment)
11. [Troubleshooting](#troubleshooting)
12. [Performance Optimization](#performance-optimization)

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Browser                             │
│                    (React Frontend - Port 3000)                  │
│                  /movie-poster-generation route                  │
└────────────┬────────────────────────────────────────────────────┘
             │ HTTP/AJAX (axios)
             │ • POST /send_prompt (JSON with prompt text)
             │ • GET /history_list (retrieve past generations)
             │ • GET /history/{timestamp}/original.png
             │ • GET /health (service status)
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Flask Backend Service                         │
│                         (Port 5002)                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Flask Routes & Handlers                      │  │
│  │  • /send_prompt      - Generate image from text prompt   │  │
│  │  • /history_list     - List generated images             │  │
│  │  • /history/<path>   - Serve history files               │  │
│  │  • /health           - Health check                      │  │
│  │  • /contact          - Contact form submission (bonus)   │  │
│  │  • /contact_logs_*   - Contact logs (dev mode)          │  │
│  └────────────┬─────────────────────────────────────────────┘  │
│               │                                                  │
│  ┌────────────▼─────────────────────────────────────────────┐  │
│  │         Core Processing Modules                          │  │
│  │  • Bedrock Client      - AWS Bedrock API calls           │  │
│  │  • S3 Client           - Image upload to S3              │  │
│  │  • Image Extraction    - Parse base64 from response      │  │
│  │  • History Manager     - Local file storage              │  │
│  │  • Thumbnail Generator - PIL/Pillow image processing     │  │
│  └────────────┬─────────────────────────────────────────────┘  │
│               │                                                  │
│  ┌────────────▼─────────────────────────────────────────────┐  │
│  │           File System Storage                            │  │
│  │  • history/{timestamp}/                                  │  │
│  │    ├── original.png    - Full resolution (1024×1024)    │  │
│  │    └── thumbnail.png   - Preview (120×120)              │  │
│  │  • contact_logs/       - Contact submissions (dev)       │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────┬────────────────────────────────────────────────────┘
             │ AWS SDK (boto3)
             │ • Bedrock Runtime API (invoke_model)
             │ • S3 API (put_object, generate_presigned_url)
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        AWS Services                              │
│  ┌─────────────────────────┐  ┌────────────────────────────┐   │
│  │    Amazon Bedrock       │  │       Amazon S3            │   │
│  │   (Nova Canvas v1)      │  │   (Image Storage)          │   │
│  │  • Text-to-Image AI     │  │  • Presigned URLs          │   │
│  │  • 1024×1024 output     │  │  • Public/Private bucket   │   │
│  │  • CFG Scale: 8         │  │  • 1-hour expiration       │   │
│  │  • Premium quality      │  │                            │   │
│  └─────────────────────────┘  └────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **AI-Powered Generation**: Leverages AWS Bedrock's Nova Canvas model for high-quality image synthesis
2. **Dual Storage**: Local history + optional S3 for scalability
3. **Automatic Thumbnails**: PIL-based thumbnail generation for fast gallery loading
4. **Graceful Degradation**: Falls back to local URLs when S3 unavailable
5. **Singleton Clients**: Lazy-loaded, reusable AWS client instances
6. **Contact Form Integration**: Bonus feature with SMTP or dev logging

---

## System Components

### Backend Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Web Framework** | Flask 2.3+ | HTTP request handling, routing |
| **CORS Handler** | Flask-CORS 4.0.0 | Cross-origin resource sharing |
| **AWS SDK** | boto3 ≥1.34.0 | AWS Bedrock & S3 integration |
| **Image Processing** | Pillow 10.4.0 | Thumbnail generation, format conversion |
| **Config Management** | python-dotenv (optional) | Environment variables |
| **Email** | smtplib (stdlib) | Contact form notifications |

### Frontend Components (Integrated in App.js)

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **UI Framework** | React 18.3.0 | Component-based UI |
| **HTTP Client** | axios 1.12.2 | API communication |
| **Styling** | styled-components 6.1.19 | CSS-in-JS styling |
| **Routing** | react-router-dom 6.21.2 | /movie-poster-generation route |

---

## Backend Architecture

### File Structure

```
imageCreation/
├── app.py                        # Flask app entry point (minimal)
├── image_creation_service.py     # Main service logic (554 lines)
├── requirements.txt              # Python dependencies
├── package.json                  # Node metadata (unused)
├── flask.log                     # Runtime logs
├── history/                      # Generated images
│   └── {timestamp}/
│       ├── original.png          # Full resolution
│       └── thumbnail.png         # 120×120 preview
└── contact_logs/                 # Contact form submissions (dev mode)
    └── {timestamp}.json
```

### Core Modules

#### 1. AWS Client Management (Singleton Pattern)

**Purpose**: Lazy-load and reuse AWS clients to avoid repeated session creation

**Implementation**:
```python
_session = boto3.session.Session()
_bedrock_client = None
_s3_client = None

def _get_bedrock_client():
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = _session.client('bedrock-runtime', region_name=BEDROCK_REGION)
    return _bedrock_client

def _get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = _session.client('s3', region_name=S3_REGION, 
                                     config=Config(signature_version='s3v4'))
    return _s3_client
```

**Benefits**:
- Single client instance per process
- Reduced memory footprint
- Faster subsequent requests
- Connection pooling via boto3

**Configuration Variables**:
```python
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
BEDROCK_REGION = os.environ.get('BEDROCK_REGION', AWS_REGION)
S3_REGION = os.environ.get('S3_REGION', AWS_REGION)
S3_BUCKET = os.environ.get('AWS_S3_BUCKET')
```

#### 2. Base64 Image Extraction (`_extract_base64_image`)

**Purpose**: Parse base64-encoded image data from various AWS Bedrock response formats

**Algorithm**:
```python
def _extract_base64_image(payload: dict | list | None) -> str | None:
    if not payload:
        return None
    
    # Try to extract from nested structures
    if isinstance(payload, dict):
        # Check common top-level keys
        for key in ('images', 'artifacts', 'data', 'outputs'):
            if key in payload and isinstance(payload[key], (list, tuple)):
                for entry in payload[key]:
                    candidate = _from_item(entry)
                    if candidate:
                        return candidate
        
        # Check direct item extraction
        direct_candidate = _from_item(payload)
        if direct_candidate:
            return direct_candidate
    
    elif isinstance(payload, (list, tuple)):
        for entry in payload:
            candidate = _from_item(entry)
            if candidate:
                return candidate
    
    return None

def _from_item(item):
    """Extract base64 string from a single item"""
    if isinstance(item, str):
        return item
    
    if isinstance(item, dict):
        # Try multiple key variations
        for key in ('imageBase64', 'image', 'base64', 'image_b64',
                   'bytesBase64Encoded', 'data', 'b64_json', 'imageData'):
            value = item.get(key)
            if value:
                return value
    
    return None
```

**Why This Logic?**

Different AWS Bedrock models return images in varying JSON structures:
- **Nova Canvas**: `{"images": [{"imageBase64": "..."}]}`
- **Stable Diffusion**: `{"artifacts": [{"base64": "..."}]}`
- **Titan Image**: `{"data": "..."}`

This flexible parser handles all formats without hardcoding model-specific logic.

**Error Handling**:
```python
image_base64 = _extract_base64_image(payload)
if not image_base64:
    raise RuntimeError('No image returned from Bedrock response')

try:
    return base64.b64decode(image_base64)
except Exception as exc:
    raise RuntimeError('Failed to decode image bytes from Bedrock response') from exc
```

#### 3. AWS Bedrock Invocation (`_invoke_bedrock`)

**Purpose**: Call Amazon Bedrock to generate images from text prompts

**Request Payload**:
```python
body = json.dumps({
    "taskType": "TEXT_IMAGE",
    "textToImageParams": {
        "text": prompt
    },
    "imageGenerationConfig": {
        "numberOfImages": 1,
        "width": IMAGE_WIDTH,         # 1024
        "height": IMAGE_HEIGHT,       # 1024
        "cfgScale": IMAGE_CFG_SCALE,  # 8.0
        "quality": IMAGE_QUALITY      # "premium"
    }
})
```

**Configuration Parameters**:

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `IMAGE_MODEL_ID` | `amazon.nova-canvas-v1:0` | Bedrock model identifier |
| `IMAGE_WIDTH` | `1024` | Output image width (pixels) |
| `IMAGE_HEIGHT` | `1024` | Output image height (pixels) |
| `IMAGE_CFG_SCALE` | `8.0` | Classifier-Free Guidance scale (adherence to prompt) |
| `IMAGE_QUALITY` | `premium` | Quality preset (standard/premium) |

**CFG Scale Explained**:
- **Lower (3-5)**: More creative, less literal interpretation
- **Medium (7-9)**: Balanced adherence to prompt
- **Higher (10-15)**: Very literal, may reduce creativity

**API Call**:
```python
response = client.invoke_model(
    modelId=IMAGE_MODEL_ID,
    contentType='application/json',
    accept='application/json',
    body=body
)
```

**Response Processing**:
```python
# Handle streaming response body
payload = response.get('body')
if hasattr(payload, 'read'):
    payload = payload.read()

# Decode bytes to string
if isinstance(payload, (bytes, bytearray)):
    payload = payload.decode('utf-8')

# Parse JSON
if isinstance(payload, str):
    payload = json.loads(payload)

# Extract base64 image
image_base64 = _extract_base64_image(payload)
return base64.b64decode(image_base64)
```

**Typical Generation Time**:
- **Standard quality**: 3-5 seconds
- **Premium quality**: 5-8 seconds
- **Complex prompts**: 8-12 seconds

#### 4. S3 Upload with Presigned URLs (`_upload_to_s3`)

**Purpose**: Upload generated images to S3 and create shareable URLs

**Storage Strategy**:
```python
now = datetime.datetime.utcnow()
folder = now.strftime('%Y-%m-%d/%H%M%S')
key = f"moviePoster/{folder}_{uuid.uuid4().hex}.png"
```

**Example Key**: `moviePoster/2025-10-21/142530_a3f8c9d2e5b7.png`

**Upload Process**:
```python
client = _get_s3_client()
client.put_object(
    Bucket=S3_BUCKET,
    Key=key,
    Body=image_bytes,
    ContentType='image/png'
)
```

**Presigned URL Generation**:
```python
url = client.generate_presigned_url(
    ClientMethod='get_object',
    Params={'Bucket': S3_BUCKET, 'Key': key},
    ExpiresIn=3600  # 1 hour
)
return key, url
```

**Why Presigned URLs?**
- No authentication required for frontend
- Time-limited access (security)
- Direct S3 → Browser transfer (faster)
- Automatic HTTPS encryption

**Graceful Degradation**:
```python
try:
    # Try S3 upload
    s3_key, presigned_url = _upload_to_s3(image_bytes)
    image_url = presigned_url
except Exception as exc:
    app.logger.warning("S3 upload failed, falling back to local URL: %s", exc)
    # Fallback to local history URL
    image_url = f"{request.host_url.rstrip('/')}/history/{timestamp}/original.png"
```

#### 5. Local History Management

**Directory Structure**:
```python
def _save_history(image_bytes: bytes, timestamp: str) -> tuple[str, str]:
    _ensure_history_dir()
    subfolder = os.path.join(IMAGE_HISTORY_DIR, timestamp)
    os.makedirs(subfolder, exist_ok=True)
    
    # Save original
    original_path = os.path.join(subfolder, 'original.png')
    with open(original_path, 'wb') as f:
        f.write(image_bytes)
    
    # Generate thumbnail
    thumbnail_path = os.path.join(subfolder, 'thumbnail.png')
    with Image.open(BytesIO(image_bytes)) as img:
        img.thumbnail((120, 120))
        img.save(thumbnail_path)
    
    return original_path, thumbnail_path
```

**PIL Thumbnail Algorithm**:
```python
img.thumbnail((120, 120))
```

This uses PIL's smart thumbnail algorithm:
- Maintains aspect ratio
- Fits within 120×120 box
- Uses high-quality Lanczos resampling
- Example: 1024×768 → 120×90

**History Listing**:
```python
@app.route('/history_list', methods=['GET'])
def history_list():
    history_dir = IMAGE_HISTORY_DIR
    thumbs = []
    if os.path.exists(history_dir):
        server_url = request.host_url.rstrip('/')
        for folder in sorted(os.listdir(history_dir), reverse=True):
            thumb = os.path.join(history_dir, folder, "thumbnail.png")
            orig = os.path.join(history_dir, folder, "original.png")
            if os.path.exists(thumb) and os.path.exists(orig):
                thumbs.append({
                    "thumb": f"{server_url}/history/{folder}/thumbnail.png",
                    "orig": f"{server_url}/history/{folder}/original.png"
                })
    return jsonify(thumbs)
```

**Sort Order**: Newest first (`reverse=True`)

#### 6. Contact Form (Bonus Feature)

**Purpose**: Allow users to submit contact requests with optional SMTP or dev logging

**Dev Mode Check**:
```python
def _email_demo_mode_enabled() -> bool:
    allow_no_smtp = os.environ.get('CONTACT_ALLOW_NO_SMTP', 'true').lower() in ('1', 'true', 'yes')
    smtp_ready = all([
        os.environ.get('SMTP_HOST'),
        os.environ.get('SMTP_USER'),
        os.environ.get('SMTP_PASS')
    ])
    return (not smtp_ready) and allow_no_smtp
```

**Dual Email Strategy**:
1. **Internal Notification** → Admin email with Reply-To set to submitter
2. **Acknowledgment Email** → Submitter with Reply-To set to admin

**SMTP Support**:
- **Port 587**: STARTTLS (most common)
- **Port 465**: SSL/TLS
- **Port 25**: Plain SMTP (legacy)

**Dev Mode Fallback**:
```python
if not smtp_ready and allow_no_smtp:
    # Save to contact_logs/{timestamp}.json
    log_path = os.path.join('contact_logs', f'{timestamp}.json')
    with open(log_path, 'w') as f:
        json.dump({
            'internal': {...},
            'ack': {...},
            'data': data
        }, f, indent=2)
    return jsonify({'ok': True, 'message': 'Received (dev mode)'}), 200
```

---

## Frontend Architecture

### Component Integration (App.js)

The Image Creation service is integrated directly into `App.js` rather than having a separate component file.

**Route Definition**:
```javascript
<Route path="/movie-poster-generation" element={
  <ImageGenPage>
    <ImageGenTitle>Movie Poster Generation</ImageGenTitle>
    {/* Form and display logic */}
  </ImageGenPage>
} />
```

### Key React Hooks & State

```javascript
const [prompt, setPrompt] = useState('');
const [imageUrl, setImageUrl] = useState('');
const [totalTime, setTotalTime] = useState(null);
const [history, setHistory] = useState([]);
const [loading, setLoading] = useState(false);
const historyRef = useRef(null);
const autoScrollTimer = useRef(null);
```

**State Management**:
- `prompt`: User's text input
- `imageUrl`: URL of generated image (S3 or local)
- `totalTime`: Measured generation time (frontend → backend → frontend)
- `history`: Array of past generations
- `loading`: Boolean for button disable and loading text

### Core Logic

#### 1. History Fetching

```javascript
useEffect(() => {
  const url = API_BASE ? `${API_BASE}/history_list` : '/history_list';
  axios.get(url)
    .then(res => setHistory(res.data))
    .catch(() => setHistory([]));
}, [imageUrl]);  // Re-fetch when new image generated
```

**Why Dependency on `imageUrl`?**
- Automatically refreshes history when new image is created
- No manual refresh button needed
- Seamless user experience

#### 2. Image Generation

```javascript
const handleSubmit = async (e) => {
  e.preventDefault();
  setLoading(true);
  const start = Date.now();
  
  try {
    const url = API_BASE ? `${API_BASE}/send_prompt` : '/send_prompt';
    const res = await axios.post(url, { prompt }, {
      headers: { 'Content-Type': 'application/json' }
    });
    
    setImageUrl(res.data.image_url);
    setTotalTime(((Date.now() - start) / 1000).toFixed(2));
  } catch {
    setImageUrl('');
    setTotalTime(null);
  }
  
  setLoading(false);
};
```

**Time Measurement**:
- Starts timer when user clicks "Generate"
- Includes network latency + AWS processing
- Displays in seconds with 2 decimal places

**Error Handling**:
- Silent catch (no alert)
- Clears image and time on error
- Loading state reset

#### 3. History Carousel

**Auto-scroll Implementation**:
```javascript
const startAutoScroll = () => {
  stopAutoScroll();
  const el = historyRef.current;
  if (!el) return;
  
  autoScrollTimer.current = setInterval(() => {
    if (!historyRef.current) return;
    const node = historyRef.current;
    node.scrollLeft += 2;  // 2px per 20ms = 100px/second
    
    if (node.scrollLeft + node.clientWidth >= node.scrollWidth) {
      node.scrollLeft = 0;  // Loop back to start
    }
  }, 20);
};
```

**Trigger Events**:
- `onMouseEnter`: Start auto-scroll
- `onMouseLeave`: Stop auto-scroll
- `onKeyDown`: Arrow key navigation

**Manual Scroll Navigation**:
```javascript
const scrollHistory = (dir) => {
  const el = historyRef.current;
  if (!el) return;
  const amount = Math.max(280, Math.floor(el.clientWidth * 0.8));
  el.scrollBy({ left: dir === 'left' ? -amount : amount, behavior: 'smooth' });
};
```

**Keyboard Accessibility**:
```javascript
const onHistoryKeyDown = (e) => {
  if (e.key === 'ArrowLeft') {
    e.preventDefault();
    scrollHistory('left');
  } else if (e.key === 'ArrowRight') {
    e.preventDefault();
    scrollHistory('right');
  }
};
```

#### 4. Clear Function

```javascript
const handleClear = () => {
  if (loading) return;  // Prevent clearing mid-generation
  
  setPrompt('');
  setImageUrl('');
  setTotalTime(null);
  
  // Focus input for next prompt
  if (promptInputRef.current) {
    promptInputRef.current.focus();
  }
};
```

### Styled Components

**Gradient Backgrounds**:
```javascript
const ImageGenPage = styled.div`
  background: linear-gradient(166deg, rgba(8, 18, 34, 0.95), rgba(15, 28, 50, 0.9));
`;
```

**Hover Effects**:
```javascript
const HistoryItem = styled.div`
  &:hover {
    transform: translateY(-4px);
    border-color: rgba(56, 189, 248, 0.6);
    box-shadow: 0 16px 32px rgba(56, 189, 248, 0.25);
  }
`;
```

**Carousel Edge Gradients**:
```javascript
const CarouselWrap = styled.div`
  &:before {
    left: 0;
    background: linear-gradient(to right, rgba(8, 18, 34, 0.92), rgba(8, 18, 34, 0));
  }
  &:after {
    right: 0;
    background: linear-gradient(to left, rgba(8, 18, 34, 0.92), rgba(8, 18, 34, 0));
  }
`;
```

---

## Data Flow & Processing Pipeline

### Complete Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. USER INPUT (Frontend)                                        │
│    • Navigate to /movie-poster-generation                        │
│    • Enter prompt: "A futuristic sci-fi movie poster..."        │
│    • Click "Generate" button                                     │
└────────────┬────────────────────────────────────────────────────┘
             │ POST /send_prompt
             │ { "prompt": "A futuristic sci-fi..." }
             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. BACKEND REQUEST HANDLING                                     │
│    • Extract prompt from JSON body                               │
│    • Validate prompt is not empty                                │
│    • Generate timestamp for tracking                             │
│    • Log request details                                         │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. AWS BEDROCK INVOCATION                                       │
│    • Get/create Bedrock client (singleton)                       │
│    • Build request body:                                         │
│      - taskType: TEXT_IMAGE                                      │
│      - text: user prompt                                         │
│      - width: 1024, height: 1024                                 │
│      - cfgScale: 8, quality: premium                             │
│    • Call invoke_model API                                       │
│    • Wait for response (5-8 seconds typical)                     │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. RESPONSE PROCESSING                                          │
│    • Parse streaming response body                               │
│    • Decode bytes → string → JSON                                │
│    • Extract base64 image data:                                  │
│      - Check 'images', 'artifacts', 'data' keys                  │
│      - Handle multiple response formats                          │
│    • Decode base64 → raw PNG bytes                               │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. LOCAL STORAGE                                                │
│    • Create history/{timestamp}/ folder                          │
│    • Save original.png (1024×1024)                              │
│    • Generate thumbnail.png:                                     │
│      - Load image with PIL                                       │
│      - Resize to 120×120 (maintain aspect ratio)                 │
│      - Save with Lanczos resampling                              │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. S3 UPLOAD (Optional)                                         │
│    • Check if S3_BUCKET configured                               │
│    • Generate key: moviePoster/YYYY-MM-DD/HHMMSS_uuid.png      │
│    • Upload PNG bytes with ContentType='image/png'              │
│    • Generate presigned URL (1-hour expiration)                  │
│    • If fails: fallback to local URL                             │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. RESPONSE GENERATION                                          │
│    • Calculate total time (seconds)                              │
│    • Build JSON response:                                        │
│      {                                                           │
│        "image_url": S3 presigned URL or local URL,              │
│        "total_time": 7.34,                                       │
│        "prompt": "A futuristic sci-fi...",                       │
│        "s3_key": "moviePoster/..." (if uploaded)                │
│      }                                                           │
│    • Return 200 OK                                               │
└────────────┬────────────────────────────────────────────────────┘
             │ JSON response
             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 8. FRONTEND DISPLAY                                             │
│    • Set imageUrl state → triggers image display                │
│    • Set totalTime → shows "Generated in 7.34s"                 │
│    • Re-fetch history → adds new thumbnail to carousel          │
│    • Enable Clear button                                         │
│    • User can download or generate another                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## AWS Integration

### Required AWS Services

1. **Amazon Bedrock**
   - Purpose: AI-powered text-to-image generation
   - Model: Amazon Nova Canvas v1:0
   - Permissions needed:
     - `bedrock:InvokeModel`
   - Region support: Check [AWS Bedrock regions](https://docs.aws.amazon.com/bedrock/latest/userguide/bedrock-regions.html)

2. **Amazon S3** (Optional)
   - Purpose: Store generated images with shareable URLs
   - Permissions needed:
     - `s3:PutObject` - Upload images
     - `s3:GetObject` - Generate presigned URLs
   - Bucket setup:
     - Public read optional (presigned URLs work with private buckets)
     - Enable versioning (recommended)
     - Lifecycle policy to delete old images

### Model Configuration

**Amazon Nova Canvas Parameters**:

```python
{
  "taskType": "TEXT_IMAGE",
  "textToImageParams": {
    "text": "<user_prompt>"
  },
  "imageGenerationConfig": {
    "numberOfImages": 1,          # Always 1 for this service
    "width": 1024,                # Fixed resolution
    "height": 1024,               # Square format
    "cfgScale": 8.0,              # Prompt adherence (1-20)
    "quality": "premium"          # "standard" or "premium"
  }
}
```

**Quality Comparison**:
| Setting | Generation Time | Detail Level | Use Case |
|---------|----------------|--------------|----------|
| Standard | 3-5 seconds | Good | Quick previews, iterations |
| Premium | 5-8 seconds | Excellent | Final outputs, marketing |

**CFG Scale Guide**:
- **1-3**: Very loose interpretation, artistic freedom
- **4-6**: Balanced creativity
- **7-9**: Recommended range (good balance)
- **10-15**: Very literal, may reduce aesthetic quality
- **16-20**: Extreme adherence, often over-constrained

---

## API Reference

### Endpoints

#### 1. Generate Image

```http
POST /send_prompt
Content-Type: application/json

Request:
{
  "prompt": "A cinematic movie poster for a sci-fi thriller"
}

Response 200:
{
  "image_url": "https://bucket.s3.amazonaws.com/moviePoster/2025-10-21/142530_abc123.png?...",
  "total_time": 7.34,
  "prompt": "A cinematic movie poster for a sci-fi thriller",
  "s3_key": "moviePoster/2025-10-21/142530_abc123.png"
}

Response 400:
{
  "image_url": "",
  "total_time": 0,
  "error": "Prompt is required"
}

Response 500:
{
  "image_url": "",
  "total_time": 5.12,
  "error": "Failed to decode image bytes from Bedrock response",
  "prompt": "A cinematic movie poster for a sci-fi thriller"
}
```

#### 2. List History

```http
GET /history_list

Response 200:
[
  {
    "thumb": "http://localhost:5002/history/1729513530/thumbnail.png",
    "orig": "http://localhost:5002/history/1729513530/original.png"
  },
  {
    "thumb": "http://localhost:5002/history/1729512340/thumbnail.png",
    "orig": "http://localhost:5002/history/1729512340/original.png"
  }
]
```

#### 3. Serve History Files

```http
GET /history/{timestamp}/original.png
GET /history/{timestamp}/thumbnail.png

Response 200:
Content-Type: image/png
<binary PNG data>

Response 404:
File not found
```

#### 4. Health Check

```http
GET /health

Response 200:
{
  "status": "ok",
  "email_demo_mode": true
}
```

#### 5. Contact Form Submission

```http
POST /contact
Content-Type: application/json

Request:
{
  "firstName": "John",
  "lastName": "Doe",
  "email": "john.doe@example.com",
  "company": "Acme Corp",
  "phone": "+1-555-0123",
  "country": "United States",
  "comments": "Interested in enterprise licensing"
}

Response 200 (SMTP configured):
{
  "ok": true,
  "message": "Submitted successfully"
}

Response 200 (Dev mode):
{
  "ok": true,
  "message": "Received (dev mode): email not sent, saved to contact_logs"
}

Response 400:
{
  "ok": false,
  "error": "Missing required fields: email"
}
```

#### 6. Contact Logs (Dev Mode)

```http
GET /contact_logs_list

Response 200:
[
  {
    "file": "1729513530.json",
    "url": "http://localhost:5002/contact_logs/1729513530.json",
    "size": 1024
  }
]
```

```http
GET /contact_logs/{timestamp}.json

Response 200:
{
  "internal": {
    "to": "admin@company.com",
    "subject": "Website Contact Form - John Doe (Acme Corp)",
    "body": "New contact form submission:\nFirst Name: John\n..."
  },
  "ack": {
    "to": "john.doe@example.com",
    "subject": "We received your request",
    "body": "Hi John,\n\nThanks for reaching out..."
  },
  "data": {
    "firstName": "John",
    "lastName": "Doe",
    ...
  }
}
```

---

## Configuration

### Environment Variables

```bash
# AWS Configuration (Required for image generation)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# Bedrock Configuration
BEDROCK_REGION=us-east-1              # Override AWS_REGION for Bedrock
IMAGE_MODEL_ID=amazon.nova-canvas-v1:0

# Image Generation Settings
IMAGE_WIDTH=1024
IMAGE_HEIGHT=1024
IMAGE_CFG_SCALE=8.0
IMAGE_QUALITY=premium                  # "standard" or "premium"

# S3 Configuration (Optional - for cloud storage)
AWS_S3_BUCKET=your-bucket-name
S3_REGION=us-east-1                    # Override AWS_REGION for S3

# Service Configuration
PORT=5002
DEBUG=false                            # Set to "true" for debug mode
RELOADER=false                         # Set to "true" to enable Flask reloader

# Contact Form Configuration (Optional)
CONTACT_ALLOW_NO_SMTP=true             # Enable dev mode (saves to files)
CONTACT_TO=admin@company.com           # Internal notification recipient
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password
SMTP_FROM=noreply@company.com          # Optional, defaults to SMTP_USER
```

### Frontend Configuration

```bash
# React Environment Variables (.env)
REACT_APP_API_BASE=http://localhost:5002
# If not set, frontend will use same origin
```

---

## Deployment

### Prerequisites

1. **System Requirements**
   - Python 3.11 or higher
   - 2GB RAM minimum
   - 10GB disk space for history storage

2. **AWS Setup**
   - IAM user with Bedrock and S3 permissions
   - Bedrock model access (may require request)
   - S3 bucket (optional but recommended)

3. **Network Requirements**
   - Outbound HTTPS (443) to AWS services
   - Inbound HTTP (5002) for API access

### Installation Steps

```bash
# 1. Navigate to service directory
cd /path/to/mediaGenAI/imageCreation

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cat > .env << EOF
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_S3_BUCKET=your-bucket
IMAGE_MODEL_ID=amazon.nova-canvas-v1:0
EOF

# 5. Create directories
mkdir -p history contact_logs

# 6. Test the service
python image_creation_service.py

# 7. Access the service
# Backend: http://localhost:5002
# Health check: http://localhost:5002/health
```

### Production Deployment

**Using systemd (Linux)**:

```ini
# /etc/systemd/system/image-creation.service
[Unit]
Description=Image Creation Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/mediaGenAI/imageCreation
Environment="PATH=/opt/mediaGenAI/.venv/bin:/usr/local/bin:/usr/bin"
ExecStart=/opt/mediaGenAI/.venv/bin/python image_creation_service.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable image-creation
sudo systemctl start image-creation
sudo systemctl status image-creation
```

**Using the provided scripts**:

```bash
# Start all services
./start-all.sh

# Start only backend services
./start-backend.sh

# Check logs
tail -f image-creation.log

# Stop services
./stop-backend.sh
```

---

## Troubleshooting

### Common Issues

#### 1. Bedrock Model Not Available

**Symptoms**:
```
botocore.errorfactory.ValidationException: An error occurred (ValidationException) 
when calling the InvokeModel operation: The requested model is not available in this region
```

**Solutions**:
```bash
# Check model availability in your region
aws bedrock list-foundation-models --region us-east-1 --query "modelSummaries[?contains(modelId, 'nova-canvas')]"

# Request model access in AWS Console:
# 1. Go to Bedrock console
# 2. Navigate to "Model access"
# 3. Request access to "Amazon Nova Canvas"
# 4. Wait for approval (usually instant)

# Try alternative region
export BEDROCK_REGION=us-west-2
```

#### 2. Base64 Decoding Error

**Symptoms**:
```
RuntimeError: Failed to decode image bytes from Bedrock response
```

**Solutions**:
- Check if response contains valid base64
- Verify model ID is correct
- Test with simple prompt first
- Check AWS Bedrock console for model status

**Debug Code**:
```python
# Add logging to see raw response
import logging
logging.basicConfig(level=logging.DEBUG)

# In _invoke_bedrock function
app.logger.debug(f"Raw payload: {payload}")
```

#### 3. S3 Upload Failures

**Symptoms**:
```
botocore.exceptions.ClientError: An error occurred (AccessDenied) when calling the PutObject operation
```

**Solutions**:
```bash
# Check bucket permissions
aws s3api get-bucket-policy --bucket your-bucket-name

# Test upload manually
aws s3 cp test.png s3://your-bucket-name/test.png

# Verify IAM permissions
aws iam get-user-policy --user-name your-user --policy-name your-policy

# Required S3 permissions:
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::your-bucket-name/*"
    }
  ]
}
```

#### 4. PIL/Pillow Errors

**Symptoms**:
```
PIL.UnidentifiedImageError: cannot identify image file
```

**Solutions**:
```bash
# Reinstall Pillow with full codec support
pip uninstall Pillow
pip install Pillow --no-cache-dir

# Check Pillow features
python -c "from PIL import features; print(features.check('webp'), features.check('jpg'))"

# Install system dependencies (Ubuntu)
sudo apt-get install libjpeg-dev libpng-dev libtiff-dev libwebp-dev
```

#### 5. History Not Displaying

**Symptoms**:
- `/history_list` returns empty array
- Thumbnails not loading

**Solutions**:
```bash
# Check directory permissions
ls -la history/
# Should show readable folders

# Check file existence
find history/ -name "*.png"

# Test manual access
curl http://localhost:5002/history_list

# Verify folder structure
tree history/ -L 2
```

#### 6. CORS Errors

**Symptoms**:
```
Access to XMLHttpRequest blocked by CORS policy
```

**Solutions**:
```python
# Update CORS in image_creation_service.py
from flask_cors import CORS

CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:3000", "https://yourdomain.com"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})
```

#### 7. Slow Generation Times

**Symptoms**:
- Images taking >15 seconds
- Timeouts on large prompts

**Solutions**:
```bash
# Switch to standard quality for faster generation
export IMAGE_QUALITY=standard

# Reduce CFG scale
export IMAGE_CFG_SCALE=6.0

# Check AWS region latency
ping bedrock-runtime.us-east-1.amazonaws.com

# Use closest region
export BEDROCK_REGION=eu-west-1  # If in Europe
```

---

## Performance Optimization

### Backend Optimizations

1. **Client Connection Pooling**
   ```python
   # boto3 automatically pools connections
   # Reuse clients via singleton pattern
   client = _get_bedrock_client()  # Reused across requests
   ```

2. **Async History Saving**
   ```python
   from concurrent.futures import ThreadPoolExecutor
   
   executor = ThreadPoolExecutor(max_workers=2)
   
   # In send_prompt handler
   executor.submit(_save_history, image_bytes, timestamp)
   executor.submit(_upload_to_s3, image_bytes)
   ```

3. **Thumbnail Caching**
   ```python
   # Generate thumbnail only if not exists
   if not os.path.exists(thumbnail_path):
       with Image.open(BytesIO(image_bytes)) as img:
           img.thumbnail((120, 120))
           img.save(thumbnail_path)
   ```

4. **S3 Transfer Acceleration**
   ```python
   client = boto3.client(
       's3',
       config=Config(
           s3={'use_accelerate_endpoint': True}
       )
   )
   ```

### Frontend Optimizations

1. **Lazy Load History Images**
   ```javascript
   <img 
     src={item.thumb} 
     loading="lazy"  // Browser native lazy loading
     alt="Thumbnail"
   />
   ```

2. **Debounce History Fetch**
   ```javascript
   const debouncedFetch = useCallback(
     debounce(() => {
       axios.get(`${API_BASE}/history_list`)
         .then(res => setHistory(res.data));
     }, 500),
     []
   );
   ```

3. **Image Preloading**
   ```javascript
   const preloadImage = (url) => {
     const img = new Image();
     img.src = url;
   };
   
   // Preload when hover on thumbnail
   <HistoryItem onMouseEnter={() => preloadImage(item.orig)}>
   ```

4. **Virtual Scrolling**
   ```javascript
   // For large history (100+ items), use react-window
   import { FixedSizeList } from 'react-window';
   
   <FixedSizeList
     height={200}
     itemCount={history.length}
     itemSize={180}
     layout="horizontal"
   >
     {({ index, style }) => (
       <HistoryItem style={style}>
         {/* Content */}
       </HistoryItem>
     )}
   </FixedSizeList>
   ```

### Caching Strategies

1. **Browser Caching**
   ```python
   @app.after_request
   def add_cache_headers(response):
       if request.path.startswith('/history/'):
           response.cache_control.max_age = 86400  # 24 hours
       return response
   ```

2. **CDN Integration**
   - Serve S3 images through CloudFront
   - Cache history thumbnails
   - Edge caching for faster global access

3. **LocalStorage Caching**
   ```javascript
   // Cache history in browser
   useEffect(() => {
     const cached = localStorage.getItem('image_history');
     if (cached) {
       setHistory(JSON.parse(cached));
     }
     
     // Update from server
     axios.get(`${API_BASE}/history_list`).then(res => {
       setHistory(res.data);
       localStorage.setItem('image_history', JSON.stringify(res.data));
     });
   }, []);
   ```

---

## Security Considerations

### Backend Security

1. **AWS Credentials Protection**
   ```bash
   # Never commit credentials
   echo ".env" >> .gitignore
   
   # Use IAM roles on EC2
   # No credentials in environment
   
   # Rotate credentials regularly
   aws iam create-access-key --user-name your-user
   aws iam delete-access-key --user-name your-user --access-key-id old-key
   ```

2. **Input Validation**
   ```python
   def sanitize_prompt(prompt: str) -> str:
       # Remove control characters
       sanitized = ''.join(c for c in prompt if c.isprintable())
       
       # Limit length
       max_length = 1000
       sanitized = sanitized[:max_length]
       
       # Strip dangerous patterns
       sanitized = sanitized.replace('<script>', '')
       
       return sanitized.strip()
   ```

3. **Rate Limiting**
   ```python
   from flask_limiter import Limiter
   from flask_limiter.util import get_remote_address
   
   limiter = Limiter(
       app,
       key_func=get_remote_address,
       default_limits=["200 per day", "50 per hour"]
   )
   
   @app.route('/send_prompt', methods=['POST'])
   @limiter.limit("10 per minute")
   def send_prompt():
       # ...
   ```

4. **History Directory Traversal Prevention**
   ```python
   from werkzeug.security import safe_join
   
   @app.route('/history/<path:filename>')
   def history_file(filename):
       # Prevent directory traversal
       safe_path = safe_join(IMAGE_HISTORY_DIR, filename)
       if not safe_path or not safe_path.startswith(IMAGE_HISTORY_DIR):
           abort(403)
       return send_from_directory(IMAGE_HISTORY_DIR, filename)
   ```

### Frontend Security

1. **HTTPS Enforcement**
   ```javascript
   if (window.location.protocol === 'http:' && 
       window.location.hostname !== 'localhost') {
       window.location.protocol = 'https:';
   }
   ```

2. **XSS Prevention**
   ```javascript
   // React automatically escapes
   <div>{prompt}</div>  // Safe
   
   // Never use dangerouslySetInnerHTML with user input
   ```

3. **CSP Headers**
   ```python
   @app.after_request
   def add_security_headers(response):
       response.headers['Content-Security-Policy'] = (
           "default-src 'self'; "
           "img-src 'self' https://*.s3.amazonaws.com; "
           "script-src 'self' 'unsafe-inline'; "
           "style-src 'self' 'unsafe-inline'"
       )
       return response
   ```

---

## Monitoring & Logging

### Backend Logging

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('image-creation.log'),
        logging.StreamHandler()
    ]
)

# Log important events
app.logger.info(f"Image generation requested: prompt={prompt[:50]}...")
app.logger.info(f"Bedrock generation took {time_taken:.2f}s")
app.logger.info(f"S3 upload: key={s3_key}")
app.logger.error(f"Generation failed: {exc}")
```

### Metrics to Monitor

1. **Generation Metrics**
   - Average generation time
   - Success/failure rate
   - Prompt length distribution
   - Quality setting usage

2. **Storage Metrics**
   - History folder size
   - Number of images
   - S3 upload success rate
   - Presigned URL expiration rate

3. **AWS Metrics**
   - Bedrock API latency
   - Bedrock throttling events
   - S3 upload time
   - S3 presigned URL usage

4. **Resource Metrics**
   - Disk usage (history folder)
   - Memory usage (PIL operations)
   - CPU usage during thumbnail generation

---

## Testing

### Backend Unit Tests

```python
import unittest
from image_creation_service import _extract_base64_image, _save_history

class TestImageService(unittest.TestCase):
    
    def test_extract_base64_nova_format(self):
        payload = {
            "images": [{"imageBase64": "iVBORw0KGgo="}]
        }
        result = _extract_base64_image(payload)
        self.assertEqual(result, "iVBORw0KGgo=")
    
    def test_extract_base64_stable_diffusion_format(self):
        payload = {
            "artifacts": [{"base64": "iVBORw0KGgo="}]
        }
        result = _extract_base64_image(payload)
        self.assertEqual(result, "iVBORw0KGgo=")
    
    def test_thumbnail_generation(self):
        # Create test image
        from PIL import Image
        from io import BytesIO
        img = Image.new('RGB', (1024, 1024), color='red')
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        
        # Save history
        orig, thumb = _save_history(img_bytes.getvalue(), '12345')
        
        # Verify files exist
        self.assertTrue(os.path.exists(orig))
        self.assertTrue(os.path.exists(thumb))
        
        # Verify thumbnail size
        thumb_img = Image.open(thumb)
        self.assertLessEqual(thumb_img.width, 120)
        self.assertLessEqual(thumb_img.height, 120)

if __name__ == '__main__':
    unittest.main()
```

### Frontend Tests

```javascript
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import App from './App';

test('image generation form renders', () => {
    render(
        <BrowserRouter>
            <App />
        </BrowserRouter>
    );
    
    // Navigate to image generation page
    const link = screen.getByText(/movie poster generation/i);
    fireEvent.click(link);
    
    // Check form elements
    expect(screen.getByPlaceholderText(/describe the poster/i)).toBeInTheDocument();
    expect(screen.getByText(/generate/i)).toBeInTheDocument();
});

test('handles image generation', async () => {
    // Mock axios
    jest.spyOn(axios, 'post').mockResolvedValue({
        data: {
            image_url: 'http://localhost:5002/history/12345/original.png',
            total_time: 7.34,
            prompt: 'Test prompt'
        }
    });
    
    render(
        <BrowserRouter>
            <App />
        </BrowserRouter>
    );
    
    // Enter prompt
    const input = screen.getByPlaceholderText(/describe the poster/i);
    fireEvent.change(input, { target: { value: 'Test prompt' } });
    
    // Submit
    const button = screen.getByText(/generate/i);
    fireEvent.click(button);
    
    // Wait for image
    await waitFor(() => {
        expect(screen.getByAltText(/generated poster/i)).toBeInTheDocument();
    });
});
```

---

## Appendix

### Supported Prompt Styles

**Effective Prompts**:
- "A cinematic movie poster for a sci-fi thriller set in 2099"
- "Vintage 1970s horror movie poster with bold typography"
- "Animated adventure film poster with vibrant colors and fantasy creatures"
- "Film noir detective poster in black and white with dramatic lighting"

**Tips for Better Results**:
1. Be specific about genre, era, style
2. Mention lighting, colors, mood
3. Specify text/typography requirements
4. Include composition details (close-up, wide shot, etc.)
5. Reference art styles (photorealistic, animated, illustrated)

### Model Limitations

**Current Limitations**:
- Fixed 1024×1024 resolution
- Text in images may have spelling errors
- Complex scenes may lack coherence
- Faces may not be perfectly realistic
- Processing time: 5-10 seconds per image

**Workarounds**:
- Use external tools for text overlay
- Upscale images with AI upscalers
- Generate multiple variations and select best
- Combine with photo editing software

---

## Quick Reference Commands

### Service Management

```bash
# Start service
python image_creation_service.py

# Using scripts
./start-backend.sh         # All backend services
./start-all.sh            # Backend + frontend

# Stop services
./stop-backend.sh

# View logs
tail -f image-creation.log

# Check health
curl http://localhost:5002/health
```

### Testing

```bash
# Generate image
curl -X POST http://localhost:5002/send_prompt \
  -H "Content-Type: application/json" \
  -d '{"prompt":"A sci-fi movie poster"}'

# List history
curl http://localhost:5002/history_list

# Download image
curl http://localhost:5002/history/1729513530/original.png -o image.png
```

### Debugging

```bash
# Check AWS credentials
aws sts get-caller-identity

# List Bedrock models
aws bedrock list-foundation-models --region us-east-1

# Test S3 access
aws s3 ls s3://your-bucket-name

# Check disk space
du -sh history/
df -h

# View history structure
tree history/ -L 2
```

---

**End of Image Creation Service Reference Guide**

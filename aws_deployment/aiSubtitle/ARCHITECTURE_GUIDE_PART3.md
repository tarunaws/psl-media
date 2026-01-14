# AI Subtitle/Dubbing System - Architecture & Logic Guide
## Part 3: Frontend Architecture & Components

**Document Version:** 1.0  
**Last Updated:** October 24, 2025  
**System:** MediaGenAI - AI Subtitle Generation & Translation Service

---

## Table of Contents (Part 3)

1. [Frontend Architecture Overview](#frontend-architecture-overview)
2. [Component Structure](#component-structure)
3. [State Management](#state-management)
4. [Video Player Integration](#video-player-integration)
5. [Progress Tracking System](#progress-tracking-system)
6. [Translation Workflow](#translation-workflow)
7. [User Interface Components](#user-interface-components)

---

## Frontend Architecture Overview

### Technology Stack

| Category | Technology | Version | Purpose |
|----------|-----------|---------|---------|
| Framework | React | 18.2+ | Component architecture |
| Styling | styled-components | 6.1+ | CSS-in-JS styling |
| HTTP Client | axios | 1.6+ | API communication |
| HLS Player | hls.js | 1.5+ | HTTP Live Streaming |
| DASH Player | dashjs | 4.7+ | MPEG-DASH streaming |
| State | React Hooks | Built-in | State management |

### Component Architecture

```
AISubtitling (Main Component)
│
├── File Upload Section
│   ├── UploadContainer (drag & drop)
│   ├── LanguageControls (source language)
│   └── LanguageCheckboxGrid (target languages)
│
├── Video Processing Section
│   ├── VideoPreview (file info)
│   ├── ProcessingContainer (progress bar)
│   └── LanguageStatus (subtitle availability)
│
├── Video Player Section
│   ├── StreamingPlayerContainer
│   ├── StreamingVideo (HLS/DASH player)
│   ├── CaptionToggleButton
│   └── PlayerControls (protocol selector)
│
└── Subtitle Management Section
    ├── Subtitle track selector
    ├── Download links
    └── Translation controls
```

### Data Flow Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     User Interactions                         │
└────────────┬─────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────┐
│                   React State Layer                           │
│  • File selection state                                       │
│  • Processing state                                           │
│  • Progress tracking state                                    │
│  • Subtitle availability state                                │
│  • Player configuration state                                 │
└────────────┬─────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────┐
│                   API Communication                           │
│  • Upload video (POST /upload)                                │
│  • Poll progress (GET /progress/:id)                          │
│  • Generate subtitles (POST /generate-subtitles)              │
│  • Fetch subtitle tracks (GET /subtitles/:id)                 │
│  • Fetch streams (GET /streams/:id)                           │
└────────────┬─────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────┐
│                   Backend Processing                          │
│  (See Part 2 for backend details)                             │
└────────────┬─────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────┐
│                   UI Updates                                   │
│  • Progress bar animation                                     │
│  • Subtitle track rendering                                   │
│  • Video player updates                                       │
│  • Download link generation                                   │
└──────────────────────────────────────────────────────────────┘
```

---

## Component Structure

### Main Component: AISubtitling

**File:** `frontend/src/AISubtitling.js` (1431 lines)

**Purpose:** Orchestrate entire subtitle generation and playback workflow

### API Base URL Resolution

```javascript
const resolveSubtitleApiBase = () => {
  // Development: Use environment variable or localhost
  if (process.env.NODE_ENV === 'development') {
    return process.env.REACT_APP_SUBTITLE_API_BASE || 'http://localhost:5001';
  }
  
  // Production: Use relative path or configured endpoint
  return process.env.REACT_APP_SUBTITLE_API_BASE || 
         window.location.origin.replace(':3000', ':5001');
};

const SUBTITLE_API_BASE = useMemo(() => resolveSubtitleApiBase(), []);
```

### Language Options Configuration

**Transcription Languages (40+ languages):**

```javascript
const TRANSCRIBE_LANGUAGE_OPTIONS = [
  { value: 'auto', label: 'Auto-detect Language' },
  { value: 'en-US', label: 'English (US)' },
  { value: 'en-GB', label: 'English (UK)' },
  { value: 'es-ES', label: 'Spanish (Spain)' },
  { value: 'es-US', label: 'Spanish (US)' },
  { value: 'fr-FR', label: 'French' },
  { value: 'de-DE', label: 'German' },
  { value: 'it-IT', label: 'Italian' },
  { value: 'pt-BR', label: 'Portuguese (Brazil)' },
  { value: 'pt-PT', label: 'Portuguese (Portugal)' },
  { value: 'ja-JP', label: 'Japanese' },
  { value: 'ko-KR', label: 'Korean' },
  { value: 'zh-CN', label: 'Chinese (Simplified)' },
  { value: 'zh-TW', label: 'Chinese (Traditional)' },
  { value: 'ar-SA', label: 'Arabic (Saudi Arabia)' },
  { value: 'hi-IN', label: 'Hindi' },
  { value: 'ru-RU', label: 'Russian' },
  // ... 25+ more languages
];
```

**Translation Languages (75+ languages):**

```javascript
const TRANSLATE_LANGUAGE_OPTIONS = [
  { value: 'af', label: 'Afrikaans' },
  { value: 'ar', label: 'Arabic' },
  { value: 'bn', label: 'Bengali' },
  { value: 'zh', label: 'Chinese (Simplified)' },
  { value: 'zh-TW', label: 'Chinese (Traditional)' },
  { value: 'en', label: 'English' },
  { value: 'fr', label: 'French' },
  { value: 'de', label: 'German' },
  { value: 'hi', label: 'Hindi' },
  { value: 'ja', label: 'Japanese' },
  { value: 'ko', label: 'Korean' },
  { value: 'es', label: 'Spanish' },
  // ... 63+ more languages
];
```

---

## State Management

### State Variables Overview

```javascript
export default function AISubtitling() {
  // File Management
  const [selectedFile, setSelectedFile] = useState(null);
  const [currentFileId, setCurrentFileId] = useState('');
  
  // Processing State
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [progressMessage, setProgressMessage] = useState('');
  const [phase, setPhase] = useState(''); // 'upload' | 'transcribe' | 'complete'
  
  // Error Handling
  const [error, setError] = useState('');
  const [languageDetectionError, setLanguageDetectionError] = useState('');
  
  // Language Configuration
  const [sourceLanguage, setSourceLanguage] = useState('auto');
  const [detectedLanguage, setDetectedLanguage] = useState('');
  const [selectedTargetLanguages, setSelectedTargetLanguages] = useState([]);
  const [requestedTargetLanguages, setRequestedTargetLanguages] = useState([]);
  
  // Subtitle Management
  const [availableSubtitles, setAvailableSubtitles] = useState([]);
  const [selectedSubtitle, setSelectedSubtitle] = useState('');
  const [captionsEnabled, setCaptionsEnabled] = useState(true);
  const [translationApplied, setTranslationApplied] = useState(false);
  
  // Video Player
  const [streams, setStreams] = useState({});
  const [selectedProtocol, setSelectedProtocol] = useState('');
  
  // UI State
  const [dragOver, setDragOver] = useState(false);
  
  // Processing Flags
  const [hasRequestedTranscription, setHasRequestedTranscription] = useState(false);
  const [hasAttemptedSubtitleFetch, setHasAttemptedSubtitleFetch] = useState(false);
  
  // Refs
  const fileInputRef = useRef(null);
  const videoRef = useRef(null);
  const hlsInstanceRef = useRef(null);
  const dashPlayerRef = useRef(null);
}
```

### State Management Patterns

#### 1. File Selection Handler

```javascript
const handleFileSelect = (file) => {
  // Validation
  if (!file || !file.type.startsWith('video/')) {
    setError('Please select a valid video file.');
    return;
  }

  const maxSize = 5 * 1024 * 1024 * 1024; // 5GB
  if (file.size > maxSize) {
    setError('File too large. Maximum size allowed is 5GB.');
    return;
  }

  // Reset all state for new upload
  setSelectedFile(file);
  setCurrentFileId('');
  setProgress(0);
  setProgressMessage('');
  setError('');
  setPhase('');
  setHasRequestedTranscription(false);
  setHasAttemptedSubtitleFetch(false);
  setDetectedLanguage('');
  setAvailableSubtitles([]);
  setSelectedSubtitle('');
  setStreams({});
  setRequestedTargetLanguages([]);
  setSelectedTargetLanguages([]);
  setTranslationApplied(false);
  setCaptionsEnabled(true);
  setLanguageDetectionError('');
  cleanupVideoPlayers();
};
```

#### 2. Drag & Drop Handlers

```javascript
const handleDrop = (event) => {
  event.preventDefault();
  setDragOver(false);
  const file = event.dataTransfer.files[0];
  handleFileSelect(file);
};

const handleDragOver = (event) => {
  event.preventDefault();
  setDragOver(true);
};

const handleDragLeave = (event) => {
  event.preventDefault();
  setDragOver(false);
};
```

#### 3. Progress Calculation Logic

```javascript
const STAGE_FALLBACK_MESSAGES = {
  upload: 'Uploading video and extracting audio…',
  transcribe: 'AWS Transcribe job in progress…',
  complete: 'Finalizing subtitles…'
};

const computeStageBaseline = ({
  stage,
  readyForTranscription,
  subtitlesInProgress,
  subtitlesAvailable
}) => {
  if (!stage) return 0;

  if (stage === 'upload') {
    return readyForTranscription ? 55 : 12;
  }

  if (stage === 'transcribe') {
    if (subtitlesAvailable) return 90;
    return subtitlesInProgress ? 78 : 64;
  }

  if (stage === 'complete') {
    return 100;
  }

  return 0;
};
```

---

## Video Player Integration

### Player Cleanup Function

```javascript
const cleanupVideoPlayers = () => {
  // Destroy HLS.js instance
  if (hlsInstanceRef.current) {
    hlsInstanceRef.current.destroy();
    hlsInstanceRef.current = null;
  }
  
  // Reset DASH.js player
  if (dashPlayerRef.current) {
    dashPlayerRef.current.reset();
    dashPlayerRef.current = null;
  }
  
  // Clear video element
  if (videoRef.current) {
    videoRef.current.removeAttribute('src');
    videoRef.current.load();
  }
};
```

### HLS Player Setup

```javascript
useEffect(() => {
  if (!selectedProtocol || !streams[selectedProtocol]) {
    cleanupVideoPlayers();
    return;
  }

  const video = videoRef.current;
  if (!video) return;

  const manifestPath = streams[selectedProtocol]?.manifest;
  if (!manifestPath) return;

  const manifestUrl = resolveUrl(manifestPath);

  cleanupVideoPlayers();

  if (selectedProtocol === 'hls') {
    // Native HLS support (Safari, iOS)
    if (video.canPlayType('application/vnd.apple.mpegurl')) {
      video.src = manifestUrl;
      video.load();
    } 
    // HLS.js for browsers without native support
    else if (Hls.isSupported()) {
      const hls = new Hls({ enableWorker: true });
      hls.loadSource(manifestUrl);
      hls.attachMedia(video);
      hlsInstanceRef.current = hls;
    } 
    // Fallback
    else {
      video.src = manifestUrl;
      video.load();
    }
  }
}, [selectedProtocol, streams, resolveUrl]);
```

### DASH Player Setup

```javascript
if (selectedProtocol === 'dash') {
  const player = dashjs.MediaPlayer().create();
  player.initialize(video, manifestUrl, false);
  dashPlayerRef.current = player;
}
```

### Subtitle Track Management

```javascript
useEffect(() => {
  const video = videoRef.current;
  if (!video) return;

  const tracks = video.textTracks;
  
  for (let index = 0; index < tracks.length; index += 1) {
    const track = tracks[index];
    const trackCode = track.language || track.label || '';
    
    // Disable all tracks if captions are off or no subtitle selected
    if (!captionsEnabled || !selectedSubtitle) {
      track.mode = 'disabled';
      continue;
    }
    
    // Enable selected track
    if (trackCode.toLowerCase() === selectedSubtitle.toLowerCase()) {
      track.mode = 'showing';
    } else {
      track.mode = 'disabled';
    }
  }
}, [captionsEnabled, selectedSubtitle, availableSubtitles]);
```

### Protocol Selection Auto-Detection

```javascript
useEffect(() => {
  if (!Object.keys(streams).length) {
    setSelectedProtocol('');
    cleanupVideoPlayers();
    return;
  }
  
  setSelectedProtocol((previous) => {
    // Keep current protocol if still available
    if (previous && streams[previous]) {
      return previous;
    }
    // Default to first available protocol
    return Object.keys(streams)[0];
  });
}, [streams]);
```

---

## Progress Tracking System

### Backend Health Check

```javascript
const checkBackendHealth = async (retries = 2) => {
  for (let attempt = 0; attempt < retries; attempt += 1) {
    try {
      const response = await axios.get(
        `${SUBTITLE_API_BASE}/health`, 
        { timeout: 5000 }
      );
      
      if (response.status === 200) {
        return true;
      }
    } catch (healthError) {
      if (attempt < retries - 1) {
        await new Promise((resolve) => setTimeout(resolve, 1000));
      }
    }
  }
  return false;
};
```

### Progress Polling Function

```javascript
const pollProgress = async (fileId) => {
  try {
    const { data } = await axios.get(`${SUBTITLE_API_BASE}/progress/${fileId}`);

    // Update phase
    const serverStage = data.stage;
    if (serverStage && serverStage !== phase) {
      setPhase(serverStage);
    }

    // Handle language detection
    if (data.languageDetectionError) {
      setLanguageDetectionError(data.languageDetectionError);
    }

    if (typeof data.detectedLanguage === 'string' && data.detectedLanguage.length) {
      setDetectedLanguage(data.detectedLanguage);
    }

    // Update target languages
    if (Array.isArray(data.targetLanguageRequested)) {
      setRequestedTargetLanguages(data.targetLanguageRequested);
    }

    // Update available subtitles
    if (Array.isArray(data.availableSubtitles)) {
      setAvailableSubtitles((previous) => 
        previous.length ? previous : data.availableSubtitles
      );
    }

    // Update streaming protocols
    if (data.streamsReady) {
      setStreams((previous) => ({ ...previous, ...data.streamsReady }));
    }

    // Update translation status
    if (typeof data.translationApplied === 'boolean') {
      setTranslationApplied(data.translationApplied);
    }

    // Process progress value
    let rawProgressValue = 0;
    if (typeof data.progress === 'number') {
      rawProgressValue = data.progress;
    } else if (typeof data.progress === 'string') {
      const parsed = Number.parseFloat(data.progress);
      rawProgressValue = Number.isFinite(parsed) ? parsed : 0;
    }

    // Handle error state (progress = -1)
    if (rawProgressValue === -1) {
      const fallbackMessage = STAGE_FALLBACK_MESSAGES[serverStage] || '';
      setProgress((previous) => Math.max(previous, computeStageBaseline({
        stage: serverStage,
        readyForTranscription: data.readyForTranscription,
        subtitlesInProgress: data.subtitlesInProgress,
        subtitlesAvailable: data.readyForFetch
      })));
      setProgressMessage(data.message || fallbackMessage);
      setError(data.message || 'Processing failed on the server.');
      setProcessing(false);
      return;
    }

    // Calculate visual progress
    const baseline = computeStageBaseline({
      stage: serverStage,
      readyForTranscription: data.readyForTranscription,
      subtitlesInProgress: data.subtitlesInProgress,
      subtitlesAvailable: data.readyForFetch
    });

    let visualProgress = Number.isFinite(rawProgressValue) 
      ? rawProgressValue 
      : baseline;
    visualProgress = Math.max(baseline, visualProgress);
    visualProgress = Math.max(0, Math.min(100, Math.round(visualProgress)));

    setProgress((previous) => Math.max(previous, visualProgress));
    const fallbackMessage = STAGE_FALLBACK_MESSAGES[serverStage] || '';
    setProgressMessage(data.message || fallbackMessage);

    // Auto-trigger subtitle generation when audio is ready
    if (!data.readyForFetch && 
        data.readyForTranscription && 
        !hasRequestedTranscription) {
      setHasRequestedTranscription(true);
      setPhase('transcribe');
      generateSubtitles(fileId);
      return;
    }

    // Auto-fetch subtitles when available
    if (data.readyForFetch && !hasAttemptedSubtitleFetch) {
      setHasAttemptedSubtitleFetch(true);
      fetchSubtitles(fileId);
      return;
    }

    // Continue polling if subtitles not available
    if (!data.readyForFetch) {
      setTimeout(() => pollProgress(fileId), 2000);
    }
  } catch (pollError) {
    setError(`Failed to track progress: ${pollError.message}`);
    setProcessing(false);
  }
};
```

### Upload Processing

```javascript
const startProcessing = async () => {
  if (!selectedFile || processing) return;

  const reuseExisting = Boolean(currentFileId && phase === 'complete');

  setProcessing(true);
  setProgress(computeStageBaseline({
    stage: 'upload',
    readyForTranscription: false,
    subtitlesInProgress: false,
    subtitlesAvailable: false
  }));
  setProgressMessage('Checking backend availability...');
  setError('');
  setPhase(reuseExisting ? 'transcribe' : 'upload');
  setHasRequestedTranscription(false);
  setHasAttemptedSubtitleFetch(false);
  setDetectedLanguage('');
  setTranslationApplied(false);
  setLanguageDetectionError('');
  setAvailableSubtitles([]);
  setSelectedSubtitle('');
  setStreams({});

  try {
    // Health check
    setProgressMessage('Connecting to subtitle service...');
    const isHealthy = await checkBackendHealth(3);

    if (!isHealthy) {
      throw new Error('Cannot connect to AI Subtitle service. Please ensure the backend is running.');
    }

    // Reuse existing audio if available
    if (reuseExisting && currentFileId) {
      setProgressMessage('Reusing existing audio for subtitle generation...');
      setRequestedTargetLanguages(selectedTargetLanguages);
      setHasRequestedTranscription(true);
      await generateSubtitles(currentFileId);
      return;
    }

    // Upload new file
    const formData = new FormData();
    formData.append('video', selectedFile);

    setProgressMessage('Starting upload...');

    const uploadResponse = await axios.post(
      `${SUBTITLE_API_BASE}/upload`, 
      formData, 
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 30 * 60 * 1000 // 30 minutes
      }
    );

    const uploadResult = uploadResponse.data;
    if (!uploadResult.file_id) {
      throw new Error('No file ID returned from upload');
    }

    setCurrentFileId(uploadResult.file_id);
    setRequestedTargetLanguages(selectedTargetLanguages);
    setProgressMessage('Upload completed, processing video...');
    
    // Start polling
    setTimeout(() => pollProgress(uploadResult.file_id), 1000);
    
  } catch (startError) {
    setError(`Upload failed: ${startError.response?.data?.error || startError.message}`);
    setProcessing(false);
  }
};
```

---

## Translation Workflow

### Subtitle Generation with Translation

```javascript
const generateSubtitles = async (fileId) => {
  try {
    const payload = {
      file_id: fileId,
      source_language: sourceLanguage,
      target_languages: selectedTargetLanguages
    };

    setTranslationApplied(false);

    await axios.post(
      `${SUBTITLE_API_BASE}/generate-subtitles`, 
      payload, 
      {
        headers: { 'Content-Type': 'application/json' }
      }
    );

    const transcriptionBaseline = computeStageBaseline({
      stage: 'transcribe',
      readyForTranscription: true,
      subtitlesInProgress: true,
      subtitlesAvailable: false
    });
    
    setProgress((previous) => Math.max(previous, transcriptionBaseline));
    setProgressMessage('Starting subtitle generation...');
    
    setTimeout(() => pollProgress(fileId), 2000);
    
  } catch (generationError) {
    const backendMessage = generationError.response?.data?.error || 
                          generationError.message;

    // Handle 404: Audio not ready yet
    if (generationError.response?.status === 404) {
      setHasRequestedTranscription(false);
      setProgressMessage('Waiting for audio extraction to finish...');
      setTimeout(() => pollProgress(fileId), 2000);
      return;
    }

    setError(`Failed to generate subtitles: ${backendMessage}`);
    setProcessing(false);
  }
};
```

### Fetch Subtitle Tracks

```javascript
const fetchSubtitles = async (fileId) => {
  try {
    const { data } = await axios.get(
      `${SUBTITLE_API_BASE}/subtitles/${fileId}`, 
      { timeout: 10000 }
    );

    const tracks = Array.isArray(data.tracks) ? data.tracks : [];
    
    // Resolve URLs
    const withUrls = tracks.map((track) => ({
      code: track.code,
      label: track.label,
      isOriginal: track.isOriginal,
      srt: resolveUrl(track.srt),
      vtt: resolveUrl(track.vtt)
    }));

    // Deduplicate tracks by code
    const deduped = withUrls.reduce((accumulator, track) => {
      if (!track.code) {
        accumulator.push(track);
        return accumulator;
      }
      
      const existingIndex = accumulator.findIndex(
        (entry) => entry.code === track.code
      );
      
      if (existingIndex === -1) {
        accumulator.push(track);
      } else if (track.isOriginal && !accumulator[existingIndex].isOriginal) {
        // Prefer original over translations
        accumulator[existingIndex] = track;
      }
      
      return accumulator;
    }, []);

    setAvailableSubtitles(deduped);
    setProcessing(false);
    setPhase('complete');
    setProgress(100);
    setProgressMessage('✅ Subtitles generated successfully!');
    setCaptionsEnabled(true);

    // Fetch streaming manifests
    await fetchStreams(fileId);
    
  } catch (fetchError) {
    setHasAttemptedSubtitleFetch(false);
    setTimeout(() => pollProgress(fileId), 3000);
  }
};
```

### Target Language Selection

```javascript
const toggleTargetLanguage = (code) => {
  setSelectedTargetLanguages((previous) =>
    previous.includes(code)
      ? previous.filter((item) => item !== code)
      : [...previous, code]
  );
};

const selectAllTargetLanguages = () => {
  setSelectedTargetLanguages(
    TRANSLATE_LANGUAGE_OPTIONS.map((option) => option.value)
  );
};

const clearTargetLanguages = () => {
  setSelectedTargetLanguages([]);
};
```

---

## User Interface Components

### File Upload Container

```javascript
<UploadContainer
  onDrop={handleDrop}
  onDragOver={handleDragOver}
  onDragLeave={handleDragLeave}
  onClick={() => fileInputRef.current?.click()}
  className={dragOver ? 'dragover' : ''}
>
  <UploadIcon>📁</UploadIcon>
  <UploadText>
    Drag & drop your video here, or click to browse
  </UploadText>
  <UploadSubtext>
    Supports MP4, AVI, MOV, MKV, WebM, FLV (max 5GB)
  </UploadSubtext>
  <HiddenInput
    ref={fileInputRef}
    type="file"
    accept="video/*"
    onChange={handleFileInputChange}
  />
</UploadContainer>
```

### Language Selection Controls

```javascript
<LanguageControls>
  <ControlGroup>
    <Label>Source Language</Label>
    <Select
      value={sourceLanguage}
      onChange={(e) => setSourceLanguage(e.target.value)}
      disabled={processing}
    >
      {TRANSCRIBE_LANGUAGE_OPTIONS.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </Select>
    <HelperText>
      Select "Auto-detect" for automatic language identification
    </HelperText>
  </ControlGroup>
</LanguageControls>
```

### Target Language Grid

```javascript
<LanguageCheckboxGrid>
  {TRANSLATE_LANGUAGE_OPTIONS.map((option) => (
    <LanguageCheckboxLabel key={option.value}>
      <LanguageCheckbox
        type="checkbox"
        checked={selectedTargetLanguages.includes(option.value)}
        onChange={() => toggleTargetLanguage(option.value)}
        disabled={processing}
      />
      {option.label}
    </LanguageCheckboxLabel>
  ))}
</LanguageCheckboxGrid>

<LanguageActions>
  <LanguageLink
    onClick={selectAllTargetLanguages}
    disabled={processing}
  >
    Select All
  </LanguageLink>
  <LanguageLink
    onClick={clearTargetLanguages}
    disabled={processing}
  >
    Clear All
  </LanguageLink>
</LanguageActions>
```

### Progress Bar

```javascript
<ProcessingContainer>
  <h3>Processing Video...</h3>
  <ProgressBar>
    <ProgressFill $progress={progress} />
  </ProgressBar>
  <p>{progressMessage}</p>
  <p style={{ fontSize: '0.9rem', color: '#a8b4da' }}>
    {progress}% complete
  </p>
</ProcessingContainer>
```

### Video Player with Captions

```javascript
<StreamingPlayerContainer>
  <StreamingVideoWrapper>
    <StreamingVideo
      ref={videoRef}
      controls
      crossOrigin="anonymous"
    >
      {availableSubtitles.map((track) => (
        <track
          key={track.code}
          kind="captions"
          src={track.vtt}
          srcLang={track.code}
          label={track.label}
          default={track.isOriginal}
        />
      ))}
    </StreamingVideo>
    
    <CaptionToggleButton
      onClick={() => setCaptionsEnabled(!captionsEnabled)}
      $active={captionsEnabled}
    >
      {captionsEnabled ? 'Captions: ON' : 'Captions: OFF'}
    </CaptionToggleButton>
  </StreamingVideoWrapper>
  
  <PlayerControls>
    <Label>Subtitle Language:</Label>
    <Select
      value={selectedSubtitle}
      onChange={(e) => setSelectedSubtitle(e.target.value)}
    >
      {availableSubtitles.map((track) => (
        <option key={track.code} value={track.code}>
          {track.label}
        </option>
      ))}
    </Select>
    
    <Label>Streaming Protocol:</Label>
    <Select
      value={selectedProtocol}
      onChange={(e) => setSelectedProtocol(e.target.value)}
    >
      {Object.keys(streams).map((protocol) => (
        <option key={protocol} value={protocol}>
          {protocol.toUpperCase()}
        </option>
      ))}
    </Select>
  </PlayerControls>
</StreamingPlayerContainer>
```

### Download Links

```javascript
<LanguageStatus>
  {availableSubtitles.map((track) => (
    <div key={track.code}>
      <strong>{track.label}:</strong>{' '}
      <DownloadLink href={track.srt} download>
        SRT
      </DownloadLink>
      {' | '}
      <DownloadLink href={track.vtt} download>
        VTT
      </DownloadLink>
    </div>
  ))}
</LanguageStatus>
```

---

## Key Frontend Features

### 1. Automatic Workflow Progression

The frontend automatically progresses through stages without user intervention:
- Upload → Audio extraction → Transcription → Subtitle generation → Translation

### 2. Smart Progress Calculation

Progress is calculated using stage baselines to ensure smooth UI updates even when backend progress is unavailable.

### 3. Multi-Protocol Streaming Support

Supports both HLS and DASH protocols with automatic fallback:
- Native HLS (Safari/iOS)
- HLS.js (Chrome/Firefox)
- DASH.js (all browsers)

### 4. Real-Time Caption Management

Subtitles are dynamically loaded and switched without page refresh.

### 5. Batch Translation Support

Users can select multiple target languages for simultaneous translation.

### 6. Error Recovery

Automatic retry logic for transient failures:
- Backend health checks with retries
- Subtitle fetch retries
- Progress polling with exponential backoff

---

## Next Document

➡️ **Part 4: Deployment & Operations**  
Covers environment setup, deployment, monitoring, and troubleshooting.

---

*End of Part 3*

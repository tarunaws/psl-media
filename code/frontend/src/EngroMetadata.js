import React, { useMemo, useRef, useState, useEffect } from 'react';
import axios from 'axios';
import styled from 'styled-components';

const PageWrapper = styled.div`
  display: flex;
  min-height: 100vh;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
`;

const Sidebar = styled.div`
  width: 280px;
  background: #f8f9fa;
  border-right: 1px solid #e0e0e0;
  padding: 20px;
  overflow-y: auto;
  max-height: 100vh;
  position: sticky;
  top: 0;
`;

const SidebarTitle = styled.h3`
  font-size: 1.2rem;
  color: #333;
  margin: 0 0 20px 0;
  display: flex;
  align-items: center;
  gap: 8px;
`;

const CatalogueItem = styled.div`
  background: white;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
  cursor: pointer;
  border: 2px solid ${props => props.isSelected ? '#667eea' : 'transparent'};
  transition: all 0.2s;
  position: relative;
  
  &:hover {
    border-color: #667eea;
    transform: translateX(4px);
  }
`;

const CatalogueThumb = styled.div`
  width: 100%;
  height: 80px;
  background: ${props => props.src ? `url(data:image/jpeg;base64,${props.src})` : '#e0e0e0'};
  background-size: cover;
  background-position: center;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
  font-size: 2rem;
  margin-bottom: 8px;
`;

const CatalogueTitle = styled.div`
  font-size: 0.9rem;
  font-weight: 600;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
`;

const CatalogueMeta = styled.div`
  font-size: 0.75rem;
  color: #666;
  margin-top: 4px;
`;

const DeleteButton = styled.button`
  position: absolute;
  top: 8px;
  right: 8px;
  background: rgba(255, 59, 48, 0.9);
  color: white;
  border: none;
  border-radius: 50%;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 16px;
  font-weight: bold;
  opacity: 0;
  transition: all 0.2s;
  z-index: 10;
  
  &:hover {
    background: rgba(255, 59, 48, 1);
    transform: scale(1.1);
  }
  
  ${CatalogueItem}:hover & {
    opacity: 1;
  }
`;

const Container = styled.div`
  flex: 1;
  max-width: 1400px;
  margin: 0 auto;
  padding: 28px 20px;
  width: 100%;
`;

const Header = styled.div`
  text-align: center;
  margin-bottom: 22px;
`;

const Title = styled.h1`
  font-size: 2.5rem;
  color: #1a1a1a;
  margin-bottom: 10px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
`;

const Subtitle = styled.p`
  font-size: 1.1rem;
  color: #666;
`;

const Section = styled.div`
  background: white;
  border-radius: 12px;
  padding: 30px;
  margin-bottom: ${props => props.noMargin ? '0' : '18px'};
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
`;

const DashboardGrid = styled.div`
  display: grid;
  grid-template-columns: 1fr;
  gap: 18px;
`;

const TwoCol = styled.div`
  display: grid;
  grid-template-columns: 1fr;
  gap: 18px;

  @media (min-width: 1100px) {
    grid-template-columns: 1fr 1fr;
    align-items: start;
  }
`;

const SectionTitle = styled.h2`
  font-size: 1.5rem;
  color: #333;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 10px;
`;

const Icon = styled.span`
  font-size: 1.8rem;
`;

const UploadArea = styled.div`
  border: 2px dashed ${props => props.isDragging ? '#667eea' : '#ddd'};
  border-radius: 8px;
  padding: 40px;
  text-align: center;
  background: ${props => props.isDragging ? '#f7f7ff' : '#fafafa'};
  cursor: pointer;
  transition: all 0.3s;
  
  &:hover {
    border-color: #667eea;
    background: #f7f7ff;
  }
`;

const Input = styled.input`
  padding: 12px 16px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 1rem;
  width: 100%;
  margin-bottom: 15px;
  
  &:focus {
    outline: none;
    border-color: #667eea;
  }
`;

const TextArea = styled.textarea`
  padding: 12px 16px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 1rem;
  width: 100%;
  margin-bottom: 15px;
  resize: vertical;
  min-height: 100px;
  
  &:focus {
    outline: none;
    border-color: #667eea;
  }
`;

const Button = styled.button`
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 12px 32px;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s;
  
  &:hover {
    transform: translateY(-2px);
  }
  
  &:disabled {
    background: #ccc;
    cursor: not-allowed;
    transform: none;
  }
`;

const SearchBox = styled.div`
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
`;

const SearchInput = styled.input`
  flex: 1;
  padding: 14px 20px;
  border: 2px solid #ddd;
  border-radius: 8px;
  font-size: 1.1rem;
  
  &:focus {
    outline: none;
    border-color: #667eea;
  }
`;

const SearchButton = styled(Button)`
  padding: 14px 40px;
`;

const VideoGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
  margin-top: 20px;
`;

const VideoCard = styled.div`
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s;
  cursor: pointer;
  
  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  }
`;

const Thumbnail = styled.div`
  width: 100%;
  height: 180px;
  background: ${props => props.src ? `url(data:image/jpeg;base64,${props.src})` : '#f0f0f0'};
  background-size: cover;
  background-position: center;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
  font-size: 3rem;
`;

const VideoInfo = styled.div`
  padding: 15px;
`;

const VideoTitle = styled.h3`
  font-size: 1.1rem;
  color: #333;
  margin: 0 0 8px 0;
`;

const VideoCardMeta = styled.p`
  font-size: 0.9rem;
  color: #666;
  margin: 4px 0;
`;

const SimilarityScore = styled.div`
  display: inline-block;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 600;
  margin-top: 8px;
`;

const Labels = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
`;

const Label = styled.span`
  background: #f0f0f0;
  color: #666;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 0.8rem;
`;

const ProgressBar = styled.div`
  width: 100%;
  height: 6px;
  background: #f0f0f0;
  border-radius: 3px;
  overflow: hidden;
  margin: 20px 0;
`;

const ProgressFill = styled.div`
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  width: ${props => props.percent}%;
  transition: width 0.3s;
`;

const Message = styled.div`
  padding: 12px 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  background: ${props => props.type === 'error' ? '#fee' : '#efe'};
  color: ${props => props.type === 'error' ? '#c33' : '#363'};
  border-left: 4px solid ${props => props.type === 'error' ? '#c33' : '#363'};
`;

const EmptyState = styled.div`
  text-align: center;
  padding: 60px 20px;
  color: #999;
`;

const EmptyIcon = styled.div`
  font-size: 4rem;
  margin-bottom: 20px;
`;

const VideoPlayer = styled.div`
  background: white;
  border-radius: 12px;
  overflow: hidden;
  margin-top: 4px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
`;

const VideoPlayerHeader = styled.div`
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 15px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
`;

const XRayButton = styled.button`
  background: rgba(255, 255, 255, ${props => (props.$active ? 0.35 : 0.2)});
  border: none;
  color: white;
  height: 32px;
  padding: 0 12px;
  border-radius: 10px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.9rem;
  font-weight: 700;
  transition: background 0.2s;

  &:hover {
    background: rgba(255, 255, 255, ${props => (props.$active ? 0.45 : 0.3)});
  }

  &:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }
`;

const PlayerOverlayControls = styled.div`
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 2;
  pointer-events: auto;
`;

const VideoPlayerTitle = styled.h3`
  margin: 0;
  font-size: 1.2rem;
`;

const CloseButton = styled.button`
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  transition: background 0.2s;
  
  &:hover {
    background: rgba(255, 255, 255, 0.3);
  }
`;

const VideoPlayerContent = styled.div`
  padding: 18px;
  background: white;
`;

const PlayerLayout = styled.div`
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;

  @media (min-width: 1100px) {
    grid-template-columns: 1.7fr 1fr;
    align-items: start;
  }
`;

const PlayerStage = styled.div`
  background: #000;
  border-radius: 12px;
  padding: 10px;
`;

const SidePanel = styled.div`
  border: 1px solid #eee;
  border-radius: 12px;
  padding: 14px;
  background: #fafafa;
`;

const MetaHeaderRow = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
`;

const CountPill = styled.span`
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 22px;
  padding: 0 10px;
  border-radius: 999px;
  background: #f0f0f0;
  color: #666;
  font-size: 0.8rem;
  font-weight: 600;
  white-space: nowrap;
`;

const MetaPanelsGrid = styled.div`
  display: grid;
  grid-template-columns: 1fr;
  gap: 14px;

  @media (min-width: 1100px) {
    grid-template-columns: 1fr 1fr;
    align-items: start;
  }
`;

const MetaPanel = styled.div`
  border: 1px solid #eee;
  border-radius: 12px;
  padding: 14px;
  background: #fafafa;
`;

const ScrollArea = styled.div`
  border: 1px solid #eee;
  border-radius: 10px;
  background: #fff;
  overflow: auto;
  max-height: 320px;
`;

const MetaTable = styled.table`
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
`;

const MetaTh = styled.th`
  text-align: left;
  padding: 10px 12px;
  color: #333;
  font-weight: 700;
  border-bottom: 1px solid #eee;
  background: #fafafa;
  position: sticky;
  top: 0;
  z-index: 1;
`;

const MetaTd = styled.td`
  padding: 10px 12px;
  border-bottom: 1px solid #f0f0f0;
  color: #555;
  vertical-align: top;
`;

const TimelineList = styled.div`
  display: grid;
  gap: 10px;
`;

const TimelineItem = styled.button`
  display: grid;
  grid-template-columns: 90px 1fr;
  gap: 10px;
  width: 100%;
  text-align: left;
  background: #fff;
  border: 1px solid #eee;
  border-radius: 12px;
  padding: 10px;
  cursor: pointer;

  &:hover {
    border-color: #667eea;
  }
`;

const TimelineTime = styled.div`
  font-weight: 800;
  color: #333;
  font-size: 0.9rem;
`;

const TimelineTitle = styled.div`
  font-weight: 700;
  color: #222;
  font-size: 0.95rem;
  line-height: 1.2;
`;

const TimelineBody = styled.div`
  margin-top: 4px;
  font-size: 0.85rem;
  color: #666;
  line-height: 1.35;
`;

const VideoElement = styled.video`
  width: 100%;
  max-height: 500px;
  object-fit: contain;
  background: #000;
  border-radius: 8px;
`;

const PreviewStage = styled.div`
  position: relative;
`;

const HoverOverlay = styled.div`
  position: absolute;
  left: 12px;
  top: 35%;
  right: auto;
  bottom: auto;
  transform: translate(0, -50%);
  padding: 12px;
  display: flex;
  gap: 12px;
  align-items: stretch;
  pointer-events: none;
  background: linear-gradient(180deg, rgba(0,0,0,0) 0%, rgba(0,0,0,0.72) 100%);
  border-radius: 8px;
  width: min(280px, calc((100% - 24px) / 2));
  max-width: 280px;
`;

const HoverRight = styled.div`
  flex: 1;
  color: #fff;
  overflow: hidden;
`;

const XRayGrid = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
`;

const XRayCol = styled.div`
  display: grid;
  gap: 6px;
`;

const CelebRow = styled.div`
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 0;
`;

const CelebThumb = styled.div`
  width: 48px;
  height: 48px;
  border-radius: 8px;
  background: ${props => props.src ? `url(data:image/jpeg;base64,${props.src})` : '#333'};
  background-size: cover;
  background-position: center;
  border: 1px solid rgba(255,255,255,0.25);
  flex-shrink: 0;
`;

const CelebName = styled.div`
  font-size: 0.9rem;
  font-weight: 600;
  line-height: 1.2;
  color: #fff;
`;

const VideoMeta = styled.div`
  margin-top: 0;
`;

const MetaSection = styled.div`
  margin-bottom: 20px;
`;

const MetaLabel = styled.h4`
  font-size: 1rem;
  color: #333;
  margin: 0 0 10px 0;
`;

const MetaContent = styled.p`
  font-size: 0.95rem;
  color: #666;
  line-height: 1.6;
  margin: 0;
`;

const MetaGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
`;

const MetaStat = styled.div`
  border: 1px solid #eee;
  border-radius: 10px;
  padding: 12px;
  background: #fafafa;
`;

const MetaStatLabel = styled.div`
  font-size: 0.8rem;
  color: #666;
  margin-bottom: 4px;
`;

const MetaStatValue = styled.div`
  font-size: 1rem;
  color: #222;
  font-weight: 600;
`;

const SecondaryButton = styled(Button)`
  background: #f0f0f0;
  color: #333;
`;

const PreBlock = styled.pre`
  background: #0b1020;
  color: #e6e6e6;
  padding: 12px;
  border-radius: 10px;
  overflow: auto;
  max-height: 420px;
  font-size: 0.8rem;
  line-height: 1.4;
`;

const BACKEND_URL = 'http://localhost:5014';

function EngroMetadata() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [videoTitle, setVideoTitle] = useState('');
  const [videoDescription, setVideoDescription] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadJob, setUploadJob] = useState(null);
  const [message, setMessage] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  
  const [searchQuery, setSearchQuery] = useState('');
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const [allVideos, setAllVideos] = useState([]);
  const [selectedVideo, setSelectedVideo] = useState(null);
  const [reprocessing, setReprocessing] = useState(false);

  const [speakerAliases, setSpeakerAliases] = useState({});

  const [awsCollectionId, setAwsCollectionId] = useState('');
  const [awsActorName, setAwsActorName] = useState('');
  const [awsActorImage, setAwsActorImage] = useState(null);
  const [awsFaces, setAwsFaces] = useState([]);
  const [awsBusy, setAwsBusy] = useState(false);

  const [localActorName, setLocalActorName] = useState('');
  const [localActorImage, setLocalActorImage] = useState(null);
  const [localActors, setLocalActors] = useState([]);
  const [localEngine, setLocalEngine] = useState(null);
  const [localBusy, setLocalBusy] = useState(false);

  const videoRef = useRef(null);
  const uploadPollRef = useRef(null);

  const uploadPhaseLabel = () => {
    if (!uploading) return 'Upload & Analyze Video';
    if (uploadJob?.message) return `Processing… ${uploadJob.message}`;
    if (uploadProgress > 0 && uploadProgress < 55) return `Uploading… ${uploadProgress}%`;
    if (uploadProgress >= 55 && uploadProgress < 100) return `Processing… ${uploadProgress}%`;
    return 'Processing…';
  };

  const stopUploadPolling = () => {
    if (uploadPollRef.current) {
      clearInterval(uploadPollRef.current);
      uploadPollRef.current = null;
    }
  };

  useEffect(() => {
    return () => {
      stopUploadPolling();
    };
  }, []);

  useEffect(() => {
    const vid = selectedVideo?.id;
    if (!vid) {
      setSpeakerAliases({});
      return;
    }
    try {
      const raw = localStorage.getItem(`engroSpeakerAliases:${vid}`);
      const parsed = raw ? JSON.parse(raw) : {};
      setSpeakerAliases(parsed && typeof parsed === 'object' ? parsed : {});
    } catch {
      setSpeakerAliases({});
    }
  }, [selectedVideo?.id]);

  useEffect(() => {
    const vid = selectedVideo?.id;
    if (!vid) return;
    try {
      localStorage.setItem(`engroSpeakerAliases:${vid}`, JSON.stringify(speakerAliases || {}));
    } catch {
      // ignore storage errors (private mode / quota)
    }
  }, [speakerAliases, selectedVideo?.id]);

  const formatSeconds = (value) => {
    const seconds = Number(value);
    if (!Number.isFinite(seconds) || seconds < 0) return '—';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${String(s).padStart(2, '0')}`;
  };

  const findNearestFrame = (frames, t) => {
    if (!Array.isArray(frames) || frames.length === 0) return null;
    let best = frames[0];
    let bestDist = Math.abs(Number(best.timestamp || 0) - t);
    for (const f of frames) {
      const ft = Number(f.timestamp || 0);
      const d = Math.abs(ft - t);
      if (d < bestDist) {
        best = f;
        bestDist = d;
      }
    }
    return best;
  };

  const getFacesForFrame = (frame) => {
    if (!frame) return { kind: 'none', faces: [] };
    if (Array.isArray(frame.custom_faces) && frame.custom_faces.length > 0) {
      return { kind: 'custom', faces: frame.custom_faces };
    }
    if (Array.isArray(frame.local_faces) && frame.local_faces.length > 0) {
      return { kind: 'local', faces: frame.local_faces };
    }
    if (Array.isArray(frame.celebrities) && frame.celebrities.length > 0) {
      return { kind: 'celebrity', faces: frame.celebrities };
    }
    return { kind: 'none', faces: [] };
  };

  const dialogueByCharacter = useMemo(() => {
    if (!selectedVideo) return [];
    const segments = Array.isArray(selectedVideo.transcript_segments) ? selectedVideo.transcript_segments : [];
    if (segments.length === 0) return [];

    const frames = Array.isArray(selectedVideo.frames) ? selectedVideo.frames : [];
    const namesFromFrame = (frame) => {
      const names = [];
      const pushName = (name) => {
        const n = String(name || '').trim();
        if (!n) return;
        if (!names.includes(n)) names.push(n);
      };
      (frame?.custom_faces || []).forEach((f) => pushName(f?.name));
      (frame?.local_faces || []).forEach((f) => pushName(f?.name));
      (frame?.celebrities || []).forEach((c) => pushName(c?.name));
      return names;
    };

    const bestNameAt = (t) => {
      if (!frames.length) return null;
      const frame = findNearestFrame(frames, t);
      const names = namesFromFrame(frame);
      return names.length ? names[0] : null;
    };

    // Learn a stable mapping: speaker -> most frequent on-screen name.
    const countsBySpeaker = new Map();
    for (const seg of segments) {
      const speaker = seg?.speaker;
      if (!speaker) continue;
      const mid = (Number(seg?.start) + Number(seg?.end)) / 2;
      const name = bestNameAt(mid);
      if (!name) continue;
      if (!countsBySpeaker.has(speaker)) countsBySpeaker.set(speaker, new Map());
      const m = countsBySpeaker.get(speaker);
      m.set(name, (m.get(name) || 0) + 1);
    }

    const speakerToCharacter = {};
    for (const [speaker, m] of countsBySpeaker.entries()) {
      let bestName = null;
      let bestCount = -1;
      for (const [name, c] of m.entries()) {
        if (c > bestCount) {
          bestCount = c;
          bestName = name;
        }
      }
      if (bestName) speakerToCharacter[speaker] = bestName;
    }

    return segments.map((seg) => {
      const speaker = seg?.speaker || null;
      const manual = speaker ? String(speakerAliases?.[speaker] || '').trim() : '';
      const mid = (Number(seg?.start) + Number(seg?.end)) / 2;
      const fallback = bestNameAt(mid);
      const character = manual || (speaker ? (speakerToCharacter[speaker] || 'Unknown') : (fallback || 'Unknown'));
      return { ...seg, speaker, character };
    });
  }, [selectedVideo, speakerAliases]);

  const uniqueSpeakers = useMemo(() => {
    const out = [];
    const seen = new Set();
    const segs = Array.isArray(selectedVideo?.transcript_segments) ? selectedVideo.transcript_segments : [];
    for (const s of segs) {
      const spk = s?.speaker;
      if (!spk) continue;
      if (seen.has(spk)) continue;
      seen.add(spk);
      out.push(spk);
    }
    return out;
  }, [selectedVideo?.transcript_segments]);

  const [xrayEnabled, setXrayEnabled] = useState(false);
  const [videoPaused, setVideoPaused] = useState(true);
  const [playerTime, setPlayerTime] = useState(0);

  const xrayAvailableFrame = useMemo(() => {
    if (!videoPaused) return null;
    const frames = Array.isArray(selectedVideo?.frames) ? selectedVideo.frames : [];
    if (!frames.length) return null;
    const t = Number(playerTime) || 0;
    const nearest = findNearestFrame(frames, t);
    if (!nearest) return null;

    const nearestTs = Number(nearest?.timestamp);
    const EPSILON_SECONDS = 5;
    if (Number.isFinite(nearestTs) && Math.abs(nearestTs - t) > EPSILON_SECONDS) {
      return null;
    }

    return nearest;
  }, [videoPaused, selectedVideo?.frames, playerTime]);

  const xrayAvailableFaces = useMemo(() => {
    if (!xrayAvailableFrame) return [];
    const out = [];
    const seen = new Set();
    const push = (kind, face) => {
      const name = String(face?.name || face?.external_image_id || '').trim();
      if (!name) return;
      const key = `${kind}:${name}`;
      if (seen.has(key)) return;
      seen.add(key);
      out.push({
        kind,
        name,
        thumbnail: face?.thumbnail || '',
      });
    };
    (xrayAvailableFrame?.custom_faces || []).forEach((f) => push('custom', f));
    (xrayAvailableFrame?.local_faces || []).forEach((f) => push('local', f));
    (xrayAvailableFrame?.celebrities || []).forEach((f) => push('celebrity', f));
    return out;
  }, [xrayAvailableFrame]);

  useEffect(() => {
    if (videoPaused && xrayEnabled && xrayAvailableFaces.length === 0) {
      setXrayEnabled(false);
    }
  }, [videoPaused, xrayEnabled, xrayAvailableFaces.length]);

  const formatTimestamp = (value) => {
    try {
      if (!value) return '—';
      const d = new Date(value);
      if (Number.isNaN(d.getTime())) return String(value);
      return d.toLocaleString();
    } catch {
      return String(value || '—');
    }
  };

  useEffect(() => {
    loadAllVideos();
  }, []);

  const seekTo = (seconds) => {
    const el = videoRef.current;
    const t = Number(seconds);
    if (!el || !Number.isFinite(t) || t < 0) return;
    try {
      el.currentTime = t;
      el.play?.();
    } catch {
      // no-op
    }
  };

  const peopleSummary = useMemo(() => {
    const frames = Array.isArray(selectedVideo?.frames) ? selectedVideo.frames : [];
    const stats = new Map();
    for (const frame of frames) {
      const ts = Number(frame?.timestamp ?? 0);
      const groups = [
        { kind: 'celebrity', list: frame?.celebrities },
        { kind: 'custom', list: frame?.custom_faces },
        { kind: 'local', list: frame?.local_faces },
      ];
      for (const g of groups) {
        const list = Array.isArray(g.list) ? g.list : [];
        for (const p of list) {
          const name = String(p?.name || p?.external_image_id || '').trim();
          if (!name) continue;
          const key = `${g.kind}:${name}`;
          const prev = stats.get(key) || {
            kind: g.kind,
            name,
            count: 0,
            first: ts,
            last: ts,
            bestScore: null,
            bestThumb: null,
          };
          prev.count += 1;
          prev.first = Math.min(prev.first, ts);
          prev.last = Math.max(prev.last, ts);
          const rawScore =
            g.kind === 'celebrity'
              ? Number(p?.confidence)
              : g.kind === 'custom'
                ? Number(p?.similarity)
                : Number(p?.similarity);
          const score = Number.isFinite(rawScore) ? rawScore : null;
          if (score !== null && (prev.bestScore === null || score > prev.bestScore)) {
            prev.bestScore = score;
            if (p?.thumbnail) prev.bestThumb = p.thumbnail;
          } else if (!prev.bestThumb && p?.thumbnail) {
            prev.bestThumb = p.thumbnail;
          }
          stats.set(key, prev);
        }
      }
    }

    const list = Array.from(stats.values());

    // Fallback: if frames are not included but aggregates exist, surface them for visibility.
    if (list.length === 0) {
      const celebs = Array.isArray(selectedVideo?.celebrities_detailed) ? selectedVideo.celebrities_detailed : [];
      const custom = Array.isArray(selectedVideo?.custom_faces_detailed) ? selectedVideo.custom_faces_detailed : [];
      const local = Array.isArray(selectedVideo?.local_faces_detailed) ? selectedVideo.local_faces_detailed : [];

      for (const c of celebs) {
        const name = String(c?.name || '').trim();
        if (!name) continue;
        const bestScore = Number(c?.max_confidence);
        stats.set(`celebrity:${name}`, {
          kind: 'celebrity',
          name,
          count: 1,
          first: 0,
          last: 0,
          bestScore: Number.isFinite(bestScore) ? bestScore : null,
          bestThumb: null,
        });
      }
      for (const c of custom) {
        const name = String(c?.name || '').trim();
        if (!name) continue;
        const bestScore = Number(c?.max_similarity);
        stats.set(`custom:${name}`, {
          kind: 'custom',
          name,
          count: 1,
          first: 0,
          last: 0,
          bestScore: Number.isFinite(bestScore) ? bestScore : null,
          bestThumb: null,
        });
      }
      for (const c of local) {
        const name = String(c?.name || '').trim();
        if (!name) continue;
        const bestScore = Number(c?.max_similarity);
        stats.set(`local:${name}`, {
          kind: 'local',
          name,
          count: 1,
          first: 0,
          last: 0,
          bestScore: Number.isFinite(bestScore) ? bestScore : null,
          bestThumb: null,
        });
      }
    }

    const finalList = Array.from(stats.values());
    finalList.sort((a, b) => {
      if (a.kind !== b.kind) return a.kind.localeCompare(b.kind);
      const as = a.bestScore === null ? -1 : a.bestScore;
      const bs = b.bestScore === null ? -1 : b.bestScore;
      if (bs !== as) return bs - as;
      if (b.count !== a.count) return b.count - a.count;
      return a.name.localeCompare(b.name);
    });
    return finalList;
  }, [selectedVideo]);

  const peopleCounts = useMemo(() => {
    const counts = { celebrity: 0, custom: 0, local: 0 };
    for (const p of peopleSummary) {
      if (p?.kind === 'celebrity') counts.celebrity += 1;
      else if (p?.kind === 'custom') counts.custom += 1;
      else if (p?.kind === 'local') counts.local += 1;
    }
    return counts;
  }, [peopleSummary]);

  const languageSummary = useMemo(() => {
    const langs = Array.isArray(selectedVideo?.languages_detected) ? selectedVideo.languages_detected : [];
    if (langs.length > 0) {
      const top = langs[0];
      const code = String(top?.language_code || '').trim();
      const score = Number(top?.score);
      return {
        code: code || '—',
        detail: Number.isFinite(score) ? `${(score * 100).toFixed(1)}% confidence` : null,
      };
    }
    const code = String(selectedVideo?.language_code || '').trim();
    return { code: code || '—', detail: null };
  }, [selectedVideo]);

  const celebrityTimeline = useMemo(() => {
    const frames = Array.isArray(selectedVideo?.frames) ? [...selectedVideo.frames] : [];
    frames.sort((a, b) => Number(a?.timestamp ?? 0) - Number(b?.timestamp ?? 0));

    const timeline = [];
    let lastSig = '';
    for (const frame of frames) {
      const ts = Number(frame?.timestamp ?? 0);
      const celebs = (Array.isArray(frame?.celebrities) ? frame.celebrities : [])
        .map((c) => String(c?.name || '').trim())
        .filter(Boolean)
        .sort();
      const custom = (Array.isArray(frame?.custom_faces) ? frame.custom_faces : [])
        .map((c) => String(c?.name || c?.external_image_id || '').trim())
        .filter(Boolean)
        .sort();

      const sig = `${celebs.join('|')}::${custom.join('|')}`;
      if (!sig || sig === '::') continue;
      if (sig === lastSig) continue;
      lastSig = sig;

      const titleParts = [];
      if (celebs.length) titleParts.push(`Celeb: ${celebs.slice(0, 3).join(', ')}${celebs.length > 3 ? '…' : ''}`);
      if (custom.length) titleParts.push(`Cast: ${custom.slice(0, 3).join(', ')}${custom.length > 3 ? '…' : ''}`);

      timeline.push({
        t: ts,
        title: titleParts.join(' • '),
        body: `${celebs.length ? `${celebs.length} celebrity match(es)` : ''}${celebs.length && custom.length ? ' • ' : ''}${custom.length ? `${custom.length} custom match(es)` : ''}`,
      });
      if (timeline.length >= 60) break;
    }
    return timeline;
  }, [selectedVideo]);

  const eventsTimeline = useMemo(() => {
    const frames = Array.isArray(selectedVideo?.frames) ? [...selectedVideo.frames] : [];
    frames.sort((a, b) => Number(a?.timestamp ?? 0) - Number(b?.timestamp ?? 0));

    const timeline = [];
    let lastSig = '';
    for (const frame of frames) {
      const ts = Number(frame?.timestamp ?? 0);

      const labels = (Array.isArray(frame?.labels) ? frame.labels : [])
        .map((l) => String(l?.name || '').trim())
        .filter(Boolean);
      const topLabels = labels.slice(0, 6).sort();

      const texts = (Array.isArray(frame?.text) ? frame.text : [])
        .map((t) => String(t?.text || '').trim())
        .filter(Boolean);
      const topText = texts.slice(0, 4).sort();

      const faceSet = (() => {
        const { faces } = getFacesForFrame(frame);
        return (Array.isArray(faces) ? faces : [])
          .map((f) => String(f?.name || f?.external_image_id || '').trim())
          .filter(Boolean)
          .slice(0, 4)
          .sort();
      })();

      const sig = `${topLabels.join('|')}::${topText.join('|')}::${faceSet.join('|')}`;
      if (!sig || sig === '::::') continue;
      if (sig === lastSig) continue;
      lastSig = sig;

      const titleBits = [];
      if (faceSet.length) titleBits.push(`People: ${faceSet.join(', ')}`);
      if (topText.length) titleBits.push(`Text: ${topText.join(' • ')}`);
      if (topLabels.length) titleBits.push(`Scene: ${topLabels.slice(0, 3).join(', ')}${topLabels.length > 3 ? '…' : ''}`);

      timeline.push({
        t: ts,
        title: titleBits[0] || 'Scene event',
        body: titleBits.slice(1).join(' | '),
      });
      if (timeline.length >= 80) break;
    }
    return timeline;
  }, [selectedVideo]);

  const loadAllVideos = async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/videos`);
      setAllVideos(response.data.videos);
    } catch (error) {
      console.error('Failed to load videos:', error);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      const file = files[0];
      if (file.type.startsWith('video/')) {
        setSelectedFile(file);
        if (!videoTitle) {
          setVideoTitle(file.name.replace(/\.[^/.]+$/, ''));
        }
      } else {
        setMessage({ type: 'error', text: 'Please upload a video file' });
      }
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      if (!videoTitle) {
        setVideoTitle(file.name.replace(/\.[^/.]+$/, ''));
      }
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setMessage({ type: 'error', text: 'Please select a video file' });
      return;
    }

    setUploading(true);
    setUploadProgress(0);
    setUploadJob(null);
    setMessage({ type: 'info', text: 'Uploading video…' });
    stopUploadPolling();

    const formData = new FormData();
    formData.append('video', selectedFile);
    formData.append('title', videoTitle || selectedFile.name);
    formData.append('description', videoDescription);

    try {
      const response = await axios.post(`${BACKEND_URL}/upload-video`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 50) / progressEvent.total);
          setUploadProgress(percentCompleted);
        }
      });

      // New async mode (202): backend returns job_id and we poll for progress.
      if (response.status === 202 && response.data?.job_id) {
        const jobId = response.data.job_id;
        setUploadProgress((p) => Math.max(p, 55));
        setUploadJob(response.data.job || { id: jobId, status: 'processing', progress: 1, message: 'Upload received' });
        setMessage({ type: 'info', text: 'Upload finished. Processing in background…' });

        uploadPollRef.current = setInterval(async () => {
          try {
            const jr = await axios.get(`${BACKEND_URL}/jobs/${jobId}`);
            const job = jr.data;
            setUploadJob(job);
            if (typeof job?.progress === 'number') {
              setUploadProgress(Math.max(0, Math.min(100, job.progress)));
            }

            if (job?.status === 'completed') {
              stopUploadPolling();
              setUploadProgress(100);
              const r = job.result || {};
              setMessage({
                type: 'success',
                text: `Video indexed successfully! Found ${r.labels_count ?? '—'} labels and ${r.frame_count ?? '—'} frames.`
              });

              setSelectedFile(null);
              setVideoTitle('');
              setVideoDescription('');
              await loadAllVideos();
              setUploading(false);
              setUploadProgress(0);
              setUploadJob(null);
            }

            if (job?.status === 'failed') {
              stopUploadPolling();
              setMessage({ type: 'error', text: job.error || 'Failed to process video' });
              setUploading(false);
              setUploadProgress(0);
            }
          } catch (e) {
            // Keep polling; transient errors can happen while backend is busy.
          }
        }, 2000);

        return;
      }

      // Backward-compatible sync mode (200)
      setUploadProgress(100);
      setMessage({
        type: 'success',
        text: `Video indexed successfully! Found ${response.data.labels_count} labels and ${response.data.frame_count} frames.`
      });

      setSelectedFile(null);
      setVideoTitle('');
      setVideoDescription('');
      loadAllVideos();
      setUploading(false);
      setUploadProgress(0);
    } catch (error) {
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.error || 'Failed to upload video' 
      });
      setUploading(false);
      setUploadProgress(0);
      setUploadJob(null);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setMessage({ type: 'error', text: 'Please enter a search query' });
      return;
    }

    // Clear any previous results immediately (prevents stale results from lingering).
    setSearchResults([]);
    setSelectedVideo(null);
    setSearching(true);
    setMessage(null);

    try {
      const response = await axios.post(`${BACKEND_URL}/search`, {
        query: searchQuery,
        top_k: 10,
        min_similarity: 0.5
      });

      setSearchResults(response.data.results);
      
      if (response.data.results.length === 0) {
        setMessage({ type: 'info', text: 'No matching videos found. Try a different query.' });
      }
      
    } catch (error) {
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.error || 'Search failed' 
      });
    } finally {
      setSearching(false);
    }
  };

  const handleSearchQueryChange = (value) => {
    setSearchQuery(value);
    // When the query changes, clear previous results until the next Search.
    setSearchResults([]);
    setSelectedVideo(null);
    if (message) setMessage(null);
  };

  const handleVideoClick = async (videoId) => {
    try {
      const response = await axios.get(`${BACKEND_URL}/video/${videoId}?include_frames=1`);
      setSelectedVideo(response.data);
      if (response.data?.custom_collection_id && !awsCollectionId) {
        setAwsCollectionId(String(response.data.custom_collection_id));
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to load video details' });
    }
  };

  const handleCreateCollection = async () => {
    const cid = String(awsCollectionId || '').trim();
    if (!cid) {
      setMessage({ type: 'error', text: 'Enter a Collection ID first' });
      return;
    }
    setAwsBusy(true);
    try {
      const resp = await axios.post(`${BACKEND_URL}/face-collection/create`, { collection_id: cid });
      setMessage({ type: 'success', text: resp.data.status === 'exists' ? 'Collection already exists' : 'Collection created' });
    } catch (e) {
      setMessage({ type: 'error', text: e.response?.data?.error || 'Failed to create collection' });
    } finally {
      setAwsBusy(false);
    }
  };

  const handleLoadCollectionFaces = async () => {
    const cid = String(awsCollectionId || '').trim();
    if (!cid) {
      setMessage({ type: 'error', text: 'Enter a Collection ID first' });
      return;
    }
    setAwsBusy(true);
    try {
      const resp = await axios.get(`${BACKEND_URL}/face-collection/${encodeURIComponent(cid)}/faces`);
      setAwsFaces(resp.data.faces || []);
      setMessage({ type: 'success', text: `Loaded ${resp.data.total || 0} enrolled faces` });
    } catch (e) {
      setMessage({ type: 'error', text: e.response?.data?.error || 'Failed to list faces' });
    } finally {
      setAwsBusy(false);
    }
  };

  const handleEnrollAwsActor = async () => {
    const cid = String(awsCollectionId || '').trim();
    const name = String(awsActorName || '').trim();
    if (!cid || !name || !awsActorImage) {
      setMessage({ type: 'error', text: 'Provide Collection ID, Actor Name, and an image' });
      return;
    }
    setAwsBusy(true);
    try {
      const form = new FormData();
      form.append('collection_id', cid);
      form.append('actor_name', name);
      form.append('image', awsActorImage);
      const resp = await axios.post(`${BACKEND_URL}/face-collection/enroll`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setMessage({ type: 'success', text: `Enrolled ${resp.data.faces_indexed || 0} face(s) for ${name}` });
      setAwsActorImage(null);
      await handleLoadCollectionFaces();
    } catch (e) {
      setMessage({ type: 'error', text: e.response?.data?.error || 'Failed to enroll actor' });
    } finally {
      setAwsBusy(false);
    }
  };

  const handleReprocessWithAwsCollection = async () => {
    if (!selectedVideo?.id) return;
    const cid = String(awsCollectionId || '').trim();
    if (!cid) {
      setMessage({ type: 'error', text: 'Enter a Collection ID first' });
      return;
    }
    setReprocessing(true);
    setMessage(null);
    try {
      const url = `${BACKEND_URL}/reprocess-video/${selectedVideo.id}?face_recognition_mode=aws_collection&collection_id=${encodeURIComponent(cid)}`;
      const response = await axios.post(url);
      setMessage({ type: 'success', text: response.data.message || 'Reprocessed with custom collection' });
      await loadAllVideos();
      await handleVideoClick(selectedVideo.id);
    } catch (e) {
      setMessage({ type: 'error', text: e.response?.data?.error || 'Failed to reprocess with collection' });
    } finally {
      setReprocessing(false);
    }
  };

  const handleLoadLocalActors = async () => {
    setLocalBusy(true);
    try {
      const resp = await axios.get(`${BACKEND_URL}/local-faces`);
      setLocalActors(resp.data.actors || []);
      setLocalEngine(resp.data.engine || null);
      if (resp.data.engine?.available) {
        setMessage({ type: 'success', text: `Loaded ${resp.data.total_actors || 0} local actors` });
      } else {
        setMessage({ type: 'info', text: resp.data.engine?.reason || 'Local engine not available' });
      }
    } catch (e) {
      setMessage({ type: 'error', text: e.response?.data?.error || 'Failed to load local actors' });
    } finally {
      setLocalBusy(false);
    }
  };

  const handleEnrollLocalActor = async () => {
    const name = String(localActorName || '').trim();
    if (!name || !localActorImage) {
      setMessage({ type: 'error', text: 'Provide Actor Name and an image' });
      return;
    }
    setLocalBusy(true);
    try {
      const form = new FormData();
      form.append('actor_name', name);
      form.append('image', localActorImage);
      const resp = await axios.post(`${BACKEND_URL}/local-faces/enroll`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setMessage({ type: 'success', text: `Local enroll ok: ${resp.data.actor_name} (${resp.data.samples} samples)` });
      setLocalActorImage(null);
      await handleLoadLocalActors();
    } catch (e) {
      const detail = e.response?.data?.detail;
      setMessage({ type: 'error', text: detail || e.response?.data?.error || 'Failed to enroll local actor' });
    } finally {
      setLocalBusy(false);
    }
  };

  const handleReprocessWithLocal = async () => {
    if (!selectedVideo?.id) return;
    setReprocessing(true);
    setMessage(null);
    try {
      const url = `${BACKEND_URL}/reprocess-video/${selectedVideo.id}?face_recognition_mode=local`;
      const response = await axios.post(url);
      setMessage({ type: 'success', text: response.data.message || 'Reprocessed with local face recognition' });
      await loadAllVideos();
      await handleVideoClick(selectedVideo.id);
    } catch (e) {
      setMessage({ type: 'error', text: e.response?.data?.error || 'Failed to reprocess with local face recognition' });
    } finally {
      setReprocessing(false);
    }
  };

  const handleReprocessVideo = async () => {
    if (!selectedVideo?.id) return;
    setReprocessing(true);
    setMessage(null);
    try {
      const response = await axios.post(`${BACKEND_URL}/reprocess-video/${selectedVideo.id}`);
      setMessage({
        type: 'success',
        text: response.data.message || 'Reprocessed. Transcript/language refreshed.'
      });
      await loadAllVideos();
      await handleVideoClick(selectedVideo.id);
    } catch (error) {
      setMessage({
        type: 'error',
        text: error.response?.data?.error || 'Failed to reprocess video'
      });
    } finally {
      setReprocessing(false);
    }
  };

  const handleDownloadMetadata = () => {
    if (!selectedVideo) return;
    try {
      const blob = new Blob([JSON.stringify(selectedVideo, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      const safeTitle = String(selectedVideo.title || selectedVideo.id || 'video')
        .replace(/[^a-z0-9\-_]+/gi, '_')
        .replace(/^_+|_+$/g, '')
        .slice(0, 80);
      a.href = url;
      a.download = `${safeTitle || 'metadata'}.metadata.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setMessage({ type: 'error', text: 'Failed to download metadata' });
    }
  };

  const handleDeleteVideo = async (videoId, videoTitle, e) => {
    e.stopPropagation(); // Prevent triggering video click
    
    if (!window.confirm(`Are you sure you want to delete "${videoTitle}"?`)) {
      return;
    }
    
    try {
      const response = await axios.delete(`${BACKEND_URL}/video/${videoId}`);
      
      setMessage({
        type: 'success',
        text: response.data.message || 'Video deleted successfully'
      });
      
      // Refresh the video list
      loadAllVideos();
      
      // Clear selected video if it was deleted
      if (selectedVideo && selectedVideo.id === videoId) {
        setSelectedVideo(null);
      }
      
      // Remove from search results if present
      setSearchResults(searchResults.filter(v => (v.video_id || v.id) !== videoId));
      
    } catch (error) {
      setMessage({
        type: 'error',
        text: error.response?.data?.error || 'Failed to delete video'
      });
    }
  };

  const renderSearchExamples = () => (
    <div style={{ marginTop: '15px' }}>
      <p style={{ fontSize: '0.9rem', color: '#666', marginBottom: '8px' }}>
        Try these example searches:
      </p>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
        {[
          'happy moments',
          'sunset scenes',
          'people dancing',
          'outdoor activities',
          'emotional speech'
        ].map(example => (
          <Label 
            key={example}
            style={{ cursor: 'pointer', background: '#e7e7ff' }}
            onClick={() => handleSearchQueryChange(example)}
          >
            {example}
          </Label>
        ))}
      </div>
    </div>
  );

  return (
    <PageWrapper>
      <Sidebar>
        <SidebarTitle>
          <span>🎬</span>
          Video Catalogue ({allVideos.length})
        </SidebarTitle>
        {allVideos.length === 0 ? (
          <div style={{ textAlign: 'center', color: '#999', padding: '20px 0' }}>
            <div style={{ fontSize: '2rem', marginBottom: '10px' }}>📹</div>
            <p style={{ fontSize: '0.85rem' }}>No videos yet</p>
          </div>
        ) : (
          allVideos.map(video => (
            <CatalogueItem
              key={video.id}
              isSelected={selectedVideo && selectedVideo.id === video.id}
              onClick={() => handleVideoClick(video.id)}
            >
              <DeleteButton
                onClick={(e) => handleDeleteVideo(video.id, video.title, e)}
                title="Delete video"
              >
                ×
              </DeleteButton>
              <CatalogueThumb src={video.thumbnail ? `data:image/jpeg;base64,${video.thumbnail}` : ''}>
                {!video.thumbnail && '🎥'}
              </CatalogueThumb>
              <CatalogueTitle>{video.title}</CatalogueTitle>
              <CatalogueMeta>
                {video.labels_count} labels • {video.frame_count} frames
              </CatalogueMeta>
            </CatalogueItem>
          ))
        )}
      </Sidebar>
      
      <Container>
        <Header>
          <Title>Envid Metadata</Title>
          <Subtitle>Upload videos, extract rich metadata, and identify actors (AWS or local)</Subtitle>
        </Header>


        {message && (
          <Message type={message.type}>{message.text}</Message>
        )}

        <DashboardGrid>
          <TwoCol>
            <Section noMargin>
              <SectionTitle>
                <Icon>📤</Icon>
                Upload
              </SectionTitle>

              <UploadArea
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                isDragging={isDragging}
                onClick={() => document.getElementById('videoInput').click()}
              >
            <input
              id="videoInput"
              type="file"
              accept="video/*"
              onChange={handleFileSelect}
              style={{ display: 'none' }}
            />
            <EmptyIcon>🎥</EmptyIcon>
            <h3>Drag & drop your video here</h3>
            <p style={{ color: '#999' }}>or click to browse</p>
            {selectedFile && (
              <div style={{ marginTop: '15px', color: '#667eea', fontWeight: 600 }}>
                ✓ {selectedFile.name} ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
              </div>
            )}
              </UploadArea>

          {selectedFile && (
            <div style={{ marginTop: '20px' }}>
              <Input
                type="text"
                placeholder="Video Title"
                value={videoTitle}
                onChange={(e) => setVideoTitle(e.target.value)}
              />
              <TextArea
                placeholder="Video Description (optional)"
                value={videoDescription}
                onChange={(e) => setVideoDescription(e.target.value)}
              />
              <Button onClick={handleUpload} disabled={uploading}>
                {uploadPhaseLabel()}
              </Button>

              {uploading && (
                <>
                  <ProgressBar>
                    <ProgressFill percent={uploadProgress} />
                  </ProgressBar>
                  {uploadJob?.message && (
                    <div style={{ marginTop: 8, color: '#666', fontSize: 12 }}>
                      {uploadJob.message}
                    </div>
                  )}
                </>
              )}
            </div>
          )}
            </Section>

            <Section noMargin>
              <SectionTitle>
                <Icon>🔍</Icon>
                Search
              </SectionTitle>

          <SearchBox>
            <SearchInput
              type="text"
              placeholder="Search by scene, object, person, emotion, or dialogue..."
              value={searchQuery}
              onChange={(e) => handleSearchQueryChange(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            />
            <SearchButton onClick={handleSearch} disabled={searching}>
              {searching ? 'Searching...' : 'Search'}
            </SearchButton>
          </SearchBox>

          {renderSearchExamples()}

          {searchResults.length > 0 && (
            <VideoGrid>
              {searchResults
                .filter((result) => result.similarity_score >= 0.5)
                .map((result) => (
                <VideoCard key={result.video_id || result.id} onClick={() => handleVideoClick(result.video_id || result.id)}>
                  <Thumbnail src={result.thumbnail || ''}>
                    {!result.thumbnail && '🎥'}
                  </Thumbnail>
                  <VideoInfo>
                    <VideoTitle>{result.title}</VideoTitle>
                    <VideoCardMeta>
                      Matched: {result.matched_labels && result.matched_labels.length > 0 
                        ? result.matched_labels.join(', ') 
                        : (result.labels && result.labels.length > 0
                          ? result.labels.join(', ')
                          : 'N/A')}
                    </VideoCardMeta>
                    <SimilarityScore>
                      {(result.similarity_score * 100).toFixed(1)}% Match
                    </SimilarityScore>
                  </VideoInfo>
                </VideoCard>
              ))}
            </VideoGrid>
          )}
            </Section>
          </TwoCol>

          {selectedVideo && (
            <VideoPlayer>
              <VideoPlayerHeader>
                <VideoPlayerTitle>{selectedVideo.title}</VideoPlayerTitle>
                <CloseButton
                  type="button"
                  onClick={() => {
                    setSelectedVideo(null);
                    setXrayEnabled(false);
                  }}
                  aria-label="Close"
                >
                  ×
                </CloseButton>
              </VideoPlayerHeader>
              <VideoPlayerContent>
                <PlayerLayout>
                  <PlayerStage>
                    {selectedVideo?.id && (
                      <PreviewStage>
                        <VideoElement
                          ref={videoRef}
                          src={`${BACKEND_URL}/video-file/${selectedVideo.id}`}
                          controls
                          preload="metadata"
                          poster={selectedVideo.thumbnail ? `data:image/jpeg;base64,${selectedVideo.thumbnail}` : undefined}
                          onPlay={() => {
                            setVideoPaused(false);
                            setXrayEnabled(false);
                          }}
                          onPause={(e) => {
                            setVideoPaused(true);
                            setPlayerTime(Number(e.currentTarget.currentTime) || 0);
                          }}
                          onTimeUpdate={(e) => {
                            setPlayerTime(Number(e.currentTarget.currentTime) || 0);
                          }}
                          onSeeked={(e) => {
                            setPlayerTime(Number(e.currentTarget.currentTime) || 0);
                          }}
                          onLoadedMetadata={(e) => {
                            setPlayerTime(Number(e.currentTarget.currentTime) || 0);
                          }}
                        />

                        {videoPaused && xrayAvailableFaces.length > 0 && (
                          <PlayerOverlayControls>
                            <XRayButton
                              type="button"
                              onClick={() => setXrayEnabled((v) => !v)}
                              $active={xrayEnabled}
                              aria-pressed={xrayEnabled}
                              title="Toggle Envid eye overlay"
                            >
                              Envid eye
                            </XRayButton>
                          </PlayerOverlayControls>
                        )}

                        {xrayEnabled && videoPaused && xrayAvailableFaces.length > 0 && (
                          <HoverOverlay>
                            <HoverRight>
                              <XRayGrid style={xrayAvailableFaces.length > 4 ? undefined : { gridTemplateColumns: '1fr' }}>
                                <XRayCol>
                                  {xrayAvailableFaces.slice(0, 4).map((c, idx) => (
                                    <CelebRow key={`${c.kind}:${c.name}:L:${idx}`}>
                                      <CelebThumb src={c.thumbnail} />
                                      <div>
                                        <CelebName>{c.name}</CelebName>
                                      </div>
                                    </CelebRow>
                                  ))}
                                </XRayCol>
                                {xrayAvailableFaces.length > 4 ? (
                                  <XRayCol>
                                    {xrayAvailableFaces.slice(4, 8).map((c, idx) => (
                                      <CelebRow key={`${c.kind}:${c.name}:R:${idx}`}>
                                        <CelebThumb src={c.thumbnail} />
                                        <div>
                                          <CelebName>{c.name}</CelebName>
                                        </div>
                                      </CelebRow>
                                    ))}
                                  </XRayCol>
                                ) : null}
                              </XRayGrid>
                            </HoverRight>
                          </HoverOverlay>
                        )}
                      </PreviewStage>
                    )}
                  </PlayerStage>

                  <SidePanel>
                    <VideoMeta>
                <MetaSection>
                  <MetaLabel>Actions</MetaLabel>
                  <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                    <SecondaryButton onClick={handleReprocessVideo} disabled={reprocessing}>
                      {reprocessing ? 'Reprocessing…' : 'Reprocess (Improve Transcript)'}
                    </SecondaryButton>
                    <SecondaryButton onClick={handleDownloadMetadata}>
                      Download Metadata (JSON)
                    </SecondaryButton>
                  </div>
                </MetaSection>

                <MetaSection>
                  <MetaLabel>Actor Recognition</MetaLabel>
                  <div style={{ display: 'grid', gap: '14px' }}>
                    <div>
                      <div style={{ fontWeight: 700, marginBottom: '8px' }}>AWS Rekognition Custom Face Collection</div>
                      <Input
                        placeholder="Collection ID (e.g., my-show-cast)"
                        value={awsCollectionId}
                        onChange={(e) => setAwsCollectionId(e.target.value)}
                      />
                      <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                        <SecondaryButton onClick={handleCreateCollection} disabled={awsBusy}>
                          {awsBusy ? 'Working...' : 'Create Collection'}
                        </SecondaryButton>
                        <SecondaryButton onClick={handleLoadCollectionFaces} disabled={awsBusy}>
                          {awsBusy ? 'Working...' : 'List Enrolled Faces'}
                        </SecondaryButton>
                        <SecondaryButton onClick={handleReprocessWithAwsCollection} disabled={reprocessing}>
                          Reprocess Using Collection
                        </SecondaryButton>
                      </div>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '10px', marginTop: '10px' }}>
                        <Input
                          placeholder="Actor Name (ExternalImageId)"
                          value={awsActorName}
                          onChange={(e) => setAwsActorName(e.target.value)}
                        />
                        <Input
                          type="file"
                          accept="image/*"
                          onChange={(e) => setAwsActorImage(e.target.files?.[0] || null)}
                        />
                        <SecondaryButton onClick={handleEnrollAwsActor} disabled={awsBusy}>
                          Enroll Actor Image
                        </SecondaryButton>
                        {awsFaces.length > 0 ? (
                          <div style={{ fontSize: '0.85rem', color: '#666' }}>
                            Enrolled: {awsFaces.slice(0, 10).map((f) => f.external_image_id).filter(Boolean).join(', ')}
                            {awsFaces.length > 10 ? '…' : ''}
                          </div>
                        ) : null}
                      </div>
                    </div>

                    <div>
                      <div style={{ fontWeight: 700, marginBottom: '8px' }}>Open-source / Local Face Recognition (InsightFace)</div>
                      <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                        <SecondaryButton onClick={handleLoadLocalActors} disabled={localBusy}>
                          {localBusy ? 'Working...' : 'Load Local Gallery'}
                        </SecondaryButton>
                        <SecondaryButton onClick={handleReprocessWithLocal} disabled={reprocessing}>
                          Reprocess Using Local Matching
                        </SecondaryButton>
                      </div>
                      {localEngine && localEngine.available === false ? (
                        <div style={{ marginTop: '8px', fontSize: '0.85rem', color: '#666' }}>
                          Local engine unavailable: {String(localEngine.reason || 'unknown')}
                        </div>
                      ) : null}
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '10px', marginTop: '10px' }}>
                        <Input
                          placeholder="Actor Name"
                          value={localActorName}
                          onChange={(e) => setLocalActorName(e.target.value)}
                        />
                        <Input
                          type="file"
                          accept="image/*"
                          onChange={(e) => setLocalActorImage(e.target.files?.[0] || null)}
                        />
                        <SecondaryButton onClick={handleEnrollLocalActor} disabled={localBusy}>
                          Enroll Actor Image (Local)
                        </SecondaryButton>
                        {localActors.length > 0 ? (
                          <div style={{ fontSize: '0.85rem', color: '#666' }}>
                            Local gallery: {localActors.slice(0, 10).map((a) => `${a.name} (${a.samples})`).join(', ')}
                            {localActors.length > 10 ? '…' : ''}
                          </div>
                        ) : null}
                      </div>
                    </div>
                  </div>
                </MetaSection>

                <MetaSection>
                  <MetaLabel>Video Stats</MetaLabel>
                  <MetaGrid>
                    <MetaStat>
                      <MetaStatLabel>Duration</MetaStatLabel>
                      <MetaStatValue>{formatSeconds(selectedVideo.duration_seconds)}</MetaStatValue>
                    </MetaStat>
                    <MetaStat>
                      <MetaStatLabel>Frames (extracted)</MetaStatLabel>
                      <MetaStatValue>{Number.isFinite(Number(selectedVideo.frame_count)) ? selectedVideo.frame_count : '—'}</MetaStatValue>
                    </MetaStat>
                    <MetaStat>
                      <MetaStatLabel>Frames (analyzed)</MetaStatLabel>
                      <MetaStatValue>{Number.isFinite(Number(selectedVideo.frames_analyzed)) ? selectedVideo.frames_analyzed : '—'}</MetaStatValue>
                    </MetaStat>
                    <MetaStat>
                      <MetaStatLabel>Frame interval</MetaStatLabel>
                      <MetaStatValue>
                        {Number.isFinite(Number(selectedVideo.frame_interval_seconds))
                          ? `${selectedVideo.frame_interval_seconds}s`
                          : '—'}
                      </MetaStatValue>
                    </MetaStat>
                    <MetaStat>
                      <MetaStatLabel>Language</MetaStatLabel>
                      <MetaStatValue>
                        {languageSummary.code}
                        {languageSummary.detail ? (
                          <span style={{ display: 'block', marginTop: 4, fontSize: '0.8rem', color: '#666', fontWeight: 600 }}>
                            {languageSummary.detail}
                          </span>
                        ) : null}
                      </MetaStatValue>
                    </MetaStat>
                    <MetaStat>
                      <MetaStatLabel>Uploaded at</MetaStatLabel>
                      <MetaStatValue>{formatTimestamp(selectedVideo.uploaded_at)}</MetaStatValue>
                    </MetaStat>
                    <MetaStat>
                      <MetaStatLabel>Reprocessed at</MetaStatLabel>
                      <MetaStatValue>{formatTimestamp(selectedVideo.reprocessed_at)}</MetaStatValue>
                    </MetaStat>
                  </MetaGrid>
                </MetaSection>

                {selectedVideo.description && (
                  <MetaSection>
                    <MetaLabel>Description</MetaLabel>
                    <MetaContent>{selectedVideo.description}</MetaContent>
                  </MetaSection>
                )}

                    </VideoMeta>
                  </SidePanel>
                </PlayerLayout>

                <div style={{ marginTop: '16px' }}>
                  <MetaPanelsGrid>
                    <MetaPanel>
                      <MetaHeaderRow>
                        <MetaLabel>Detected Content</MetaLabel>
                        <CountPill>{Array.isArray(selectedVideo.labels) ? selectedVideo.labels.length : 0}</CountPill>
                      </MetaHeaderRow>

                      {Array.isArray(selectedVideo.labels) && selectedVideo.labels.length > 0 ? (
                        <Labels>
                          {selectedVideo.labels.map((label, idx) => (
                            <Label key={idx}>{label}</Label>
                          ))}
                        </Labels>
                      ) : (
                        <MetaContent>—</MetaContent>
                      )}

                      {Array.isArray(selectedVideo.labels_detailed) && selectedVideo.labels_detailed.length > 0 ? (
                        <div style={{ marginTop: '12px' }}>
                          <MetaHeaderRow>
                            <MetaLabel style={{ marginBottom: 0 }}>Top Labels (ranked)</MetaLabel>
                            <CountPill>{selectedVideo.labels_detailed.length}</CountPill>
                          </MetaHeaderRow>
                          <div style={{ marginTop: '10px' }}>
                            <ScrollArea>
                              <MetaTable>
                                <thead>
                                  <tr>
                                    <MetaTh style={{ width: '55%' }}>Label</MetaTh>
                                    <MetaTh style={{ width: '20%' }}>Count</MetaTh>
                                    <MetaTh style={{ width: '25%' }}>Max conf.</MetaTh>
                                  </tr>
                                </thead>
                                <tbody>
                                  {selectedVideo.labels_detailed.map((item, idx) => (
                                    <tr key={idx}>
                                      <MetaTd>{item.name || '—'}</MetaTd>
                                      <MetaTd>{Number.isFinite(Number(item.occurrences)) ? item.occurrences : '—'}</MetaTd>
                                      <MetaTd>
                                        {Number.isFinite(Number(item.max_confidence)) ? `${Number(item.max_confidence).toFixed(1)}%` : '—'}
                                      </MetaTd>
                                    </tr>
                                  ))}
                                </tbody>
                              </MetaTable>
                            </ScrollArea>
                          </div>
                        </div>
                      ) : null}

                      {Array.isArray(selectedVideo.emotions) && selectedVideo.emotions.length > 0 ? (
                        <div style={{ marginTop: '12px' }}>
                          <MetaHeaderRow>
                            <MetaLabel style={{ marginBottom: 0 }}>Emotions</MetaLabel>
                            <CountPill>{selectedVideo.emotions.length}</CountPill>
                          </MetaHeaderRow>
                          <Labels>
                            {selectedVideo.emotions.map((emotion, idx) => (
                              <Label key={idx}>{emotion}</Label>
                            ))}
                          </Labels>
                        </div>
                      ) : null}
                    </MetaPanel>

                    <MetaPanel>
                      <MetaHeaderRow>
                        <MetaLabel>People Detection</MetaLabel>
                        <CountPill>{peopleSummary.length}</CountPill>
                      </MetaHeaderRow>

                      {(peopleCounts.celebrity || peopleCounts.custom || peopleCounts.local) ? (
                        <div style={{ marginTop: 8, color: '#666', fontSize: 12 }}>
                          Celeb: <b>{peopleCounts.celebrity}</b> • Cast: <b>{peopleCounts.custom}</b> • Local: <b>{peopleCounts.local}</b>
                        </div>
                      ) : null}

                      {peopleSummary.length > 0 ? (
                        <div style={{ marginTop: '10px' }}>
                          <ScrollArea>
                            <MetaTable>
                              <thead>
                                <tr>
                                  <MetaTh style={{ width: '44%' }}>Name</MetaTh>
                                  <MetaTh style={{ width: '14%' }}>Type</MetaTh>
                                  <MetaTh style={{ width: '14%' }}>Seen</MetaTh>
                                  <MetaTh style={{ width: '28%' }}>First → Last</MetaTh>
                                </tr>
                              </thead>
                              <tbody>
                                {peopleSummary.slice(0, 50).map((p, idx) => (
                                  <tr key={idx}>
                                    <MetaTd>
                                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                        <div
                                          style={{
                                            width: 34,
                                            height: 34,
                                            borderRadius: 10,
                                            background: p.bestThumb ? `url(data:image/jpeg;base64,${p.bestThumb})` : '#eee',
                                            backgroundSize: 'cover',
                                            backgroundPosition: 'center',
                                            border: '1px solid #eee',
                                            flexShrink: 0,
                                          }}
                                        />
                                        <div>
                                          <div style={{ fontWeight: 800, color: '#222' }}>{p.name}</div>
                                          {p.bestScore !== null ? (
                                            <div style={{ fontSize: '0.8rem', color: '#666' }}>
                                              Best: {p.kind === 'local' ? `${(p.bestScore * 100).toFixed(1)}%` : `${Number(p.bestScore).toFixed(1)}%`}
                                            </div>
                                          ) : null}
                                        </div>
                                      </div>
                                    </MetaTd>
                                    <MetaTd>{p.kind}</MetaTd>
                                    <MetaTd>{p.count}</MetaTd>
                                    <MetaTd>
                                      <button
                                        onClick={() => seekTo(p.first)}
                                        style={{
                                          background: 'transparent',
                                          border: 'none',
                                          color: '#667eea',
                                          cursor: 'pointer',
                                          fontWeight: 700,
                                          padding: 0,
                                        }}
                                        title="Seek to first appearance"
                                      >
                                        {formatSeconds(p.first)}
                                      </button>
                                      {' → '}
                                      <button
                                        onClick={() => seekTo(p.last)}
                                        style={{
                                          background: 'transparent',
                                          border: 'none',
                                          color: '#667eea',
                                          cursor: 'pointer',
                                          fontWeight: 700,
                                          padding: 0,
                                        }}
                                        title="Seek to last appearance"
                                      >
                                        {formatSeconds(p.last)}
                                      </button>
                                    </MetaTd>
                                  </tr>
                                ))}
                              </tbody>
                            </MetaTable>
                          </ScrollArea>
                        </div>
                      ) : (
                        <div style={{ marginTop: '10px' }}>
                          <MetaContent>—</MetaContent>
                        </div>
                      )}

                      {celebrityTimeline.length > 0 ? (
                        <div style={{ marginTop: '12px' }}>
                          <MetaHeaderRow>
                            <MetaLabel style={{ marginBottom: 0 }}>Timeline (changes)</MetaLabel>
                            <CountPill>{celebrityTimeline.length}</CountPill>
                          </MetaHeaderRow>
                          <div style={{ marginTop: '10px' }}>
                            <TimelineList>
                              {celebrityTimeline.map((it, idx) => (
                                <TimelineItem key={idx} onClick={() => seekTo(it.t)}>
                                  <TimelineTime>{formatSeconds(it.t)}</TimelineTime>
                                  <div>
                                    <TimelineTitle>{it.title}</TimelineTitle>
                                    {it.body ? <TimelineBody>{it.body}</TimelineBody> : null}
                                  </div>
                                </TimelineItem>
                              ))}
                            </TimelineList>
                          </div>
                        </div>
                      ) : null}
                    </MetaPanel>

                    <MetaPanel>
                      <MetaHeaderRow>
                        <MetaLabel>Main Events / Scene Timeline</MetaLabel>
                        <CountPill>{eventsTimeline.length}</CountPill>
                      </MetaHeaderRow>

                      {eventsTimeline.length > 0 ? (
                        <div style={{ marginTop: '10px' }}>
                          <TimelineList>
                            {eventsTimeline.map((it, idx) => (
                              <TimelineItem key={idx} onClick={() => seekTo(it.t)}>
                                <TimelineTime>{formatSeconds(it.t)}</TimelineTime>
                                <div>
                                  <TimelineTitle>{it.title}</TimelineTitle>
                                  {it.body ? <TimelineBody>{it.body}</TimelineBody> : null}
                                </div>
                              </TimelineItem>
                            ))}
                          </TimelineList>
                        </div>
                      ) : (
                        <div style={{ marginTop: '10px' }}>
                          <MetaContent>—</MetaContent>
                        </div>
                      )}
                    </MetaPanel>

                    <MetaPanel>
                      <MetaHeaderRow>
                        <MetaLabel>On-screen Text</MetaLabel>
                        <CountPill>{Array.isArray(selectedVideo.text_detected) ? selectedVideo.text_detected.length : 0}</CountPill>
                      </MetaHeaderRow>

                      {Array.isArray(selectedVideo.text_detected) && selectedVideo.text_detected.length > 0 ? (
                        <Labels>
                          {selectedVideo.text_detected.map((text, idx) => (
                            <Label key={idx}>{text}</Label>
                          ))}
                        </Labels>
                      ) : (
                        <MetaContent>—</MetaContent>
                      )}

                      {Array.isArray(selectedVideo.text_detailed) && selectedVideo.text_detailed.length > 0 ? (
                        <div style={{ marginTop: '12px' }}>
                          <MetaHeaderRow>
                            <MetaLabel style={{ marginBottom: 0 }}>On-screen Text (ranked)</MetaLabel>
                            <CountPill>{selectedVideo.text_detailed.length}</CountPill>
                          </MetaHeaderRow>
                          <div style={{ marginTop: '10px' }}>
                            <ScrollArea>
                              <MetaTable>
                                <thead>
                                  <tr>
                                    <MetaTh>Text</MetaTh>
                                    <MetaTh style={{ width: '25%' }}>Count</MetaTh>
                                  </tr>
                                </thead>
                                <tbody>
                                  {selectedVideo.text_detailed.map((item, idx) => (
                                    <tr key={idx}>
                                      <MetaTd>{item.text || '—'}</MetaTd>
                                      <MetaTd>{Number.isFinite(Number(item.occurrences)) ? item.occurrences : '—'}</MetaTd>
                                    </tr>
                                  ))}
                                </tbody>
                              </MetaTable>
                            </ScrollArea>
                          </div>
                        </div>
                      ) : null}
                    </MetaPanel>

                    <MetaPanel>
                      <MetaHeaderRow>
                        <MetaLabel>Speech (Transcript)</MetaLabel>
                        <CountPill>
                          {Array.isArray(selectedVideo.transcript_segments) ? selectedVideo.transcript_segments.length : (selectedVideo.transcript ? '1' : '0')}
                        </CountPill>
                      </MetaHeaderRow>

                      {selectedVideo.transcript ? (
                        <div style={{ marginTop: '10px' }}>
                          <MetaContent>{selectedVideo.transcript}</MetaContent>
                        </div>
                      ) : (
                        <MetaContent>—</MetaContent>
                      )}

                      {Array.isArray(selectedVideo.transcript_segments) && selectedVideo.transcript_segments.length > 0 ? (
                        <div style={{ marginTop: '12px' }}>
                          <MetaHeaderRow>
                            <MetaLabel style={{ marginBottom: 0 }}>Dialogue by Character</MetaLabel>
                            <CountPill>{dialogueByCharacter.length}</CountPill>
                          </MetaHeaderRow>

                          {uniqueSpeakers.length > 0 ? (
                            <div style={{ marginTop: 10, background: '#f8f9fa', border: '1px solid #eaeaea', borderRadius: 10, padding: 12 }}>
                              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginBottom: 8 }}>
                                <div style={{ fontWeight: 800, color: '#333' }}>Rename speakers</div>
                                <button
                                  onClick={() => {
                                    const vid = selectedVideo?.id;
                                    setSpeakerAliases({});
                                    if (vid) {
                                      try {
                                        localStorage.removeItem(`engroSpeakerAliases:${vid}`);
                                      } catch {
                                        // ignore
                                      }
                                    }
                                  }}
                                  type="button"
                                  style={{
                                    background: 'transparent',
                                    border: '1px solid #ddd',
                                    color: '#666',
                                    cursor: 'pointer',
                                    fontWeight: 800,
                                    padding: '8px 10px',
                                    borderRadius: 10,
                                  }}
                                  title="Clear saved speaker names for this video"
                                >
                                  Clear speaker names
                                </button>
                              </div>
                              <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 10, alignItems: 'center' }}>
                                {uniqueSpeakers.slice(0, 10).map((spk) => (
                                  <React.Fragment key={spk}>
                                    <div style={{ fontWeight: 800, color: '#666' }}>{spk}</div>
                                    <input
                                      value={String(speakerAliases?.[spk] || '')}
                                      onChange={(e) => {
                                        const v = e.target.value;
                                        setSpeakerAliases((prev) => ({ ...(prev || {}), [spk]: v }));
                                      }}
                                      placeholder="e.g., Shah Rukh Khan"
                                      style={{
                                        width: '100%',
                                        padding: '10px 12px',
                                        borderRadius: 10,
                                        border: '1px solid #ddd',
                                        outline: 'none',
                                        fontWeight: 700,
                                      }}
                                    />
                                  </React.Fragment>
                                ))}
                              </div>
                              {uniqueSpeakers.length > 10 ? (
                                <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
                                  Showing first 10 speakers.
                                </div>
                              ) : null}
                            </div>
                          ) : null}

                          <div style={{ marginTop: '10px' }}>
                            <ScrollArea>
                              <MetaTable>
                                <thead>
                                  <tr>
                                    <MetaTh style={{ width: '18%' }}>Character</MetaTh>
                                    <MetaTh style={{ width: '14%' }}>Speaker</MetaTh>
                                    <MetaTh style={{ width: '22%' }}>Time</MetaTh>
                                    <MetaTh>Text</MetaTh>
                                  </tr>
                                </thead>
                                <tbody>
                                  {dialogueByCharacter.slice(0, 120).map((seg, idx) => (
                                    <tr key={idx}>
                                      <MetaTd>{seg.character || 'Unknown'}</MetaTd>
                                      <MetaTd>{seg.speaker || '—'}</MetaTd>
                                      <MetaTd>
                                        <button
                                          onClick={() => seekTo(seg.start || 0)}
                                          style={{
                                            background: 'transparent',
                                            border: 'none',
                                            color: '#667eea',
                                            cursor: 'pointer',
                                            fontWeight: 800,
                                            padding: 0,
                                          }}
                                          title="Seek to this dialogue"
                                        >
                                          {formatSeconds(seg.start)} → {formatSeconds(seg.end)}
                                        </button>
                                      </MetaTd>
                                      <MetaTd>{seg.text || '—'}</MetaTd>
                                    </tr>
                                  ))}
                                </tbody>
                              </MetaTable>
                            </ScrollArea>
                          </div>
                        </div>
                      ) : null}

                      {Array.isArray(selectedVideo.transcript_segments) && selectedVideo.transcript_segments.length > 0 ? (
                        <div style={{ marginTop: '12px' }}>
                          <MetaHeaderRow>
                            <MetaLabel style={{ marginBottom: 0 }}>Transcript Segments (timed)</MetaLabel>
                            <CountPill>{selectedVideo.transcript_segments.length}</CountPill>
                          </MetaHeaderRow>
                          <div style={{ marginTop: '10px' }}>
                            <ScrollArea>
                              <MetaTable>
                                <thead>
                                  <tr>
                                    <MetaTh style={{ width: '14%' }}>Speaker</MetaTh>
                                    <MetaTh style={{ width: '28%' }}>Time</MetaTh>
                                    <MetaTh>Text</MetaTh>
                                  </tr>
                                </thead>
                                <tbody>
                                  {selectedVideo.transcript_segments.map((seg, idx) => (
                                    <tr key={idx}>
                                      <MetaTd>{seg.speaker || '—'}</MetaTd>
                                      <MetaTd>
                                        <button
                                          onClick={() => seekTo(seg.start || 0)}
                                          style={{
                                            background: 'transparent',
                                            border: 'none',
                                            color: '#667eea',
                                            cursor: 'pointer',
                                            fontWeight: 800,
                                            padding: 0,
                                          }}
                                          title="Seek to this segment"
                                        >
                                          {formatSeconds(seg.start)} → {formatSeconds(seg.end)}
                                        </button>
                                      </MetaTd>
                                      <MetaTd>{seg.text || '—'}</MetaTd>
                                    </tr>
                                  ))}
                                </tbody>
                              </MetaTable>
                            </ScrollArea>
                          </div>

                          {selectedVideo.transcript_words_count ? (
                            <div style={{ marginTop: '10px', fontSize: '0.85rem', color: '#666' }}>
                              Word-level timestamps available ({selectedVideo.transcript_words_count} words). Backend supports `include_words=1` if needed.
                            </div>
                          ) : null}
                        </div>
                      ) : null}
                    </MetaPanel>

                    <MetaPanel>
                      <MetaHeaderRow>
                        <MetaLabel>Safety (Moderation)</MetaLabel>
                        <CountPill>{Array.isArray(selectedVideo.moderation_detailed) ? selectedVideo.moderation_detailed.length : 0}</CountPill>
                      </MetaHeaderRow>

                      {Array.isArray(selectedVideo.moderation_detailed) && selectedVideo.moderation_detailed.length > 0 ? (
                        <div style={{ marginTop: '10px' }}>
                          <ScrollArea>
                            <MetaTable>
                              <thead>
                                <tr>
                                  <MetaTh>Category</MetaTh>
                                  <MetaTh style={{ width: '30%' }}>Max conf.</MetaTh>
                                </tr>
                              </thead>
                              <tbody>
                                {selectedVideo.moderation_detailed.map((item, idx) => (
                                  <tr key={idx}>
                                    <MetaTd>{item.name || '—'}</MetaTd>
                                    <MetaTd>
                                      {Number.isFinite(Number(item.max_confidence)) ? `${Number(item.max_confidence).toFixed(1)}%` : '—'}
                                    </MetaTd>
                                  </tr>
                                ))}
                              </tbody>
                            </MetaTable>
                          </ScrollArea>
                        </div>
                      ) : (
                        <div style={{ marginTop: '10px' }}>
                          <MetaContent>—</MetaContent>
                        </div>
                      )}
                    </MetaPanel>

                    <MetaPanel>
                      <MetaHeaderRow>
                        <MetaLabel>Raw JSON</MetaLabel>
                        <CountPill>debug</CountPill>
                      </MetaHeaderRow>
                      <div style={{ marginTop: '10px' }}>
                        <details>
                          <summary style={{ cursor: 'pointer', color: '#667eea', fontWeight: 600 }}>
                            Show metadata JSON
                          </summary>
                          <PreBlock>{JSON.stringify(selectedVideo, null, 2)}</PreBlock>
                        </details>
                      </div>
                    </MetaPanel>
                  </MetaPanelsGrid>
                </div>
              </VideoPlayerContent>
            </VideoPlayer>
          )}

          {allVideos.length === 0 && !uploading && searchResults.length === 0 && (
            <EmptyState>
              <EmptyIcon>🎬</EmptyIcon>
              <h3>No videos indexed yet</h3>
              <p>Upload a video to start extracting metadata and identifying actors</p>
            </EmptyState>
          )}
        </DashboardGrid>
      </Container>
    </PageWrapper>
  );
}

export default EngroMetadata;

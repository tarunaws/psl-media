import React, { useState, useEffect } from 'react';
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
  padding: 40px 20px;
  width: 100%;
`;

const Header = styled.div`
  text-align: center;
  margin-bottom: 50px;
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
  margin-bottom: 30px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
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
  background: #000;
  border-radius: 12px;
  overflow: hidden;
  margin-top: 20px;
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
  padding: 20px;
  background: white;
`;

const VideoThumbnail = styled.img`
  width: 100%;
  max-height: 500px;
  object-fit: contain;
  background: #000;
  border-radius: 8px;
`;

const VideoMeta = styled.div`
  margin-top: 20px;
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

const BACKEND_URL = 'http://localhost:5008';

function SemanticSearchVideo() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [videoTitle, setVideoTitle] = useState('');
  const [videoDescription, setVideoDescription] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [message, setMessage] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  
  const [searchQuery, setSearchQuery] = useState('');
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const [allVideos, setAllVideos] = useState([]);
  const [selectedVideo, setSelectedVideo] = useState(null);

  useEffect(() => {
    loadAllVideos();
  }, []);

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
    setMessage(null);

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

      setUploadProgress(100);
      setMessage({ 
        type: 'success', 
        text: `Video indexed successfully! Found ${response.data.labels_count} labels and ${response.data.frame_count} frames.` 
      });
      
      setSelectedFile(null);
      setVideoTitle('');
      setVideoDescription('');
      loadAllVideos();
      
    } catch (error) {
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.error || 'Failed to upload video' 
      });
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setMessage({ type: 'error', text: 'Please enter a search query' });
      return;
    }

    setSearching(true);
    setMessage(null);

    try {
      const response = await axios.post(`${BACKEND_URL}/search`, {
        query: searchQuery,
        top_k: 10,
        min_similarity: 0.51
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

  const handleVideoClick = async (videoId) => {
    try {
      const response = await axios.get(`${BACKEND_URL}/video/${videoId}`);
      setSelectedVideo(response.data);
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to load video details' });
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
            onClick={() => setSearchQuery(example)}
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
          <Title>🎬 Semantic Search (Video)</Title>
          <Subtitle>Upload videos and search them using natural language across visuals, dialogue, and emotions</Subtitle>
        </Header>

        {message && (
          <Message type={message.type}>{message.text}</Message>
        )}

        <Section>
          <SectionTitle>
            <Icon>📤</Icon>
            Upload Video
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
                {uploading ? 'Processing...' : 'Upload & Analyze Video'}
              </Button>

              {uploading && (
                <ProgressBar>
                  <ProgressFill percent={uploadProgress} />
                </ProgressBar>
              )}
            </div>
          )}
        </Section>

        <Section>
          <SectionTitle>
            <Icon>🔍</Icon>
            Search Videos
          </SectionTitle>

          <SearchBox>
            <SearchInput
              type="text"
              placeholder="Search by scene, object, person, emotion, or dialogue..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
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
                .filter((result) => result.similarity_score >= 0.51)
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

        {selectedVideo && (
          <VideoPlayer>
            <VideoPlayerHeader>
              <VideoPlayerTitle>{selectedVideo.title}</VideoPlayerTitle>
              <CloseButton onClick={() => setSelectedVideo(null)}>×</CloseButton>
            </VideoPlayerHeader>
            <VideoPlayerContent>
              {selectedVideo.thumbnail && (
                <VideoThumbnail 
                  src={`data:image/jpeg;base64,${selectedVideo.thumbnail}`}
                  alt={selectedVideo.title}
                />
              )}
              <VideoMeta>
                {selectedVideo.description && (
                  <MetaSection>
                    <MetaLabel>Description</MetaLabel>
                    <MetaContent>{selectedVideo.description}</MetaContent>
                  </MetaSection>
                )}
                {selectedVideo.labels && selectedVideo.labels.length > 0 && (
                  <MetaSection>
                    <MetaLabel>Detected Content</MetaLabel>
                    <Labels>
                      {selectedVideo.labels.map((label, idx) => (
                        <Label key={idx}>{label}</Label>
                      ))}
                    </Labels>
                  </MetaSection>
                )}
                {selectedVideo.transcript && (
                  <MetaSection>
                    <MetaLabel>Transcript</MetaLabel>
                    <MetaContent>{selectedVideo.transcript}</MetaContent>
                  </MetaSection>
                )}
              </VideoMeta>
            </VideoPlayerContent>
          </VideoPlayer>
        )}

        {allVideos.length === 0 && !uploading && searchResults.length === 0 && (
          <EmptyState>
            <EmptyIcon>🎬</EmptyIcon>
            <h3>No videos indexed yet</h3>
            <p>Upload your first video to get started with semantic search</p>
          </EmptyState>
        )}
      </Container>
    </PageWrapper>
  );
}

export default SemanticSearchVideo;

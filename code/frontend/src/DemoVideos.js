import React from 'react';
import styled from 'styled-components';

// Demo videos for each use case
const videos = [
  {
    title: 'AI Based Highlight & Movie',
    desc: 'Demo of AI-based highlight and movie generation.',
    url: '/demo_video/AI_based_highlight&Movie.mp4',
    thumbnail: '/demo_video/thumbnails/AI_based_highlight&Movie.jpg',
  },
  {
    title: 'AI Subtitle Generation',
    desc: 'Demo of AI subtitle generation.',
    url: '/demo_video/AISubtitleGeneration.mp4',
    thumbnail: '/demo_video/thumbnails/AISubtitleGeneration.jpg',
  },
  {
    title: 'Content Moderation',
    desc: 'Demo of content moderation workflow.',
    url: '/demo_video/ContentModeration.mp4',
    thumbnail: '/demo_video/thumbnails/ContentModeration.jpg',
  },
  {
    title: 'Dynamic Ad Insertion',
    desc: 'Demo of dynamic ad insertion.',
    url: '/demo_video/DynamicAdInsertion.mp4',
    thumbnail: '/demo_video/thumbnails/DynamicAdInsertion.jpg',
  },
  {
    title: 'AI Based Video Generation',
    desc: 'Prompt-to-video generation powered by Amazon Nova Reel.',
    url: '/demo_video/genAIVideoGeneration.mp4',
    thumbnail: '/demo_video/thumbnails/genAIVideoGeneration.jpg',
  },
  {
    title: 'Personalized Trailer',
    desc: 'Demo of personalized trailer generation.',
    url: '/demo_video/personalizedTrailer.mp4',
    thumbnail: '/demo_video/thumbnails/personalizedTrailer.jpg',
  },
  {
    title: 'AI Based Movie Trailer',
    desc: 'Demo of AI-based movie trailer.',
    url: '/demo_video/AI Based Movie trailer.mp4',
    thumbnail: '/demo_video/thumbnails/AI Based Movie trailer.jpg',
  },
  {
    title: 'Scene Summarization',
    desc: 'Demo of scene summarization.',
    url: '/demo_video/SceneSummarization.mp4',
    thumbnail: '/demo_video/thumbnails/SceneSummarization.jpg',
  },
  {
    title: 'Movie Poster Generation',
    desc: 'Demo of movie poster generation.',
    url: '/demo_video/moviePosterGeneration.mp4',
    thumbnail: '/demo_video/thumbnails/moviePosterGeneration.jpg',
  },
  {
    title: 'Movie Script Generation',
    desc: 'Demo of movie script generation.',
    url: '/demo_video/movieScriptGeneration.mp4',
    thumbnail: '/demo_video/thumbnails/movieScriptGeneration.jpg',
  },
  {
    title: 'Semantic Search',
    desc: 'Demo of semantic search in video.',
    url: '/demo_video/SemanticSearch.mp4',
    thumbnail: '/demo_video/thumbnails/SemanticSearch.jpg',
  },
  {
    title: 'Synthetic Voiceover',
    desc: 'Demo of synthetic voiceover.',
    url: '/demo_video/syntheticVoiceover.mp4',
    thumbnail: '/demo_video/thumbnails/syntheticVoiceover.jpg',
  },
  // ...existing code...
];

const VideoGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
  gap: 2rem;
  padding: 2rem;
`;
const VideoCard = styled.div`
  background: #23232a;
  border-radius: 16px;
  box-shadow: 0 0 16px #0ff2, 0 0 4px #fff inset;
  padding: 1rem;
  text-align: center;
  transition: box-shadow 0.2s;
  &:hover {
    box-shadow: 0 0 32px #0ff2, 0 0 8px #fff inset;
  }
`;
const VideoTitle = styled.h2`
  color: #0ff2;
`;
const VideoDesc = styled.p`
  color: #fff;
`;
const Player = styled.video`
  width: 100%;
  height: 220px;
  border: none;
  border-radius: 8px;
  margin-bottom: 1rem;
  background: #000;
`;
const Thumbnail = styled.img`
  width: 100%;
  height: 180px;
  object-fit: cover;
  border-radius: 8px;
  margin-bottom: 1rem;
  background: #111;
`;

export default function DemoVideos() {
  return (
    <VideoGrid>
      {videos.length === 0 ? (
        <VideoCard>
          <VideoTitle>Persistent Generated Videos Coming Soon</VideoTitle>
          <VideoDesc>Demo videos will be available here once provided.</VideoDesc>
        </VideoCard>
      ) : (
        videos.map((v, i) => (
          <VideoCard key={i}>
            <Thumbnail src={v.thumbnail} alt={v.title + ' thumbnail'} />
            <Player controls preload="none">
              <source src={v.url} type="video/mp4" />
              Your browser does not support the video tag.
            </Player>
            <VideoTitle>{v.title}</VideoTitle>
            <VideoDesc>{v.desc}</VideoDesc>
          </VideoCard>
        ))
      )}
    </VideoGrid>
  );
}

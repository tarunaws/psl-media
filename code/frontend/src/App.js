import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, NavLink } from 'react-router-dom';
import styled, { createGlobalStyle } from 'styled-components';

import About from './About';
import AdminUseCases from './AdminUseCases';
import AISubtitling from './AISubtitling';
import AskMe from './AskMe';
import ContentModeration from './ContentModeration';
import DemoVideos from './DemoVideos';
import DynamicAdInsertion from './DynamicAdInsertion';
import HighlightTrailer from './HighlightTrailer';
import Home from './Home';
import InteractiveShoppable from './InteractiveShoppable';
import MoviePosterGeneration from './MoviePosterGeneration';
import MovieScriptCreation from './MovieScriptCreation';
import SceneSummarization from './SceneSummarization';
import SemanticSearchText from './SemanticSearchText';
import SemanticSearchVideo from './SemanticSearchVideo';
import SyntheticVoiceover from './SyntheticVoiceover';
import AIBasedTrailer from './PersonalizedTrailer';
import UseCaseDetail from './UseCaseDetail';
import UseCases from './UseCases';
import VideoGeneration from './VideoGeneration';
import MediaSupplyChain from './MediaSupplyChain';
import { VisibleUseCasesProvider } from './VisibleUseCasesContext';

function App() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 12);
    handleScroll();
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <VisibleUseCasesProvider>
      <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <GlobalStyle />
        <AppContainer>
          <NeonNav $scrolled={scrolled}>
            <NavInner>
              <Brand to="/">
                <BrandLogo src="/psllogo.svg" alt="Persistent Systems" />
                <BrandCopy>
                  <BrandText>Media GenAI Lab</BrandText>
                  <BrandTagline>Product engineering for media & entertainment</BrandTagline>
                </BrandCopy>
              </Brand>
              <NavLinks>
                <NeonLink to="/">Home</NeonLink>
                <NeonLink to="/admin-usecases">Admin</NeonLink>
                <NeonLink to="/use-cases">Live Demo</NeonLink>
                <NeonLink to="/demo-videos">Demo Videos</NeonLink>
                <NeonLink to="/about">About</NeonLink>
              </NavLinks>
              <Spacer />
            </NavInner>
          </NeonNav>

          <MainContent>
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/use-cases" element={<UseCases />} />
              <Route path="/use-cases/:slug" element={<UseCaseDetail />} />
              <Route path="/movie-script-creation" element={<MovieScriptCreation />} />
              <Route path="/movie-poster-generation" element={<MoviePosterGeneration />} />
              <Route path="/content-moderation" element={<ContentModeration />} />
              <Route path="/personalized-trailers" element={<AIBasedTrailer />} />
              <Route path="/semantic-search-text" element={<SemanticSearchText />} />
              <Route path="/semantic-search-video" element={<SemanticSearchVideo />} />
              <Route path="/video-generation" element={<VideoGeneration />} />
              <Route path="/dynamic-ad-insertion" element={<DynamicAdInsertion />} />
              <Route path="/highlight-trailer" element={<HighlightTrailer />} />
              <Route path="/synthetic-voiceover" element={<SyntheticVoiceover />} />
              <Route path="/scene-summarization" element={<SceneSummarization />} />
              <Route path="/ai-subtitling" element={<AISubtitling />} />
              <Route path="/media-supply-chain" element={<MediaSupplyChain />} />
              <Route path="/demo-videos" element={<DemoVideos />} />
              <Route path="/about" element={<About />} />
                <Route path="/interactive-video" element={<InteractiveShoppable />} />
              <Route path="/tech-stack" element={<Navigate to="/" replace />} />
              <Route path="/admin-usecases" element={<AdminUseCases />} />
              <Route path="/solutions" element={<Navigate to="/use-cases" replace />} />
            </Routes>
          </MainContent>

          <AskMe />
        </AppContainer>
      </Router>
    </VisibleUseCasesProvider>
  );
}

export default App;

const GlobalStyle = createGlobalStyle`
  :root {
    color-scheme: dark;
  }

  * {
    box-sizing: border-box;
  }

  body {
    margin: 0;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: radial-gradient(circle at 10% 20%, #050816 0%, #02050c 60%, #01030a 100%);
    color: #f3f4f6;
    min-height: 100vh;
    -webkit-font-smoothing: antialiased;
  }

  a {
    color: inherit;
  }
`;

const AppContainer = styled.div`
  min-height: 100vh;
  display: flex;
  flex-direction: column;
`;

const MainContent = styled.main`
  flex: 1;
  padding: 120px 4vw 48px;
`;

const NeonNav = styled.nav`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 10;
  transition: background 0.2s ease, box-shadow 0.2s ease;
  background: ${props => (props.$scrolled ? 'rgba(7, 12, 22, 0.9)' : 'transparent')};
  box-shadow: ${props => (props.$scrolled ? '0 10px 40px rgba(0, 0, 0, 0.35)' : 'none')};
  border-bottom: 1px solid rgba(56, 189, 248, ${props => (props.$scrolled ? 0.12 : 0)});
`;

const NavInner = styled.div`
  display: flex;
  align-items: center;
  gap: 32px;
  padding: 20px clamp(16px, 4vw, 48px);
`;

const Brand = styled(NavLink)`
  display: inline-flex;
  align-items: center;
  gap: 0.65rem;
  padding-bottom: 4px;
  text-decoration: none;
  flex-shrink: 0;
`;

const BrandLogo = styled.img`
  height: clamp(34px, 4vw, 44px);
  filter: drop-shadow(0 10px 26px rgba(56, 189, 248, 0.28));
`;

const BrandCopy = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
`;

const BrandText = styled.span`
  font-weight: 700;
  font-size: 1.05rem;
  letter-spacing: 0.01em;
`;

const BrandTagline = styled.span`
  font-size: 0.78rem;
  color: #93c5fd;
`;

const NavLinks = styled.div`
  display: flex;
  align-items: center;
  gap: clamp(0.5rem, 1.6vw, 1.5rem);
`;

const NeonLink = styled(NavLink)`
  text-decoration: none;
  font-weight: 600;
  font-size: 0.95rem;
  color: #cbd5f5;
  padding-bottom: 4px;
  border-bottom: 2px solid transparent;
  transition: color 0.15s ease, border-color 0.15s ease;

  &.active {
    color: #f0f9ff;
    border-color: #38bdf8;
  }

  &:hover {
    color: #f8fafc;
  }
`;

const Spacer = styled.div`
  flex: 1;
`;


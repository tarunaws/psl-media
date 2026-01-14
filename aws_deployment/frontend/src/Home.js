import React from 'react';
import styled from 'styled-components';
import { NavLink } from 'react-router-dom';

const Hero = styled.section`
  position: relative;
  min-height: 56vh;
  display: flex;
  justify-content: center;
  text-align: left;
  padding: 5rem 1.25rem 3.25rem;
  background: radial-gradient(circle at 18% 18%, rgba(61, 110, 189, 0.55) 0%, rgba(12, 27, 52, 0.6) 45%, rgba(7, 14, 25, 0.92) 100%),
              url('/tech-abstract.svg') center/cover no-repeat;
  border-bottom: 1px solid rgba(99, 102, 241, 0.25);
  @media (max-width: 720px) {
    text-align: center;
    padding: 4rem 1.1rem 2.75rem;
  }
`;

const HeroInner = styled.div`
  width: min(1120px, 100%);
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 1rem;
  @media (max-width: 720px) {
    align-items: center;
  }
`;

const HeroBrand = styled.div`
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: clamp(0.6rem, 2vw, 0.9rem);
  margin-bottom: clamp(1.6rem, 3vw, 2.6rem);
  @media (max-width: 720px) {
    align-items: center;
  }
`;

const HeroLogo = styled.img`
  height: clamp(38px, 6vw, 60px);
  filter: drop-shadow(0 8px 22px rgba(56, 189, 248, 0.35));
`;

const HeroTagline = styled.span`
  font-size: clamp(1rem, 2.5vw, 1.35rem);
  font-weight: 600;
  color: #e2e9f5;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  @media (max-width: 720px) {
    letter-spacing: 0.08em;
  }
`;

const HighlightTag = styled.span`
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 999px;
  font-size: 0.85rem;
  letter-spacing: 0.4px;
  text-transform: uppercase;
  background: rgba(56, 189, 248, 0.12);
  color: #bae6fd;
  border: 1px solid rgba(56, 189, 248, 0.35);
  margin-bottom: 1.25rem;
`;

const Title = styled.h1`
  font-size: clamp(2.25rem, 4.6vw, 3.6rem);
  color: #ffffff;
  font-weight: 800;
  letter-spacing: -0.02em;
  margin: 0 0 0.75rem 0;
`;

const Subtitle = styled.p`
  font-size: clamp(1rem, 2.1vw, 1.2rem);
  color: #cbd5f5;
  margin: 0;
  line-height: 1.8;
  max-width: 840px;
  @media (max-width: 720px) {
    text-align: center;
  }
`;

const CTAGroup = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  justify-content: flex-start;
  margin-top: 1.75rem;
  @media (max-width: 720px) {
    justify-content: center;
  }
`;

const CTA = styled(NavLink)`
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  padding: 0.95rem 1.45rem;
  background: linear-gradient(135deg, #38bdf8, #6366f1);
  color: #0b1220;
  border-radius: 999px;
  font-weight: 800;
  text-decoration: none;
  letter-spacing: 0.3px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  box-shadow: 0 18px 40px rgba(56, 189, 248, 0.35);
  &:hover {
    transform: translateY(-2px) scale(1.01);
    box-shadow: 0 24px 46px rgba(99, 102, 241, 0.4);
  }
`;

export default function Home() {
  return (
    <>
      <Hero>
        <HeroInner>
          <HeroBrand>
            <HeroLogo src="/psllogo.svg" alt="Persistent logo" />
            <HeroTagline>Engineering experiences that matter</HeroTagline>
          </HeroBrand>
          <HighlightTag>Persistent media & entertainment engineering</HighlightTag>
          <Title>Media GenAI Lab for next-gen content ecosystems.</Title>
          <Subtitle>
            Media GenAI Lab combines Persistent&apos;s product engineering heritage with adaptive subtitling, synthetic voice, intelligent editing, and semantic discovery. Build resilient media workflows that scale across languages, channels, and audiences.
          </Subtitle>
          <CTAGroup>
            <CTA to="/use-cases">Explore All Solutions</CTA>
          </CTAGroup>
        </HeroInner>
      </Hero>
    </>
  );
}

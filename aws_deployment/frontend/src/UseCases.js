import React, { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import styled from 'styled-components';
import useCases from './data/useCases';

const PageWrap = styled.section`
  padding: 2.5rem 1.5rem 3.5rem;
  max-width: 1200px;
  margin: 0 auto;
`;

const Header = styled.div`
  text-align: center;
  max-width: 760px;
  margin: 0 auto 2rem;
`;

const Title = styled.h1`
  margin: 0 0 0.75rem;
  font-size: clamp(1.9rem, 4vw, 2.6rem);
  font-weight: 800;
  color: #f8fafc;
`;

const Lead = styled.p`
  margin: 0;
  font-size: 1.05rem;
  line-height: 1.8;
  color: #cbd5f5;
`;

const Grid = styled.div`
  display: grid;
  gap: 1.5rem;
  grid-template-columns: repeat(4, minmax(0, 1fr));

  @media (max-width: 1280px) {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  @media (max-width: 960px) {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  @media (max-width: 640px) {
    grid-template-columns: 1fr;
  }
`;

const Card = styled.article`
  background: linear-gradient(166deg, rgba(15, 28, 50, 0.9), rgba(32, 49, 80, 0.85));
  border-radius: 16px;
  border: 1px solid rgba(99, 102, 241, 0.18);
  padding: 0;
  text-align: left;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
  cursor: pointer;
  color: #e5efff;
  overflow: hidden;
  box-shadow: 0 22px 48px rgba(6, 15, 30, 0.55);
  min-height: 100%;
  display: flex;
  flex-direction: column;
  &:hover {
    transform: translateY(-6px);
    border-color: rgba(56, 189, 248, 0.45);
    box-shadow: 0 26px 56px rgba(14, 35, 68, 0.65);
  }
  &:focus-within,
  &:focus-visible {
    outline: none;
    border-color: rgba(56, 189, 248, 0.65);
    box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.18), 0 26px 56px rgba(14, 35, 68, 0.65);
  }
  @media (max-width: 640px) {
    min-height: auto;
  }
`;

const ThumbWrap = styled.div`
  height: 150px;
  background: rgba(12, 22, 42, 0.95);
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid rgba(79, 70, 229, 0.25);
`;

const Thumb = styled.img`
  height: 72px;
  width: 72px;
  object-fit: contain;
  filter: drop-shadow(0 8px 24px rgba(56, 189, 248, 0.38));
`;

const Body = styled.div`
  padding: 1.15rem 1.15rem 1.35rem;
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  gap: 0.6rem;
`;

const CardTitle = styled.h2`
  color: #f8fafc;
  margin: 0 0 0.6rem 0;
  font-size: 1.18rem;
  font-weight: 800;
`;

const CardDesc = styled.p`
  color: #b6c5ef;
  margin: 0;
  font-size: 0.98rem;
  line-height: 1.65;
  flex: 1 1 auto;
`;

const StatusTag = styled.span`
  display: inline-flex;
  align-items: center;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  margin-bottom: 0.75rem;
  color: ${({ $variant }) => ($variant === 'coming-soon' ? '#fef9c3' : '#c7d2fe')};
  background: ${({ $variant }) => ($variant === 'coming-soon' ? 'rgba(234, 179, 8, 0.18)' : 'rgba(99, 102, 241, 0.2)')};
  border: 1px solid ${({ $variant }) => ($variant === 'coming-soon' ? 'rgba(250, 204, 21, 0.32)' : 'rgba(129, 140, 248, 0.3)')};
`;

const LaunchButton = styled.button`
  margin-top: auto;
  align-self: flex-start;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.45rem;
  padding: 0.55rem 1.1rem;
  border-radius: 999px;
  border: none;
  background: linear-gradient(135deg, #38bdf8, #6366f1);
  color: #041427;
  font-weight: 700;
  font-size: 0.9rem;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;

  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 16px 32px rgba(56, 189, 248, 0.35);
  }

  &:focus-visible {
    outline: none;
    box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.4);
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    box-shadow: none;
    transform: none;
  }
`;

const FooterNote = styled.p`
  margin: 2.5rem auto 0;
  max-width: 640px;
  text-align: center;
  color: #94a3e6;
  font-size: 0.95rem;
  line-height: 1.7;
`;

const LoadingState = styled.div`
  text-align: center;
  padding: 3rem 1rem 4rem;
  color: #a5b4fc;
  font-size: 1.05rem;
`;

function UseCases() {
  const navigate = useNavigate();
  const allowedUseCases = new Set(['dynamic-ad-insertion', 'highlight-trailer', 'subtitle-lab']);
  const solutions = useCases.filter((useCase) => !useCase.hidden && allowedUseCases.has(useCase.id));

  const handleNavigate = useCallback((solution) => {
    if (solution.path) {
      navigate(solution.path);
    }
  }, [navigate]);

  const handleCardKeyDown = useCallback((event, solution) => {
    if ((event.key === 'Enter' || event.key === ' ') && solution.path) {
      event.preventDefault();
      handleNavigate(solution);
    }
  }, [handleNavigate]);

  const onLaunch = useCallback((event, solution) => {
    event.stopPropagation();
    const destination = solution.workspacePath || solution.path;
    if (destination) {
      navigate(destination);
    }
  }, [navigate]);

  return (
    <PageWrap>
      <Header>
        <Title>Solutions engineered for modern media pipelines</Title>
        <Lead>
          Pair Persistent&apos;s product engineering expertise with our GenAI accelerators. Customizable solution modules drop into your workflows—complete with governance, review loops, and observability.
        </Lead>
      </Header>
      <Grid>
        {solutions.map((solution) => {
          const isComingSoon = solution.status === 'coming-soon';
          return (
            <Card
              key={solution.id || solution.title}
              id={solution.id}
              onClick={() => handleNavigate(solution)}
              onKeyDown={(event) => handleCardKeyDown(event, solution)}
              tabIndex={0}
              role="link"
              aria-label={`${solution.title} solution`}
            >
              <ThumbWrap>
                <Thumb src={solution.image} alt={solution.title} onError={(e) => { e.currentTarget.src = '/usecases/placeholder.svg'; }} />
              </ThumbWrap>
              <Body>
                <CardTitle>{solution.title}</CardTitle>
                {solution.status === 'coming-soon' && (
                  <StatusTag $variant="coming-soon">Coming soon</StatusTag>
                )}
                <CardDesc>{solution.cardDescription}</CardDesc>
                <LaunchButton
                  type="button"
                  onClick={(event) => onLaunch(event, solution)}
                  disabled={!solution.path}
                >
                  {isComingSoon ? 'View details' : 'Launch'}
                </LaunchButton>
              </Body>
            </Card>
          );
        })}
      </Grid>
      <FooterNote>
        Looking for something bespoke? Let&apos;s co-create guardrailed LLM workflows, episodic automation, and enterprise integrations tailored to your content supply chain.
      </FooterNote>
    </PageWrap>
  );
}

export default UseCases;

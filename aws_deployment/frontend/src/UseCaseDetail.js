import React, { useEffect, useMemo } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import styled from 'styled-components';
import useCases from './data/useCases';

const Page = styled.section`
  padding: 3rem 1.5rem 4rem;
  max-width: 920px;
  margin: 0 auto;
  color: #e2e9f5;
`;

const BackButton = styled.button`
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.45rem 0.9rem;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 255, 0.35);
  background: rgba(15, 28, 52, 0.75);
  color: #dbe4ff;
  font-weight: 600;
  font-size: 0.9rem;
  cursor: pointer;
  margin-bottom: 1.5rem;
  transition: transform 0.2s ease, border-color 0.2s ease;

  &:hover {
    transform: translateX(-2px);
    border-color: rgba(56, 189, 248, 0.6);
  }

  &:focus-visible {
    outline: none;
    box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.35);
  }
`;

const Title = styled.h1`
  margin: 0 0 0.75rem;
  font-size: clamp(2rem, 5vw, 2.85rem);
  font-weight: 800;
  color: #ffffff;
`;

const StatusTag = styled.span`
  display: inline-flex;
  align-items: center;
  padding: 0.2rem 0.65rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: ${({ $variant }) => ($variant === 'coming-soon' ? '#fef3c7' : '#c7d2fe')};
  background: ${({ $variant }) => ($variant === 'coming-soon' ? 'rgba(251, 191, 36, 0.16)' : 'rgba(99, 102, 241, 0.22)')};
  border: 1px solid ${({ $variant }) => ($variant === 'coming-soon' ? 'rgba(250, 204, 21, 0.35)' : 'rgba(129, 140, 248, 0.35)')};
  margin-right: 0.65rem;
`;

const Summary = styled.p`
  font-size: 1.08rem;
  line-height: 1.8;
  color: #cbd5f5;
  margin: 0 0 1.75rem;
`;

const HighlightsHeading = styled.h2`
  margin: 2.5rem 0 1rem;
  color: #f8fafc;
  font-size: 1.35rem;
  font-weight: 700;
`;

const HighlightsList = styled.ul`
  margin: 0;
  padding-left: 1.2rem;
  display: grid;
  gap: 0.85rem;
`;

const HighlightItem = styled.li`
  color: #b6c5ef;
  line-height: 1.7;
`;

const ActionRow = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 0.85rem;
  margin-top: 2.5rem;
`;

const PrimaryAction = styled.button`
  padding: 0.75rem 1.35rem;
  border-radius: 999px;
  border: none;
  background: linear-gradient(135deg, #38bdf8, #6366f1);
  color: #041427;
  font-weight: 700;
  font-size: 0.95rem;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 18px 36px rgba(56, 189, 248, 0.32);
  }

  &:focus-visible {
    outline: none;
    box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.45);
  }
`;

const SecondaryAction = styled.button`
  padding: 0.75rem 1.3rem;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 255, 0.35);
  background: rgba(18, 32, 56, 0.78);
  color: #dce7ff;
  font-weight: 700;
  font-size: 0.95rem;
  cursor: pointer;
  transition: transform 0.2s ease, border-color 0.2s ease;

  &:hover {
    transform: translateY(-2px);
    border-color: rgba(56, 189, 248, 0.5);
  }

  &:focus-visible {
    outline: none;
    box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.35);
  }
`;

export default function UseCaseDetail() {
  const { slug } = useParams();
  const navigate = useNavigate();

  const useCase = useMemo(() => useCases.find((item) => item.id === slug), [slug]);

  useEffect(() => {
    if (!useCase || useCase.hidden) {
      navigate('/use-cases', { replace: true });
    }
  }, [useCase, navigate]);

  if (!useCase || useCase.hidden) {
    return null;
  }

  const isComingSoon = useCase.status === 'coming-soon';

  return (
    <Page>
      <BackButton type="button" onClick={() => navigate('/use-cases')}>
        ← Back to use cases
      </BackButton>
      <div>
        {isComingSoon && <StatusTag $variant="coming-soon">Coming soon</StatusTag>}
        <Title>{useCase.title}</Title>
      </div>
      <Summary>{useCase.detailDescription}</Summary>
      {useCase.highlights?.length > 0 && (
        <>
          <HighlightsHeading>What you can expect</HighlightsHeading>
          <HighlightsList>
            {useCase.highlights.map((point, index) => (
              <HighlightItem key={index}>{point}</HighlightItem>
            ))}
          </HighlightsList>
        </>
      )}
      <ActionRow>
        {!isComingSoon && (
            <PrimaryAction
              type="button"
              onClick={() => navigate(useCase.workspacePath || useCase.path)}
            >
            Launch workspace
          </PrimaryAction>
        )}
        <SecondaryAction type="button" onClick={() => navigate('/use-cases')}>
          Browse all solutions
        </SecondaryAction>
      </ActionRow>
    </Page>
  );
}

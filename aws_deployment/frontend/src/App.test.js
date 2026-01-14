import { render, screen } from '@testing-library/react';
import App from './App';

test('renders Media GenAI Lab hero content', () => {
  render(<App />);
  expect(
    screen.getByRole('heading', {
      name: /Media GenAI Lab for next-gen content ecosystems\./i,
    }),
  ).toBeInTheDocument();

  expect(
    screen.getByText(/Persistent media & entertainment engineering/i),
  ).toBeInTheDocument();
});
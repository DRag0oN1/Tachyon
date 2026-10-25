import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { blockedDesignFixture, strategyFixture } from '../test/strategy';
import { ArchitecturesPanel } from './ArchitecturesPanel';

it('compares supplied subsystems and labels alternatives as schematic engineering intent', () => {
  const session = strategyFixture(), onRealize = vi.fn(), onSelect = vi.fn();
  render(<ArchitecturesPanel session={session} loading={false} selectedArchitectureId={session.architectures[0].id} onSelectArchitecture={onSelect} onRealizeArchitecture={onRealize} onStrategy={vi.fn()} onGenerate={vi.fn()} />);
  expect(screen.getByRole('table')).toHaveTextContent('Linear elevator parallel gripper');
  expect(screen.getByRole('table')).toHaveTextContent('Opposed rollers with orientation guides');
  expect(screen.getByRole('img', { name: /not CAD/ })).toBeVisible();
  expect(screen.getByText(/mechanically different proposals for one learned family/)).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: /Check parts and realize concept/ }));
  expect(onRealize).toHaveBeenCalledWith(session.architectures[0].id);
  fireEvent.click(screen.getByRole('button', { name: /ALTERNATIVE B/ }));
  expect(onSelect).toHaveBeenCalledWith(session.architectures[1].id);
});

it('shows missing mechanisms and offers reference inspection for a blocked response', () => {
  const session = strategyFixture(), blocked = blockedDesignFixture(), inspect = vi.fn();
  render(<ArchitecturesPanel session={session} loading={false} selectedArchitectureId={session.architectures[0].id} onSelectArchitecture={vi.fn()} onRealizeArchitecture={vi.fn()} onInspectReference={inspect} onStrategy={vi.fn()} onGenerate={vi.fn()} realization={{ state: 'loaded', architectureId: blocked.architectureId, result: blocked }} />);
  expect(screen.getByRole('status')).toHaveTextContent('CAD blocked');
  expect(screen.getByRole('status')).toHaveTextContent('No qualified scoring mechanism recipe');
  expect(screen.getByRole('status')).toHaveTextContent('No architecture CAD is available');
  fireEvent.click(screen.getByRole('button', { name: 'Inspect reference' }));
  expect(inspect).toHaveBeenCalledOnce();
});

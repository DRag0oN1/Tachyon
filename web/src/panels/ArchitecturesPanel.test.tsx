import { fireEvent, render, screen, within } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { blockedDesignFixture, editableDesignFixture, strategyFixture } from '../test/strategy';
import type { DesignCatalog } from '../api/designCatalog';
import { ArchitecturesPanel } from './ArchitecturesPanel';

function catalog():DesignCatalog {
  return {schemaVersion:1,kind:'tachyon.design_catalog',saved:[],canGenerateAdditionalArchitectures:false,
    architectures:strategyFixture().architectures.map(a=>({architectureId:a.id,alternative:a.alternative,
      recipeAvailable:a.alternative==='A',recipeKind:a.alternative==='A'?'authored_component_recipe':'none',
      requestedPlacements:a.alternative==='A'?1:0,roleIds:a.alternative==='A'?['scorer']:[],qualification:'not_checked'}))};
}

it('compares supplied subsystems and labels alternatives as schematic engineering intent', () => {
  const session = strategyFixture(), onRealize = vi.fn(), onSelect = vi.fn();
  const props={session,loading:false,onSelectArchitecture:onSelect,onRealizeArchitecture:onRealize,onStrategy:vi.fn(),onGenerate:vi.fn(),designCatalog:catalog()};
  const view=render(<ArchitecturesPanel {...props} selectedArchitectureId={session.architectures[0].id}/>);
  expect(screen.getByRole('heading',{name:'Choose your machine.'})).toBeVisible();
  const mechanisms=screen.getByRole('heading',{name:'Inside this machine'}).parentElement!;
  expect(mechanisms).toHaveTextContent('Opposed rollers with orientation guides');
  expect(within(mechanisms).getAllByRole('listitem')).toHaveLength(session.architectures[0].subsystems.length);
  for(const img of screen.getAllByRole('img', { name: /not CAD/ }))expect(img).toBeVisible();
  expect(screen.getByText('Different mechanisms. The same learned strategy.')).toBeVisible();
  expect(screen.getByText(/not an unrestricted robot generator/)).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'Assemble local recipe' }));
  expect(onRealize).toHaveBeenCalledWith(session.architectures[0].id);
  fireEvent.click(screen.getByRole('button', { name: /DESIGN 02/ }));
  expect(onSelect).toHaveBeenCalledWith(session.architectures[1].id);
  view.rerender(<ArchitecturesPanel {...props} selectedArchitectureId={session.architectures[1].id}/>);
  expect(screen.getByRole('heading',{name:'Inside this machine'}).parentElement).toHaveTextContent('Linear elevator parallel gripper');
  expect(screen.queryByRole('button',{name:'Assemble local recipe'})).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'Review build requirements'}));
  expect(screen.getByRole('status')).toHaveTextContent('Assembly still required');
  expect(onRealize).toHaveBeenCalledOnce();
});

it('shows missing mechanisms while retaining the conceptual schematic for a blocked response', () => {
  const session = strategyFixture(), blocked = blockedDesignFixture(), inspect = vi.fn();
  render(<ArchitecturesPanel session={session} loading={false} selectedArchitectureId={session.architectures[0].id} onSelectArchitecture={vi.fn()} onRealizeArchitecture={vi.fn()} onInspectReference={inspect} onStrategy={vi.fn()} onGenerate={vi.fn()} designCatalog={catalog()} realization={{ state: 'loaded', architectureId: blocked.architectureId, result: blocked }} />);
  expect(screen.getByRole('status')).toHaveTextContent('Assembly still required');
  expect(screen.getByRole('status')).toHaveTextContent('No qualified scoring mechanism recipe');
  expect(screen.getByText('Conceptual arrangement from this proposal. Not CAD or a verified mechanical layout.')).toBeVisible();
  expect(screen.queryByRole('button', { name: 'Inspect assembly' })).not.toBeInTheDocument();
  expect(inspect).not.toHaveBeenCalled();
});

it('opens a cached partial assembly without treating recipe availability as qualification',()=>{
  const session=strategyFixture(),design=editableDesignFixture(),inspect=vi.fn(),realize=vi.fn();
  render(<ArchitecturesPanel session={session} loading={false} selectedArchitectureId={design.architectureId}
    onSelectArchitecture={vi.fn()} onRealizeArchitecture={realize} onStrategy={vi.fn()} onGenerate={vi.fn()}
    designCatalog={catalog()} designSessions={{[design.architectureId]:design}} onInspectAssembly={inspect}/>);
  expect(screen.getByRole('button',{name:/DESIGN 01/})).toHaveTextContent('Partial assembly');
  expect(screen.queryByText('Realized assembly')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'Inspect assembly'}));
  expect(inspect).toHaveBeenCalledExactlyOnceWith(design.architectureId);
  expect(realize).not.toHaveBeenCalled();
});

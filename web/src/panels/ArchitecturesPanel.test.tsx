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
  const index=catalog(),openSaved=vi.fn();
  index.saved=[{designId:design.designId,architectureId:design.architectureId,strategyId:design.strategyId,revisionId:'older-index-revision',hasCandidate:false}];
  render(<ArchitecturesPanel session={session} loading={false} selectedArchitectureId={design.architectureId}
    onSelectArchitecture={vi.fn()} onRealizeArchitecture={realize} onStrategy={vi.fn()} onGenerate={vi.fn()}
    designCatalog={index} designSessions={{[design.architectureId]:design}} onInspectAssembly={inspect} onOpenSavedDesign={openSaved}/>);
  expect(screen.getByRole('button',{name:/DESIGN 01/})).toHaveTextContent('Partial assembly · development CAD');
  expect(screen.getByText(/This development CAD is a partial assembly, not a complete robot/)).toBeVisible();
  expect(screen.queryByText('Realized assembly')).not.toBeInTheDocument();
  expect(screen.queryByRole('button',{name:'Open development CAD'})).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'Inspect assembly'}));
  expect(inspect).toHaveBeenCalledExactlyOnceWith(design.architectureId);
  expect(realize).not.toHaveBeenCalled();
  expect(openSaved).not.toHaveBeenCalled();
});

it('opens the matching saved revision by design ID for requalification without claiming its current rights',()=>{
  const session=strategyFixture(),design=editableDesignFixture(),index=catalog();
  const openSaved=vi.fn(),realize=vi.fn(),inspect=vi.fn();
  index.saved=[{designId:'saved-development-assembly',architectureId:design.architectureId,strategyId:design.strategyId,revisionId:'saved-revision',hasCandidate:true}];
  render(<ArchitecturesPanel session={session} loading={false} selectedArchitectureId={design.architectureId}
    onSelectArchitecture={vi.fn()} onRealizeArchitecture={realize} onStrategy={vi.fn()} onGenerate={vi.fn()}
    designCatalog={index} onInspectAssembly={inspect} onOpenSavedDesign={openSaved}/>);
  expect(screen.getByRole('button',{name:/DESIGN 01/})).toHaveTextContent('Saved development CAD · check on open');
  expect(screen.getByRole('button',{name:/DESIGN 02/})).toHaveTextContent('Distinct proposal · no CAD yet');
  expect(screen.getByText('Saved assembly metadata only. Source rights and assembly qualification are checked again when opened.')).toBeVisible();
  expect(screen.getByText('Conceptual arrangement from this proposal. Not CAD or a verified mechanical layout.')).toBeVisible();
  expect(screen.queryByText('Realized assembly')).not.toBeInTheDocument();
  expect(screen.queryByRole('button',{name:'Inspect assembly'})).not.toBeInTheDocument();
  expect(screen.queryByRole('button',{name:'Assemble local recipe'})).not.toBeInTheDocument();
  const open=screen.getByRole('button',{name:'Open development CAD'});
  expect(open).toHaveClass('primary-button');
  fireEvent.click(open);
  expect(openSaved).toHaveBeenCalledExactlyOnceWith('saved-development-assembly');
  expect(realize).not.toHaveBeenCalled();expect(inspect).not.toHaveBeenCalled();
});

it('keeps Design 02 as its distinct proposal when only Design 01 has saved CAD',()=>{
  const session=strategyFixture(),design=editableDesignFixture(),index=catalog(),onSelect=vi.fn();
  const openSaved=vi.fn(),realize=vi.fn();
  index.saved=[{designId:design.designId,architectureId:design.architectureId,strategyId:design.strategyId,revisionId:design.revisionId,hasCandidate:false}];
  const props={session,loading:false,onSelectArchitecture:onSelect,onRealizeArchitecture:realize,
    onStrategy:vi.fn(),onGenerate:vi.fn(),designCatalog:index,onOpenSavedDesign:openSaved};
  const view=render(<ArchitecturesPanel {...props} selectedArchitectureId={design.architectureId}/>);
  fireEvent.click(screen.getByRole('button',{name:/DESIGN 02/}));
  expect(onSelect).toHaveBeenCalledExactlyOnceWith(session.architectures[1].id);
  view.rerender(<ArchitecturesPanel {...props} selectedArchitectureId={session.architectures[1].id}/>);
  expect(screen.getByRole('heading',{name:'Guided elevator'})).toBeVisible();
  expect(screen.getByRole('button',{name:/DESIGN 02/})).toHaveTextContent('Distinct proposal · no CAD yet');
  expect(screen.getByText(/This design is a distinct proposal, not yet CAD/)).toBeVisible();
  expect(screen.getByRole('heading',{name:'Inside this machine'}).parentElement).toHaveTextContent('Linear elevator parallel gripper');
  expect(screen.queryByRole('button',{name:'Open development CAD'})).not.toBeInTheDocument();
  expect(screen.queryByRole('button',{name:'Assemble local recipe'})).not.toBeInTheDocument();
  for(const image of screen.getAllByRole('img',{name:/not CAD/}))expect(image).toBeVisible();
  fireEvent.click(screen.getByRole('button',{name:'Review build requirements'}));
  expect(screen.getByRole('status')).toHaveTextContent('Assembly still required');
  expect(openSaved).not.toHaveBeenCalled();expect(realize).not.toHaveBeenCalled();
});

it.each(['missing-revision','empty-revision','other-architecture','other-strategy'] as const)(
  'does not advertise a saved CAD opening for %s metadata',fault=>{
    const session=strategyFixture(),design=editableDesignFixture(),index=catalog();
    const openSaved=vi.fn(),realize=vi.fn();
    index.saved=[{designId:design.designId,architectureId:design.architectureId,strategyId:design.strategyId,
      revisionId:design.revisionId,hasCandidate:true}];
    if(fault==='missing-revision')index.saved[0].revisionId=null;
    if(fault==='empty-revision')index.saved[0].revisionId='';
    if(fault==='other-architecture')index.saved[0].architectureId=session.architectures[1].id;
    if(fault==='other-strategy')index.saved[0].strategyId='different-strategy';
    render(<ArchitecturesPanel session={session} loading={false} selectedArchitectureId={design.architectureId}
      onSelectArchitecture={vi.fn()} onRealizeArchitecture={realize} onStrategy={vi.fn()} onGenerate={vi.fn()}
      designCatalog={index} onOpenSavedDesign={openSaved}/>);
    expect(screen.queryByRole('button',{name:'Open development CAD'})).not.toBeInTheDocument();
    expect(screen.getByRole('button',{name:/DESIGN 01/})).toHaveTextContent('Authored recipe available');
    fireEvent.click(screen.getByRole('button',{name:'Assemble local recipe'}));
    expect(realize).toHaveBeenCalledExactlyOnceWith(design.architectureId);
    expect(openSaved).not.toHaveBeenCalled();
  },
);

it('keeps the optional saved-CAD opening disabled until its parent callback is supplied',()=>{
  const session=strategyFixture(),design=editableDesignFixture(),index=catalog();
  index.saved=[{designId:design.designId,architectureId:design.architectureId,strategyId:design.strategyId,revisionId:design.revisionId,hasCandidate:false}];
  render(<ArchitecturesPanel session={session} loading={false} selectedArchitectureId={design.architectureId}
    onSelectArchitecture={vi.fn()} onRealizeArchitecture={vi.fn()} onStrategy={vi.fn()} onGenerate={vi.fn()}
    designCatalog={index}/>);
  expect(screen.getByRole('button',{name:'Open development CAD'})).toBeDisabled();
  expect(screen.queryByRole('button',{name:'Assemble local recipe'})).not.toBeInTheDocument();
});

it('keeps CAD availability unknown when the optional catalog is unavailable',()=>{
  const session=strategyFixture();
  render(<ArchitecturesPanel session={session} loading={false} selectedArchitectureId={session.architectures[1].id}
    onSelectArchitecture={vi.fn()} onRealizeArchitecture={vi.fn()} onStrategy={vi.fn()} onGenerate={vi.fn()}/>);
  expect(screen.getByRole('button',{name:/DESIGN 02/})).toHaveTextContent('Architecture only');
  expect(screen.getByText(/Recipe availability is unknown/)).toBeVisible();
  expect(screen.queryByRole('button',{name:'Open development CAD'})).not.toBeInTheDocument();
});

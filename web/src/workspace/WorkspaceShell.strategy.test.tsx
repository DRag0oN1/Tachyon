import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { api } from '../api/client';
import { capabilitiesFixture, catalogFixture, componentFixture, workspaceFixture } from '../test/contracts';
import { blockedDesignFixture, editableDesignFixture, strategyFixture } from '../test/strategy';
import { WorkspaceShell } from './WorkspaceShell';
import type { DesignSession } from '../api/strategy';
import type { DesignCatalog } from '../api/designCatalog';

vi.mock('../api/client', async original => ({ ...await original<object>(), api: {
  health: vi.fn(), catalog: vi.fn(), capabilities: vi.fn(), workspace: vi.fn(), patchWorkspace: vi.fn(),
  strategyStatus: vi.fn(), generateStrategy: vi.fn(), post: vi.fn(), get: vi.fn(),
} }));
// Contract stubs deliberately provide no browser or authentic geometry evidence.
vi.mock('../viewer/AssemblyScene', () => ({ AssemblyScene: () => <div data-testid="unit-reference-scene" /> }));
vi.mock('../viewer/DesignAssemblyScene', () => ({ DesignAssemblyScene: ({ session, activeActionId, focusKey, onSelectInstance }: {
  session: DesignSession; activeActionId: string | null; focusKey: number; onSelectInstance: (id: string) => void;
}) => <div data-testid="unit-design-scene" data-revision={session.candidate?.id ?? session.revisionId} data-engineering-hash={(session.candidate??session.accepted)?.engineeringHash} data-bindings-revision={(session.candidate?session.candidateBindings:session.bindings)?.revisionId} data-action={activeActionId} data-focus={focusKey}><button onClick={() => onSelectInstance('unit-scorer')}>Select original software fixture</button></div> }));

function designCatalog():DesignCatalog {
  return {schemaVersion:1,kind:'tachyon.design_catalog',canGenerateAdditionalArchitectures:false,saved:[],
    architectures:strategyFixture().architectures.map(a=>({architectureId:a.id,alternative:a.alternative,
      recipeAvailable:a.alternative==='A',recipeKind:a.alternative==='A'?'authored_component_recipe':'none',
      requestedPlacements:a.alternative==='A'?1:0,roleIds:a.alternative==='A'?['scorer']:[],qualification:'not_checked'}))};
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(api.health).mockResolvedValue({ status: 'ok', version: '0.1.0', cadProfile: 'user_provided_local', providerConfigured: false });
  vi.mocked(api.catalog).mockResolvedValue(catalogFixture);
  vi.mocked(api.capabilities).mockResolvedValue({ ...capabilitiesFixture, canGenerateStrategy: true });
  vi.mocked(api.workspace).mockResolvedValue({ ...workspaceFixture, activeComponentId: componentFixture.id });
  vi.mocked(api.patchWorkspace).mockResolvedValue(workspaceFixture);
  vi.mocked(api.strategyStatus).mockResolvedValue({ available: true, competitionId: 'v5-override-v2.1', environmentId: 'override_abstract_strategy_v2_cups' });
  vi.mocked(api.generateStrategy).mockResolvedValue(strategyFixture());
  vi.mocked(api.get).mockImplementation(async path=>{
    if(path==='/api/designs/catalog')return designCatalog();
    throw new Error(`Unexpected test GET: ${path}`);
  });
});
async function home() { render(<WorkspaceShell />); await waitFor(() => expect(screen.getByRole('button', { name: 'Generate Strategy' })).toBeEnabled()); }

it.each(['Generate Strategy', 'Create Robot'])('enters through %s without requiring the other screen or any CAD request', async name => {
  await home(); fireEvent.click(screen.getByRole('button', { name }));
  expect(await screen.findByRole('heading', { name: name === 'Create Robot' ? 'Choose your machine.' : 'Low quadrant scoring cycles' })).toBeVisible();
  expect(api.generateStrategy).toHaveBeenCalledOnce();
  expect(api.post).not.toHaveBeenCalled();
  expect(screen.queryByTestId('unit-reference-scene')).not.toBeInTheDocument();
  expect(screen.queryByTestId('unit-design-scene')).not.toBeInTheDocument();
  expect(screen.getByRole('main')).toHaveAttribute('data-canvas',name==='Create Robot'?'concept':'empty');
  expect(screen.getAllByRole('dialog')).toHaveLength(1);
});
it('keeps a blocked architecture schematic separate from source CAD, reports missing parts, and refuses edits', async () => {
  vi.mocked(api.post).mockResolvedValue(blockedDesignFixture());
  await home(); fireEvent.click(screen.getByRole('button', { name: 'Create Robot' }));
  fireEvent.click(await screen.findByRole('button', { name: 'Assemble local recipe' }));
  expect(await screen.findByRole('heading',{name:'Assembly still required'})).toBeVisible();
  expect(screen.getByRole('heading',{name:'Assembly still required'}).parentElement).toHaveTextContent('No qualified scoring mechanism recipe');
  expect(api.post).toHaveBeenCalledWith('/api/designs/realize', { architecture_id: strategyFixture().architectures[0].id });
  expect(screen.queryByTestId('unit-reference-scene')).not.toBeInTheDocument();
  expect(screen.getByTestId('concept-canvas')).toHaveTextContent('Not CAD');
  expect(screen.queryByTestId('unit-design-scene')).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Expand assistant' }));
  fireEvent.change(screen.getByLabelText('Design request'), { target: { value: 'raise scorer' } });
  fireEvent.click(screen.getByRole('button', { name: 'Send request' }));
  expect(await screen.findByText(/Editing requires a qualified mechanism recipe, components, and assembly placement/)).toBeVisible();
  expect(api.post).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole('button', { name: 'Components' }));
  expect(screen.getByRole('dialog', { name: 'Components' })).toBeVisible();
  expect(screen.getByText(/These are separate local source components, not its realized assembly/)).toBeVisible();
});
it('retains the previous strategy if a fresh generation fails; switching panels reuses it without unrelated source CAD', async () => {
  await home(); fireEvent.click(screen.getByRole('button', { name: 'Generate Strategy' }));
  await screen.findByRole('heading', { name: 'Low quadrant scoring cycles' });
  vi.mocked(api.generateStrategy).mockRejectedValueOnce(new Error('Frozen inference failed'));
  fireEvent.click(screen.getByRole('button', { name: 'Rerun the seeded policy' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Frozen inference failed');
  expect(screen.getByRole('heading', { name: 'Low quadrant scoring cycles' })).toBeVisible();
  fireEvent.click(within(screen.getByRole('navigation', { name: 'Workspace tools' })).getByRole('button', { name: 'Design' }));
  expect(screen.getByRole('heading', { name: 'Choose your machine.' })).toBeVisible();
  expect(api.generateStrategy).toHaveBeenCalledTimes(2);
  expect(screen.queryByTestId('unit-reference-scene')).not.toBeInTheDocument();
  expect(screen.getByTestId('concept-canvas')).toHaveTextContent('CONCEPTUAL SCHEMATIC');
});
it('reflects status loading/unavailability and retries without relying on the legacy CAD capability', async () => {
  vi.mocked(api.strategyStatus).mockRejectedValueOnce(new Error('Checkpoint service unavailable'));
  render(<WorkspaceShell />);
  expect(await screen.findByRole('alert')).toHaveTextContent('Checkpoint service unavailable');
  expect(screen.getByRole('button', { name: 'Generate Strategy' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Retry strategy connection' }));
  await waitFor(() => expect(screen.getByRole('button', { name: 'Generate Strategy' })).toBeEnabled());
});
it('previews the selected design, applies exactly that candidate, and passes action/focus and reverse bindings', async () => {
  const accepted = editableDesignFixture();
  const candidate = structuredClone(accepted);
  candidate.candidate = { ...structuredClone(accepted.accepted!), id: 'unit-candidate', parentRevisionId: accepted.revisionId, engineeringHash: 'c'.repeat(64) };
  candidate.candidateBindings = { ...structuredClone(accepted.bindings!), revisionId: 'unit-candidate', engineeringHash: 'c'.repeat(64) };
  candidate.candidateWorldTransforms = structuredClone(accepted.worldTransforms);
  const applied = { ...structuredClone(candidate), accepted: candidate.candidate, bindings: candidate.candidateBindings, revisionId: 'unit-candidate', candidate: null, candidateBindings: null, candidateWorldTransforms: {}, previous: accepted.accepted };
  const undone = { ...structuredClone(accepted), revisionId: 'unit-undone', accepted: { ...structuredClone(accepted.accepted!), id: 'unit-undone', parentRevisionId: 'unit-candidate' }, bindings: { ...structuredClone(accepted.bindings!), revisionId: 'unit-undone' } };
  vi.mocked(api.post).mockResolvedValueOnce(accepted).mockResolvedValueOnce(candidate).mockResolvedValueOnce(applied).mockResolvedValueOnce(undone);
  await home(); fireEvent.click(screen.getByRole('button', { name: 'Create Robot' }));
  fireEvent.click(await screen.findByRole('button', { name: 'Assemble local recipe' }));
  await screen.findByTestId('unit-design-scene');
  expect(screen.getByTestId('design-status')).toHaveTextContent('NOT AUTHENTIC VEX / NOT COMPLETE ROBOT');
  fireEvent.click(screen.getByRole('button', { name: 'Select original software fixture' }));
  fireEvent.click(screen.getByRole('button', { name: 'Place an alliance Pin' }));
  expect(screen.getByTestId('unit-design-scene')).toHaveAttribute('data-action', 'place_alliance');
  const before = Number(screen.getByTestId('unit-design-scene').dataset.focus);
  fireEvent.click(screen.getByRole('button', { name: 'Expand assistant' }));
  fireEvent.click(screen.getByRole('button', { name: 'Preview raised' }));
  await waitFor(() => expect(screen.getByTestId('unit-design-scene')).toHaveAttribute('data-revision', 'unit-candidate'));
  expect(api.post).toHaveBeenNthCalledWith(2, '/api/designs/unit-design/preview', { base_revision_id: 'unit-accepted', configuration_id: 'raised' });
  expect(Number(screen.getByTestId('unit-design-scene').dataset.focus)).toBeGreaterThan(before);
  fireEvent.click(screen.getByRole('button', { name: 'Apply' }));
  expect(await screen.findByText('The server accepted the exact previewed revision.')).toBeVisible();
  expect(api.post).toHaveBeenNthCalledWith(3, '/api/designs/unit-design/decision', { base_revision_id: 'unit-accepted', candidate_revision_id: 'unit-candidate', action: 'apply' });
  expect(screen.getByRole('button', { name: 'Undo' })).toBeEnabled();
  expect(screen.getByRole('button', { name: 'Apply' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Undo' }));
  expect(await screen.findByText('Undo confirmed by the server as a new accepted revision.')).toBeVisible();
  expect(api.post).toHaveBeenNthCalledWith(4, '/api/designs/unit-design/decision', { base_revision_id: 'unit-candidate', action: 'undo' });
  expect(screen.getByRole('button', { name: 'Undo' })).toBeDisabled();
});
it('ignores duplicate generation submits until the active request finishes', async () => {
  let finish!: (s: ReturnType<typeof strategyFixture>) => void;
  vi.mocked(api.generateStrategy).mockImplementation(() => new Promise(resolve => { finish = resolve; }));
  await home(); fireEvent.click(screen.getByRole('button', { name: 'Create Robot' }));
  expect(screen.getByRole('heading', { name: 'Preparing the design bench…' })).toBeVisible();
  fireEvent.click(within(screen.getByRole('navigation',{name:'Workspace tools'})).getByRole('button', { name: 'Strategy' }));
  expect(api.generateStrategy).toHaveBeenCalledOnce();
  await act(async () => finish(strategyFixture()));
  expect(await screen.findByRole('heading', { name: 'Low quadrant scoring cycles' })).toBeVisible();
});

it('replaces edit controls with actual missing qualifications if a preview request becomes blocked', async () => {
  vi.mocked(api.post).mockResolvedValueOnce(editableDesignFixture()).mockResolvedValueOnce(blockedDesignFixture());
  await home(); fireEvent.click(screen.getByRole('button', { name: 'Create Robot' }));
  fireEvent.click(await screen.findByRole('button', { name: 'Assemble local recipe' }));
  await screen.findByTestId('unit-design-scene');
  fireEvent.click(screen.getByRole('button', { name: 'Expand assistant' }));
  fireEvent.click(screen.getByRole('button', { name: 'Preview raised' }));
  expect(await screen.findByText(/Design qualification is now blocked/)).toHaveTextContent('No qualified scoring mechanism recipe');
  expect(screen.getByRole('button', { name: 'Preview raised' })).toBeDisabled();
  expect(screen.queryByTestId('unit-design-scene')).toBeNull();
  expect(screen.queryByTestId('unit-reference-scene')).not.toBeInTheDocument();
  expect(screen.getByTestId('concept-canvas')).toHaveTextContent('Not CAD');
});

it.each(['Do not raise the scorer', 'Raise scoring height by 20 cm', 'Raise the drivetrain', 'Raise the cup cradle', 'Increase drive speed', 'Increase reliability'])('refuses an unsupported or negated engineering command: %s', async text => {
  vi.mocked(api.post).mockResolvedValueOnce(editableDesignFixture());
  await home(); fireEvent.click(screen.getByRole('button', {name:'Create Robot'}));
  fireEvent.click(await screen.findByRole('button', {name:'Assemble local recipe'}));
  await screen.findByTestId('unit-design-scene');
  fireEvent.click(screen.getByRole('button', {name:'Expand assistant'}));
  fireEvent.change(screen.getByLabelText('Design request'), {target:{value:text}});
  fireEvent.click(screen.getByRole('button', {name:'Send request'}));
  await waitFor(() => expect(screen.getByLabelText('Design request')).toHaveValue(''));
  expect(api.post).toHaveBeenCalledTimes(1); // Only the existing realization.
});

it('retains Undo when the bounded accepted-edit history prevents another preview', async () => {
  const limited=editableDesignFixture(); limited.canEdit=false;
  limited.previous=structuredClone(limited.accepted);
  const restored=structuredClone(limited);
  restored.canEdit=true; restored.previous=null; restored.revisionId='unit-history-restored';
  restored.accepted={...restored.accepted!,id:restored.revisionId,parentRevisionId:limited.revisionId};
  restored.bindings={...restored.bindings!,revisionId:restored.revisionId};
  vi.mocked(api.post).mockResolvedValueOnce(limited).mockResolvedValueOnce(restored);
  await home(); fireEvent.click(screen.getByRole('button',{name:'Create Robot'}));
  fireEvent.click(await screen.findByRole('button',{name:'Assemble local recipe'}));
  await screen.findByTestId('unit-design-scene');
  fireEvent.click(screen.getByRole('button',{name:'Expand assistant'}));
  expect(screen.getByRole('button',{name:'Preview raised'})).toBeDisabled();
  expect(screen.getByRole('button',{name:'Undo'})).toBeEnabled();
  fireEvent.click(screen.getByRole('button',{name:'Undo'}));
  expect(await screen.findByText('Undo confirmed by the server as a new accepted revision.')).toBeVisible();
});

it('switches actual proposal A to conceptual B and restores A with its cached revision and bindings without another CAD POST',async()=>{
  const accepted=editableDesignFixture(),strategy=strategyFixture();
  const [a,b]=strategy.architectures;
  expect(b.id).toBe('strategy-spec-4c5452f1550499ebcd54cab6:architecture-b:213d5164d5b6ff3a239e0bdd');
  vi.mocked(api.post).mockResolvedValueOnce(accepted);
  await home();fireEvent.click(screen.getByRole('button',{name:'Create Robot'}));
  fireEvent.click(await screen.findByRole('button',{name:'Assemble local recipe'}));
  const scene=await screen.findByTestId('unit-design-scene');
  expect(scene).toHaveAttribute('data-revision',accepted.revisionId);
  expect(scene).toHaveAttribute('data-engineering-hash',accepted.accepted!.engineeringHash);
  fireEvent.click(screen.getByRole('button',{name:'Select Design 02'}));
  expect(screen.getByRole('button',{name:'Select Design 02'})).toHaveAttribute('aria-pressed','true');
  const concept=screen.getByTestId('concept-canvas');
  expect(concept).toHaveAttribute('data-architecture-id',b.id);
  expect(concept).toHaveTextContent('Guided elevator');
  expect(concept).toHaveTextContent('Not CAD · not to scale · assembly not realized');
  expect(within(concept).getByRole('img',{name:/architecture B/})).toHaveAttribute('data-architecture-id',b.id);
  expect(screen.queryByTestId('unit-design-scene')).not.toBeInTheDocument();
  expect(screen.queryByTestId('unit-reference-scene')).not.toBeInTheDocument();
  for(const name of ['Strategy','Design'])fireEvent.click(within(screen.getByRole('navigation',{name:'Workspace tools'})).getByRole('button',{name}));
  expect(api.generateStrategy).toHaveBeenCalledOnce();
  fireEvent.click(screen.getByRole('button',{name:'Select Design 01'}));
  const restored=await screen.findByTestId('unit-design-scene');
  expect(screen.getByRole('button',{name:'Select Design 01'})).toHaveAttribute('aria-pressed','true');
  expect(restored).toHaveAttribute('data-revision',accepted.revisionId);
  expect(restored).toHaveAttribute('data-bindings-revision',accepted.bindings!.revisionId);
  expect(restored).toHaveAttribute('data-engineering-hash',accepted.accepted!.engineeringHash);
  expect(screen.queryByTestId('concept-canvas')).not.toBeInTheDocument();
  expect(api.post).toHaveBeenCalledExactlyOnceWith('/api/designs/realize',{architecture_id:a.id});
  expect(vi.mocked(api.get).mock.calls.every(([path])=>path==='/api/designs/catalog')).toBe(true);
});

it('blocks switching to B during an A preview with visible feedback and preserves the exact candidate until discard',async()=>{
  const accepted=editableDesignFixture(),candidate=structuredClone(accepted);
  candidate.candidate={...structuredClone(accepted.accepted!),id:'unit-pending-preview',parentRevisionId:accepted.revisionId,engineeringHash:'c'.repeat(64)};
  candidate.candidateBindings={...structuredClone(accepted.bindings!),revisionId:candidate.candidate.id,engineeringHash:candidate.candidate.engineeringHash};
  candidate.candidateWorldTransforms=structuredClone(accepted.worldTransforms);
  vi.mocked(api.post).mockResolvedValueOnce(accepted).mockResolvedValueOnce(candidate).mockResolvedValueOnce(accepted);
  await home();fireEvent.click(screen.getByRole('button',{name:'Create Robot'}));
  fireEvent.click(await screen.findByRole('button',{name:'Assemble local recipe'}));
  await screen.findByTestId('unit-design-scene');
  fireEvent.click(screen.getByRole('button',{name:'Expand assistant'}));
  fireEvent.click(screen.getByRole('button',{name:'Preview raised'}));
  await waitFor(()=>expect(screen.getByTestId('unit-design-scene')).toHaveAttribute('data-revision','unit-pending-preview'));
  fireEvent.click(screen.getByRole('button',{name:'Select Design 02'}));
  expect(await screen.findByRole('alert')).toHaveTextContent('Apply or discard the current preview before switching designs.');
  expect(screen.getByRole('button',{name:'Select Design 01'})).toHaveAttribute('aria-pressed','true');
  expect(screen.getByRole('button',{name:'Select Design 02'})).toHaveAttribute('aria-pressed','false');
  expect(screen.getByTestId('unit-design-scene')).toHaveAttribute('data-revision',candidate.candidate.id);
  expect(screen.getByTestId('unit-design-scene')).toHaveAttribute('data-engineering-hash',candidate.candidate.engineeringHash);
  expect(screen.getByTestId('unit-design-scene')).toHaveAttribute('data-bindings-revision',candidate.candidateBindings.revisionId);
  expect(screen.queryByTestId('concept-canvas')).not.toBeInTheDocument();
  expect(api.post).toHaveBeenCalledTimes(2);
  fireEvent.click(screen.getByRole('button',{name:'Discard'}));
  await waitFor(()=>expect(screen.getByTestId('unit-design-scene')).toHaveAttribute('data-revision',accepted.revisionId));
  expect(api.post).toHaveBeenNthCalledWith(3,'/api/designs/unit-design/decision',{
    base_revision_id:accepted.revisionId,candidate_revision_id:candidate.candidate.id,action:'discard'});
  fireEvent.click(screen.getByRole('button',{name:'Select Design 02'}));
  expect(screen.getByTestId('concept-canvas')).toHaveAttribute('data-architecture-id',strategyFixture().architectures[1].id);
  fireEvent.click(screen.getByRole('button',{name:'Select Design 01'}));
  expect(await screen.findByTestId('unit-design-scene')).toHaveAttribute('data-revision',accepted.revisionId);
  expect(api.post).toHaveBeenCalledTimes(3);expect(api.generateStrategy).toHaveBeenCalledOnce();
});

it('opens a saved build through GET requalification and displays that response rather than index or cached revision metadata',async()=>{
  const accepted=editableDesignFixture(),rechecked=structuredClone(accepted),index=designCatalog();
  rechecked.revisionId='unit-requalified';
  rechecked.accepted={...rechecked.accepted!,id:rechecked.revisionId,engineeringHash:'d'.repeat(64)};
  rechecked.bindings={...rechecked.bindings!,revisionId:rechecked.revisionId,engineeringHash:rechecked.accepted.engineeringHash};
  index.saved=[{designId:accepted.designId,architectureId:accepted.architectureId,strategyId:accepted.strategyId,
    revisionId:'stale-index-revision',hasCandidate:false}];
  let finish!:(value:DesignSession)=>void;
  const pending=new Promise<DesignSession>(resolve=>{finish=resolve;});
  vi.mocked(api.get).mockImplementation(async path=>{
    // The build enters the saved index after its initial realization. This
    // keeps the first action a POST rather than the direct saved-build opener.
    if(path==='/api/designs/catalog')return {...index,saved:vi.mocked(api.post).mock.calls.length?index.saved:[]};
    if(path==='/api/designs/unit-design')return pending;
    throw new Error(`Unexpected test GET: ${path}`);
  });
  vi.mocked(api.post).mockResolvedValueOnce(accepted);
  await home();fireEvent.click(screen.getByRole('button',{name:'Create Robot'}));
  fireEvent.click(await screen.findByRole('button',{name:'Assemble local recipe'}));
  await screen.findByTestId('unit-design-scene');
  fireEvent.click(screen.getByRole('button',{name:'Home'}));
  fireEvent.click(await screen.findByRole('button',{name:/Design 01 Saved assembly.*recheck on open/}));
  await waitFor(()=>expect(api.get).toHaveBeenCalledWith('/api/designs/unit-design'));
  expect(screen.getByTestId('unit-design-scene')).toHaveAttribute('data-revision',accepted.revisionId);
  await act(async()=>finish(rechecked));
  await waitFor(()=>expect(screen.getByTestId('unit-design-scene')).toHaveAttribute('data-revision',rechecked.revisionId));
  expect(screen.getByTestId('unit-design-scene')).toHaveAttribute('data-bindings-revision',rechecked.revisionId);
  expect(screen.getByTestId('unit-design-scene')).toHaveAttribute('data-engineering-hash',rechecked.accepted.engineeringHash);
  expect(api.post).toHaveBeenCalledOnce();expect(api.generateStrategy).toHaveBeenCalledOnce();
});

it('keeps the studio generation flow usable when the optional read-only design index is unavailable',async()=>{
  vi.mocked(api.get).mockRejectedValue(new Error('Optional index unavailable'));
  await home();fireEvent.click(screen.getByRole('button',{name:'Create Robot'}));
  expect(await screen.findByRole('heading',{name:'Choose your machine.'})).toBeVisible();
  expect(api.generateStrategy).toHaveBeenCalledOnce();expect(api.post).not.toHaveBeenCalled();
});

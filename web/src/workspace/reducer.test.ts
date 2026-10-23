import { expect, it } from 'vitest';
import { initialState, workspaceReducer } from './reducer';

it('preserves source selection and command draft through theme, mode and assistant presentation changes', () => {
  let state = workspaceReducer(initialState, { type: 'draft', text: 'Raise the scoring mechanism' });
  state = workspaceReducer(state, { type: 'select', selection: { componentId: 'source-1', catalogMeshSha256: 'hash-1', nativeNodeId: 'node-4' } });
  const selection = state.selection;
  state = workspaceReducer(state, { type: 'preferences', preferences: { theme: 'shift', mode: 'advanced' } });
  state = workspaceReducer(state, { type: 'assistant', size: 'fullscreen' });
  state = workspaceReducer(state, { type: 'assistant', size: 'compact' });
  expect(state.selection).toBe(selection);
  expect(state.commandDraft).toBe('Raise the scoring mechanism');
  expect(state.preferences).toEqual({ theme: 'shift', mode: 'advanced' });
});
it('coordinates one content sheet and clears stale selection when the source changes', () => {
  let state = workspaceReducer(initialState, { type: 'assistant', size: 'expanded' });
  expect(state.panel).toBeNull();
  state = workspaceReducer(state, { type: 'panel', panel: 'components' });
  expect(state.assistantSize).toBe('compact');
  expect(state.panel).toBe('components');
  state = workspaceReducer(state, { type: 'select', selection: { componentId: 'old', catalogMeshSha256: 'old' } });
  state = workspaceReducer(state, { type: 'component', componentId: 'new' });
  expect(state.selection).toBeNull();
});

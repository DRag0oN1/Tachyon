import type { Preferences, Selection, Workspace } from '../api/contracts';
export type Panel = 'home' | 'components' | 'preferences' | null;
export type AssistantSize = 'compact' | 'expanded' | 'fullscreen';
export interface WorkspaceState {
  preferences: Preferences;
  activeComponentId: string | null;
  selection: Selection | null;
  panel: Panel;
  assistantSize: AssistantSize;
  commandDraft: string;
}
export const initialState: WorkspaceState = {
  preferences: { theme: 'snap', mode: 'simple' }, activeComponentId: null,
  selection: null, panel: 'home', assistantSize: 'compact', commandDraft: '',
};
export type Action =
  | { type: 'restore'; workspace: Workspace }
  | { type: 'preferences'; preferences: Partial<Preferences> }
  | { type: 'component'; componentId: string | null }
  | { type: 'select'; selection: Selection | null }
  | { type: 'panel'; panel: Panel }
  | { type: 'assistant'; size: AssistantSize }
  | { type: 'draft'; text: string };
export function workspaceReducer(state: WorkspaceState, action: Action): WorkspaceState {
  switch (action.type) {
    case 'restore': return { ...state, preferences: action.workspace.preferences, activeComponentId: action.workspace.activeComponentId, selection: null };
    case 'preferences': return { ...state, preferences: { ...state.preferences, ...action.preferences } };
    case 'component': return { ...state, activeComponentId: action.componentId, selection: null };
    case 'select': return { ...state, selection: action.selection };
    case 'panel': return { ...state, panel: action.panel, assistantSize: 'compact' };
    case 'assistant': return { ...state, assistantSize: action.size, panel: action.size === 'compact' ? state.panel : null };
    case 'draft': return { ...state, commandDraft: action.text };
  }
}

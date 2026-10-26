import { SessionBoundary } from './session/SessionBoundary';
import { WorkspaceShell } from './workspace/WorkspaceShell';

export function App() { return <SessionBoundary><WorkspaceShell /></SessionBoundary>; }

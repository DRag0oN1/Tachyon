import {act,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {beforeEach,expect,it,vi} from 'vitest';
import {api,captureSession,clearOwnerSession,SESSION_REQUIRED_EVENT,SESSION_KEY} from '../api/client';
import {workspaceFixture} from '../test/contracts';
import {SessionBoundary} from './SessionBoundary';

beforeEach(()=>{clearOwnerSession();history.replaceState(null,'','/');vi.restoreAllMocks();});
function app(){return render(<SessionBoundary><main aria-label="Actual workspace">Studio content</main></SessionBoundary>);}
it('shows one useful connection screen before requesting any private data in a fresh browser',async()=>{
  const read=vi.spyOn(api,'workspace');app();await screen.findByRole('heading',{name:'Connect to your studio.'});
  expect(read).not.toHaveBeenCalled();expect(screen.queryByLabelText('Actual workspace')).toBeNull();expect(screen.queryAllByRole('alert')).toHaveLength(0);
  expect(screen.getByText('.venv/bin/tachyon launch --port 8019')).toBeVisible();
});
it('accepts an actual authorized fragment, strips it and supports refreshing this tab',async()=>{
  history.replaceState(null,'','/#session=valid-local-owner');captureSession();const read=vi.spyOn(api,'workspace').mockResolvedValue(workspaceFixture);
  const first=app();await screen.findByLabelText('Actual workspace');expect(location.hash).toBe('');expect(sessionStorage.getItem(SESSION_KEY)).toBe('valid-local-owner');
  first.unmount();app();await screen.findByLabelText('Actual workspace');expect(read).toHaveBeenCalledTimes(2);
});
it('validates a pasted launch against the real protected API, stores it only in this tab, and never echoes it',async()=>{
  vi.spyOn(api,'workspace').mockResolvedValue(workspaceFixture);app();await screen.findByRole('heading',{name:'Connect to your studio.'});
  fireEvent.click(screen.getByText('Connect with an authorized launch URL'));
  const secret=location.origin+'/#session=current-private-owner';fireEvent.change(screen.getByLabelText('Authorized launch URL'),{target:{value:secret}});
  fireEvent.click(screen.getByRole('button',{name:'Connect to studio'}));await screen.findByLabelText('Actual workspace');
  expect(localStorage.getItem(SESSION_KEY)).toBeNull();expect(sessionStorage.getItem(SESSION_KEY)).toBe('current-private-owner');expect(document.body.textContent).not.toContain(secret);
});
it('refuses foreign origins before sending any owner credential',async()=>{
  const read=vi.spyOn(api,'workspace');app();await screen.findByRole('heading',{name:'Connect to your studio.'});
  fireEvent.click(screen.getByText('Connect with an authorized launch URL'));fireEvent.change(screen.getByLabelText('Authorized launch URL'),{target:{value:'https://example.com/#session=private-owner'}});
  fireEvent.click(screen.getByRole('button',{name:'Connect to studio'}));await screen.findByRole('alert');expect(read).not.toHaveBeenCalled();expect(sessionStorage.getItem(SESSION_KEY)).toBeNull();
});
it('collapses concurrent authorization failures into one recovery screen',async()=>{
  history.replaceState(null,'','/#session=valid-local-owner');captureSession();vi.spyOn(api,'workspace').mockResolvedValue(workspaceFixture);app();await screen.findByLabelText('Actual workspace');
  act(()=>{window.dispatchEvent(new Event(SESSION_REQUIRED_EVENT));window.dispatchEvent(new Event(SESSION_REQUIRED_EVENT));});
  expect(screen.queryByLabelText('Actual workspace')).toBeNull();expect(screen.getAllByRole('alert')).toHaveLength(1);expect(screen.getByRole('heading',{name:'Connect to your studio.'})).toBeVisible();
});
it('handles a launch fragment added to an already-open locked tab',async()=>{
  vi.spyOn(api,'workspace').mockResolvedValue(workspaceFixture);app();await screen.findByRole('heading',{name:'Connect to your studio.'});
  act(()=>{history.replaceState(null,'','/#session=new-private-owner');window.dispatchEvent(new HashChangeEvent('hashchange'));});
  await waitFor(()=>expect(screen.getByLabelText('Actual workspace')).toBeVisible());expect(location.hash).toBe('');
});

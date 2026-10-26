import {useEffect,useState,type FormEvent,type ReactNode} from 'react';
import {api,ApiError,captureSession,clearOwnerSession,hasOwnerSession,installLaunchUrl,SESSION_REQUIRED_EVENT} from '../api/client';
import {MechanicalCore,TachyonWordmark} from '../studio/Mechanical';
import '../styles/session.css';

/** One authorization gate, before any CAD, strategy or workspace requests. */
export function SessionBoundary({children}:{children:ReactNode}){
  const [ready,setReady]=useState(false),[checking,setChecking]=useState(true),[attempt,setAttempt]=useState(0);
  const [url,setUrl]=useState(''),[message,setMessage]=useState<string|null>(null),[connecting,setConnecting]=useState(false);
  useEffect(()=>{
    const lost=()=>{setReady(false);setChecking(false);setMessage('This connection has expired. Reopen the current authorized launch link to reconnect. Your saved designs remain on the local server.');};
    const incoming=()=>{if(new URLSearchParams(location.hash.slice(1)).has('session')){captureSession();setAttempt(n=>n+1);}};
    window.addEventListener(SESSION_REQUIRED_EVENT,lost);window.addEventListener('hashchange',incoming);
    return()=>{window.removeEventListener(SESSION_REQUIRED_EVENT,lost);window.removeEventListener('hashchange',incoming);};
  },[]);
  useEffect(()=>{
    const abort=new AbortController();setChecking(true);
    if(!hasOwnerSession()){setReady(false);setChecking(false);return;}
    api.workspace(abort.signal).then(()=>{if(!abort.signal.aborted){setReady(true);setMessage(null);}}).catch(error=>{
      if(abort.signal.aborted)return;
      setReady(false);setMessage(error instanceof ApiError&&[401,403].includes(error.status)?'This launch link is no longer authorized. Use the current link from your running local server.':'The local server could not be reached. Start Tachyon, then try connecting again.');
    }).finally(()=>{if(!abort.signal.aborted)setChecking(false);});
    return()=>abort.abort();
  },[attempt]);
  async function connect(event:FormEvent){
    event.preventDefault();if(connecting||!url.trim())return;setConnecting(true);setMessage(null);
    try{
      installLaunchUrl(url.trim());setUrl('');await api.workspace();setReady(true);
    }catch(error){
      clearOwnerSession();setReady(false);setUrl('');setMessage(error instanceof ApiError?'The server did not authorize that link. Reopen the current launch link from your terminal.':'Use the full authorized launch URL for this exact local studio address.');
    }finally{setConnecting(false);setChecking(false);}
  }
  if(ready)return <>{children}</>;
  return <main className="session-screen" data-theme="snap" aria-label="Connect to Tachyon">
    <header><TachyonWordmark/><span>LOCAL ENGINEERING STUDIO</span></header>
    <section className="session-housing">
      <div className="session-core" aria-hidden="true"><MechanicalCore expanded={checking||connecting}/></div>
      <span className="eyebrow">PRIVATE WORKSPACE / OWNER CONNECTION</span>
      <h1>{checking?'Opening your studio…':'Connect to your studio.'}</h1>
      <p className="session-lead">Open Tachyon through its authorized launch link. The plain address keeps your private CAD and designs locked.</p>
      {message&&<p className="session-feedback" role="alert">{message}</p>}
      {checking?<p role="status">Checking this tab’s connection…</p>:<>
        <div className="session-launch"><span>From the Tachyon project folder:</span><code>.venv/bin/tachyon launch --port 8019</code><p>This opens a connected browser tab without displaying the credential.</p></div>
        <details><summary>Connect with an authorized launch URL</summary><p>Run <code>tachyon launch --port 8019 --show-url</code> privately if automatic opening is unavailable. Paste its full URL below. It stays in this tab and is never included in a request URL.</p>
          <form onSubmit={connect}><label htmlFor="owner-launch">Authorized launch URL</label><input id="owner-launch" type="password" autoComplete="off" spellCheck={false} value={url} onChange={event=>setUrl(event.target.value)} placeholder="Paste the current private launch link"/><button disabled={!url.trim()||connecting}>{connecting?'Connecting…':'Connect to studio'}</button></form>
        </details>
        <button className="session-retry" onClick={()=>setAttempt(n=>n+1)} disabled={connecting}>Check connection again</button>
      </>}
      <p className="session-note">Refreshing a connected tab keeps its session. Reopening a browser or restarting the server may require the launch command again. Saved assemblies are retained.</p>
    </section>
  </main>;
}

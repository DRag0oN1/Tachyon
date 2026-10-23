import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App';
import { captureSession } from './api/client';
import './styles/tokens.css';
import './styles/workspace.css';
import './styles/motion.css';

// Strip the launch credential before React, loaders, or any requests can run.
captureSession();
createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>);

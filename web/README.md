# Tachyon frontend · slice 1

New React 19 / TypeScript / R3F 9 frontend for source component inspection.
The approved spec is `../devpost/spec.md`; this slice does not generate or edit
robots. All displayed CAD comes from the running backend's qualified local GLB
API. No CAD, source files, remote fonts, icon packs, or environment secrets are
bundled. Fixture geometry is always labeled **Tachyon-authored, non-VEX,
converter proof only**. A source component is never a complete robot.

```sh
npm ci --prefix web
npm run dev --prefix web
npm run test --prefix web -- --run
npm run build --prefix web
```

Vite runs at `http://127.0.0.1:5173`, proxies `/api` to port 8000, and preserves
the original Origin header. Set backend `TACHYON_UI_ORIGIN` to that frontend
origin. Use the serving process's authorized launch URL. The frontend strips
`#session=<token>` immediately and retains the owner token in tab sessionStorage
(memory only if browser storage is blocked). All APIs except redacted health
require `X-Tachyon-Session`. Tokens never enter source, query strings, logs,
recordings, localStorage, model requests, or static bundles.

GLBs are fetched with that header, verified against mesh SHA-256, validated as
self-contained binary glTF 2, then loaded through short-lived blob URLs. The
renderer preserves source GLTF children, native transforms/materials and semantic
node mapping, checks actual world bounds in metres, and reports ready only after
a real draw. It does not rescale parts. The SHA-256 fallback for HTTP phone
origins uses `@noble/hashes/sha2.js`; its upstream documentation and license are
recorded in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

The idle canvas uses demand rendering, bounded DPR, and orbit/zoom/pan controls.
Changes to theme, panels and assistant size preserve the scene and selection.
Workspace PATCHes serialize; failures visibly retain unsaved preferences and
offer retry. One content sheet is expanded at a time. The assistant retains its
draft through compact/expanded/fullscreen states and never submits a fake edit.

API integration contracts live in `src/api/contracts.ts`. Additional catalog
fields accepted/displayed include native hierarchy, conversion metadata,
attribution and `completeRobot:false`; `sku:null` is valid. Readiness comes from
capabilities and actual rendering, never the health provider-configured flag.

## Real-backend browser checks

Install official test browsers with `cd web && npx playwright install chromium webkit`.
The Playwright config provides desktop Chromium and mobile WebKit projects, starts
Vite if needed, and never starts/replaces the backend. It uses an existing backend
on port 8000. Owner session input is runtime-only:

```sh
TACHYON_E2E_SESSION_FILE=/absolute/path/to/private/session-file npm run test:e2e --prefix web -- --grep @cad-import
```

The private file may contain the token or the serving process launch URL.
Alternatively use `TACHYON_E2E_SESSION` in the environment. Do not paste either
into tracked files. For a running UI elsewhere set `TACHYON_E2E_BASE_URL`.
The SHA-256 standard-vector browser check imports the Vite-served module and
therefore expects the development server.

There are no mocked CAD-success routes. Missing backend/session/qualified sources
produce explicitly skipped, input-dependent checks. The suite validates actual
protected GLB requests, observed mesh bounds, canvas picking/native node IDs,
hierarchy picking, source labels, preference preservation, and assistant draft
continuity. It restores initial persisted preferences/active component afterward.
Tests share one backend workspace and run serially.

Only `test_fixture` render runs write CAD screenshots, named
`*-tachyon-authored-non-vex-converter-fixture.png`, under ignored `web/test-results/`.
Traces, automatic failure screenshots and videos are off to avoid capturing
unreviewed CAD/credentials. These converter screenshots cannot satisfy authentic
VEX or complete-robot acceptance. Physical phone/LAN rights remain separate.

Run `npm run licenses --prefix web` after changing the lockfile to refresh
dependency provenance and the distribution's license texts.

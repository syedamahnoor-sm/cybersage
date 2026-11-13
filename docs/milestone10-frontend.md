# Milestone 10: CyberSage frontend

## Scope and architecture

The frontend is an independent Next.js App Router application in `frontend/`.
Python services, database schema, citation safeguards and Milestone 9 results
were not modified. No authentication, deployment, new domain backend or fake
security telemetry was introduced.

The application uses Next.js 16.4.6, React 19.3.1, TypeScript 6.0.3 in strict mode,
Tailwind 4.3.5, Lucide React 1.72.0 and Motion 14.14.0. The lockfile pins the
installed dependency tree. Node 24.20.0/npm 11.19.0 were used locally.

TypeScript 7 was initially incompatible with `typescript-eslint`'s supported
range, so TypeScript 6 is pinned. ESLint 9.39.5 is the mutually compatible major
declared by the installed React/import plugins; ESLint 10 is not yet declared
compatible by those plugins. npm marks ESLint 9 deprecated, so revisit this
tooling when the plugins support the next major. A targeted override upgrades
vulnerable minimatch versions 7–10 to 11.0.8; lint, tests and build validate that
tree. No force-upgrade or audit suppression was used.

Structure:

```text
frontend/
  src/app/                 Layout, route pages, transition, loading/error/404
  src/components/          Application shell and feature workspaces
    ui/                    Locally owned shadcn/ui-style components
  src/lib/                 API contracts/client, corpus, risk, local shortcuts
  tests/                   Vitest + Testing Library
  e2e/                     Playwright + axe browser checks
  components.json          shadcn/ui aliases, theme and configuration
  next.config.ts           Fixed-target FastAPI rewrite
  .env.example             Non-secret development configuration
```

Components follow the [shadcn/ui manual installation](https://ui.shadcn.com/docs/installation/manual)
and locally owned component model: Button uses class-variance-authority and
Radix Slot; Sheet composes Radix Dialog for focus management, Escape dismissal
and restoration. Card, Badge and Textarea share the design tokens. Components
are adapted to CyberSage's styling rather than importing a second visual theme.

## Design system

The interface uses deep navy (`#090f18`), charcoal navy surfaces (`#101925`),
restrained mint/teal (`#8ae7c2`), quiet blue and warm source-document accents.
Borders, ambient gradients and layered cards provide hierarchy without live
monitoring-style decoration. Manrope headings and Inter body text are bundled
locally with fontsource. No external font fetch is required for a build.

The original SVG mark combines a shield with a connected knowledge hexagon.
It appears in the wordmark, assistant avatar, overview orbit and favicon. The
overview's orbital diagram represents the three source classifications; it is
decorative, not a threat feed or operational graph. Document covers are original
CSS/SVG treatments, not screenshots of inaccessible PDFs.

Spacing follows a shared 4/8px rhythm, with 40px desktop workspace gutters,
responsive cards, consistent 7–12px corner radii and restrained borders. Motion
handles short page-entry transitions. `prefers-reduced-motion` is honored by
Motion and CSS. Pending requests use an indeterminate icon and explanatory text;
there is no simulated token streaming or invented stage progress.

Accessibility includes a skip link, semantic navigation/current route, visible
focus outlines, native controls, labeled forms, live status/error regions and
Radix modal focus management. Risk categories use text and scores as well as
color. On mobile, navigation becomes a focus-trapped drawer and content stacks.
Desktop navigation can collapse while keeping accessible names.

## Pages and reusable components

| Route | Implementation |
|---|---|
| `/` | Product introduction, original knowledge orbit, snapshot statistics, capability cards, three source summaries |
| `/assistant` | Empty suggestions, conversational layout, message composer, real API call foundation, citations, history, retry, copy |
| `/risk-analyzer` | Five-value selectors, selectable 25-cell matrix, live score/category, interpretation and limitations |
| `/knowledge-base` | Actual three-source catalog, text search, classification filter, empty/reset state |
| `/about` | Project purpose, architecture flow, risk branch, grounding/memory/privacy limitations |

Shared components include `AppShell`, `Brand/BrandMark`, `ConnectionStatus`,
`PageIntro`, `Reveal`, `DocumentCard`, `KnowledgeOrbit`, `CitationList`,
`SafeMarkdown` and the UI primitives. Feature workspaces own state while pure
data/calculation/client modules remain separate.

The catalog contains the verified source filenames and the Milestone 9 snapshot:
Pakistan policy 22 pages/52 chunks, NIST 32/93, synthetic casebook 21/61. Total:
75 pages/206 chunks. No document-list/file-serving endpoint exists, so the UI
does not pretend these are live counts or offer PDF downloads or management.
Casebook descriptions and classifications explicitly state that incidents are
fictional.

## Assistant behavior and API foundation

`src/lib/api-types.ts` mirrors the inspected Pydantic contracts, including all
agent statuses, nullable model/assessment/error fields, citations, retrieval
scores and paged history. Existing endpoints only:

- `POST /api/v1/agent/invoke`
- `POST /api/v1/rag/ask`
- `POST /api/v1/retrieval/search`
- `GET /api/v1/health`
- `GET /api/v1/conversations/{id}/messages?limit=10&before_turn=…`

`createApiClient` centralizes JSON serialization, no-cache requests, configurable
base URL, timeout/cancellation and safe error messages. It never renders raw
provider/HTTP error bodies. It validates conversation ID syntax and uses actual
backend field names. The schemas are compile-time interfaces; comprehensive
runtime response validation remains a Milestone 11 task.

The default is browser → same-origin `/api/v1/*` → Next.js rewrite → FastAPI.
`FASTAPI_BASE_URL` is server-side and defaults to `http://127.0.0.1:8000`.
Only this fixed configuration supplies the rewrite target, not user input.
`NEXT_PUBLIC_API_BASE_URL` is an optional direct-browser override. Such direct
cross-origin requests require explicit backend CORS configuration; no wildcard
CORS or backend modification was added. The frontend never contacts Groq.

Health is an actual reachability request in the application, with checking,
unavailable and retry states. A healthy response does not imply PostgreSQL,
embedding or Groq readiness. Browser tests intercept health with an explicit
fixture, so their screenshots are not evidence of live backend availability.

Assistant details:

- Suggestions fill the composer; they do not fabricate or automatically send
  answers. Source cards prefill a relevant question.
- Enter sends, Shift+Enter inserts a newline, and IME composition is respected.
  Client validation matches the backend's trimmed 1–2,000-character bounds.
- Responses appear only after the actual request completes. Status, contextual
  resolution and returned model are preserved. Insufficient evidence has no
  fabricated source fallback.
- Citation details show returned document title/filename, physical PDF page,
  chunk index, evidence ID and exact quote. No client-generated citations.
- Markdown disables raw HTML, remote images and actionable generated links.
  User text and source quotes render escaped. Copy has success/failure feedback.
- A failed request can retry its original body and request UUID. The composer
  is locked until retry or a new conversation, preventing conflicting reuse.
  In-flight work is canceled when the workspace unmounts.
- Recent shortcuts contain only conversation IDs, initial titles and timestamps,
  bounded to eight entries in this browser. Answers are fetched from persisted
  history; older turns can be loaded using the real pagination fields.
- No endpoint enumerates all conversations. Clearing shortcuts removes local
  references only, not backend history. Without authentication, possession of a
  conversation UUID grants history access; avoid sensitive/shared-machine use.

Risk calculations are intentionally local and centralized in `src/lib/risk.ts`.
Both inputs must be actual integers 1–5. Multiplication and thresholds match the
existing Python tool: Low 1–5, Medium 6–10, High 11–15, Critical 16–25. The UI
states that it is an illustrative qualitative matrix, not a validated prediction.
It does not generate PDF citations or use an LLM to calculate a score.

## Local setup and checks

From `frontend/`, with Node 24 LTS:

```powershell
npm.cmd ci
Copy-Item .env.example .env.local
# Start FastAPI separately with the existing backend setup.
npm.cmd run dev -- --hostname 127.0.0.1
# Alternate port when 3000 is already occupied:
npm.cmd run dev -- --hostname 127.0.0.1 --port 3100
```

Set `FASTAPI_BASE_URL` in `.env.local` to the actual FastAPI origin. Restart
Next.js after configuration changes; rebuild when using `npm run start`.
Never store provider keys or database passwords in frontend configuration.

Validation commands:

```powershell
npm.cmd run build
npm.cmd run typecheck
npm.cmd run lint
npm.cmd test
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path (Get-Location) '.cache\playwright'
npm.cmd exec -- playwright install chromium
npm.cmd run test:e2e
npm.cmd audit
```

`npm.cmd` avoids this machine's disabled PowerShell `.ps1` execution policy.
Other platforms use `npm`. Browser tests use a dedicated local port 3100, not
the already occupied port 3000, and start the production build. Windows sandbox
restrictions on process-tree cleanup required approved execution outside the
sandbox for the browser run; unrelated running services were not stopped.

Actual final validation (13 November 2026):

| Check | Result |
|---|---|
| Dependency installation / lockfile | Installed successfully; exact package versions pinned |
| Development smoke | Next.js ready; overview HTTP 200 with expected content on localhost:3101 |
| Production build | Passed; all five routes and favicon generated |
| Strict TypeScript | `tsc --noEmit` passed |
| ESLint | Passed with zero warnings |
| Vitest | 31 passed: 16 risk/validation, 11 API client, 4 component/navigation |
| Playwright Chromium | 5 passed in the final run |
| axe | No serious/critical violations on all five desktop routes after entry animations complete |
| Responsive browser checks | All five routes fit a 390px viewport; drawer Escape/focus restoration passed |
| Assistant browser checks | Empty-input validation, suggestion fill, Shift+Enter/Enter, safe errors, same-body/request-ID retry, citation expansion, copy feedback, fresh conversation |
| History browser checks | Persisted-history contract rendering and earlier-turn pagination using explicit fixtures |
| Dependency audit | Zero vulnerabilities after the targeted patched minimatch override |
| Backend / Milestone 9 | No file changes; backend suite was not rerun for this frontend-only milestone |

The first accessibility run identified decorative cover-label contrast and the
logo's accessible-name mismatch; both were corrected. Another scan ran during
entry opacity transitions, so accessibility tests now wait for complete visible
rendering before measuring contrast. Visual review caught and fixed automatic
scrolling of the empty mobile chat. All final checks above executed successfully;
these were not inferred from previous milestones.

Actual screenshots were captured and inspected locally:

- `frontend/.cache/screenshots/overview-desktop.png` (1440px viewport)
- `frontend/.cache/screenshots/risk-desktop.png` (1440px viewport)
- `frontend/.cache/screenshots/assistant-mobile.png` (390px viewport)

They are generated local evidence, excluded from Git. The final screenshot test
recreates them. Its health response is mocked; images do not prove live backend
availability. Unit/browser API responses are explicit fixtures confined to test
files, never bundled example answers. They verify UI behavior, not live Groq
relevance or citation entailment.

## Milestone 11 integration checklist

- Run full browser → Next rewrite → FastAPI → PostgreSQL → Groq flows with actual
  questions, abstentions, rate limits, unavailable models and provider timeouts.
- Verify server memory persistence, concurrent tabs, idempotent retries and
  paged-history ordering through live browser interactions.
- Add runtime response-schema checks/contract-drift detection and richer
  diagnostics without exposing secrets or internal provider errors.
- Check citation display and synthetic labeling against actual answers; preserve
  all existing backend grounding/rejection behavior.
- Validate local risk results against real backend assessments for all 25 cells.
- Expand browser coverage to Firefox/WebKit and additional device sizes; perform
  manual screen-reader and zoom checks. Automated axe checks are not a complete
  accessibility certification.
- Revisit tool versions when React/import ESLint plugins support ESLint 10.

No authentication, file access, deployment or document-management feature is
implied by this foundation. There is no source inventory endpoint; keep snapshot
labels until an authorized backend contract exists. Existing evaluation failures
remain unresolved and untouched.

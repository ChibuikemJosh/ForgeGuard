# AGENTS.md — Forge frontend

Guidance for AI agents and contributors working in `frontend/`. Read this
before editing. For product/architecture context see `../README.md`,
`../docs/architecture.md` and `../docs/project-model.md` (repo root).

## What Forge is

A developer environment combining source-code editing with a visual,
node-based representation of software architecture. Goal: structured,
understandable, reusable, controllable development — especially with AI
coding assistance. This frontend is currently the Task-A foundation plus a
one-page landing page: app shell routing, a real backend health indicator,
and (on the landing page) a React Flow graph preview. Not yet built: graph
editor interactions beyond the preview, Monaco, AI proposals backend,
source analysis, auth, persistence.

## Commands (run from `frontend/`)

```bash
npm install          # Node 20.19+ / 22.12+, npm 10+
npm run dev          # Vite dev server — http://localhost:5173
npm run build        # tsc -b && vite build  (type-check is part of build)
npm run lint         # oxlint (config: .oxlintrc.json)
npm run preview      # preview production build
```

Backend (separate process, from `../backend/`): `uvicorn app.main:app --reload --reload-dir app --host 127.0.0.1 --port 8000` — API at `http://127.0.0.1:8000`,
docs at `/docs`. The frontend alone shows "Backend unreachable"; that is
honest, not a bug.

## Stack

React 19 · TypeScript (strict, bundler resolution) · Vite 8 · Tailwind
CSS 4 (via `@tailwindcss/vite`, CSS-first config in `src/index.css`) ·
React Router 7 (`react-router-dom`) · **React Flow `@xyflow/react` 12**
for node graphs · **Motion (`motion`)** for animation · **Shiki** (lazy, Python only)
for code highlighting · **sonner** for toasts · **canvas-confetti** (single 403 moment,
reduced-motion gated) · **@dagrejs/dagre** for security-graph layout · oxlint for linting.
No other UI/animation/icon libraries — do not add one without a concrete need.

## Project structure

```
src/
├── main.tsx                  # Entry: StrictMode + BrowserRouter
├── App.tsx                   # Route table only ( / → Home )
├── index.css                 # Tailwind v4 @theme tokens + base + React Flow chrome
├── pages/
│   └── Home.tsx              # Landing route — composition only, no sections inline
├── components/
│   ├── landing/              # Everything the Home page renders (see below)
│   └── layout/               # (reserved) app-shell primitives
├── hooks/
│   └── useBackendHealth.ts   # Real GET /api/health state: loading|connected|error
└── services/
    └── api/client.ts         # Typed fetch client; base URL from VITE_API_BASE_URL
```

### `components/landing/` map

| File | Owns |
| --- | --- |
| `data.ts` | All landing copy + graph node metadata (`FORGE_NODES`, `CAPABILITIES`, `CONNECTIONS`, `STACK`, `NAV_LINKS`). No JSX. |
| `LandingNav.tsx` | Sticky header + anchor nav |
| `Hero.tsx` | Headline, CTAs, stat strip, embeds `ForgeGraph` |
| `ForgeGraph.tsx` | React Flow canvas: node/edge state, selection, inspector footer, `BackendPill` |
| `ForgeNode.tsx` | Custom React Flow node type (`memo`, typed `NodeProps`) |
| `BackendPill.tsx` | Live health pill (uses `useBackendHealth`) |
| `BootScreen.tsx` / `Ticker.tsx` / `Reveal.tsx` / `motion.ts` | Boot splash, mono ticker, scroll-reveal wrapper, shared Motion variants |
| `Capabilities.tsx` | Numbered capability index rows |
| `WorkflowTabs.tsx` | `WorkflowSection` + code/graph/AI-proposal tabs |
| `ModelSection.tsx` | Typed-edge table + design principles |
| `StackSection.tsx` | Stack list + live-backend explainer card |
| `SiteFooter.tsx` | `ClosingSection` (CTA) + footer |

## React conventions (follow these)

- **Pages compose, components render, hooks fetch.** `pages/Home.tsx`
  only imports and orders sections. Put new landing sections in
  `components/landing/`, never inline in `Home.tsx`.
- **One component per file**, named export for components
  (`export function Hero()`), default export only for page components
  consumed by the router. Keep files under ~200 lines; split before they
  grow past that.
- **Static copy/data lives in `data.ts`** (or a colocated `*.ts`), not
  inside JSX files. Type shared shapes and export them (`ForgeNodeMeta`).
- **State stays local** (`useState`/`useCallback`/`useMemo`) unless two
  distant components need it. There is no global store — don't add Redux/
  Zustand for landing-page state.
- **Custom hooks for data**: components must not call `fetch` directly.
  Go through `services/api/client.ts` and expose state via a hook like
  `useBackendHealth` (AbortController, no retries, no fake success).
- **React Flow**: import `@xyflow/react/dist/style.css` in the component
  that renders `<ReactFlow>`; use `useNodesState`/`useEdgesState`;
  register custom node types in a module-level `nodeTypes` object (never
  inline in JSX — it remounts nodes); wrap custom nodes in `memo` with
  typed `NodeProps`; memoize handlers with `useCallback`. The landing
  graph is a preview (`nodesConnectable={false}`, `zoomOnScroll={false}`
  so it never hijacks page scroll) — the future editor belongs in a new
  feature folder, not here.
- **Motion**: import from `motion/react` (not `framer-motion`). Shared variants/easing live in `landing/motion.ts`; use `Reveal` for one-shot section entrances — vary effects (masked lines, HUD sweeps, `layoutId` tab pill), never the same fade-up on every element. `Home.tsx` wraps the page in `MotionConfig reducedMotion="user"` and skips the boot splash for reduced motion; loops (ticker, scan, pulse) must check `useReducedMotion`.
- Lists need stable keys from data ids — never array indexes for
  interactive items. Interactive elements are real `<button>`/`<a>` with
  `focus-visible:` styles; tabs use `role="tablist"/"tab"` +
  `aria-selected`; live regions use `aria-live="polite"`.
- TypeScript is strict: `verbatimModuleSyntax` is on, so type-only
  imports must use `import type`. `noUnusedLocals`/`noUnusedParameters`
  are on — the build fails on dead code.

## Styling conventions

- **Tailwind CSS 4, CSS-first.** Design tokens are `@theme` variables in
  `src/index.css` (`--color-ember`, `--color-coal`, `--color-panel`,
  `--color-line`, fonts). Use utilities (`bg-coal`, `border-line`,
  `text-ember`); do not hardcode hex values in JSX except inside React
  Flow edge/node style objects where the library needs raw values.
- **Typography: Petrona** (`--font-sans`, loaded in `index.html`) for all
  landing headings and body. **JetBrains Mono** (`--font-mono`) only for
  code, file paths, edge labels and micro-labels. Never reintroduce
  Manrope/Inter as the identity font.
- Palette: near-black `coal` background, `panel` surfaces, `line`
  borders, single **deep ember orange** accent (`--color-ember: #c2410c` for fills/buttons, `--color-ember-bright` only for tiny mono labels/live edges on near-black). No purple/blue gradients, no
  gradient headline text, no glassmorphism-everywhere, no identical
  icon-card grids — varied layouts (index rows, tables, split sections).
- Radii are small and deliberate (`rounded-sm`/`rounded-md`); don't put
  `rounded-2xl` on everything. Respect `prefers-reduced-motion` (already
  handled globally in `index.css`).
- React Flow chrome overrides live at the bottom of `src/index.css`
  (`.react-flow__controls*`, attribution). Extend those, don't restyle
  per-component.

## Backend contract

- `GET /api/health` → `200 {"status": "ok", "service": "forge-api"}`.
- Base URL: `VITE_API_BASE_URL` (see `.env.example`), default
  `http://127.0.0.1:8000`. Never hardcode a different origin in
  components, and never put secrets/API keys in frontend code.
- Connection UI must reflect the real request result (checking /
  connected / unreachable + reason). No mock success states.

## Domain language (from `../docs/project-model.md`)

- Nodes are **real components** (function, schema, API, test) with stable
  id, typed input/output ports, properties, source location, dependencies,
  version + validation state — not decorative diagram shapes.
- Edges have exactly three kinds, never interchangeable: **data**
  (values port→port), **execution** (control-flow order), **dependency**
  (depends on another's definition). Each validates independently.
- Grow the schema only when a feature consumes it; keep frontend and
  backend models aligned with the backend as source of truth.

## Workspace page (`/workspace`) — single real-data workspace

One workspace, no mode toggle. Everything is the Project workflow's real
data (backend SourceGraph, manifest, Muse investigation); there is no
mock `components/workspace/data.ts` and no security-demo mode in the
frontend (the backend `/api/security/*` and `/api/demo/*` endpoints still
exist, the frontend just no longer calls them).

```
src/hooks/useProjectWorkflow.ts   # useReducer machine; opening a project
                                  # (sample or folder upload) auto-fetches
                                  # manifest then SourceGraph — no Analyze click
src/features/project/
├── types.ts                      # Project/manifest/SourceGraph/investigation types
├── tree.ts                       # Explorer tree from manifest paths; folderColor()
├── graphLevels.ts                # Deterministic grouping + dagre positions (generous nodesep/ranksep)
├── graphScene.ts                 # Builds the 3-level React Flow scene
└── zipFolder.ts                  # Folder → zip; returns { zip, fileCount, skippedCount }
src/components/workspace/
├── TitleBar.tsx                  # FORGE (home), real project name, Change project, left and right panel toggles only
├── StatusBar.tsx                 # Real values only: backend, project, file, investigation, review/apply
├── WorkflowStepper.tsx           # Generic stepper (steps prop, layoutId ember pill)
├── AiLoading.tsx                 # AiLoading (graph parsing) + AiInlinePulse (Muse calls)
├── ResizeHandle.tsx              # Panel sashes (shared)
├── shared/                       # DiffViewer, DiffCompare (SideBySideDiff), diffLines, ShikiLines, PlainLines
└── project/
    ├── ProjectPicker.tsx         # Sample button + "Upload project folder"
    ├── ProjectExplorer.tsx       # Overview-style tree (react-icons, badges) from the manifest
    ├── ExplorerTree.tsx          # TreeRow + FileIcon
    ├── SourceGraphCanvas.tsx     # 3-level drill-down canvas (see below)
    ├── GraphCardNode.tsx         # memo card node: eyebrow/name/desc/meta, ember select, finding badge
    ├── ProjectCodeViewer.tsx     # Shiki viewer, opens at finding/node line
    ├── RulePanel.tsx             # Per-project rules (preset/generated) + custom; "Run AI investigation"
    ├── AgentActivity.tsx         # Live backend step timeline (aria-live, never invented steps)
    ├── FindingsPanel.tsx         # Findings, backend status word-for-word ("potential")
    └── FixPanel.tsx              # Generate → approve/reject → apply → rollback → re-run
├── WorkspaceTabs.tsx             # Investigate / Changes top-level tabs (role=tablist)
└── changes/
    └── ChangesView.tsx           # Changes tab: finding header, wide FixPanel + SideBySideDiff,
                                  # applied-fixes list, .patch/.zip downloads
```

### Graph: 3 deterministic levels (no invented data)

- **Level 0, Project:** one card per top-level folder of Python (module)
  files; root files go to "Root modules". Meta is real counts
  (`N files · M functions · R routes`). Edges aggregate `IMPORTS`,
  `DEPENDS_ON`, `CALLS` across groups, labelled with the count.
- **Level 1, Folder:** clicking a card expands its module (file) nodes in
  place inside a container over the card's home; other groups stay mounted
  and dimmed, a vignette shows, and cross-group edges become ghost
  (faded, dashed) edges. Back button (ember pill) + breadcrumb
  (`Project › LAYER › file.py`); Esc goes back one level.
- **Level 2, File:** clicking a file expands its classes, functions,
  methods and routes with `CALLS`/`DEFINES`/`HANDLES_ROUTE` edges.
  Clicking a function/route opens the code viewer at `source.line_start`.

Rules: `target: null` edges are never drawn; `status !== "resolved"` edges
are dashed/dimmed and labelled unresolved ("structural only"). Positions
inside each level come from `@dagrejs/dagre`. No fabricated complexity —
cards show a real finding badge or route count. Selecting a finding glows
its `related_graph_nodes`/`affected_files` and auto-drills to the file.
Canvas chrome: dotted `Background`, `colorMode="dark"`, curved `default`
edges, `<Controls position="bottom-left" showInteractive />`, MiniMap
bottom-right. `nodeTypes` is module-level; nodes are `memo` components.

### Stepper mapping (real state only)

Load (project selected) → Map (SourceGraph ready) → Investigate (rule +
Muse run) → Understand (finding selected) → Review (proposal pending/
approved/rejected) → Apply (fix applied, rollback available) → Verify
(investigation re-run after apply; backend summary shown word-for-word).
`current`/`maxReached` derive only from `useProjectWorkflow` state;
clicking a reachable step only focuses a panel, never fakes progress.
Steps 1–4 (Load–Understand) switch to the **Investigate** tab; steps 5–7
(Review–Verify) switch to the **Changes** tab. The workspace has two tabs
(`WorkspaceTabs`, `role="tablist"`): Investigate (graph/code/split +
RulePanel, AgentActivity, FindingsPanel, "Propose a fix →") and Changes
(`ChangesView`). All state stays in `useProjectWorkflow` on the same page —
no route change. Investigations run as backend jobs: the hook polls
`GET /api/workspace/investigations/{id}` every 1.5s, shows live `steps` in
`AgentActivity`, and cancels via the cancel endpoint. Selecting a finding
opens the narrowest `node_matches` node; graph highlighting uses only
matched/related nodes, falling back to affected files only when both are empty.

### Layout (no bottom panel)

The workspace layout is: title bar, then left Explorer, centre
Graph/Code/Split (or the Changes tab), and right sidebar, then status
bar, with no bottom panel. The centre column fills the full height so
the graph and code area reaches down to the status bar.
`AgentActivity` sits in the Investigate sidebar between `RulePanel`
and `FindingsPanel`, updating live during a run. Graph parse errors
show as a warning overlay in the top-right of the graph; investigation
errors appear in `FindingsPanel` (for failed runs the first error is
shown by the status callout and not repeated in the list).

### Rules

Rules are loaded per project from `GET /api/workspace/projects/{id}/rules`:
the sample project gets the 3 preset demo rules, and uploaded projects
get only rules generated from their own routes and resource IDs
(`services/generated_rules.py`; ownership, admin, authentication),
labelled “Generated for your project” in `RulePanel`. A custom rule is
the fallback for both, and the only option when an upload has no routes. The `?` button at
the top-right of the rules widget shows a hover/focus pop-up explaining
what a rule is and how investigation uses it. Layout stays generous in
the graph: `dagrePositions` uses wide `nodesep`/`ranksep` so nodes and
edge labels do not crowd in large codebases.

### Auto-analyze & truthfulness

Opening a project immediately fetches manifest → SourceGraph and shows
Level 0 with a "Parsing project and building graph…" loading animation
(`AiLoading`); backend errors show word-for-word with Retry. The selected
rule is the rule set's `default_rule_id` for the opened project (the
order-ownership preset for the sample, the first generated rule for an
upload, or none). Findings, errors and summaries
show backend wording verbatim; exactly one ember primary button at a time.
AI waits use `AiLoading`/`AiInlinePulse` (Motion, reduced-motion safe).

## Before you finish

1. `npm run build` passes (includes `tsc -b` type-check).
2. `npm run lint` passes (oxlint; hooks rules are errors).
3. New landing UI goes through `components/landing/` + `data.ts`;
   `Home.tsx` stays a short composition.
4. Check `git status` from the repo root — `npm install` can rewrite
   lockfiles; revert collateral changes you didn't intend.

export const NAV_LINKS = [
  { label: "Capabilities", href: "#capabilities" },
  { label: "How it works", href: "#how-it-works" },
  { label: "Workflow", href: "#workflow" },
  { label: "FAQ", href: "#faq" },
  { label: "Stack", href: "#stack" },
] as const;

export const HOW_STEPS = [
  { n: "01", title: "Upload a Python folder", body: "Pick a folder in the browser. Ignored folders, .env files and files over 1 MB are skipped, then it is packed and extracted safely on the backend — parsed, never executed.", mono: "folder → zip in browser → POST /api/workspace/projects/upload" },
  { n: "02", title: "See the SourceGraph", body: "Forge indexes the AST and maps folders, modules, classes, functions and routes into a three-level graph you can drill into, with real counts and source lines.", mono: "GET /source-graph · IMPORTS / CALLS / HANDLES_ROUTE" },
  { n: "03", title: "Ask a security rule", body: "Choose a preset — like “customers may only access their own orders” — or write your own invariant, then run the Meta Muse investigation.", mono: "POST /investigate · muse-spark-1.3" },
  { n: "04", title: "Check the evidence", body: "Every finding is labelled potential. The backend validates the file, line, excerpt and hash before it maps to a graph node, so you review real code, not a guess.", mono: "evidence: valid / invalid · status stays potential" },
  { n: "05", title: "Approve, apply, re-run", body: "Muse proposes a full corrected file. Nothing is written until a human approves; apply is hash-checked and atomic, rollback restores the original, then you re-run to verify.", mono: "review → apply → rollback → investigate again" },
] as const;

export const FAQ_ITEMS = [
  { q: "What does Forge Guard actually do?", a: "You upload a Python project folder, Forge builds a read-only SourceGraph of its modules, functions and routes, then a Meta Muse agent checks it against a security or business rule you pick. Findings come back as potential with validated source evidence pinned to graph nodes." },
  { q: "Is my code executed or stored?", a: "Never executed — uploaded code is only read and parsed with Python's ast module. There is no account and no database: projects live on the backend disk under an unguessable id and are lost on refresh or restart by design. Old uploads are cleaned up automatically after a few hours." },
  { q: "Are the findings confirmed vulnerabilities?", a: "No. Every finding is labelled potential. Evidence validation proves the cited file and line are real and unchanged — it does not prove the rule is broken. You read the excerpt, check the graph, and decide." },
  { q: "How do fixes work?", a: "Select a finding and Muse drafts a full corrected file. The backend checks it parses as Python and actually changes something. A human must approve before apply; apply is hash-checked and atomic, and rollback restores the exact original so you can re-run the investigation." },
  { q: "What projects work best?", a: "Python projects, especially, services with routes and auth checks. Forge analyses graph-guided, structure-aware source chunks with configurable budgets and warns you when any chunk cannot be completed." },
  { q: "Do I need an account or API key to try it?", a: "No account — the hosted demo is intentionally no-auth. Just open the workspace, try the bundled Orders API sample, or upload your own folder (max 10 MB after skipping ignored folders). Your code is sent to the Meta model API for investigation." },
] as const;

export type ForgeNodeId = "api" | "schema" | "service" | "test";

export interface ForgeNodeMeta {
  id: ForgeNodeId;
  name: string;
  kind: string;
  file: string;
  detail: string;
  position: { x: number; y: number };
}

export const FORGE_NODES: readonly ForgeNodeMeta[] = [
  { id: "api", name: "GET /api/health", kind: "API", file: "app/api/health.py", detail: "FastAPI route. Returns status + service name.", position: { x: 24, y: 36 } },
  { id: "schema", name: "HealthResponse", kind: "Schema", file: "app/schemas.py", detail: "Typed response shape shared by API and client.", position: { x: 336, y: 24 } },
  { id: "service", name: "forge-api", kind: "Service", file: "app/main.py", detail: "Application entry. Mounts routers, sets CORS.", position: { x: 168, y: 196 } },
  { id: "test", name: "test_health", kind: "Test", file: "tests/test_health.py", detail: "Asserts GET /api/health returns 200 · ok.", position: { x: 408, y: 208 } },
];

export const FORGE_NODE_BY_ID: Record<ForgeNodeId, ForgeNodeMeta> = Object.fromEntries(
  FORGE_NODES.map((node) => [node.id, node]),
) as Record<ForgeNodeId, ForgeNodeMeta>;

export const CAPABILITIES = [
  { n: "01", title: "Folder in, graph out", body: "Upload a Python folder (or try the Orders API sample) and get a three-level SourceGraph — project, folder, file — built from the real AST, not a diagram you maintain.", tag: "SourceGraph" },
  { n: "02", title: "Rules, not just signatures", body: "Investigate business-logic rules a scanner cannot see: order ownership, admin-only routes, invoice access. Pick a preset or write your own invariant.", tag: "Investigation" },
  { n: "03", title: "Evidence before claims", body: "Muse proposes locations; the backend independently validates file, line range, excerpt, symbol and hash. Invalid locations never become validated evidence.", tag: "Evidence-gated" },
  { n: "04", title: "AI proposes. You approve.", body: "Corrections arrive as a reviewable diff of a full corrected file. Human-only approval, hash-checked atomic apply, and one-click rollback.", tag: "Fix proposals" },
] as const;

export const CONNECTIONS = [
  { kind: "data", meaning: "Values flowing from a source port to a target port", example: "HealthResponse → client.ts" },
  { kind: "execution", meaning: "Control-flow ordering between components", example: "main.py → mounts router" },
  { kind: "dependency", meaning: "A component depends on another's definition", example: "test_health → GET /api/health" },
] as const;

export const STACK = [
  { layer: "Frontend", items: "React 19 · TypeScript · Vite · Tailwind CSS 4 · React Flow · Motion — deployed on Vercel" },
  { layer: "Backend", items: "FastAPI · Python 3.12 · Uvicorn (single process) · pytest — deployed on Render" },
  { layer: "AI", items: "Meta Muse (muse-spark-1.3) via the Meta Model API · LangChain / LangGraph agent" },
  { layer: "Contract", items: "Folder upload (10 MB max) · SourceGraph · evidence-validated findings · no auth, no database" },
] as const;

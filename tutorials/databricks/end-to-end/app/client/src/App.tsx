import { useEffect, useState } from "react";
import { gql } from "@apollo/client";
import { useMutation, useQuery } from "@apollo/client/react";
import SetupView from "./views/SetupView";
import LandingZoneView from "./views/LandingZoneView";
import ProjectView from "./views/ProjectView";
import ProvisionView from "./views/ProvisionView";
import SeedView from "./views/SeedView";
import DataApiView from "./views/DataApiView";
import IngestView from "./views/IngestView";
import MedallionView from "./views/MedallionView";
import LiveView from "./views/LiveView";
import BusinessLayerView from "./views/BusinessLayerView";
import SemanticView from "./views/SemanticView";
import AiBiView from "./views/AiBiView";
import ChatPanel from "./ChatPanel";
import SelectionTooltip from "./SelectionTooltip";
import VerifyPanel from "./VerifyPanel";
import "./App.css";

const CONN = gql`
  query Conn {
    connectionStatus {
      connected
      user
      workspace
      warehouseId
      lakebaseHost
    }
  }
`;

const CONFIGURE = gql`
  mutation Configure($workspaceUrl: String!, $token: String!) {
    configure(workspaceUrl: $workspaceUrl, token: $token) {
      connected
    }
  }
`;

type StepId =
  | "connect"
  | "landing-zone"
  | "project"
  | "provision"
  | "seed"
  | "data-api"
  | "ingest"
  | "medallion"
  | "refresh"
  | "business-layer"
  | "semantic"
  | "ai-bi";

const STEPS: { id: StepId; phase: string; label: string; icon: string }[] = [
  { id: "connect",        phase: "Setup",     label: "Connect",           icon: "🔌" },
  { id: "landing-zone",   phase: "Setup",     label: "Landing Zone",      icon: "🗂️" },
  { id: "project",        phase: "Setup",     label: "Project · dbt",     icon: "🛠️" },
  { id: "provision",      phase: "Lakebase",  label: "Provision",         icon: "🐘" },
  { id: "seed",           phase: "Lakebase",  label: "Seed",              icon: "🌱" },
  { id: "data-api",       phase: "Lakebase",  label: "Data API",          icon: "🌐" },
  { id: "ingest",         phase: "Lakehouse", label: "Ingest",            icon: "📥" },
  { id: "medallion",      phase: "Lakehouse", label: "Medallion",         icon: "🏗️" },
  { id: "refresh",        phase: "Lakehouse", label: "Refresh · Live",    icon: "⚡" },
  { id: "business-layer", phase: "Analytics", label: "Business Layer",    icon: "📋" },
  { id: "semantic",       phase: "Analytics", label: "Semantic · Metrics", icon: "📐" },
  { id: "ai-bi",          phase: "Analytics", label: "AI/BI · Genie",    icon: "🤖" },
];

const TITLES: Record<StepId, string> = {
  "connect":        "Connect — point the app at your workspace",
  "landing-zone":   "Landing Zone — Unity Catalog, schemas, and managed volume",
  "project":        "Project · dbt — local tooling (mise, uv, dbt via OAuth)",
  "provision":      "Provision — create the Lakebase PG17 autoscaling project",
  "seed":           "Seed — load Silverline Capital's 9-table OLTP",
  "data-api":       "Data API — expose Lakebase as a REST endpoint",
  "ingest":         "Ingest — land Lakebase data into bronze Delta",
  "medallion":      "Medallion — bronze → silver → gold (three ways)",
  "refresh":        "Refresh · Live — change the source, watch it stream",
  "business-layer": "Business Layer — document gold tables for Genie",
  "semantic":       "Semantic · Metrics — governed MEASURE() Metric View",
  "ai-bi":          "AI/BI · Genie — dashboard + natural-language queries",
};

// Stages that have real server-side checks — show VerifyPanel instead of the plain "Mark done" button.
const HAS_VERIFY = new Set<StepId>([
  "landing-zone", "provision", "seed", "ingest", "medallion", "refresh", "business-layer", "semantic", "ai-bi",
]);

const KEY = "silverline.progress";
const loadDone = (): string[] => {
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? "[]");
  } catch {
    return [];
  }
};

type Conn = { connected: boolean; user?: string; workspace?: string; warehouseId?: string; lakebaseHost?: string };

export default function App() {
  const { data, refetch } = useQuery<{ connectionStatus: Conn }>(CONN, { fetchPolicy: "cache-and-network" });
  const conn = data?.connectionStatus;
  const connected = !!conn?.connected;

  const [configure] = useMutation(CONFIGURE);

  // Re-establish the server-side pool whenever it's lost (e.g. after a server restart),
  // regardless of which step is currently shown.
  useEffect(() => {
    if (connected) return;
    const savedUrl = localStorage.getItem("silverline.workspaceUrl");
    const savedPat = localStorage.getItem("silverline.pat");
    if (savedUrl && savedPat) {
      configure({ variables: { workspaceUrl: savedUrl, token: savedPat } })
        .then(() => refetch())
        .catch(() => {}); // SetupView handles error display if the user navigates there
    }
  }, [connected]);

  const [doneAfter, setDoneAfter] = useState<string[]>(loadDone);
  const [view, setView] = useState<StepId>("connect");
  const [pendingContext, setPendingContext] = useState<string | undefined>();
  const [theme, setTheme] = useState<"dark" | "light">(
    () => (localStorage.getItem("silverline.theme") as "dark" | "light") ?? "dark",
  );
  const [chatWidth, setChatWidth] = useState<number>(
    () => parseInt(localStorage.getItem("silverline.chatWidth") ?? "320"),
  );

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("silverline.theme", theme);
  }, [theme]);

  const idxOf = (id: StepId) => STEPS.findIndex((s) => s.id === id);
  const isDone = (id: StepId) => (id === "connect" ? connected : doneAfter.includes(id));
  const firstUndone = STEPS.findIndex((s) => !isDone(s.id));
  const currentIdx = firstUndone === -1 ? STEPS.length - 1 : firstUndone;
  const unlocked = (id: StepId) => idxOf(id) <= currentIdx;

  const go = (id: StepId) => unlocked(id) && setView(id);

  const completeAndAdvance = (id: StepId) => {
    const nd = Array.from(new Set([...doneAfter, id]));
    setDoneAfter(nd);
    localStorage.setItem(KEY, JSON.stringify(nd));
    setView(STEPS[Math.min(idxOf(id) + 1, STEPS.length - 1)].id);
  };

  const onRefresh = async () => { await refetch(); };
  const onContinue = () => setView("landing-zone");

  const stepState = (id: StepId): "done" | "current" | "locked" =>
    isDone(id) ? "done" : idxOf(id) === currentIdx ? "current" : "locked";

  let lastPhase = "";

  return (
    <div className="shell" style={{ "--chat-w": `${chatWidth}px` } as React.CSSProperties}>
      <aside className="side">
        <div className="brand">🐺 <span>Silverline<small>Explorer · guided</small></span></div>
        {STEPS.map((s) => {
          const st = stepState(s.id);
          const header = s.phase !== lastPhase ? ((lastPhase = s.phase), s.phase) : null;
          return (
            <div key={s.id}>
              {header && <div className="phase">{header}</div>}
              <button
                className={`navitem ${view === s.id ? "on" : ""} ${st}`}
                onClick={() => go(s.id)}
                disabled={st === "locked"}
                title={st === "locked" ? "Finish the previous step first" : ""}
              >
                <span className="ic">{st === "done" ? "✓" : st === "locked" ? "🔒" : s.icon}</span>
                <span>{s.label}</span>
              </button>
            </div>
          );
        })}
      </aside>

      <main className="content">
        <SelectionTooltip within=".content, .chat-msgs" onSend={setPendingContext} />
        <div className="content-hdr">
          <h2 className="vtitle">{TITLES[view]}</h2>
          <button
            className="theme-toggle"
            onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
            title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          >
            {theme === "dark" ? "☀️" : "🌙"}
          </button>
        </div>
        {view === "connect"        && <SetupView conn={conn} onRefresh={onRefresh} onContinue={onContinue} />}
        {view === "landing-zone"   && <LandingZoneView />}
        {view === "project"        && <ProjectView />}
        {view === "provision"      && <ProvisionView />}
        {view === "seed"           && <SeedView />}
        {view === "data-api"       && <DataApiView />}
        {view === "ingest"         && <IngestView />}
        {view === "medallion"      && <MedallionView />}
        {view === "refresh"        && <LiveView />}
        {view === "business-layer" && <BusinessLayerView />}
        {view === "semantic"       && <SemanticView />}
        {view === "ai-bi"          && <AiBiView />}

        {view !== "connect" && idxOf(view) === currentIdx && idxOf(view) < STEPS.length - 1 && (
          <div className="advance">
            {HAS_VERIFY.has(view) ? (
              <VerifyPanel
                key={view}
                stageId={view}
                nextLabel={STEPS[idxOf(view) + 1].label}
                onVerified={() => completeAndAdvance(view)}
              />
            ) : (
              <button onClick={() => completeAndAdvance(view)}>
                Mark done & continue → {STEPS[idxOf(view) + 1].label}
              </button>
            )}
          </div>
        )}
      </main>

      <ChatPanel
        step={{
          id: view,
          phase: STEPS[idxOf(view)].phase,
          label: STEPS[idxOf(view)].label,
          title: TITLES[view],
          index: idxOf(view) + 1,
          total: STEPS.length,
          status: stepState(view),
        }}
        pendingContext={pendingContext}
        onContextConsumed={() => setPendingContext(undefined)}
        onResize={(w) => {
          setChatWidth(w);
          localStorage.setItem("silverline.chatWidth", String(w));
        }}
      />
    </div>
  );
}

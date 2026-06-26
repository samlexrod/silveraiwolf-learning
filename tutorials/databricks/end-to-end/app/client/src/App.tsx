import { useEffect, useMemo, useState } from "react";
import { gql } from "@apollo/client";
import { useMutation, useQuery } from "@apollo/client/react";
import SetupView from "./views/SetupView";
import StageView, { type StageConfigView } from "./views/StageView";
import ChatPanel from "./ChatPanel";
import SelectionTooltip from "./SelectionTooltip";
import VerifyPanel from "./VerifyPanel";
import "./App.css";

// ── GraphQL ───────────────────────────────────────────────────────────────────

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

const TUTORIAL_CONFIG = gql`
  query TutorialConfig {
    tutorialConfig {
      id
      name
      stages {
        id
        phase
        label
        icon
        title
        special
        hasVerify
        widgets
        content {
          callout {
            icon
            body
          }
          sections {
            heading
            body
          }
        }
      }
    }
  }
`;

// ── Types ─────────────────────────────────────────────────────────────────────

type Conn = { connected: boolean; user?: string; workspace?: string; warehouseId?: string; lakebaseHost?: string };

// ── Progress helpers ──────────────────────────────────────────────────────────

const KEY = "silverline.progress";
const loadDone = (): string[] => {
  try { return JSON.parse(localStorage.getItem(KEY) ?? "[]"); } catch { return []; }
};

// ── Component ─────────────────────────────────────────────────────────────────

export default function App() {
  // Connection state
  const { data: connData, refetch: refetchConn } = useQuery<{ connectionStatus: Conn }>(CONN, { fetchPolicy: "cache-and-network" });
  const conn      = connData?.connectionStatus;
  const connected = !!conn?.connected;
  const [configure] = useMutation(CONFIGURE);

  // Tutorial config — drives all stage definitions, replaces hardcoded STEPS/TITLES/HAS_VERIFY
  const { data: configData } = useQuery<{
    tutorialConfig: { id: string; name: string; stages: StageConfigView[] };
  }>(TUTORIAL_CONFIG);
  const stages = useMemo(() => configData?.tutorialConfig?.stages ?? [], [configData]);

  // Progress + navigation
  const [doneAfter, setDoneAfter] = useState<string[]>(loadDone);
  const [view, setView]           = useState<string>("connect");
  const [pendingContext, setPendingContext] = useState<string | undefined>();

  // Theme
  const [theme, setTheme] = useState<"dark" | "light">(
    () => (localStorage.getItem("silverline.theme") as "dark" | "light") ?? "dark",
  );
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("silverline.theme", theme);
  }, [theme]);

  // Chat panel width
  const [chatWidth, setChatWidth] = useState<number>(
    () => parseInt(localStorage.getItem("silverline.chatWidth") ?? "320"),
  );

  // Re-establish server-side pool whenever it's lost (e.g. after a server restart)
  useEffect(() => {
    if (connected) return;
    const savedUrl = localStorage.getItem("silverline.workspaceUrl");
    const savedPat = localStorage.getItem("silverline.pat");
    if (savedUrl && savedPat) {
      configure({ variables: { workspaceUrl: savedUrl, token: savedPat } })
        .then(() => refetchConn())
        .catch(() => {});
    }
  }, [connected]);

  // ── Stage helpers ─────────────────────────────────────────────────────────

  const idxOf   = (id: string) => stages.findIndex((s) => s.id === id);
  const isDone  = (id: string) => (id === "connect" ? connected : doneAfter.includes(id));
  const firstUndone = stages.findIndex((s) => !isDone(s.id));
  const currentIdx  = firstUndone === -1 ? stages.length - 1 : firstUndone;
  const unlocked    = (id: string) => idxOf(id) <= currentIdx;

  const go = (id: string) => { if (unlocked(id)) setView(id); };

  const completeAndAdvance = (id: string) => {
    const nd = Array.from(new Set([...doneAfter, id]));
    setDoneAfter(nd);
    localStorage.setItem(KEY, JSON.stringify(nd));
    const next = stages[Math.min(idxOf(id) + 1, stages.length - 1)];
    if (next) setView(next.id);
  };

  const stepState = (id: string): "done" | "current" | "locked" =>
    isDone(id) ? "done" : idxOf(id) === currentIdx ? "current" : "locked";

  const activeStage = stages.find((s) => s.id === view);
  const activeIdx   = idxOf(view);

  // ── Sidebar phase grouping ────────────────────────────────────────────────
  let lastPhase = "";

  return (
    <div className="shell" style={{ "--chat-w": `${chatWidth}px` } as React.CSSProperties}>
      {/* Sidebar */}
      <aside className="side">
        <div className="brand">🐺 <span>Silverline<small>Explorer · guided</small></span></div>
        {stages.map((s) => {
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

      {/* Main content */}
      <main className="content">
        <SelectionTooltip within=".content, .chat-msgs" onSend={setPendingContext} />
        <div className="content-hdr">
          <h2 className="vtitle">{activeStage?.title ?? "Loading…"}</h2>
          <button
            className="theme-toggle"
            onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
            title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          >
            {theme === "dark" ? "☀️" : "🌙"}
          </button>
        </div>

        {/* Stage content */}
        {activeStage?.special === "connect" ? (
          <SetupView
            conn={conn}
            onRefresh={async () => { await refetchConn(); }}
            onContinue={() => { const next = stages[1]; if (next) setView(next.id); }}
          />
        ) : activeStage ? (
          <StageView stage={activeStage} />
        ) : null}

        {/* Advance / verify panel */}
        {view !== "connect" && activeIdx === currentIdx && activeIdx < stages.length - 1 && activeStage && (
          <div className="advance">
            {activeStage.hasVerify ? (
              <VerifyPanel
                key={view}
                stageId={view}
                nextLabel={stages[activeIdx + 1]?.label ?? "Next"}
                onVerified={() => completeAndAdvance(view)}
              />
            ) : (
              <button className="form-continue" onClick={() => completeAndAdvance(view)}>
                Mark done & continue → {stages[activeIdx + 1]?.label}
              </button>
            )}
          </div>
        )}
      </main>

      {/* Chat panel */}
      <ChatPanel
        step={activeStage ? {
          id: view,
          phase: activeStage.phase,
          label: activeStage.label,
          title: activeStage.title,
          index: activeIdx + 1,
          total: stages.length,
          status: stepState(view),
        } : undefined}
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

import { useState } from "react";
import { gql } from "@apollo/client";
import { useQuery } from "@apollo/client/react";
import SetupView from "./views/SetupView";
import SourceView from "./views/SourceView";
import LiveView from "./views/LiveView";
import MedallionView from "./views/MedallionView";
import AnalyticsView from "./views/AnalyticsView";
import ChatPanel from "./ChatPanel";
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

type StepId = "connect" | "source" | "refresh" | "medallion" | "analytics";
const STEPS: { id: StepId; phase: string; label: string; icon: string; soon?: boolean }[] = [
  { id: "connect", phase: "Setup", label: "Connect", icon: "🔌" },
  { id: "source", phase: "Lakebase", label: "Source · OLTP", icon: "🗃️" },
  { id: "refresh", phase: "Lakehouse", label: "Refresh · Live", icon: "⚡" },
  { id: "medallion", phase: "Lakehouse", label: "Medallion", icon: "🏗️", soon: true },
  { id: "analytics", phase: "Analytics", label: "Analytics", icon: "📈", soon: true },
];

const TITLES: Record<StepId, string> = {
  connect: "Connect — point the app at your workspace",
  source: "Source — the operational data (Lakebase OLTP)",
  refresh: "Refresh — change the source, watch it stream",
  medallion: "Medallion — bronze → silver → gold",
  analytics: "Analytics — governed metrics",
};

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

  const [doneAfter, setDoneAfter] = useState<string[]>(loadDone);
  const [view, setView] = useState<StepId>("connect");

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

  const onConnected = async () => {
    await refetch();
    setView("source");
  };

  const stepState = (id: StepId): "done" | "current" | "locked" =>
    isDone(id) ? "done" : idxOf(id) === currentIdx ? "current" : "locked";

  let lastPhase = "";

  return (
    <div className="shell">
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
                {s.soon && <span className="soon">soon</span>}
              </button>
            </div>
          );
        })}
      </aside>

      <main className="content">
        <h2 className="vtitle">{TITLES[view]}</h2>
        {view === "connect" && <SetupView conn={conn} onConnected={onConnected} />}
        {view === "source" && <SourceView />}
        {view === "refresh" && <LiveView />}
        {view === "medallion" && <MedallionView />}
        {view === "analytics" && <AnalyticsView />}

        {view !== "connect" && idxOf(view) === currentIdx && idxOf(view) < STEPS.length - 1 && (
          <div className="advance">
            <button onClick={() => completeAndAdvance(view)}>
              Mark done & continue → {STEPS[idxOf(view) + 1].label}
            </button>
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
      />
    </div>
  );
}

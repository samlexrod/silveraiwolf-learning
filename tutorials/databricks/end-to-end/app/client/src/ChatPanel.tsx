import { useEffect, useRef, useState, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const SERVER = import.meta.env.VITE_SERVER ?? "localhost:4000";
const KEY = "silverline.anthropicKey";
const MKEY = "silverline.chatModel";
const AMODE = "silverline.chatAuthMode"; // "" | "ambient" | "key"

const MODELS = [
  { id: "claude-opus-4-8", label: "Opus 4.8 — most capable" },
  { id: "claude-sonnet-4-6", label: "Sonnet 4.6 — balanced" },
  { id: "claude-haiku-4-5", label: "Haiku 4.5 — fastest" },
  { id: "claude-opus-4-7", label: "Opus 4.7" },
];

type Msg = { role: "user" | "assistant"; content: string };

// Detect messages that were built from a text-selection context chip.
function parseContextMsg(text: string): { quote: string; question?: string } | null {
  const m = text.match(
    /^(?:Regarding this from the tutorial:|Can you explain this from the tutorial\?)\n> "([\s\S]+?)"(?:\n\n([\s\S]*))?$/,
  );
  if (!m) return null;
  return { quote: m[1], question: m[2]?.trim() || undefined };
}

// Where the learner is right now — sent with each request so Claude has phase/step context.
export type StepCtx = {
  id: string;
  phase: string;
  label: string;
  title: string;
  index: number;
  total: number;
  status: "done" | "current" | "locked";
};

export default function ChatPanel({
  step,
  pendingContext,
  onContextConsumed,
  onResize,
}: {
  step?: StepCtx;
  pendingContext?: string;
  onContextConsumed?: () => void;
  onResize?: (w: number) => void;
}) {
  const [authMode, setAuthMode] = useState<string>(() => localStorage.getItem(AMODE) ?? "");
  const [apiKey, setApiKey] = useState<string>(() => localStorage.getItem(KEY) ?? "");
  const [keyInput, setKeyInput] = useState("");
  const [ambient, setAmbient] = useState<boolean | null>(null);
  const [antAvailable, setAntAvailable] = useState(false);
  const [signingIn, setSigningIn] = useState(false);
  const [signInErr, setSignInErr] = useState("");
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [model, setModel] = useState<string>(() => localStorage.getItem(MKEY) ?? MODELS[0].id);
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const chatRef = useRef<HTMLElement>(null);

  const startResize = useCallback((e: React.MouseEvent) => {
    if (!onResize) return;
    e.preventDefault();
    const startX = e.clientX;
    const startW = chatRef.current?.offsetWidth ?? 320;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    const onMove = (ev: MouseEvent) => {
      const newW = Math.max(240, Math.min(700, startW + (startX - ev.clientX)));
      onResize(newW);
    };
    const onUp = () => {
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  }, [onResize]);

  const enabled = authMode === "ambient" || (authMode === "key" && !!apiKey);

  useEffect(() => {
    fetch(`http://${SERVER}/api/chat/auth-status`)
      .then((r) => r.json())
      .then((d) => {
        setAmbient(!!d.ambient);
        setAntAvailable(!!d.antAvailable);
      })
      .catch(() => {
        setAmbient(false);
        setAntAvailable(false);
      });
  }, []);

  const signIn = async () => {
    setSigningIn(true);
    setSignInErr("");
    try {
      const r = await fetch(`http://${SERVER}/api/chat/login`, { method: "POST" });
      const d = await r.json();
      if (!d.ok) throw new Error(d.error ?? "sign-in failed");
      useAmbient(); // server now holds the OAuth token
    } catch (e) {
      setSignInErr(e instanceof Error ? e.message : String(e));
    } finally {
      setSigningIn(false);
    }
  };

  useEffect(() => {
    scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight);
  }, [messages, busy]);

  // When highlighted text arrives, focus the chat input so the user can type their question
  useEffect(() => {
    if (pendingContext && enabled) {
      textareaRef.current?.focus();
    }
  }, [pendingContext, enabled]);

  const useAmbient = () => {
    localStorage.setItem(AMODE, "ambient");
    setAuthMode("ambient");
  };
  const saveKey = () => {
    const k = keyInput.trim();
    localStorage.setItem(KEY, k);
    localStorage.setItem(AMODE, "key");
    setApiKey(k);
    setAuthMode("key");
  };
  const clearAuth = () => {
    localStorage.removeItem(KEY);
    localStorage.removeItem(AMODE);
    setApiKey("");
    setAuthMode("");
    setMessages([]);
  };

  const send = useCallback(async () => {
    const rawText = input.trim();
    // allow sending with just a context chip (no extra text)
    if ((!rawText && !pendingContext) || busy) return;
    const text = pendingContext
      ? rawText
        ? `Regarding this from the tutorial:\n> "${pendingContext}"\n\n${rawText}`
        : `Can you explain this from the tutorial?\n> "${pendingContext}"`
      : rawText;
    const next: Msg[] = [...messages, { role: "user", content: text }];
    onContextConsumed?.();
    setMessages([...next, { role: "assistant", content: "" }]);
    setInput("");
    setBusy(true);

    const patchLast = (fn: (c: string) => string) =>
      setMessages((m) => {
        const copy = m.slice();
        const last = copy[copy.length - 1];
        copy[copy.length - 1] = { role: "assistant", content: fn(last.content) };
        return copy;
      });

    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (authMode === "key") headers["x-anthropic-key"] = apiKey;
      const resp = await fetch(`http://${SERVER}/api/chat`, {
        method: "POST",
        headers,
        body: JSON.stringify({ messages: next, model, step }),
      });
      if (!resp.ok || !resp.body) {
        const err = await resp.json().catch(() => ({ error: resp.statusText }));
        throw new Error(err.error ?? "request failed");
      }
      const reader = resp.body.getReader();
      const dec = new TextDecoder();
      let buf = "";
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const parts = buf.split("\n\n");
        buf = parts.pop() ?? "";
        for (const p of parts) {
          const line = p.replace(/^data: /, "").trim();
          if (!line) continue;
          const ev = JSON.parse(line) as { text?: string; error?: string; done?: boolean };
          if (ev.text) patchLast((c) => c + ev.text);
          else if (ev.error) patchLast(() => `⚠️ ${ev.error}`);
        }
      }
    } catch (e) {
      patchLast(() => `⚠️ ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setBusy(false);
    }
  }, [input, pendingContext, busy, messages, authMode, apiKey, model, step, onContextConsumed]);

  if (!enabled) {
    return (
      <aside className="chat" ref={chatRef}>
        <div className="chat-resize-handle" onMouseDown={startResize} />
        <div className="chat-head">💬 Ask Claude</div>
        <div className="chat-key">
          {ambient === null && <p className="muted">Checking for credentials…</p>}

          {antAvailable && (
            <>
              <button onClick={signIn} disabled={signingIn}>
                {signingIn ? "Opening browser…" : "🔓 Sign in with Claude"}
              </button>
              {signingIn && <small className="muted">Approve the sign-in in your browser, then return here.</small>}
              {signInErr && <p className="err">{signInErr}</p>}
            </>
          )}

          {ambient && (
            <button onClick={useAmbient}>✦ Use this machine's credentials</button>
          )}

          {(antAvailable || ambient) && <div className="chat-or"><span>or paste a key</span></div>}

          {ambient === false && !antAvailable && (
            <p className="muted">
              Paste your Anthropic API key — browser + server memory only, never written to disk. (Install the
              Anthropic CLI for one-click sign-in instead.)
            </p>
          )}
          <input
            type="password"
            placeholder="sk-ant-…"
            value={keyInput}
            onChange={(e) => setKeyInput(e.target.value)}
          />
          <button onClick={saveKey} disabled={!keyInput.trim()}>Enable with key</button>
          <small className="muted">Get a key at console.anthropic.com → Settings → API keys</small>
        </div>
      </aside>
    );
  }

  return (
    <aside className="chat" ref={chatRef}>
      <div className="chat-resize-handle" onMouseDown={startResize} />
      <div className="chat-head">
        💬 Ask Claude
        <button className="link" onClick={clearAuth}>{authMode === "ambient" ? "switch" : "reset key"}</button>
      </div>
      <div className="chat-model-row">
        <select
          value={model}
          onChange={(e) => {
            setModel(e.target.value);
            localStorage.setItem(MKEY, e.target.value);
          }}
        >
          {MODELS.map((m) => (
            <option key={m.id} value={m.id}>{m.label}</option>
          ))}
        </select>
      </div>
      <div className="chat-msgs" ref={scrollRef}>
        {messages.length === 0 && (
          <p className="muted chat-empty">Ask anything about the tutorial, Databricks, Lakebase, or SQL.</p>
        )}
        {messages.map((m, i) => {
          if (m.role === "user") {
            const ctx = parseContextMsg(m.content);
            return (
              <div key={i} className="bubble user">
                {ctx ? (
                  <>
                    <div className="bubble-quote">
                      <span className="bubble-quote-label">From the tutorial</span>
                      <span className="bubble-quote-text">{ctx.quote}</span>
                    </div>
                    {ctx.question
                      ? <div className="bubble-question">{ctx.question}</div>
                      : <div className="bubble-question muted">Can you explain this?</div>
                    }
                  </>
                ) : m.content}
              </div>
            );
          }
          return (
            <div key={i} className="bubble assistant">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {m.content || (busy && i === messages.length - 1 ? "…" : "")}
              </ReactMarkdown>
            </div>
          );
        })}
      </div>
      {pendingContext && (
        <div className="ctx-chip">
          <span>
            Re: &ldquo;
            {pendingContext.length > 80 ? pendingContext.slice(0, 80) + "…" : pendingContext}
            &rdquo;
          </span>
          <button
            type="button"
            aria-label="Dismiss context"
            onClick={onContextConsumed}
          >
            ✕
          </button>
        </div>
      )}
      <form
        className="chat-input"
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
      >
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={pendingContext ? "Type your question about the highlighted text…" : "Ask about a stage…"}
          rows={2}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
        />
        <button type="submit" disabled={busy || (!input.trim() && !pendingContext)}>
          {busy ? "…" : "Send"}
        </button>
      </form>
    </aside>
  );
}

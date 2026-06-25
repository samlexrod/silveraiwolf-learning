import { useEffect, useRef, useState } from "react";

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

export default function ChatPanel() {
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

  const send = async () => {
    const text = input.trim();
    if (!text || busy) return;
    const next: Msg[] = [...messages, { role: "user", content: text }];
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
        body: JSON.stringify({ messages: next, model }),
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
  };

  if (!enabled) {
    return (
      <aside className="chat">
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
    <aside className="chat">
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
        {messages.map((m, i) => (
          <div key={i} className={`bubble ${m.role}`}>
            {m.content || (busy && i === messages.length - 1 ? "…" : "")}
          </div>
        ))}
      </div>
      <form
        className="chat-input"
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
      >
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about a stage…"
          rows={2}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
        />
        <button type="submit" disabled={busy || !input.trim()}>
          {busy ? "…" : "Send"}
        </button>
      </form>
    </aside>
  );
}

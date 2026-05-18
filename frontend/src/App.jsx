import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const API_BASE = "http://127.0.0.1:8000";
const SESSION_KEY = "linkedin-llm-chat-session";

function mkSessionId() {
  return `session-${crypto.randomUUID()}`;
}

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [customModel, setCustomModel] = useState("");
  const [useWebSearch, setUseWebSearch] = useState(true);
  const [isStreaming, setIsStreaming] = useState(false);
  const [sources, setSources] = useState([]);
  const [webSources, setWebSources] = useState([]);
  const [error, setError] = useState("");
  const [kbExpanded, setKbExpanded] = useState(true);
  const [webExpanded, setWebExpanded] = useState(true);

  const endRef = useRef(null);

  const sessionId = useMemo(() => {
    const saved = localStorage.getItem(SESSION_KEY);
    if (saved) return saved;
    const created = mkSessionId();
    localStorage.setItem(SESSION_KEY, created);
    return created;
  }, []);

  useEffect(() => {
    void fetch(`${API_BASE}/api/models`)
      .then((res) => res.json())
      .then((data) => {
        setModels(data.models || []);
        setSelectedModel(data.default || data.models?.[0]?.id || "");
      })
      .catch(() => setError("Failed to load model list"));

    void fetch(`${API_BASE}/api/memory/${sessionId}`)
      .then((res) => res.json())
      .then((data) => {
        if (!Array.isArray(data.messages)) return;
        setMessages(data.messages.map((m) => ({ role: m.role, content: m.content })));
      })
      .catch(() => {});
  }, [sessionId]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isStreaming]);

  async function clearMemory() {
    await fetch(`${API_BASE}/api/memory/${sessionId}`, { method: "DELETE" });
    setMessages([]);
    setSources([]);
    setWebSources([]);
  }

  async function onSubmit(e) {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;

    setError("");

    const userMessage = { role: "user", content: input.trim() };
    const assistantMessage = { role: "assistant", content: "" };
    setMessages((prev) => [...prev, userMessage, assistantMessage]);

    const outgoing = input.trim();
    setInput("");
    setIsStreaming(true);

    const modelId = selectedModel === "__custom__" ? customModel.trim() : selectedModel;

    try {
      const res = await fetch(`${API_BASE}/api/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: outgoing,
          session_id: sessionId,
          model_id: modelId,
          use_web_search: useWebSearch,
          n_results: 10
        })
      });

      if (!res.ok || !res.body) {
        throw new Error(`Request failed: ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.trim()) continue;
          const event = JSON.parse(line);

          if (event.type === "meta") {
            setSources(event.sources || []);
            setWebSources(event.web_sources || []);
          }

          if (event.type === "delta") {
            setMessages((prev) => {
              const next = [...prev];
              const idx = next.length - 1;
              next[idx] = {
                ...next[idx],
                content: (next[idx].content || "") + (event.text || "")
              };
              return next;
            });
          }

          if (event.type === "error") {
            setError(event.message || "Streaming failed");
          }
        }
      }
    } catch (err) {
      setError(String(err));
    } finally {
      setIsStreaming(false);
    }
  }

  return (
    <div className="page-shell">
      <div className="grain" />
      <main className="chat-wrap">
        <header className="topbar">
          <div>
            <p className="kicker">LinkedIn LLM</p>
            <h1>Career Chat</h1>
          </div>

          <div className="controls">
            <label className="control">
              <span>Model</span>
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                disabled={isStreaming}
              >
                {models.map((m) => (
                  <option key={m.id} value={m.id}>{m.label}</option>
                ))}
                <option value="__custom__">Custom model id</option>
              </select>
            </label>

            {selectedModel === "__custom__" && (
              <label className="control">
                <span>Model id</span>
                <input
                  value={customModel}
                  onChange={(e) => setCustomModel(e.target.value)}
                  placeholder="eu.anthropic.claude-..."
                  disabled={isStreaming}
                />
              </label>
            )}

            <label className="check">
              <input
                type="checkbox"
                checked={useWebSearch}
                onChange={(e) => setUseWebSearch(e.target.checked)}
                disabled={isStreaming}
              />
              <span>Web search</span>
            </label>

            <button className="ghost" type="button" onClick={clearMemory} disabled={isStreaming}>
              Clear memory
            </button>
          </div>
        </header>

        <div className="content-grid">
          <section className="chat-main">
            <section className="messages">
              {messages.length === 0 && (
                <div className="empty">
                  <h2>Ask about your network, companies, jobs, or recent activity</h2>
                  <p>
                    This chat remembers your previous turns in this session, streams answers live,
                    and can optionally pull web context.
                  </p>
                </div>
              )}

              {messages.map((m, idx) => (
                <article key={`${m.role}-${idx}`} className={`bubble ${m.role}`}>
                  {m.role === "assistant" ? (
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                  ) : (
                    <p>{m.content}</p>
                  )}
                </article>
              ))}
              <div ref={endRef} />
            </section>

            <form className="composer" onSubmit={onSubmit}>
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Message LinkedIn LLM..."
                rows={2}
                disabled={isStreaming}
              />
              <button type="submit" disabled={isStreaming || !input.trim()}>
                {isStreaming ? "Streaming..." : "Send"}
              </button>
            </form>
          </section>

          <aside className="sidebar">
            {error && <p className="error">{error}</p>}

            <div className="sources">
              <div className="source-section">
                <button className="section-toggle" onClick={() => setKbExpanded(v => !v)}>
                  <span>Knowledge base{sources.length > 0 ? ` · ${sources.length}` : ""}</span>
                  <span className={`chevron${kbExpanded ? " open" : ""}`}>›</span>
                </button>
                {kbExpanded && (
                  <div className="section-body">
                    {sources.length === 0 ? (
                      <p className="muted">No sources yet.</p>
                    ) : (
                      <ul>
                        {sources.slice(0, 8).map((s) => (
                          <li key={`${s.rank}-${s.entity_name}-${s.source}`}>
                            <strong>{s.entity_name || s.source || "Source"}</strong>
                            <span>{s.snippet}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </div>

              <div className="source-section">
                <button className="section-toggle" onClick={() => setWebExpanded(v => !v)}>
                  <span>Web sources{webSources.length > 0 ? ` · ${webSources.length}` : ""}</span>
                  <span className={`chevron${webExpanded ? " open" : ""}`}>›</span>
                </button>
                {webExpanded && (
                  <div className="section-body">
                    {webSources.length === 0 ? (
                      <p className="muted">No web sources for this turn.</p>
                    ) : (
                      <ul>
                        {webSources.slice(0, 5).map((s) => (
                          <li key={s.url || s.title}>
                            <a href={s.url} target="_blank" rel="noreferrer">{s.title}</a>
                            <span>{s.snippet}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </div>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}

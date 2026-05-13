import React, { useEffect, useMemo, useRef, useState } from 'react';

const HISTORY_KEY = 'linkedin-llm-chat-history';

const STARTER_PROMPTS = [
  'Summarise my recent networking activity.',
  'Who in my network looks relevant for cloud platform roles?',
  'What themes keep coming up in my recent messages?',
];

function parseSseBlock(block) {
  const lines = block.split('\n');
  let event = 'message';
  const dataLines = [];

  for (const line of lines) {
    if (line.startsWith('event:')) {
      event = line.slice(6).trim();
    } else if (line.startsWith('data:')) {
      dataLines.push(line.startsWith('data: ') ? line.slice(6) : line.slice(5));
    }
  }

  return {
    event,
    data: dataLines.join('\n'),
  };
}

function formatTime(timestamp) {
  return new Date(timestamp).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  });
}

function App() {
  const [draft, setDraft] = useState('');
  const [messages, setMessages] = useState(() => {
    const saved = window.localStorage.getItem(HISTORY_KEY);
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        return [];
      }
    }
    return [
      {
        id: crypto.randomUUID(),
        role: 'assistant',
        content:
          'Your LinkedIn knowledge base is loaded. Ask about people, conversations, roles, company signals, or recent activity.',
        createdAt: Date.now(),
        sources: [],
      },
    ];
  });
  const [status, setStatus] = useState({ state: 'checking', collections: {} });
  const [isSending, setIsSending] = useState(false);
  const listRef = useRef(null);

  function updateMessage(messageId, updater) {
    setMessages((current) => current.map((message) => {
      if (message.id !== messageId) {
        return message;
      }
      return typeof updater === 'function' ? updater(message) : { ...message, ...updater };
    }));
  }

  useEffect(() => {
    window.localStorage.setItem(HISTORY_KEY, JSON.stringify(messages));
  }, [messages]);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, isSending]);

  useEffect(() => {
    async function loadHealth() {
      try {
        const response = await fetch('/api/health');
        if (!response.ok) {
          throw new Error('Healthcheck failed');
        }
        const payload = await response.json();
        setStatus({ state: 'online', collections: payload.collections });
      } catch {
        setStatus({ state: 'offline', collections: {} });
      }
    }

    loadHealth();
  }, []);

  const collectionEntries = useMemo(
    () => Object.entries(status.collections || {}).sort((left, right) => right[1] - left[1]),
    [status.collections],
  );

  async function sendMessage(text) {
    const trimmed = text.trim();
    if (!trimmed || isSending) {
      return;
    }

    const userMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: trimmed,
      createdAt: Date.now(),
      sources: [],
    };

    const assistantId = crypto.randomUUID();
    const assistantMessage = {
      id: assistantId,
      role: 'assistant',
      content: '',
      createdAt: Date.now(),
      sources: [],
      streaming: true,
    };

    setMessages((current) => [...current, userMessage, assistantMessage]);
    setDraft('');
    setIsSending(true);

    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: trimmed }),
      });

      if (!response.ok) {
        throw new Error('The assistant could not answer right now.');
      }

      if (!response.body) {
        throw new Error('Streaming is not available in this browser.');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      const handleEvent = (eventName, rawData) => {
        if (eventName === 'token') {
          updateMessage(assistantId, (message) => ({
            ...message,
            content: `${message.content}${rawData}`,
          }));
          return;
        }

        if (eventName === 'meta') {
          const payload = JSON.parse(rawData);
          updateMessage(assistantId, { sources: payload.sources || [] });
          return;
        }

        if (eventName === 'done') {
          const payload = JSON.parse(rawData);
          updateMessage(assistantId, {
            content: payload.answer,
            sources: payload.sources || [],
            streaming: false,
          });
          setIsSending(false);
          return;
        }

        if (eventName === 'error') {
          const payload = JSON.parse(rawData);
          setIsSending(false);
          throw new Error(payload.message || 'The assistant could not answer right now.');
        }
      };

      while (true) {
        const { value, done } = await reader.read();
        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const blocks = buffer.split('\n\n');
        buffer = blocks.pop() || '';

        for (const block of blocks) {
          if (!block.trim()) {
            continue;
          }
          const parsed = parseSseBlock(block);
          handleEvent(parsed.event, parsed.data);
        }
      }

      const trailing = decoder.decode();
      if (trailing) {
        buffer += trailing;
      }

      if (buffer.trim()) {
        const parsed = parseSseBlock(buffer.trim());
        handleEvent(parsed.event, parsed.data);
      }
    } catch (error) {
      updateMessage(assistantId, {
        content: error.message,
        sources: [],
        error: true,
        streaming: false,
      });
    } finally {
      setIsSending(false);
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    void sendMessage(draft);
  }

  function clearHistory() {
    const seed = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content:
        'History cleared. Ask a fresh question about your profile, network, messages, jobs, or activity.',
      createdAt: Date.now(),
      sources: [],
    };
    setMessages([seed]);
  }

  return (
    <div className="shell">
      <aside className="rail">
        <div className="rail__masthead">
          <p className="eyebrow">Signal Deck</p>
          <h1>LinkedIn Career Assistant</h1>
          <p className="lede">
            A dark, local-first operator console for your network, messages, hiring signals, and career memory.
          </p>
        </div>

        <section className="panel panel--status">
          <div className="panel__header">
            <span>Neural link</span>
            <span className={`status-pill status-pill--${status.state}`}>{status.state}</span>
          </div>
          <p>
            {status.state === 'online'
              ? 'Vector collections are online and the streaming assistant is ready.'
              : status.state === 'checking'
                ? 'Bootstrapping API and collection telemetry.'
                : 'API unavailable. Start the FastAPI server before chatting.'}
          </p>
        </section>

        <section className="panel">
          <div className="panel__header">
            <span>Knowledge banks</span>
            <span>{collectionEntries.length}</span>
          </div>
          <div className="collection-list">
            {collectionEntries.length ? (
              collectionEntries.map(([name, count]) => (
                <div key={name} className="collection-row">
                  <span>{name.replaceAll('_', ' ')}</span>
                  <strong>{count}</strong>
                </div>
              ))
            ) : (
              <p className="muted">No collection stats loaded yet.</p>
            )}
          </div>
        </section>

        <section className="panel">
          <div className="panel__header">
            <span>Quick probes</span>
            <span>{STARTER_PROMPTS.length}</span>
          </div>
          <div className="prompt-stack">
            {STARTER_PROMPTS.map((prompt) => (
              <button
                key={prompt}
                className="prompt-chip"
                type="button"
                onClick={() => void sendMessage(prompt)}
              >
                {prompt}
              </button>
            ))}
          </div>
        </section>
      </aside>

      <main className="conversation-frame">
        <header className="conversation-header">
          <div>
            <p className="eyebrow">Tech assistant mode</p>
            <h2>Ask across your profile, network, communications, and jobs</h2>
          </div>
          <div className="header-actions">
            <span className="mode-chip">Streaming enabled · history stored locally</span>
            <button className="ghost-button" type="button" onClick={clearHistory}>
              Clear history
            </button>
          </div>
        </header>

        <div className="conversation-list" ref={listRef}>
          {messages.map((message) => (
            <article
              key={message.id}
              className={`message-card message-card--${message.role} ${message.error ? 'message-card--error' : ''}`}
            >
              <div className="message-card__meta">
                <span>{message.role === 'user' ? 'You' : 'Assistant'}</span>
                <time>{formatTime(message.createdAt)}</time>
              </div>
              <p className="message-card__body">{message.content}</p>

              {message.sources?.length > 0 && !message.streaming && (
                <div className="source-grid">
                  {message.sources.slice(0, 4).map((source) => (
                    <section key={`${message.id}-${source.rank}`} className="source-card">
                      <div className="source-card__meta">
                        <span>{source.collection || source.type}</span>
                        <span>{source.entity_name || source.source || 'LinkedIn source'}</span>
                      </div>
                      <p>{source.snippet}</p>
                    </section>
                  ))}
                </div>
              )}
            </article>
          ))}

          {isSending && messages[messages.length - 1]?.streaming && !messages[messages.length - 1]?.content && (
            <article className="message-card message-card--assistant message-card--loading">
              <div className="message-card__meta">
                <span>Assistant</span>
                <span>streaming</span>
              </div>
              <div className="typing-bar">
                <span />
                <span />
                <span />
              </div>
            </article>
          )}
        </div>

        <form className="composer" onSubmit={handleSubmit}>
          <label className="composer__label" htmlFor="chat-message">
            Ask the assistant to reason over your LinkedIn memory
          </label>
          <div className="composer__row">
            <textarea
              id="chat-message"
              rows="3"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Ask about recent networking momentum, inbound roles, message themes, skills, or company signals."
            />
            <button className="send-button" type="submit" disabled={isSending || !draft.trim()}>
              {isSending ? 'Streaming...' : 'Transmit'}
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}

export default App;
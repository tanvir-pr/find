"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { ChatTurn } from "@/lib/types";

type Bubble = ChatTurn & { tools?: string[] };

export default function ChatPage() {
  const { t } = useI18n();
  const [history, setHistory] = useState<Bubble[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  const suggestions = useMemo(
    () => [t("chat.s1"), t("chat.s2"), t("chat.s3"), t("chat.s4"), t("chat.s5")],
    [t],
  );

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history, busy]);

  async function send(message: string) {
    const text = message.trim();
    if (!text || busy) return;
    setBusy(true);
    setError("");
    const prior = history.map(({ role, content }) => ({ role, content }));
    setHistory((prev) => [...prev, { role: "user", content: text }]);
    setInput("");
    try {
      const res = await api.chat(text, prior);
      setHistory((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.reply,
          tools: res.tools_used.map((tool) => tool.name),
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("chat.failed"));
      setHistory((prev) => prev.slice(0, -1));
      setInput(text);
    } finally {
      setBusy(false);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void send(input);
  }

  return (
    <div className="fade-up flex h-[calc(100vh-7rem)] flex-col gap-4">
      <header>
        <h1 className="text-3xl">{t("chat.title")}</h1>
        <p className="mt-1 text-sm opacity-70">{t("chat.subtitle")}</p>
      </header>

      <div className="flex flex-wrap gap-2">
        {suggestions.map((s) => (
          <button
            key={s}
            type="button"
            className="btn btn-ghost text-xs"
            onClick={() => void send(s)}
            disabled={busy}
          >
            {s}
          </button>
        ))}
      </div>

      <section className="panel flex min-h-0 flex-1 flex-col overflow-hidden">
        <div className="flex-1 space-y-3 overflow-y-auto p-4">
          {history.length === 0 ? (
            <p className="text-sm opacity-60">{t("chat.empty")}</p>
          ) : null}
          {history.map((m, idx) => (
            <article
              key={`${m.role}-${idx}`}
              className={`max-w-[90%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                m.role === "user"
                  ? "ml-auto bg-[var(--ink)] text-white"
                  : "bg-white/85 text-[var(--ink)]"
              }`}
            >
              <p className="whitespace-pre-wrap">{m.content}</p>
              {m.tools?.length ? (
                <p className="mt-2 text-xs opacity-60">
                  {t("chat.tools")}: {m.tools.join(", ")}
                </p>
              ) : null}
            </article>
          ))}
          {busy ? <p className="text-sm opacity-60">{t("chat.thinking")}</p> : null}
          <div ref={endRef} />
        </div>

        <form onSubmit={onSubmit} className="flex gap-2 border-t border-[var(--line)] p-3">
          <input
            className="field"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={t("chat.placeholder")}
            disabled={busy}
          />
          <button className="btn btn-primary" type="submit" disabled={busy || !input.trim()}>
            {t("chat.send")}
          </button>
        </form>
      </section>
      {error ? <p className="text-[var(--coral)]">{error}</p> : null}
    </div>
  );
}

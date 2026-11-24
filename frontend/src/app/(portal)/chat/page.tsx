"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { Alert, PageHeader } from "@/components/ui";
import { ChatRichReply } from "@/components/ChatRichReply";
import type { ChatTurn } from "@/lib/types";

type ToolUsed = {
  name: string;
  arguments: Record<string, unknown>;
  result_preview: string;
};

type Bubble = ChatTurn & { tools?: ToolUsed[]; ask?: string };

export default function ChatPage() {
  const { t, lang } = useI18n();
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
          tools: res.tools_used,
          ask: text,
        },
      ]);
    } catch (err) {
      const msg =
        err instanceof Error && err.name === "AbortError"
          ? lang === "bn"
            ? "সময় শেষ — AI দেরি করছে। আবার চেষ্টা করুন।"
            : "Timed out — AI is slow. Try again."
          : err instanceof Error
            ? err.message
            : t("chat.failed");
      setError(msg);
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
    <div className="flex h-[calc(100vh-5.5rem)] flex-col gap-3">
      <PageHeader title={t("chat.title")} subtitle={t("chat.subtitle")} />

      <div className="flex flex-wrap gap-1.5">
        {suggestions.map((s) => (
          <button
            key={s}
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => void send(s)}
            disabled={busy}
          >
            {s}
          </button>
        ))}
      </div>

      <section className="panel flex min-h-0 flex-1 flex-col overflow-hidden">
        <div className="flex-1 space-y-3 overflow-y-auto p-3 md:p-4">
          {history.length === 0 ? (
            <p className="py-8 text-center text-sm text-[var(--muted)]">{t("chat.empty")}</p>
          ) : null}
          {history.map((m, idx) =>
            m.role === "user" ? (
              <article key={`${m.role}-${idx}`} className="chat-bubble-user text-sm leading-relaxed">
                <p className="whitespace-pre-wrap">{m.content}</p>
              </article>
            ) : (
              <article key={`${m.role}-${idx}`} className="chat-bubble-ai">
                <ChatRichReply content={m.content} tools={m.tools} userQuery={m.ask} />
              </article>
            ),
          )}
          {busy ? <p className="text-sm text-[var(--muted)]">{t("chat.thinking")}</p> : null}
          <div ref={endRef} />
        </div>

        <form onSubmit={onSubmit} className="flex gap-2 border-t border-[var(--line)] p-2.5">
          <input
            className="field"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={t("chat.placeholder")}
            disabled={busy}
          />
          <button className="btn btn-primary shrink-0" type="submit" disabled={busy || !input.trim()}>
            {t("chat.send")}
          </button>
        </form>
      </section>
      {error ? <Alert>{error}</Alert> : null}
    </div>
  );
}

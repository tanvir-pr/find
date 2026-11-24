"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { Alert, PageHeader } from "@/components/ui";
import type { AgentAction, AutomationSettings } from "@/lib/types";

export default function AutomationPage() {
  const { lang } = useI18n();
  const bn = lang === "bn";
  const [settings, setSettings] = useState<AutomationSettings | null>(null);
  const [actions, setActions] = useState<AgentAction[]>([]);
  const [filter, setFilter] = useState<"pending" | "all">("pending");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      const [s, a] = await Promise.all([
        api.automationSettings(),
        api.automationActions(filter === "pending" ? "pending" : undefined),
      ]);
      setSettings(s);
      setActions(a);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Load failed");
    }
  }, [filter]);

  useEffect(() => {
    void load();
  }, [load]);

  async function toggleAutopilot(on: boolean) {
    setBusy(true);
    setError("");
    try {
      const s = await api.updateAutomationSettings({ autopilot_enabled: on });
      setSettings(s);
      setMsg(
        on
          ? bn
            ? "Autopilot চালু — Auto মার্ক করা কাজ নিজে চলবে"
            : "Autopilot on — auto-marked actions will run"
          : bn
            ? "Autopilot বন্ধ — সব কাজে Approve লাগবে"
            : "Autopilot off — every action needs approve",
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    } finally {
      setBusy(false);
    }
  }

  async function patchFlag(key: keyof AutomationSettings, value: boolean) {
    setBusy(true);
    try {
      const s = await api.updateAutomationSettings({ [key]: value });
      setSettings(s);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    } finally {
      setBusy(false);
    }
  }

  async function runScan() {
    setBusy(true);
    setError("");
    setMsg("");
    try {
      const res = await api.automationScan();
      setMsg(res.message);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Scan failed");
    } finally {
      setBusy(false);
    }
  }

  async function approve(id: string) {
    setBusy(true);
    try {
      await api.approveAction(id);
      setMsg(bn ? "Approve করে চালানো হয়েছে" : "Approved and executed");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approve failed");
    } finally {
      setBusy(false);
    }
  }

  async function reject(id: string) {
    setBusy(true);
    try {
      await api.rejectAction(id);
      setMsg(bn ? "Reject করা হয়েছে" : "Rejected");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reject failed");
    } finally {
      setBusy(false);
    }
  }

  const flags: { key: keyof AutomationSettings; en: string; bn: string; risk: "auto" | "approval" }[] = [
    { key: "auto_due_reminders", en: "Due reminder SMS", bn: "বাকি SMS", risk: "auto" },
    { key: "auto_daily_sms", en: "Daily sales SMS", bn: "দৈনিক সেল SMS", risk: "auto" },
    { key: "auto_low_stock_alerts", en: "Low-stock alerts", bn: "লো-স্টক অ্যালার্ট", risk: "approval" },
    { key: "auto_expiring_alerts", en: "Expiry alerts", bn: "মেয়াদ অ্যালার্ট", risk: "approval" },
    { key: "auto_reorder_draft", en: "Reorder draft", bn: "অর্ডার ড্রাফট", risk: "approval" },
  ];

  return (
    <div className="space-y-5">
      <PageHeader
        title={bn ? "AI অ্যাকশন" : "AI Actions"}
        subtitle={
          bn
            ? "স্ক্যান → Auto চালাও অথবা Approve দিয়ে এক্সিকিউট"
            : "Scan → run Auto actions or Approve to execute"
        }
        actions={
          <button className="btn btn-primary" type="button" disabled={busy} onClick={() => void runScan()}>
            {busy ? (bn ? "চলছে…" : "Working…") : bn ? "এখন স্ক্যান করো" : "Run scan now"}
          </button>
        }
      />

      {error ? <Alert>{error}</Alert> : null}
      {msg ? <Alert tone="ok">{msg}</Alert> : null}

      <section className="panel p-4 md:p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold">{bn ? "Autopilot" : "Autopilot"}</h2>
            <p className="mt-1 text-sm text-[var(--muted)]">
              {bn
                ? "বন্ধ থাকলে সব কাজে Approve লাগবে। চালু থাকলে নিচের Auto টিকগুলো নিজে চলবে।"
                : "When off, everything needs Approve. When on, checked Auto items run themselves."}
            </p>
          </div>
          <div className="seg">
            <button
              type="button"
              className="seg-btn"
              data-active={settings?.autopilot_enabled === false}
              disabled={busy || !settings}
              onClick={() => void toggleAutopilot(false)}
            >
              {bn ? "সব Approve" : "Approve all"}
            </button>
            <button
              type="button"
              className="seg-btn"
              data-active={settings?.autopilot_enabled === true}
              disabled={busy || !settings}
              onClick={() => void toggleAutopilot(true)}
            >
              {bn ? "Autopilot ON" : "Autopilot ON"}
            </button>
          </div>
        </div>

        <div className="grid gap-2 sm:grid-cols-2">
          {flags.map((f) => {
            const on = Boolean(settings?.[f.key]);
            return (
              <label
                key={String(f.key)}
                className="flex items-start gap-3 rounded-[12px] border border-[var(--line)] bg-[var(--surface-2)] px-3 py-2.5 text-sm"
              >
                <input
                  type="checkbox"
                  className="mt-1"
                  checked={on}
                  disabled={busy || !settings}
                  onChange={(e) => void patchFlag(f.key, e.target.checked)}
                />
                <span>
                  <span className="font-medium">{bn ? f.bn : f.en}</span>
                  <span className="mt-0.5 block text-xs text-[var(--muted)]">
                    {f.risk === "auto"
                      ? bn
                        ? "কম ঝুঁকি · Autopilot ON হলে অটো"
                        : "Low risk · auto when Autopilot ON"
                      : bn
                        ? "বেশি ঝুঁকি · ডিফল্টে Approve"
                        : "Higher risk · Approve by default"}
                  </span>
                </span>
              </label>
            );
          })}
        </div>
      </section>

      <section className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold">{bn ? "অ্যাকশন কিউ" : "Action queue"}</h2>
          <div className="seg">
            <button
              type="button"
              className="seg-btn"
              data-active={filter === "pending"}
              onClick={() => setFilter("pending")}
            >
              Pending
            </button>
            <button
              type="button"
              className="seg-btn"
              data-active={filter === "all"}
              onClick={() => setFilter("all")}
            >
              All
            </button>
          </div>
        </div>

        {!actions.length ? (
          <div className="panel px-4 py-8 text-center text-sm text-[var(--muted)]">
            {bn ? "কোনো অ্যাকশন নেই — স্ক্যান চালান" : "No actions — run a scan"}
          </div>
        ) : (
          <ul className="space-y-3">
            {actions.map((a) => (
              <li key={a.id} className="panel p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-semibold">{a.title}</h3>
                      <span className={`badge ${a.mode === "auto" ? "badge-accent" : "badge-warn"}`}>
                        {a.mode === "auto" ? "Auto" : "Needs approve"}
                      </span>
                      <span className="badge badge-muted">{a.status}</span>
                    </div>
                    <p className="mt-1 text-sm text-[var(--muted)]">{a.summary}</p>
                    {a.error_message ? (
                      <p className="mt-1 text-sm text-[var(--danger)]">{a.error_message}</p>
                    ) : null}
                  </div>
                  {a.status === "pending" ? (
                    <div className="flex gap-2">
                      <button
                        className="btn btn-primary btn-sm"
                        type="button"
                        disabled={busy}
                        onClick={() => void approve(a.id)}
                      >
                        Approve
                      </button>
                      <button
                        className="btn btn-ghost btn-sm"
                        type="button"
                        disabled={busy}
                        onClick={() => void reject(a.id)}
                      >
                        Reject
                      </button>
                    </div>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

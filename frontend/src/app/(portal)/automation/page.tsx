"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { Alert, PageHeader } from "@/components/ui";
import type { AgentAction, AutomationSettings } from "@/lib/types";

const KIND_LABEL: Record<string, { bn: string; en: string; tipBn: string; tipEn: string }> = {
  low_stock_alert: {
    bn: "স্টক কম",
    en: "Low stock",
    tipBn: "শুধু জানায় — কেনা হয় না",
    tipEn: "Notice only — does not buy",
  },
  expiring_alert: {
    bn: "মেয়াদ শেষ হতে যাচ্ছে",
    en: "Expiring soon",
    tipBn: "শুধু জানায়",
    tipEn: "Notice only",
  },
  reorder_draft: {
    bn: "কেনার তালিকা",
    en: "Buy list",
    tipBn: "তালিকা সেভ — কেনা ম্যানুয়াল",
    tipEn: "Saves list — buy manually",
  },
  due_reminders: {
    bn: "বাকি SMS",
    en: "Due SMS",
    tipBn: "কাস্টমারকে SMS যাবে",
    tipEn: "Sends SMS to customers",
  },
  daily_summary_sms: {
    bn: "দৈনিক সেল SMS",
    en: "Daily sales SMS",
    tipBn: "মালিককে SMS যাবে",
    tipEn: "Sends SMS to owner",
  },
};

function labelOf(kind: string, bn: boolean) {
  const row = KIND_LABEL[kind];
  if (!row) return { title: kind, tip: "" };
  return { title: bn ? row.bn : row.en, tip: bn ? row.tipBn : row.tipEn };
}

function statusLabel(status: string, bn: boolean): string {
  const map: Record<string, [string, string]> = {
    pending: ["অপেক্ষমাণ", "Waiting"],
    executed: ["সম্পন্ন", "Done"],
    rejected: ["বাতিল", "Rejected"],
    failed: ["ব্যর্থ", "Failed"],
  };
  const pair = map[status] || [status, status];
  return bn ? pair[0] : pair[1];
}

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
      setError(err instanceof Error ? err.message : bn ? "লোড হয়নি" : "Load failed");
    }
  }, [filter, bn]);

  useEffect(() => {
    void load();
  }, [load]);

  async function toggleAutopilot(on: boolean) {
    setBusy(true);
    setError("");
    try {
      const s = await api.updateAutomationSettings({ autopilot_enabled: on });
      setSettings(s);
      setMsg(on ? (bn ? "অটো মোড চালু" : "Auto mode on") : bn ? "ম্যানুয়াল মোড" : "Manual mode");
    } catch (err) {
      setError(err instanceof Error ? err.message : bn ? "আপডেট হয়নি" : "Update failed");
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
      setError(err instanceof Error ? err.message : bn ? "আপডেট হয়নি" : "Update failed");
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
      const n = res.created?.length ?? 0;
      setMsg(bn ? `চেক শেষ · ${n}টি কাজ` : `Check done · ${n} task(s)`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : bn ? "চেক হয়নি" : "Scan failed");
    } finally {
      setBusy(false);
    }
  }

  async function approve(action: AgentAction) {
    setBusy(true);
    setError("");
    try {
      await api.approveAction(action.id);
      const { tip } = labelOf(action.kind, bn);
      setMsg(tip ? (bn ? `হ্যাঁ · ${tip}` : `Yes · ${tip}`) : bn ? "সম্পন্ন" : "Done");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : bn ? "হয়নি" : "Failed");
    } finally {
      setBusy(false);
    }
  }

  async function reject(id: string) {
    setBusy(true);
    try {
      await api.rejectAction(id);
      setMsg(bn ? "বাতিল" : "Cancelled");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : bn ? "হয়নি" : "Failed");
    } finally {
      setBusy(false);
    }
  }

  const flags: { key: keyof AutomationSettings; bn: string; en: string }[] = [
    { key: "auto_due_reminders", bn: "বাকি SMS", en: "Due SMS" },
    { key: "auto_daily_sms", bn: "দৈনিক সেল SMS", en: "Daily sales SMS" },
    { key: "auto_low_stock_alerts", bn: "স্টক কম নোটিস", en: "Low stock notice" },
    { key: "auto_expiring_alerts", bn: "মেয়াদ নোটিস", en: "Expiry notice" },
    { key: "auto_reorder_draft", bn: "কেনার তালিকা", en: "Buy list" },
  ];

  return (
    <div className="space-y-5">
      <PageHeader
        title={bn ? "দোকান অ্যালার্ট" : "Shop alerts"}
        subtitle={
          bn
            ? "চেক করুন → হ্যাঁ/না দিন। কেনা অটো হয় না।"
            : "Check → Yes/No. Buying is never automatic."
        }
        actions={
          <button className="btn btn-primary" type="button" disabled={busy} onClick={() => void runScan()}>
            {busy ? (bn ? "চেক হচ্ছে…" : "Checking…") : bn ? "দোকান চেক" : "Check shop"}
          </button>
        }
      />

      {error ? <Alert>{error}</Alert> : null}
      {msg ? <Alert tone="ok">{msg}</Alert> : null}

      <section className="panel space-y-4 p-4 md:p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold">{bn ? "মোড" : "Mode"}</h2>
            <p className="mt-1 text-sm text-[var(--muted)]">
              {bn ? "সাধারণত ম্যানুয়াল রাখুন।" : "Usually keep manual."}
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
              {bn ? "ম্যানুয়াল" : "Manual"}
            </button>
            <button
              type="button"
              className="seg-btn"
              data-active={settings?.autopilot_enabled === true}
              disabled={busy || !settings}
              onClick={() => void toggleAutopilot(true)}
            >
              {bn ? "অটো" : "Auto"}
            </button>
          </div>
        </div>

        <div className="grid gap-2 sm:grid-cols-2">
          {flags.map((f) => (
            <label
              key={String(f.key)}
              className="flex items-center gap-3 rounded-[12px] border border-[var(--line)] bg-[var(--surface-2)] px-3 py-2.5 text-sm"
            >
              <input
                type="checkbox"
                checked={Boolean(settings?.[f.key])}
                disabled={busy || !settings || !settings.autopilot_enabled}
                onChange={(e) => void patchFlag(f.key, e.target.checked)}
              />
              <span className="font-medium">{bn ? f.bn : f.en}</span>
            </label>
          ))}
        </div>
      </section>

      <section className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold">{bn ? "কাজ" : "Tasks"}</h2>
          <div className="seg">
            <button
              type="button"
              className="seg-btn"
              data-active={filter === "pending"}
              onClick={() => setFilter("pending")}
            >
              {bn ? "অপেক্ষমাণ" : "Waiting"}
            </button>
            <button
              type="button"
              className="seg-btn"
              data-active={filter === "all"}
              onClick={() => setFilter("all")}
            >
              {bn ? "সব" : "All"}
            </button>
          </div>
        </div>

        {!actions.length ? (
          <div className="panel px-4 py-8 text-center text-sm text-[var(--muted)]">
            {bn ? "কোনো কাজ নেই — উপরে চেক করুন" : "No tasks — check shop above"}
          </div>
        ) : (
          <ul className="space-y-3">
            {actions.map((a) => {
              const { title, tip } = labelOf(a.kind, bn);
              return (
                <li key={a.id} className="panel p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="font-semibold">{title}</h3>
                        <span className="badge badge-muted">{statusLabel(a.status, bn)}</span>
                      </div>
                      <p className="mt-1 text-sm text-[var(--muted)]">{a.summary}</p>
                      {a.status === "pending" && tip ? (
                        <p className="mt-1 text-xs text-[var(--muted)]">{tip}</p>
                      ) : null}
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
                          onClick={() => void approve(a)}
                        >
                          {bn ? "হ্যাঁ" : "Yes"}
                        </button>
                        <button
                          className="btn btn-ghost btn-sm"
                          type="button"
                          disabled={busy}
                          onClick={() => void reject(a.id)}
                        >
                          {bn ? "না" : "No"}
                        </button>
                      </div>
                    ) : null}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}

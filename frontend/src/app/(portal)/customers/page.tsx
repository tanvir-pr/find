"use client";

import { useEffect, useState } from "react";
import { api, money } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { Alert, EmptyState, PageHeader } from "@/components/ui";
import type { Customer, CustomerHistoryItem } from "@/lib/types";

export default function CustomersPage() {
  const { t, lang } = useI18n();
  const bn = lang === "bn";
  const [area, setArea] = useState("");
  const [items, setItems] = useState<Customer[]>([]);
  const [selected, setSelected] = useState<Customer | null>(null);
  const [history, setHistory] = useState<CustomerHistoryItem[]>([]);
  const [collectAmt, setCollectAmt] = useState("500");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState<string | null>(null);
  const [msg, setMsg] = useState("");

  async function load(filter = area) {
    setError("");
    try {
      setItems(await api.customers(filter || undefined));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.failed"));
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function openHistory(customer: Customer) {
    setSelected(customer);
    try {
      setHistory(await api.customerHistory(customer.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "History failed");
    }
  }

  async function toggleOffer(customer: Customer) {
    setSaving(customer.id);
    try {
      const updated = await api.updateCustomer(customer.id, {
        offer_opt_in: !customer.offer_opt_in,
      });
      setItems((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("customers.updateFailed"));
    } finally {
      setSaving(null);
    }
  }

  async function collect() {
    if (!selected) return;
    try {
      const updated = await api.collectDue(selected.id, {
        amount: collectAmt,
        method: "bkash",
        txn_id: `COL-${Date.now()}`,
      });
      setMsg(bn ? "কালেকশন সেভ" : "Collection saved");
      setItems((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
      setSelected(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Collect failed");
    }
  }

  return (
    <div className="space-y-4">
      <PageHeader title={t("customers.title")} subtitle={t("customers.subtitle")} />

      <form
        className="panel toolbar p-4"
        onSubmit={(e) => {
          e.preventDefault();
          void load();
        }}
      >
        <label className="field-label min-w-[200px] flex-1">
          {bn ? "এলাকা" : "Area"}
          <input
            className="field mt-2"
            value={area}
            onChange={(e) => setArea(e.target.value)}
            placeholder={t("customers.areaPlaceholder")}
          />
        </label>
        <button className="btn btn-primary" type="submit">
          {t("customers.filter")}
        </button>
        <button
          className="btn btn-ghost"
          type="button"
          onClick={() => {
            setArea("");
            void load("");
          }}
        >
          {t("customers.clear")}
        </button>
        <button
          className="btn btn-ghost"
          type="button"
          onClick={() =>
            void api
              .dueReminders()
              .then((r) =>
                setMsg(`${bn ? "রিমাইন্ডার" : "Reminders"}: ${JSON.stringify(r).slice(0, 120)}`),
              )
              .catch((e) => setError(e.message))
          }
        >
          {bn ? "বাকি SMS" : "Due SMS"}
        </button>
      </form>

      {error ? <Alert>{error}</Alert> : null}
      {msg ? <Alert tone="ok">{msg}</Alert> : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="panel overflow-hidden">
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>{t("dash.name")}</th>
                  <th>{bn ? "পয়েন্ট" : "Points"}</th>
                  <th>{t("customers.due")}</th>
                  <th>{t("customers.offers")}</th>
                </tr>
              </thead>
              <tbody>
                {items.map((c) => (
                  <tr
                    key={c.id}
                    className={`cursor-pointer ${selected?.id === c.id ? "bg-[var(--surface-2)]" : ""}`}
                    onClick={() => void openHistory(c)}
                  >
                    <td>
                      <span className="font-medium">{c.name}</span>
                      <div className="text-xs text-[var(--muted)]">
                        {c.phone} · {c.email}
                        {c.area ? ` · ${c.area}` : ""}
                      </div>
                    </td>
                    <td className="tabular-nums font-semibold">{c.loyalty_points ?? 0}</td>
                    <td
                      className={`tabular-nums font-semibold ${
                        Number(c.current_due) > 0 ? "text-[var(--danger)]" : ""
                      }`}
                    >
                      {money(c.current_due)}
                    </td>
                    <td>
                      <button
                        className="btn btn-ghost btn-sm"
                        type="button"
                        disabled={saving === c.id}
                        onClick={(e) => {
                          e.stopPropagation();
                          void toggleOffer(c);
                        }}
                      >
                        {c.offer_opt_in ? t("customers.optedIn") : t("customers.optIn")}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <section className="panel p-5">
          <h2 className="text-lg font-bold">{bn ? "হিস্ট্রি / কালেকশন" : "History / collection"}</h2>
          {!selected ? (
            <div className="mt-4">
              <EmptyState
                title={bn ? "একজন কাস্টমার বেছে নিন" : "Select a customer"}
                detail={bn ? "বাম তালিকা থেকে ক্লিক করুন" : "Click a row on the left"}
              />
            </div>
          ) : (
            <div className="mt-4 space-y-4 text-sm">
              <div className="border border-[var(--line)] bg-[var(--surface-2)] p-3">
                <p className="font-medium">{selected.name}</p>
                <p className="mt-1 text-[var(--muted)]">
                  limit {money(selected.credit_limit)} · due{" "}
                  <strong className="text-[var(--danger)]">{money(selected.current_due)}</strong>
                </p>
              </div>
              <ul className="max-h-48 space-y-1 overflow-auto">
                {history.map((h) => (
                  <li key={h.sale_id} className="list-row py-2">
                    <span>{h.bill_no}</span>
                    <span className="tabular-nums font-semibold">{money(h.total)}</span>
                  </li>
                ))}
                {!history.length ? (
                  <li className="text-[var(--muted)]">{bn ? "কোনো বিল নেই" : "No bills"}</li>
                ) : null}
              </ul>
              <div className="flex gap-2">
                <input
                  className="field"
                  value={collectAmt}
                  onChange={(e) => setCollectAmt(e.target.value)}
                />
                <button className="btn btn-primary shrink-0" type="button" onClick={() => void collect()}>
                  {bn ? "কালেক্ট" : "Collect"}
                </button>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

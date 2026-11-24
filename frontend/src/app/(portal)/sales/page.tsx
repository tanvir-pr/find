"use client";

import { useEffect, useState } from "react";
import { api, money } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { Alert, EmptyState, PageHeader } from "@/components/ui";
import type { Sale } from "@/lib/types";

export default function SalesPage() {
  const { t, lang } = useI18n();
  const bn = lang === "bn";
  const [sales, setSales] = useState<Sale[]>([]);
  const [billNo, setBillNo] = useState("");
  const [selected, setSelected] = useState<Sale | null>(null);
  const [receipt, setReceipt] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .sales(40)
      .then(setSales)
      .catch((err) => setError(err.message || t("common.failed")));
  }, [t]);

  async function lookup() {
    setError("");
    setReceipt(null);
    try {
      const sale = await api.saleByBill(billNo.trim());
      setSelected(sale);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("sales.notFound"));
    }
  }

  async function reprint() {
    if (!selected) return;
    try {
      const data = await api.reprintReceipt(selected.bill_no);
      setReceipt(data.payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("sales.receiptFailed"));
    }
  }

  function printReceipt() {
    window.print();
  }

  return (
    <div className="space-y-4">
      <div className="no-print space-y-4">
        <PageHeader title={t("sales.title")} subtitle={t("sales.subtitle")} />

        <form
          className="panel toolbar p-4"
          onSubmit={(e) => {
            e.preventDefault();
            void lookup();
          }}
        >
          <label className="field-label min-w-[220px] flex-1">
            Bill
            <input
              className="field mt-2"
              value={billNo}
              onChange={(e) => setBillNo(e.target.value)}
              placeholder={t("sales.billPlaceholder")}
            />
          </label>
          <button className="btn btn-primary" type="submit">
            {t("sales.lookup")}
          </button>
        </form>

        {error ? <Alert>{error}</Alert> : null}

        <div className="grid gap-4 lg:grid-cols-2">
          <section className="panel overflow-hidden">
            <div className="border-b border-[var(--line)] px-5 py-4">
              <h2 className="text-lg font-bold">{t("sales.recent")}</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="table">
                <thead>
                  <tr>
                    <th>{t("sales.bill")}</th>
                    <th>{t("dash.total")}</th>
                    <th>{t("sales.when")}</th>
                  </tr>
                </thead>
                <tbody>
                  {sales.map((s) => (
                    <tr
                      key={s.id}
                      className={`cursor-pointer ${selected?.id === s.id ? "bg-[var(--surface-2)]" : ""}`}
                      onClick={() => {
                        setSelected(s);
                        setBillNo(s.bill_no);
                        setReceipt(null);
                      }}
                    >
                      <td className="font-medium">{s.bill_no}</td>
                      <td className="tabular-nums font-semibold">{money(s.total)}</td>
                      <td className="text-[var(--muted)]">{new Date(s.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="panel p-5">
            <h2 className="text-lg font-bold">{t("sales.receipt")}</h2>
            {!selected ? (
              <div className="mt-4">
                <EmptyState title={t("sales.selectBill")} />
              </div>
            ) : (
              <div className="mt-4 space-y-4 text-sm">
                <div className="border border-[var(--line)] bg-[var(--surface-2)] px-3 py-2.5">
                  <p className="font-medium">{selected.bill_no}</p>
                  <p className="stat-value mt-1 text-xl">{money(selected.total)}</p>
                </div>
                <ul className="space-y-1">
                  {selected.items.map((item) => (
                    <li key={item.id} className="list-row py-2">
                      <span>
                        {item.qty} × {money(item.unit_price)}
                      </span>
                      <span className="tabular-nums font-semibold">
                        {money(Number(item.qty) * Number(item.unit_price) - Number(item.discount))}
                      </span>
                    </li>
                  ))}
                </ul>
                <ul className="space-y-1 text-sm text-[var(--muted)]">
                  <li className="flex justify-between">
                    <span>{bn ? "সাবটোটাল" : "Subtotal"}</span>
                    <span className="tabular-nums">{money(selected.subtotal)}</span>
                  </li>
                  {Number(selected.discount) > 0 ? (
                    <li className="flex justify-between">
                      <span>{bn ? "বিল ডিসকাউন্ট" : "Bill discount"}</span>
                      <span className="tabular-nums">−{money(selected.discount)}</span>
                    </li>
                  ) : null}
                  {Number(selected.points_discount || 0) > 0 ? (
                    <li className="flex justify-between font-medium text-[var(--ink)]">
                      <span>
                        {bn ? "পয়েন্ট ছাড়" : "Points discount"}
                        {selected.points_redeemed
                          ? ` (${selected.points_redeemed} pts)`
                          : ""}
                      </span>
                      <span className="tabular-nums">−{money(selected.points_discount || "0")}</span>
                    </li>
                  ) : null}
                  <li className="flex justify-between font-semibold text-[var(--ink)]">
                    <span>{bn ? "পরিশোধযোগ্য" : "Payable"}</span>
                    <span className="tabular-nums">{money(selected.total)}</span>
                  </li>
                </ul>
                <ul className="space-y-1 text-[var(--muted)]">
                  {selected.payments.map((p) => (
                    <li key={p.id}>
                      {p.method}: {money(p.amount)} {p.txn_id ? `(${p.txn_id})` : ""}
                    </li>
                  ))}
                </ul>
                <div className="flex flex-wrap gap-2">
                  <button className="btn btn-primary" type="button" onClick={() => void reprint()}>
                    {t("sales.logCopy")}
                  </button>
                  <button className="btn btn-ghost" type="button" onClick={printReceipt}>
                    {t("sales.print")}
                  </button>
                </div>
                <p className="text-xs text-[var(--muted)]">
                  {bn
                    ? "প্রিন্টার থাকলে প্রিন্ট ডায়ালগ খুলবে; না থাকলে বাতিল করুন — সেল ঠিক থাকবে।"
                    : "If a printer is connected, the print dialog opens; otherwise cancel — the sale stays saved."}
                </p>
                {receipt ? (
                  <pre className="overflow-auto rounded-[10px] border border-[var(--line)] bg-[var(--surface-2)] p-3 text-xs">
                    {JSON.stringify(receipt, null, 2)}
                  </pre>
                ) : null}
              </div>
            )}
          </section>
        </div>
      </div>

      {selected ? (
        <section className="print-receipt panel p-5" aria-label="Printable invoice">
          <p className="text-lg font-bold">Dokan POS</p>
          <p>
            <strong>{selected.bill_no}</strong>
          </p>
          <p className="text-sm text-[var(--muted)]">{new Date(selected.created_at).toLocaleString()}</p>
          <ul className="mt-3 divide-y divide-[var(--line)] border-y border-[var(--line)] py-2 text-sm">
            {selected.items.map((item) => (
              <li key={item.id} className="flex justify-between gap-3 py-1.5">
                <span>
                  {item.qty} × {money(item.unit_price)}
                </span>
                <span className="tabular-nums">
                  {money(Number(item.qty) * Number(item.unit_price) - Number(item.discount))}
                </span>
              </li>
            ))}
          </ul>
          <div className="mt-2 space-y-1 text-sm">
            <div className="flex justify-between">
              <span>{bn ? "সাবটোটাল" : "Subtotal"}</span>
              <span className="tabular-nums">{money(selected.subtotal)}</span>
            </div>
            {Number(selected.discount) > 0 ? (
              <div className="flex justify-between">
                <span>{bn ? "বিল ডিসকাউন্ট" : "Bill discount"}</span>
                <span className="tabular-nums">−{money(selected.discount)}</span>
              </div>
            ) : null}
            {Number(selected.points_discount || 0) > 0 ? (
              <div className="flex justify-between">
                <span>
                  {bn ? "পয়েন্ট ছাড়" : "Points discount"}
                  {selected.points_redeemed ? ` (${selected.points_redeemed} pts)` : ""}
                </span>
                <span className="tabular-nums">−{money(selected.points_discount || "0")}</span>
              </div>
            ) : null}
            <div className="flex justify-between font-semibold">
              <span>{bn ? "পরিশোধযোগ্য" : "Payable"}</span>
              <span className="tabular-nums">{money(selected.total)}</span>
            </div>
          </div>
        </section>
      ) : null}
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { api, money } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { Sale } from "@/lib/types";

export default function SalesPage() {
  const { t } = useI18n();
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
    <div className="fade-up space-y-5">
      <header>
        <h1 className="text-3xl">{t("sales.title")}</h1>
        <p className="mt-1 text-sm opacity-70">{t("sales.subtitle")}</p>
      </header>

      <form
        className="panel flex flex-col gap-3 p-4 sm:flex-row"
        onSubmit={(e) => {
          e.preventDefault();
          void lookup();
        }}
      >
        <input
          className="field"
          value={billNo}
          onChange={(e) => setBillNo(e.target.value)}
          placeholder={t("sales.billPlaceholder")}
        />
        <button className="btn btn-primary" type="submit">
          {t("sales.lookup")}
        </button>
      </form>

      {error ? <p className="text-[var(--coral)]">{error}</p> : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="panel overflow-x-auto p-3">
          <h2 className="px-2 pt-2 text-xl">{t("sales.recent")}</h2>
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
                  className="cursor-pointer hover:bg-white/60"
                  onClick={() => {
                    setSelected(s);
                    setBillNo(s.bill_no);
                    setReceipt(null);
                  }}
                >
                  <td>{s.bill_no}</td>
                  <td>{money(s.total)}</td>
                  <td>{new Date(s.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className="panel p-4" id="receipt-panel">
          <h2 className="text-xl">{t("sales.receipt")}</h2>
          {!selected ? (
            <p className="mt-3 text-sm opacity-60">{t("sales.selectBill")}</p>
          ) : (
            <div className="mt-3 space-y-3 text-sm">
              <p>
                <strong>{selected.bill_no}</strong> · {money(selected.total)}
              </p>
              <ul className="space-y-1">
                {selected.items.map((item) => (
                  <li key={item.id} className="flex justify-between gap-2 border-b border-[var(--line)] py-1">
                    <span>
                      {item.qty} × {money(item.unit_price)}
                    </span>
                    <span>{money(Number(item.qty) * Number(item.unit_price) - Number(item.discount))}</span>
                  </li>
                ))}
              </ul>
              <ul className="space-y-1">
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
              {receipt ? (
                <pre className="overflow-auto rounded-xl bg-white/80 p-3 text-xs">
                  {JSON.stringify(receipt, null, 2)}
                </pre>
              ) : null}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { api, money, monthStartISO, todayISO } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { ExpiringItem, LowStockItem, SalesSummary } from "@/lib/types";

export default function DashboardPage() {
  const { t } = useI18n();
  const [summary, setSummary] = useState<SalesSummary | null>(null);
  const [month, setMonth] = useState<SalesSummary | null>(null);
  const [low, setLow] = useState<LowStockItem[]>([]);
  const [expiring, setExpiring] = useState<ExpiringItem[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    const today = todayISO();
    const start = monthStartISO();
    Promise.all([
      api.salesSummary(today, today),
      api.salesSummary(start, today),
      api.lowStock(),
      api.expiring(30),
    ])
      .then(([s, m, l, e]) => {
        setSummary(s);
        setMonth(m);
        setLow(l);
        setExpiring(e);
      })
      .catch((err) => setError(err.message || t("dash.loadFailed")));
  }, [t]);

  return (
    <div className="fade-up space-y-6">
      <header>
        <h1 className="text-3xl md:text-4xl">{t("dash.title")}</h1>
        <p className="mt-1 text-sm opacity-70">{t("dash.subtitle")}</p>
      </header>

      {error ? <p className="text-[var(--coral)]">{error}</p> : null}

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          { label: t("dash.todaySales"), value: money(summary?.total_sales) },
          { label: t("dash.todayProfit"), value: money(summary?.estimated_profit) },
          { label: t("dash.billsToday"), value: String(summary?.bill_count ?? "—") },
          { label: t("dash.monthSales"), value: money(month?.total_sales) },
        ].map((card) => (
          <article key={card.label} className="panel p-5">
            <p className="text-xs uppercase tracking-wide opacity-60">{card.label}</p>
            <p className="brand mt-2 text-3xl">{card.value}</p>
          </article>
        ))}
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <article className="panel p-5">
          <h2 className="text-xl">{t("dash.paymentMix")}</h2>
          <ul className="mt-4 space-y-2 text-sm">
            {[
              [t("pay.cash"), summary?.cash],
              [t("pay.bkash"), summary?.bkash],
              [t("pay.nagad"), summary?.nagad],
              [t("pay.credit"), summary?.credit],
            ].map(([label, value]) => (
              <li key={String(label)} className="flex justify-between border-b border-[var(--line)] py-2">
                <span>{label}</span>
                <strong>{money(value as string)}</strong>
              </li>
            ))}
          </ul>
        </article>

        <article className="panel p-5">
          <h2 className="text-xl">{t("dash.staffToday")}</h2>
          <div className="mt-3 overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>{t("dash.name")}</th>
                  <th>{t("dash.bills")}</th>
                  <th>{t("dash.total")}</th>
                </tr>
              </thead>
              <tbody>
                {(summary?.by_staff || []).length === 0 ? (
                  <tr>
                    <td colSpan={3} className="opacity-60">
                      {t("dash.noSales")}
                    </td>
                  </tr>
                ) : (
                  summary?.by_staff.map((row) => (
                    <tr key={row.user_id}>
                      <td>{row.name}</td>
                      <td>{row.bill_count}</td>
                      <td>{money(row.total)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </article>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <article className="panel p-5">
          <h2 className="text-xl">
            {t("dash.lowStock")} ({low.length})
          </h2>
          <ul className="mt-3 max-h-64 space-y-2 overflow-auto text-sm">
            {low.slice(0, 12).map((item) => (
              <li key={item.variant_id} className="flex justify-between gap-3 border-b border-[var(--line)] py-2">
                <span>
                  {item.product_name} · {item.variant_name}
                </span>
                <strong>
                  {item.current_stock}/{item.low_stock_threshold}
                </strong>
              </li>
            ))}
            {low.length === 0 ? <li className="opacity-60">{t("dash.allGood")}</li> : null}
          </ul>
        </article>

        <article className="panel p-5">
          <h2 className="text-xl">
            {t("dash.expiring")} ({expiring.length})
          </h2>
          <ul className="mt-3 max-h-64 space-y-2 overflow-auto text-sm">
            {expiring.slice(0, 12).map((item) => (
              <li key={item.batch_id} className="flex justify-between gap-3 border-b border-[var(--line)] py-2">
                <span>
                  {item.product_name} · {item.variant_name}
                </span>
                <strong>
                  {item.expiry_date} · {item.remaining_qty}
                </strong>
              </li>
            ))}
            {expiring.length === 0 ? <li className="opacity-60">{t("dash.noneSoon")}</li> : null}
          </ul>
        </article>
      </section>
    </div>
  );
}

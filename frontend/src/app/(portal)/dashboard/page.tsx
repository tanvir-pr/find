"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, money, monthStartISO, todayISO } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { Alert, PageHeader, StatCard } from "@/components/ui";
import type { ExpiringItem, LowStockItem, SalesSummary } from "@/lib/types";

export default function DashboardPage() {
  const { t, lang } = useI18n();
  const bn = lang === "bn";
  const [summary, setSummary] = useState<SalesSummary | null>(null);
  const [month, setMonth] = useState<SalesSummary | null>(null);
  const [low, setLow] = useState<LowStockItem[]>([]);
  const [expiring, setExpiring] = useState<ExpiringItem[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const today = todayISO();
    const start = monthStartISO();
    setLoading(true);
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
      .catch((err) => setError(err.message || t("dash.loadFailed")))
      .finally(() => setLoading(false));
  }, [t]);

  return (
    <div className="space-y-5">
      <PageHeader
        title={t("dash.title")}
        subtitle={t("dash.subtitle")}
        actions={
          <>
            <Link href="/pos" className="btn btn-primary">
              {bn ? "দ্রুত বিক্রি" : "Quick sale"}
            </Link>
            <Link href="/chat" className="btn btn-ghost">
              {bn ? "AI সহায়ক" : "AI helper"}
            </Link>
          </>
        }
      />

      {error ? <Alert>{error}</Alert> : null}

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {loading
          ? Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="panel h-20 p-4">
                <div className="skeleton h-3 w-16" />
                <div className="skeleton mt-3 h-6 w-24" />
              </div>
            ))
          : [
              { label: t("dash.todaySales"), value: money(summary?.total_sales) },
              {
                label: bn ? "পয়েন্ট ছাড় (আজ)" : "Points discount (today)",
                value: money(summary?.total_points_discount || "0"),
              },
              { label: t("dash.todayProfit"), value: money(summary?.estimated_profit) },
              { label: t("dash.billsToday"), value: String(summary?.bill_count ?? "—") },
              { label: t("dash.monthSales"), value: money(month?.total_sales) },
            ].map((card) => (
              <StatCard key={card.label} label={card.label} value={card.value} />
            ))}
      </section>

      <section className="grid gap-3 lg:grid-cols-2">
        <article className="panel p-4">
          <h2 className="text-sm font-semibold">{t("dash.paymentMix")}</h2>
          <p className="mt-1 text-xs text-[var(--muted)]">
            {bn
              ? "ক্যাশ/বিকাশ/নগদ = আসল টাকা। পয়েন্ট ছাড় আলাদা — ড্রয়ারে ঢোকে না।"
              : "Cash/bKash/Nagad = real money. Points discount is separate — not in the till."}
          </p>
          <ul className="mt-3">
            {[
              [t("pay.cash"), summary?.cash],
              [t("pay.bkash"), summary?.bkash],
              [t("pay.nagad"), summary?.nagad],
              [t("pay.credit"), summary?.credit],
              [bn ? "পয়েন্ট ছাড়" : "Points discount", summary?.total_points_discount || "0"],
              [bn ? "বিল ডিসকাউন্ট" : "Bill discount", summary?.total_discount || "0"],
            ].map(([label, value]) => (
              <li
                key={String(label)}
                className="flex justify-between border-b border-[var(--line)] py-2 text-sm last:border-0"
              >
                <span className="text-[var(--ink-soft)]">{label}</span>
                <span className="tabular-nums font-medium">{money(value as string)}</span>
              </li>
            ))}
          </ul>
        </article>

        <article className="panel overflow-hidden">
          <div className="border-b border-[var(--line)] px-4 py-3">
            <h2 className="text-sm font-semibold">{t("dash.staffToday")}</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>{t("dash.name")}</th>
                  <th>{t("dash.bills")}</th>
                  <th>{t("dash.total")}</th>
                  <th>{bn ? "পয়েন্ট ছাড়" : "Pts ৳"}</th>
                </tr>
              </thead>
              <tbody>
                {(summary?.by_staff || []).length === 0 ? (
                  <tr>
                    <td colSpan={4} className="text-[var(--muted)]">
                      {t("dash.noSales")}
                    </td>
                  </tr>
                ) : (
                  summary?.by_staff.map((row) => (
                    <tr key={row.user_id}>
                      <td>{row.name}</td>
                      <td className="tabular-nums">{row.bill_count}</td>
                      <td className="tabular-nums font-medium">{money(row.total)}</td>
                      <td className="tabular-nums text-[var(--muted)]">
                        {money(row.points_discount || "0")}
                        {row.points_redeemed ? (
                          <span className="ml-1 text-xs">({row.points_redeemed} pts)</span>
                        ) : null}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </article>
      </section>

      <section className="grid gap-3 lg:grid-cols-2">
        <article className="panel p-4">
          <div className="flex items-baseline justify-between gap-2">
            <h2 className="text-sm font-semibold">{t("dash.lowStock")}</h2>
            <span className="text-xs text-[var(--muted)]">{low.length}</span>
          </div>
          <ul className="mt-2 max-h-60 overflow-auto">
            {low.slice(0, 12).map((item) => (
              <li key={item.variant_id} className="list-row text-sm">
                <span>
                  {item.product_name} · {item.variant_name}
                </span>
                <span className="tabular-nums font-medium text-[var(--danger)]">
                  {item.current_stock}/{item.low_stock_threshold}
                </span>
              </li>
            ))}
            {low.length === 0 ? (
              <li className="py-3 text-sm text-[var(--muted)]">{t("dash.allGood")}</li>
            ) : null}
          </ul>
        </article>

        <article className="panel p-4">
          <div className="flex items-baseline justify-between gap-2">
            <h2 className="text-sm font-semibold">{t("dash.expiring")}</h2>
            <span className="text-xs text-[var(--muted)]">{expiring.length}</span>
          </div>
          <ul className="mt-2 max-h-60 overflow-auto">
            {expiring.slice(0, 12).map((item) => (
              <li key={item.batch_id} className="list-row text-sm">
                <span>
                  {item.product_name} · {item.variant_name}
                </span>
                <span className="tabular-nums font-medium text-[var(--warn)]">
                  {item.expiry_date} · {item.remaining_qty}
                </span>
              </li>
            ))}
            {expiring.length === 0 ? (
              <li className="py-3 text-sm text-[var(--muted)]">{t("dash.noneSoon")}</li>
            ) : null}
          </ul>
        </article>
      </section>
    </div>
  );
}

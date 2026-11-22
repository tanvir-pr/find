"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { Product, Variant } from "@/lib/types";

type CountRow = { variant: Variant; productName: string; system: number; counted: string };

export default function StockPage() {
  const { t } = useI18n();
  const [rows, setRows] = useState<CountRow[]>([]);
  const [apply, setApply] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .products()
      .then((data) => {
        const next: CountRow[] = [];
        data.items.forEach((p: Product) => {
          p.variants.forEach((v) => {
            next.push({
              variant: v,
              productName: p.name,
              system: Number(v.current_stock),
              counted: String(v.current_stock),
            });
          });
        });
        setRows(next.slice(0, 40));
      })
      .catch((err) => setError(err.message || t("common.failed")));
  }, [t]);

  async function submit() {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const result = await api.createStockCount({
        apply_adjustments: apply,
        note: "Portal stock count",
        lines: rows.map((r) => ({
          variant_id: r.variant.id,
          counted_qty: r.counted,
        })),
      });
      setMessage(
        t("stock.saved", {
          adj: apply ? t("stock.withAdj") : "",
          n: (result as { lines?: unknown[] }).lines?.length ?? rows.length,
        }),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : t("stock.failed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fade-up space-y-5">
      <header>
        <h1 className="text-3xl">{t("stock.title")}</h1>
        <p className="mt-1 text-sm opacity-70">{t("stock.subtitle")}</p>
      </header>

      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={apply} onChange={(e) => setApply(e.target.checked)} />
        {t("stock.apply")}
      </label>

      <div className="panel overflow-x-auto p-2">
        <table className="table">
          <thead>
            <tr>
              <th>{t("products.product")}</th>
              <th>{t("stock.system")}</th>
              <th>{t("stock.counted")}</th>
              <th>{t("stock.diff")}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const counted = Number(r.counted || 0);
              const diff = counted - r.system;
              return (
                <tr key={r.variant.id}>
                  <td>
                    {r.productName} · {r.variant.name}
                  </td>
                  <td>{r.system}</td>
                  <td>
                    <input
                      className="field max-w-28"
                      value={r.counted}
                      onChange={(e) =>
                        setRows((prev) =>
                          prev.map((x) =>
                            x.variant.id === r.variant.id
                              ? { ...x, counted: e.target.value }
                              : x,
                          ),
                        )
                      }
                    />
                  </td>
                  <td className={diff !== 0 ? "text-[var(--coral)]" : ""}>{diff}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <button className="btn btn-primary" disabled={busy || !rows.length} onClick={() => void submit()}>
        {busy ? t("stock.saving") : t("stock.save")}
      </button>
      {message ? <p className="text-[var(--teal)]">{message}</p> : null}
      {error ? <p className="text-[var(--coral)]">{error}</p> : null}
    </div>
  );
}

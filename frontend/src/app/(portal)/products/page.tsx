"use client";

import { useEffect, useState } from "react";
import { api, money } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { Product } from "@/lib/types";

export default function ProductsPage() {
  const { t } = useI18n();
  const [q, setQ] = useState("");
  const [onlyLow, setOnlyLow] = useState(false);
  const [items, setItems] = useState<Product[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function load(search = q, low = onlyLow) {
    setLoading(true);
    setError("");
    try {
      const data = await api.products(search || undefined, low || undefined);
      setItems(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.failed"));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="fade-up space-y-5">
      <header>
        <h1 className="text-3xl">{t("products.title")}</h1>
        <p className="mt-1 text-sm opacity-70">{t("products.subtitle")}</p>
      </header>

      <form
        className="panel flex flex-col gap-3 p-4 sm:flex-row sm:items-end"
        onSubmit={(e) => {
          e.preventDefault();
          void load();
        }}
      >
        <label className="flex-1 text-sm font-medium">
          {t("products.nameBarcode")}
          <input
            className="field mt-2"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={t("products.placeholder")}
          />
        </label>
        <label className="flex items-center gap-2 pb-2 text-sm">
          <input type="checkbox" checked={onlyLow} onChange={(e) => setOnlyLow(e.target.checked)} />
          {t("products.lowOnly")}
        </label>
        <button className="btn btn-primary" type="submit" disabled={loading}>
          {loading ? t("products.searching") : t("products.search")}
        </button>
      </form>

      {error ? <p className="text-[var(--coral)]">{error}</p> : null}
      <p className="text-sm opacity-70">{t("products.count", { n: total })}</p>

      <div className="panel overflow-x-auto p-2">
        <table className="table">
          <thead>
            <tr>
              <th>{t("products.product")}</th>
              <th>{t("products.variant")}</th>
              <th>{t("products.barcode")}</th>
              <th>{t("products.stock")}</th>
              <th>{t("products.retail")}</th>
              <th>{t("products.dealer")}</th>
            </tr>
          </thead>
          <tbody>
            {items.flatMap((p) =>
              p.variants.map((v) => (
                <tr key={v.id}>
                  <td>
                    {p.name}
                    <div className="text-xs opacity-60">{p.category}</div>
                  </td>
                  <td>{v.name}</td>
                  <td>{v.barcode || "—"}</td>
                  <td>
                    <strong
                      className={
                        Number(v.current_stock) <= Number(v.low_stock_threshold)
                          ? "text-[var(--coral)]"
                          : ""
                      }
                    >
                      {v.current_stock}
                    </strong>
                  </td>
                  <td>{money(v.retail_price)}</td>
                  <td>{money(v.dealer_price)}</td>
                </tr>
              )),
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

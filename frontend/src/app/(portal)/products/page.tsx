"use client";

import { useEffect, useState } from "react";
import { api, money } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { Alert, PageHeader } from "@/components/ui";
import type { Product } from "@/lib/types";

export default function ProductsPage() {
  const { t, lang } = useI18n();
  const bn = lang === "bn";
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [categories, setCategories] = useState<string[]>([]);
  const [onlyLow, setOnlyLow] = useState(false);
  const [items, setItems] = useState<Product[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function load(search = q, low = onlyLow, cat = category) {
    setLoading(true);
    setError("");
    try {
      const data = await api.products(search || undefined, low || undefined, cat || undefined, 200);
      setItems(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.failed"));
    } finally {
      setLoading(false);
    }
  }

  function pickCategory(cat: string) {
    setCategory(cat);
    void load(q, onlyLow, cat);
  }

  useEffect(() => {
    void load();
    void api.productCategories().then((r) => setCategories(r.categories)).catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="space-y-4">
      <PageHeader title={t("products.title")} subtitle={t("products.subtitle")} />

      <div className="panel space-y-3 p-4">
        <div className="flex flex-wrap gap-1.5">
          <button
            type="button"
            className="seg-btn"
            data-active={!category}
            onClick={() => pickCategory("")}
          >
            {bn ? "সব" : "All"}
          </button>
          {categories.map((c) => (
            <button
              key={c}
              type="button"
              className="seg-btn"
              data-active={category === c}
              onClick={() => pickCategory(c)}
            >
              {c}
            </button>
          ))}
        </div>

        <form
          className="toolbar"
          onSubmit={(e) => {
            e.preventDefault();
            void load();
          }}
        >
          <label className="field-label min-w-[220px] flex-1">
            {t("products.nameBarcode")}
            <input
              className="field mt-1.5"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder={t("products.placeholder")}
            />
          </label>
          <label className="flex items-center gap-2 pb-0.5 text-sm">
            <input
              type="checkbox"
              checked={onlyLow}
              onChange={(e) => {
                setOnlyLow(e.target.checked);
                void load(q, e.target.checked, category);
              }}
            />
            {t("products.lowOnly")}
          </label>
          <button className="btn btn-primary" type="submit" disabled={loading}>
            {loading ? t("products.searching") : t("products.search")}
          </button>
        </form>
      </div>

      {error ? <Alert>{error}</Alert> : null}
      <p className="text-sm text-[var(--muted)]">
        {t("products.count", { n: total })}
        {category ? ` · ${category}` : ""}
      </p>

      <div className="panel overflow-hidden">
        <div className="overflow-x-auto">
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
                p.variants.map((v) => {
                  const low = Number(v.current_stock) <= Number(v.low_stock_threshold);
                  return (
                    <tr key={v.id}>
                      <td>
                        <span className="font-medium">{p.name}</span>
                        <div className="text-xs text-[var(--muted)]">{p.category}</div>
                      </td>
                      <td>{v.name}</td>
                      <td className="font-mono text-xs">{v.barcode || "—"}</td>
                      <td>
                        <strong className={`tabular-nums ${low ? "text-[var(--danger)]" : ""}`}>
                          {v.current_stock}
                        </strong>
                      </td>
                      <td className="tabular-nums">{money(v.retail_price)}</td>
                      <td className="tabular-nums">{money(v.dealer_price)}</td>
                    </tr>
                  );
                }),
              )}
              {!loading && items.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-sm text-[var(--muted)]">
                    {bn ? "এই ক্যাটাগরিতে পণ্য নেই" : "No products in this category"}
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

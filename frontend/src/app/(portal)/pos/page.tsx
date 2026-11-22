"use client";

import { useEffect, useMemo, useState } from "react";
import { api, money } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { Product, Variant } from "@/lib/types";

type CartLine = { variant: Variant; productName: string; qty: number };

export default function PosPage() {
  const { t } = useI18n();
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<Product[]>([]);
  const [cart, setCart] = useState<CartLine[]>([]);
  const [method, setMethod] = useState<"cash" | "bkash" | "nagad">("cash");
  const [txnId, setTxnId] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const total = useMemo(
    () => cart.reduce((sum, line) => sum + Number(line.variant.retail_price) * line.qty, 0),
    [cart],
  );

  async function search(term = q) {
    setError("");
    try {
      const data = await api.products(term.trim() || undefined);
      setHits(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("pos.searchFailed"));
    }
  }

  useEffect(() => {
    void search("");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function addVariant(productName: string, variant: Variant) {
    setCart((prev) => {
      const existing = prev.find((l) => l.variant.id === variant.id);
      if (existing) {
        return prev.map((l) =>
          l.variant.id === variant.id ? { ...l, qty: l.qty + 1 } : l,
        );
      }
      return [...prev, { variant, productName, qty: 1 }];
    });
  }

  function changeQty(id: string, delta: number) {
    setCart((prev) =>
      prev
        .map((l) => (l.variant.id === id ? { ...l, qty: Math.max(0, l.qty + delta) } : l))
        .filter((l) => l.qty > 0),
    );
  }

  async function checkout() {
    if (!cart.length) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const payments =
        method === "cash"
          ? [{ method: "cash", amount: String(total.toFixed(2)) }]
          : [
              {
                method,
                amount: String(total.toFixed(2)),
                txn_id: txnId || `PORTAL-${Date.now()}`,
              },
            ];
      const sale = await api.createSale({
        items: cart.map((l) => ({ variant_id: l.variant.id, qty: String(l.qty) })),
        payments,
      });
      setMessage(
        t("pos.saleSaved", { bill: sale.bill_no, total: money(sale.total) }),
      );
      setCart([]);
      setTxnId("");
    } catch (err) {
      setError(err instanceof Error ? err.message : t("pos.saleFailed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fade-up space-y-5">
      <header>
        <h1 className="text-3xl">{t("pos.title")}</h1>
        <p className="mt-1 text-sm opacity-70">{t("pos.subtitle")}</p>
      </header>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="panel space-y-3 p-4">
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              void search();
            }}
          >
            <input
              className="field"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder={t("pos.searchPlaceholder")}
            />
            <button className="btn btn-primary" type="submit">
              {t("pos.find")}
            </button>
          </form>
          <ul className="max-h-80 space-y-2 overflow-auto">
            {hits.flatMap((p) =>
              p.variants.map((v) => (
                <li
                  key={v.id}
                  className="flex items-center justify-between gap-3 rounded-xl border border-[var(--line)] bg-white/70 px-3 py-2 text-sm"
                >
                  <div>
                    <strong>
                      {p.name} · {v.name}
                    </strong>
                    <div className="opacity-60">
                      {v.barcode || t("pos.noBarcode")} · {t("pos.stock")} {v.current_stock} ·{" "}
                      {money(v.retail_price)}
                    </div>
                  </div>
                  <button className="btn btn-ghost text-sm" type="button" onClick={() => addVariant(p.name, v)}>
                    {t("pos.add")}
                  </button>
                </li>
              )),
            )}
          </ul>
        </section>

        <section className="panel space-y-3 p-4">
          <h2 className="text-xl">{t("pos.cart")}</h2>
          {cart.length === 0 ? <p className="text-sm opacity-60">{t("pos.empty")}</p> : null}
          <ul className="space-y-2">
            {cart.map((line) => (
              <li key={line.variant.id} className="flex items-center justify-between gap-2 text-sm">
                <span>
                  {line.productName} · {line.variant.name}
                </span>
                <div className="flex items-center gap-2">
                  <button className="btn btn-ghost px-3 py-1" type="button" onClick={() => changeQty(line.variant.id, -1)}>
                    −
                  </button>
                  <strong>{line.qty}</strong>
                  <button className="btn btn-ghost px-3 py-1" type="button" onClick={() => changeQty(line.variant.id, 1)}>
                    +
                  </button>
                </div>
              </li>
            ))}
          </ul>

          <div className="border-t border-[var(--line)] pt-3">
            <p className="brand text-2xl">{money(total)}</p>
            <label className="mt-3 block text-sm">
              {t("pos.payment")}
              <select
                className="field mt-2"
                value={method}
                onChange={(e) => setMethod(e.target.value as typeof method)}
              >
                <option value="cash">{t("pay.cash")}</option>
                <option value="bkash">{t("pay.bkash")}</option>
                <option value="nagad">{t("pay.nagad")}</option>
              </select>
            </label>
            {method !== "cash" ? (
              <label className="mt-3 block text-sm">
                {t("pos.txnId")}
                <input className="field mt-2" value={txnId} onChange={(e) => setTxnId(e.target.value)} />
              </label>
            ) : null}
            <button className="btn btn-primary mt-4 w-full" disabled={busy || !cart.length} onClick={() => void checkout()}>
              {busy ? t("pos.saving") : t("pos.complete")}
            </button>
          </div>
          {message ? <p className="text-sm text-[var(--teal)]">{message}</p> : null}
          {error ? <p className="text-sm text-[var(--coral)]">{error}</p> : null}
        </section>
      </div>
    </div>
  );
}

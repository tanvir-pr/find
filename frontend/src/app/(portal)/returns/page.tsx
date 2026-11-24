"use client";

import { useState } from "react";
import { api, money } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { Sale } from "@/lib/types";

export default function ReturnsPage() {
  const { lang } = useI18n();
  const bn = lang === "bn";
  const [billNo, setBillNo] = useState("");
  const [sale, setSale] = useState<Sale | null>(null);
  const [itemId, setItemId] = useState("");
  const [qty, setQty] = useState("1");
  const [damaged, setDamaged] = useState(false);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");

  async function lookup() {
    setError("");
    setMsg("");
    try {
      const s = await api.saleByBill(billNo.trim());
      setSale(s);
      setItemId(s.items[0]?.id || "");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Not found");
    }
  }

  async function submit() {
    if (!sale || !itemId) return;
    try {
      await api.createReturn({
        bill_no: sale.bill_no,
        sale_item_id: itemId,
        qty,
        is_damaged: damaged,
        reason: damaged ? "damaged" : "customer return",
      });
      setMsg(bn ? "রিটার্ন সেভ হয়েছে" : "Return saved");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Return failed");
    }
  }

  return (
    <div className="space-y-5">
      <header>
        <h1 className="page-title">{bn ? "পণ্য ফেরত" : "Returns"}</h1>
        <p className="page-sub">
          {bn ? "পুরনো বিল থেকে ফেরত নিন।" : "Return items from a past bill."}
        </p>
      </header>
      {error ? <p className="text-[var(--coral)]">{error}</p> : null}
      {msg ? <p className="text-[var(--teal)]">{msg}</p> : null}

      <form
        className="panel flex gap-2 p-4"
        onSubmit={(e) => {
          e.preventDefault();
          void lookup();
        }}
      >
        <input
          className="field"
          value={billNo}
          onChange={(e) => setBillNo(e.target.value)}
          placeholder={bn ? "বিল নম্বর" : "Bill no"}
        />
        <button className="btn btn-primary" type="submit">
          {bn ? "খুঁজুন" : "Lookup"}
        </button>
      </form>

      {sale ? (
        <section className="panel space-y-3 p-5">
          <p>
            <strong>{sale.bill_no}</strong> · {money(sale.total)}
          </p>
          <label className="block text-sm">
            {bn ? "আইটেম" : "Item"}
            <select className="field mt-1" value={itemId} onChange={(e) => setItemId(e.target.value)}>
              {sale.items.map((it) => (
                <option key={it.id} value={it.id}>
                  {it.qty} × {money(it.unit_price)} ({it.id.slice(0, 8)})
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm">
            Qty
            <input className="field mt-1" value={qty} onChange={(e) => setQty(e.target.value)} />
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={damaged} onChange={(e) => setDamaged(e.target.checked)} />
            {bn ? "নষ্ট মাল (স্টকে ফিরবে না)" : "Damaged (do not restock)"}
          </label>
          <button className="btn btn-primary" type="button" onClick={() => void submit()}>
            {bn ? "রিটার্ন সেভ" : "Save return"}
          </button>
        </section>
      ) : null}
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { api, money, todayISO } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { Product, Purchase, Supplier } from "@/lib/types";

export default function PurchasesPage() {
  const { lang } = useI18n();
  const bn = lang === "bn";
  const [purchases, setPurchases] = useState<Purchase[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [supplierId, setSupplierId] = useState("");
  const [invoiceNo, setInvoiceNo] = useState("");
  const [variantId, setVariantId] = useState("");
  const [qty, setQty] = useState("10");
  const [cost, setCost] = useState("40");
  const [expiry, setExpiry] = useState("");
  const [csvText, setCsvText] = useState("SEED-GLUE-20,10,35\nSEED-NOTE-80,20,30");
  const [ocrText, setOcrText] = useState("SEED-PEN-ORIG,50,8");
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");

  async function reload() {
    const [p, s, prod] = await Promise.all([api.purchases(), api.suppliers(), api.products()]);
    setPurchases(p);
    setSuppliers(s);
    setProducts(prod.items);
    if (!supplierId && s[0]) setSupplierId(s[0].id);
    const firstVar = prod.items[0]?.variants[0];
    if (!variantId && firstVar) setVariantId(firstVar.id);
  }

  useEffect(() => {
    void reload().catch((e) => setError(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function createPurchase() {
    setError("");
    setMsg("");
    try {
      await api.createPurchase({
        supplier_id: supplierId,
        invoice_no: invoiceNo || `INV-${Date.now()}`,
        invoice_date: todayISO(),
        lines: [
          {
            variant_id: variantId,
            qty,
            cost_price: cost,
            expiry_date: expiry || null,
          },
        ],
      });
      setMsg(bn ? "কেনা সেভ হয়েছে" : "Purchase saved");
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    }
  }

  async function importCsv() {
    setError("");
    try {
      const lines = csvText
        .split("\n")
        .map((l) => l.trim())
        .filter(Boolean)
        .map((line) => {
          const [barcode, q, c, exp] = line.split(",").map((x) => x.trim());
          return {
            barcode,
            qty: q,
            cost_price: c,
            expiry_date: exp || null,
          };
        });
      await api.importCsv({
        supplier_id: supplierId,
        invoice_no: `CSV-${Date.now()}`,
        invoice_date: todayISO(),
        lines,
      });
      setMsg(bn ? "CSV ইমপোর্ট হয়েছে" : "CSV imported");
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Import failed");
    }
  }

  async function runOcr() {
    setError("");
    try {
      const res = (await api.ocrInvoice({ text: ocrText })) as {
        provider: string;
        lines: { barcode?: string; name: string; qty?: string; cost_price?: string }[];
      };
      setMsg(
        `${bn ? "OCR" : "OCR"} (${res.provider}): ` +
          res.lines.map((l) => `${l.barcode || l.name} x${l.qty || "?"}`).join(", "),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "OCR failed");
    }
  }

  const variants = products.flatMap((p) =>
    p.variants.map((v) => ({ id: v.id, label: `${p.name} · ${v.name} (${v.barcode})` })),
  );

  return (
    <div className="space-y-5">
      <header>
        <h1 className="page-title">{bn ? "কেনা / ইনভয়েস" : "Purchases / invoices"}</h1>
        <p className="page-sub">
          {bn
            ? "ম্যানুয়াল এন্ট্রি, CSV/Excel ইমপোর্ট, AI OCR।"
            : "Manual entry, CSV/Excel import, AI OCR."}
        </p>
      </header>
      {error ? <p className="text-[var(--coral)]">{error}</p> : null}
      {msg ? <p className="text-[var(--teal)]">{msg}</p> : null}

      <section className="panel grid gap-3 p-4 md:grid-cols-2">
        <label className="text-sm">
          {bn ? "সাপ্লায়ার" : "Supplier"}
          <select className="field mt-1" value={supplierId} onChange={(e) => setSupplierId(e.target.value)}>
            {suppliers.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          {bn ? "ইনভয়েস নং" : "Invoice no"}
          <input className="field mt-1" value={invoiceNo} onChange={(e) => setInvoiceNo(e.target.value)} />
        </label>
        <label className="text-sm md:col-span-2">
          {bn ? "পণ্য" : "Product"}
          <select className="field mt-1" value={variantId} onChange={(e) => setVariantId(e.target.value)}>
            {variants.map((v) => (
              <option key={v.id} value={v.id}>
                {v.label}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          Qty
          <input className="field mt-1" value={qty} onChange={(e) => setQty(e.target.value)} />
        </label>
        <label className="text-sm">
          {bn ? "ক্রয়মূল্য" : "Cost"}
          <input className="field mt-1" value={cost} onChange={(e) => setCost(e.target.value)} />
        </label>
        <label className="text-sm md:col-span-2">
          {bn ? "মেয়াদ (ঐচ্ছিক)" : "Expiry (optional)"}
          <input className="field mt-1" type="date" value={expiry} onChange={(e) => setExpiry(e.target.value)} />
        </label>
        <button className="btn btn-primary md:col-span-2" type="button" onClick={() => void createPurchase()}>
          {bn ? "কেনা সেভ" : "Save purchase"}
        </button>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="panel space-y-2 p-4">
          <h2 className="text-lg font-bold">{bn ? "CSV ইমপোর্ট" : "CSV import"}</h2>
          <p className="text-xs opacity-60">barcode,qty,cost[,expiry]</p>
          <textarea className="field min-h-28 font-mono text-xs" value={csvText} onChange={(e) => setCsvText(e.target.value)} />
          <button className="btn btn-primary" type="button" onClick={() => void importCsv()}>
            {bn ? "ইমপোর্ট" : "Import"}
          </button>
        </div>
        <div className="panel space-y-2 p-4">
          <h2 className="text-lg font-bold">{bn ? "AI ইনভয়েস OCR" : "AI invoice OCR"}</h2>
          <textarea className="field min-h-28 font-mono text-xs" value={ocrText} onChange={(e) => setOcrText(e.target.value)} />
          <button className="btn btn-ghost" type="button" onClick={() => void runOcr()}>
            {bn ? "পার্স করুন" : "Parse"}
          </button>
        </div>
      </section>

      <section className="panel overflow-x-auto p-3">
        <h2 className="px-2 pt-2 text-xl">{bn ? "সাম্প্রতিক কেনা" : "Recent purchases"}</h2>
        <table className="table">
          <thead>
            <tr>
              <th>Invoice</th>
              <th>{bn ? "তারিখ" : "Date"}</th>
              <th>{bn ? "মোট" : "Total"}</th>
              <th>Batches</th>
            </tr>
          </thead>
          <tbody>
            {purchases.map((p) => (
              <tr key={p.id}>
                <td>{p.invoice_no}</td>
                <td>{p.invoice_date}</td>
                <td>{money(p.total_amount)}</td>
                <td>{p.batches?.length ?? 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { api, deviceId, money } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { enqueueOfflineSale } from "@/lib/offline";
import { Alert, PageHeader } from "@/components/ui";
import type { Customer, Product, Sale, Variant } from "@/lib/types";

type CartLine = {
  variant: Variant;
  productName: string;
  qty: number;
  useDealer: boolean;
  lineDiscount: number;
};

const MIN_REDEEM = 100;

export default function PosPage() {
  const { t, lang } = useI18n();
  const bn = lang === "bn";
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [categories, setCategories] = useState<string[]>([]);
  const [hits, setHits] = useState<Product[]>([]);
  const [cart, setCart] = useState<CartLine[]>([]);
  const [method, setMethod] = useState<"cash" | "bkash" | "nagad" | "credit">("cash");
  const [txnId, setTxnId] = useState("");
  const [invoicePhone, setInvoicePhone] = useState("");
  const [invoiceEmail, setInvoiceEmail] = useState("");
  const [customerName, setCustomerName] = useState("");
  const [matched, setMatched] = useState<Customer | null>(null);
  const [lookupHint, setLookupHint] = useState("");
  const [redeemPoints, setRedeemPoints] = useState(0);
  const [billDiscount, setBillDiscount] = useState("0");
  const [dealerDefault, setDealerDefault] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [online, setOnline] = useState(true);
  const [lastSale, setLastSale] = useState<Sale | null>(null);
  const [lastCartSnapshot, setLastCartSnapshot] = useState<CartLine[]>([]);
  const lookupTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const subtotal = useMemo(() => {
    return cart.reduce((sum, line) => {
      const unit = Number(line.useDealer ? line.variant.dealer_price : line.variant.retail_price);
      return sum + unit * line.qty - line.lineDiscount;
    }, 0);
  }, [cart]);

  const afterBillDiscount = Math.max(0, subtotal - Number(billDiscount || 0));
  const pointsDiscount = redeemPoints > 0 ? redeemPoints : 0;
  const total = Math.max(0, afterBillDiscount - pointsDiscount);
  const earnPreview = Math.floor((total * 5) / 1000);

  async function search(term = q, cat = category) {
    setError("");
    try {
      const data = await api.products(term.trim() || undefined, undefined, cat || undefined, 200);
      setHits(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("pos.searchFailed"));
    }
  }

  async function runLookup(phone = invoicePhone, email = invoiceEmail) {
    const p = phone.trim();
    const e = email.trim();
    if (!p && !e) {
      setMatched(null);
      setLookupHint("");
      setRedeemPoints(0);
      return;
    }
    try {
      const c = await api.lookupCustomer(p || undefined, e || undefined);
      if (c) {
        setMatched(c);
        setInvoicePhone(c.phone || p);
        setInvoiceEmail(c.email || e);
        setCustomerName(c.name);
        setLookupHint("");
        if ((c.loyalty_points || 0) < MIN_REDEEM) setRedeemPoints(0);
      } else {
        setMatched(null);
        setRedeemPoints(0);
        setLookupHint(
          bn
            ? "নতুন কাস্টমার — রেজিস্টার করতে মোবাইল + ইমেইল দুটোই দিন"
            : "New customer — enter both mobile + email to register",
        );
      }
    } catch (err) {
      setMatched(null);
      setLookupHint(err instanceof Error ? err.message : "Lookup failed");
    }
  }

  function scheduleLookup(phone: string, email: string) {
    if (lookupTimer.current) clearTimeout(lookupTimer.current);
    lookupTimer.current = setTimeout(() => void runLookup(phone, email), 450);
  }

  useEffect(() => {
    void search("");
    void api.productCategories().then((r) => setCategories(r.categories)).catch(() => undefined);
    const syncOnline = () => setOnline(navigator.onLine);
    syncOnline();
    window.addEventListener("online", syncOnline);
    window.addEventListener("offline", syncOnline);
    return () => {
      window.removeEventListener("online", syncOnline);
      window.removeEventListener("offline", syncOnline);
      if (lookupTimer.current) clearTimeout(lookupTimer.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function addVariant(productName: string, variant: Variant) {
    setCart((prev) => {
      const existing = prev.find((l) => l.variant.id === variant.id && l.useDealer === dealerDefault);
      if (existing) {
        return prev.map((l) => (l === existing ? { ...l, qty: l.qty + 1 } : l));
      }
      return [
        ...prev,
        { variant, productName, qty: 1, useDealer: dealerDefault, lineDiscount: 0 },
      ];
    });
  }

  function changeQty(id: string, dealer: boolean, delta: number) {
    setCart((prev) =>
      prev
        .map((l) =>
          l.variant.id === id && l.useDealer === dealer
            ? { ...l, qty: Math.max(0, l.qty + delta) }
            : l,
        )
        .filter((l) => l.qty > 0),
    );
  }

  function toggleRedeem() {
    if (!matched) return;
    const bal = matched.loyalty_points || 0;
    if (bal < MIN_REDEEM) return;
    if (redeemPoints > 0) {
      setRedeemPoints(0);
      return;
    }
    const maxUse = Math.min(bal, Math.floor(afterBillDiscount));
    if (maxUse < MIN_REDEEM) return;
    setRedeemPoints(maxUse);
  }

  async function checkout() {
    if (!cart.length) return;
    setBusy(true);
    setError("");
    setMessage("");
    setLastSale(null);
    const phone = invoicePhone.trim();
    const email = invoiceEmail.trim();
    const payload = {
      items: cart.map((l) => ({
        variant_id: l.variant.id,
        qty: String(l.qty),
        use_dealer_price: l.useDealer,
        discount: String(l.lineDiscount || 0),
      })),
      discount: String(Number(billDiscount || 0)),
      customer_id: matched?.id || null,
      customer_name: customerName.trim() || null,
      device_id: deviceId(),
      invoice_phone: phone || null,
      invoice_email: email || null,
      points_to_redeem: redeemPoints || 0,
      payments:
        method === "cash"
          ? [{ method: "cash", amount: String(total.toFixed(2)) }]
          : method === "credit"
            ? [{ method: "credit", amount: String(total.toFixed(2)) }]
            : [
                {
                  method,
                  amount: String(total.toFixed(2)),
                  txn_id: txnId || `PORTAL-${Date.now()}`,
                },
              ],
    };

    try {
      if (!navigator.onLine) {
        enqueueOfflineSale(payload);
        setMessage(bn ? "অফলাইন কিউতে সেভ হয়েছে" : "Saved to offline queue");
        setCart([]);
        return;
      }
      const snapshot = [...cart];
      const sale = await api.createSale(payload);
      setLastCartSnapshot(snapshot);
      setLastSale(sale);
      const loyaltyBit = sale.loyalty
        ? bn
          ? ` · পয়েন্ট +${sale.loyalty.points_earned} / বাকি ${sale.loyalty.points_balance}`
          : ` · points +${sale.loyalty.points_earned} / bal ${sale.loyalty.points_balance}`
        : "";
      const deliveryNote = sale.invoice_delivery?.detail ? ` · ${sale.invoice_delivery.detail}` : "";
      setMessage(
        `${t("pos.saleSaved", { bill: sale.bill_no, total: money(sale.total) })}${loyaltyBit}${deliveryNote}`,
      );
      setCart([]);
      setTxnId("");
      setBillDiscount("0");
      setRedeemPoints(0);
      if (phone || email) void runLookup(phone, email);
    } catch (err) {
      if (!navigator.onLine) {
        enqueueOfflineSale(payload);
        setMessage(bn ? "নেট নেই — কিউতে রাখা হয়েছে" : "Offline — queued");
        setCart([]);
      } else {
        setError(err instanceof Error ? err.message : t("pos.saleFailed"));
      }
    } finally {
      setBusy(false);
    }
  }

  function printInvoice() {
    window.print();
  }

  const canRedeem = Boolean(matched && (matched.loyalty_points || 0) >= MIN_REDEEM);

  return (
    <div className="space-y-4">
      <div className="no-print space-y-4">
        <PageHeader
          title={t("pos.title")}
          subtitle={`${t("pos.subtitle")}${!online ? (bn ? " · অফলাইন" : " · Offline") : ""}`}
        />

        <div className="grid gap-3 xl:grid-cols-[1.2fr_0.8fr]">
          <section className="panel p-4">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-sm font-semibold">{bn ? "পণ্য · ক্যাটাগরি" : "Products · category"}</h2>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={dealerDefault}
                  onChange={(e) => setDealerDefault(e.target.checked)}
                />
                {bn ? "ডিলার দাম" : "Dealer price"}
              </label>
            </div>

            <div className="mb-3 flex flex-wrap gap-1.5">
              <button
                type="button"
                className="seg-btn"
                data-active={!category}
                onClick={() => {
                  setCategory("");
                  void search(q, "");
                }}
              >
                {bn ? "সব" : "All"}
              </button>
              {categories.map((c) => (
                <button
                  key={c}
                  type="button"
                  className="seg-btn"
                  data-active={category === c}
                  onClick={() => {
                    setCategory(c);
                    void search(q, c);
                  }}
                >
                  {c}
                </button>
              ))}
            </div>

            <form
              className="mb-3 flex gap-2"
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
                autoFocus
              />
              <button className="btn btn-primary shrink-0" type="submit">
                {t("pos.find")}
              </button>
            </form>

            <ul className="max-h-[28rem] overflow-auto">
              {hits.flatMap((p) =>
                p.variants.map((v) => {
                  const low = Number(v.current_stock) <= Number(v.low_stock_threshold);
                  return (
                    <li key={v.id} className="list-row">
                      <div className="min-w-0 text-sm">
                        <p className="font-medium">
                          {p.name} · {v.name}
                        </p>
                        <p className="mt-0.5 text-xs text-[var(--muted)]">
                          {p.category || "General"} · {v.barcode || t("pos.noBarcode")} · {t("pos.stock")}{" "}
                          <span className={low ? "font-semibold text-[var(--danger)]" : ""}>
                            {v.current_stock}
                          </span>
                          {" · "}R {money(v.retail_price)} / D {money(v.dealer_price)}
                        </p>
                      </div>
                      <button
                        className="btn btn-ghost btn-sm shrink-0"
                        type="button"
                        onClick={() => addVariant(p.name, v)}
                      >
                        {t("pos.add")}
                      </button>
                    </li>
                  );
                }),
              )}
              {hits.length === 0 ? (
                <li className="py-6 text-center text-sm text-[var(--muted)]">
                  {bn ? "কোনো পণ্য নেই" : "No products"}
                </li>
              ) : null}
            </ul>
          </section>

          <section className="panel flex flex-col p-4">
            <div className="mb-2 flex items-baseline justify-between">
              <h2 className="text-sm font-semibold">{t("pos.cart")}</h2>
              <span className="text-xs text-[var(--muted)]">{cart.length}</span>
            </div>

            <div className="min-h-[8rem] flex-1 overflow-auto">
              {cart.length === 0 ? (
                <p className="py-6 text-center text-sm text-[var(--muted)]">{t("pos.empty")}</p>
              ) : (
                cart.map((line) => {
                  const unit = Number(
                    line.useDealer ? line.variant.dealer_price : line.variant.retail_price,
                  );
                  return (
                    <div key={`${line.variant.id}-${line.useDealer}`} className="list-row">
                      <div className="min-w-0 text-sm">
                        <p>
                          {line.productName} · {line.variant.name}
                          {line.useDealer ? " (D)" : ""}
                        </p>
                        <p className="text-xs text-[var(--muted)] tabular-nums">
                          {money(unit)} × {line.qty}
                        </p>
                      </div>
                      <div className="flex items-center gap-1">
                        <button
                          className="btn btn-ghost btn-sm px-2"
                          type="button"
                          onClick={() => changeQty(line.variant.id, line.useDealer, -1)}
                        >
                          −
                        </button>
                        <span className="w-5 text-center text-sm tabular-nums">{line.qty}</span>
                        <button
                          className="btn btn-ghost btn-sm px-2"
                          type="button"
                          onClick={() => changeQty(line.variant.id, line.useDealer, 1)}
                        >
                          +
                        </button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            <div className="mt-3 space-y-3 border-t border-[var(--line)] pt-3">
              <div className="grid gap-2 sm:grid-cols-2">
                <label className="field-label">
                  {bn ? "মোবাইল" : "Mobile"}
                  <input
                    className="field mt-1.5"
                    value={invoicePhone}
                    onChange={(e) => {
                      setInvoicePhone(e.target.value);
                      scheduleLookup(e.target.value, invoiceEmail);
                    }}
                    onBlur={() => void runLookup()}
                    placeholder="01XXXXXXXXX"
                  />
                </label>
                <label className="field-label">
                  {bn ? "ইমেইল" : "Email"}
                  <input
                    className="field mt-1.5"
                    type="email"
                    value={invoiceEmail}
                    onChange={(e) => {
                      setInvoiceEmail(e.target.value);
                      scheduleLookup(invoicePhone, e.target.value);
                    }}
                    onBlur={() => void runLookup()}
                    placeholder="name@example.com"
                  />
                </label>
              </div>

              {!matched ? (
                <label className="field-label">
                  {bn ? "নাম (নতুন কাস্টমার)" : "Name (new customer)"}
                  <input
                    className="field mt-1.5"
                    value={customerName}
                    onChange={(e) => setCustomerName(e.target.value)}
                    placeholder={bn ? "ঐচ্ছিক" : "Optional"}
                  />
                </label>
              ) : null}

              {matched ? (
                <div className="rounded-[12px] border border-[var(--line)] bg-[var(--surface-2)] px-3 py-2.5 text-sm">
                  <p className="font-semibold">{matched.name}</p>
                  <p className="mt-0.5 text-xs text-[var(--muted)]">
                    {matched.phone} · {matched.email}
                    {matched.area ? ` · ${matched.area}` : ""}
                  </p>
                  <p className="mt-1.5 tabular-nums">
                    <span className="font-semibold text-[var(--accent)]">
                      {matched.loyalty_points} {bn ? "পয়েন্ট" : "pts"}
                    </span>
                    {" · "}
                    {bn ? "বাকি" : "due"} {money(matched.current_due)}
                  </p>
                  <p className="mt-1 text-xs text-[var(--muted)]">
                    {bn
                      ? "৳১০০০ = ৫ পয়েন্ট · রিডিম মিন ১০০ (১ পয়েন্ট = ৳১)"
                      : "৳1000 = 5 pts · redeem min 100 (1 pt = ৳1)"}
                  </p>
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm mt-2"
                    disabled={!canRedeem}
                    onClick={toggleRedeem}
                  >
                    {redeemPoints > 0
                      ? bn
                        ? `রিডিম বন্ধ (${redeemPoints})`
                        : `Clear redeem (${redeemPoints})`
                      : canRedeem
                        ? bn
                          ? "পয়েন্ট রিডিম করো"
                          : "Redeem points"
                        : bn
                          ? `রিডিম করতে কমপক্ষে ${MIN_REDEEM} পয়েন্ট লাগে`
                          : `Need ≥ ${MIN_REDEEM} points to redeem`}
                  </button>
                </div>
              ) : lookupHint ? (
                <p className="text-xs text-[var(--muted)]">{lookupHint}</p>
              ) : (
                <p className="text-xs text-[var(--muted)]">
                  {bn
                    ? "মোবাইল বা ইমেইল দিলে কাস্টমার + পয়েন্ট দেখাবে; ইনভয়েসও যাবে।"
                    : "Enter mobile or email to load customer + points; invoice sends too."}
                </p>
              )}

              <label className="field-label">
                {bn ? "বিল ডিসকাউন্ট" : "Bill discount"}
                <input
                  className="field mt-1.5"
                  value={billDiscount}
                  onChange={(e) => setBillDiscount(e.target.value)}
                />
              </label>

              <div className="space-y-1 border border-[var(--line)] bg-[var(--surface-2)] px-3 py-2.5 text-sm">
                {pointsDiscount > 0 ? (
                  <div className="flex justify-between text-[var(--muted)]">
                    <span>{bn ? "পয়েন্ট ছাড়" : "Points discount"}</span>
                    <span className="tabular-nums">−{money(pointsDiscount)}</span>
                  </div>
                ) : null}
                <div className="flex items-end justify-between gap-3">
                  <span className="text-[var(--muted)]">{bn ? "মোট" : "Total"}</span>
                  <span className="stat-value text-xl">{money(total)}</span>
                </div>
                {matched ? (
                  <p className="text-xs text-[var(--muted)]">
                    {bn ? `এই বিলে ≈ ${earnPreview} পয়েন্ট পাবে` : `This bill earns ≈ ${earnPreview} pts`}
                  </p>
                ) : null}
              </div>

              <div>
                <p className="field-label mb-1.5">{t("pos.payment")}</p>
                <div className="seg w-full">
                  {(["cash", "bkash", "nagad", "credit"] as const).map((m) => (
                    <button
                      key={m}
                      type="button"
                      className="seg-btn flex-1"
                      data-active={method === m}
                      onClick={() => setMethod(m)}
                    >
                      {t(`pay.${m}` as "pay.cash")}
                    </button>
                  ))}
                </div>
              </div>

              {method === "bkash" || method === "nagad" ? (
                <label className="field-label">
                  {t("pos.txnId")}
                  <input
                    className="field mt-1.5"
                    value={txnId}
                    onChange={(e) => setTxnId(e.target.value)}
                  />
                </label>
              ) : null}

              <button
                className="btn btn-primary w-full"
                disabled={busy || !cart.length}
                onClick={() => void checkout()}
                type="button"
              >
                {busy ? t("pos.saving") : t("pos.complete")}
              </button>

              {lastSale ? (
                <button className="btn btn-ghost w-full" type="button" onClick={printInvoice}>
                  {bn ? "ইনভয়েস প্রিন্ট" : "Print invoice"}
                </button>
              ) : null}

              {message ? <Alert tone="ok">{message}</Alert> : null}
              {error ? <Alert>{error}</Alert> : null}
            </div>
          </section>
        </div>
      </div>

      {lastSale ? (
        <section className="print-receipt panel p-5" aria-label="Invoice">
          <div className="no-print mb-3 flex items-center justify-between gap-2">
            <h2 className="text-sm font-semibold">{bn ? "ইনভয়েস প্রিভিউ" : "Invoice preview"}</h2>
            <button className="btn btn-primary btn-sm" type="button" onClick={printInvoice}>
              {bn ? "প্রিন্ট" : "Print"}
            </button>
          </div>
          <div className="space-y-2 text-sm">
            <p className="text-lg font-bold">Dokan POS</p>
            <p>
              <strong>{lastSale.bill_no}</strong>
            </p>
            <p className="text-[var(--muted)]">{new Date(lastSale.created_at).toLocaleString()}</p>
            <ul className="divide-y divide-[var(--line)] border-y border-[var(--line)] py-2">
              {lastCartSnapshot.map((line) => {
                const unit = Number(
                  line.useDealer ? line.variant.dealer_price : line.variant.retail_price,
                );
                return (
                  <li key={`${line.variant.id}-${line.useDealer}`} className="flex justify-between gap-3 py-1.5">
                    <span>
                      {line.productName} · {line.variant.name} × {line.qty}
                    </span>
                    <span className="tabular-nums">{money(unit * line.qty - line.lineDiscount)}</span>
                  </li>
                );
              })}
            </ul>
            <div className="space-y-1">
              <div className="flex justify-between">
                <span>{bn ? "সাবটোটাল" : "Subtotal"}</span>
                <span className="tabular-nums">{money(lastSale.subtotal)}</span>
              </div>
              {Number(lastSale.discount) > 0 ? (
                <div className="flex justify-between">
                  <span>{bn ? "বিল ডিসকাউন্ট" : "Bill discount"}</span>
                  <span className="tabular-nums">−{money(lastSale.discount)}</span>
                </div>
              ) : null}
              {Number(lastSale.points_discount || lastSale.loyalty?.points_discount || 0) > 0 ? (
                <div className="flex justify-between">
                  <span>
                    {bn ? "পয়েন্ট ছাড়" : "Points discount"}
                    {(lastSale.points_redeemed || lastSale.loyalty?.points_redeemed)
                      ? ` (${lastSale.points_redeemed || lastSale.loyalty?.points_redeemed} pts)`
                      : ""}
                  </span>
                  <span className="tabular-nums">
                    −{money(lastSale.points_discount || lastSale.loyalty?.points_discount || "0")}
                  </span>
                </div>
              ) : null}
              <div className="flex justify-between font-semibold">
                <span>{bn ? "পরিশোধযোগ্য" : "Payable"}</span>
                <span className="tabular-nums">{money(lastSale.total)}</span>
              </div>
            </div>
            {lastSale.loyalty ? (
              <p className="text-xs text-[var(--muted)]">
                Points +{lastSale.loyalty.points_earned}
                {lastSale.loyalty.points_redeemed
                  ? ` · redeemed ${lastSale.loyalty.points_redeemed}`
                  : ""}{" "}
                · bal {lastSale.loyalty.points_balance}
              </p>
            ) : null}
          </div>
        </section>
      ) : null}
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { api, money } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { Shift, ShiftSummary } from "@/lib/types";

export default function ShiftsPage() {
  const { lang } = useI18n();
  const bn = lang === "bn";
  const [shift, setShift] = useState<Shift | null>(null);
  const [summary, setSummary] = useState<ShiftSummary | null>(null);
  const [opening, setOpening] = useState("1000");
  const [counted, setCounted] = useState("0");
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");

  async function load() {
    const open = await api.myOpenShift();
    setShift(open);
    if (open) {
      const s = await api.shiftSummary(open.id);
      setSummary(s);
      setCounted(String(s.expected_cash));
    } else {
      setSummary(null);
    }
  }

  useEffect(() => {
    void load().catch((e) => setError(e.message));
  }, []);

  async function openShift() {
    setError("");
    try {
      await api.openShift(opening);
      setMsg(bn ? "শিফট খোলা হয়েছে" : "Shift opened");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    }
  }

  async function closeShift() {
    if (!shift) return;
    try {
      await api.closeShift(shift.id, counted, "portal close");
      setMsg(bn ? "ক্যাশ ক্লোজিং সম্পন্ন" : "Cash closing done");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    }
  }

  return (
    <div className="space-y-5">
      <header>
        <h1 className="page-title">{bn ? "শিফট ও ক্যাশ ক্লোজিং" : "Shifts & cash closing"}</h1>
        <p className="page-sub">
          {bn ? "শিফট খুলুন, সারাংশ দেখুন, ক্যাশ মেলান।" : "Open shift, review totals, close cash."}
        </p>
      </header>
      {error ? <p className="text-[var(--coral)]">{error}</p> : null}
      {msg ? <p className="text-[var(--teal)]">{msg}</p> : null}

      {!shift ? (
        <section className="panel flex flex-col gap-3 p-4 sm:flex-row sm:items-end">
          <label className="text-sm">
            {bn ? "শুরুর ক্যাশ" : "Opening cash"}
            <input className="field mt-1" value={opening} onChange={(e) => setOpening(e.target.value)} />
          </label>
          <button className="btn btn-primary" type="button" onClick={() => void openShift()}>
            {bn ? "শিফট খুলুন" : "Open shift"}
          </button>
        </section>
      ) : (
        <section className="panel space-y-3 p-5">
          <p className="text-sm opacity-70">
            {bn ? "খোলা" : "Opened"}: {new Date(shift.opened_at).toLocaleString()}
          </p>
          {summary ? (
            <ul className="space-y-1 text-sm">
              <li>
                {bn ? "ক্যাশ বিক্রি" : "Cash sales"}: {money(summary.cash_sales)}
              </li>
              <li>bKash: {money(summary.bkash_sales)}</li>
              <li>Nagad: {money(summary.nagad_sales)}</li>
              <li>
                {bn ? "বাকি" : "Credit"}: {money(summary.credit_sales)}
              </li>
              <li>
                {bn ? "পয়েন্ট ছাড় (ড্রয়ারে নয়)" : "Points discount (not in till)"}:{" "}
                {money(summary.points_discount || "0")}
              </li>
              <li>
                {bn ? "বিল ডিসকাউন্ট" : "Bill discount"}: {money(summary.bill_discount || "0")}
              </li>
              <li>
                <strong>
                  {bn ? "প্রত্যাশিত ক্যাশ" : "Expected cash"}: {money(summary.expected_cash)}
                </strong>
              </li>
              <li>
                {bn ? "বিল" : "Bills"}: {summary.bill_count}
              </li>
            </ul>
          ) : null}
          <label className="block text-sm">
            {bn ? "গণনা করা ক্যাশ" : "Counted cash"}
            <input className="field mt-1" value={counted} onChange={(e) => setCounted(e.target.value)} />
          </label>
          <button className="btn btn-primary" type="button" onClick={() => void closeShift()}>
            {bn ? "ক্যাশ ক্লোজ" : "Close cash"}
          </button>
        </section>
      )}
    </div>
  );
}

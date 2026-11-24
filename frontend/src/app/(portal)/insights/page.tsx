"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export default function InsightsPage() {
  const { lang } = useI18n();
  const bn = lang === "bn";
  const [reorder, setReorder] = useState<Record<string, unknown>[]>([]);
  const [seasonal, setSeasonal] = useState<Record<string, unknown>[]>([]);
  const [season, setSeason] = useState("winter_start");
  const [branches, setBranches] = useState<{ id: string; name: string; code: string | null }[]>([]);
  const [error, setError] = useState("");

  async function loadReorder() {
    try {
      const data = await api.reorder(14);
      setReorder(data.suggestions || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    }
  }

  async function loadSeasonal() {
    try {
      const data = await api.seasonal(season);
      setSeasonal(data.items || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    }
  }

  async function loadBranches() {
    try {
      setBranches(await api.branches());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    }
  }

  return (
    <div className="space-y-5">
      <header>
        <h1 className="page-title">{bn ? "ইনসাইট" : "Insights"}</h1>
        <p className="page-sub">
          {bn
            ? "রিঅর্ডার, মৌসুমি বিক্রি, ব্রাঞ্চ।"
            : "Reorder suggestions, seasonal sales, branches."}
        </p>
      </header>
      {error ? <p className="text-[var(--coral)]">{error}</p> : null}

      <section className="panel space-y-3 p-5">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-lg font-bold">{bn ? "রিঅর্ডার সাজেশন" : "Reorder suggestions"}</h2>
          <button className="btn btn-primary" type="button" onClick={() => void loadReorder()}>
            {bn ? "লোড" : "Load"}
          </button>
        </div>
        <ul className="space-y-2 text-sm">
          {reorder.map((r, i) => (
            <li key={i} className="border-b border-[var(--line)] py-2">
              {String(r.product || r.variant || "item")} · suggest {String(r.suggested_qty)} (avg{" "}
              {String(r.avg_daily)})
            </li>
          ))}
          {!reorder.length ? <li className="opacity-60">{bn ? "এখনো লোড হয়নি" : "Not loaded yet"}</li> : null}
        </ul>
      </section>

      <section className="panel space-y-3 p-5">
        <div className="flex flex-wrap items-end gap-2">
          <label className="text-sm">
            {bn ? "মৌসুম" : "Season"}
            <select className="field mt-1" value={season} onChange={(e) => setSeason(e.target.value)}>
              <option value="winter_start">Winter start</option>
              <option value="winter_end">Winter end</option>
              <option value="summer_start">Summer start</option>
              <option value="summer_end">Summer end</option>
            </select>
          </label>
          <button className="btn btn-primary" type="button" onClick={() => void loadSeasonal()}>
            {bn ? "মৌসুমি টপ" : "Seasonal top"}
          </button>
        </div>
        <ul className="space-y-2 text-sm">
          {seasonal.map((r, i) => (
            <li key={i} className="border-b border-[var(--line)] py-2">
              {String(r.product)} · {String(r.variant)} · qty {String(r.qty_sold)}
            </li>
          ))}
        </ul>
      </section>

      <section className="panel space-y-3 p-5">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold">{bn ? "ব্রাঞ্চ" : "Branches"}</h2>
          <button className="btn btn-ghost" type="button" onClick={() => void loadBranches()}>
            {bn ? "দেখুন" : "Show"}
          </button>
        </div>
        <ul className="text-sm">
          {branches.map((b) => (
            <li key={b.id} className="border-b border-[var(--line)] py-2">
              {b.name} {b.code ? `(${b.code})` : ""}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

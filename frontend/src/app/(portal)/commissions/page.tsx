"use client";

import { useEffect, useState } from "react";
import { api, money } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";

type Rule = {
  id: string;
  user_id: string;
  name: string;
  basis: string;
  rate: string;
  is_active: boolean;
};

type Entry = {
  id: string;
  user_id: string;
  sale_id: string;
  amount: string;
  created_at: string;
};

export default function CommissionsPage() {
  const { lang } = useI18n();
  const { user } = useAuth();
  const bn = lang === "bn";
  const [rules, setRules] = useState<Rule[]>([]);
  const [entries, setEntries] = useState<Entry[]>([]);
  const [rate, setRate] = useState("2");
  const [error, setError] = useState("");

  async function load() {
    const [r, e] = await Promise.all([
      api.commissionRules() as Promise<Rule[]>,
      api.commissionEntries() as Promise<Entry[]>,
    ]);
    setRules(r);
    setEntries(e);
  }

  useEffect(() => {
    void load().catch((err) => setError(err.message));
  }, []);

  async function createRule() {
    if (!user) return;
    try {
      await api.createCommissionRule({
        user_id: user.id,
        name: "Sale percent",
        basis: "percent_of_sale",
        rate,
      });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    }
  }

  return (
    <div className="space-y-5">
      <header>
        <h1 className="page-title">{bn ? "কমিশন" : "Commissions"}</h1>
        <p className="page-sub">
          {bn
            ? "রুল সেট করলে বিক্রিতে অটো কমিশন হয়।"
            : "Rules auto-apply commission on each sale."}
        </p>
      </header>
      {error ? <p className="text-[var(--coral)]">{error}</p> : null}

      <section className="panel flex flex-col gap-3 p-4 sm:flex-row sm:items-end">
        <label className="text-sm">
          {bn ? "রেট %" : "Rate %"}
          <input className="field mt-1" value={rate} onChange={(e) => setRate(e.target.value)} />
        </label>
        <button className="btn btn-primary" type="button" onClick={() => void createRule()}>
          {bn ? "রুল যোগ" : "Add rule"}
        </button>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="panel p-5">
          <h2 className="text-lg font-bold">{bn ? "রুলস" : "Rules"}</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {rules.map((r) => (
              <li key={r.id}>
                {r.name} · {r.basis} · {r.rate}
              </li>
            ))}
          </ul>
        </div>
        <div className="panel p-5">
          <h2 className="text-lg font-bold">{bn ? "এন্ট্রি" : "Entries"}</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {entries.map((e) => (
              <li key={e.id}>
                {money(e.amount)} · {new Date(e.created_at).toLocaleString()}
              </li>
            ))}
          </ul>
        </div>
      </section>
    </div>
  );
}

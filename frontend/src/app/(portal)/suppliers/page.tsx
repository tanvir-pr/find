"use client";

import { useEffect, useState } from "react";
import { api, money } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { Supplier } from "@/lib/types";

export default function SuppliersPage() {
  const { lang } = useI18n();
  const bn = lang === "bn";
  const [items, setItems] = useState<Supplier[]>([]);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [payId, setPayId] = useState("");
  const [amount, setAmount] = useState("1000");
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");

  async function load() {
    setItems(await api.suppliers());
  }

  useEffect(() => {
    void load().catch((e) => setError(e.message));
  }, []);

  async function create() {
    try {
      await api.createSupplier({ name, phone: phone || null });
      setName("");
      setPhone("");
      setMsg(bn ? "সাপ্লায়ার যোগ হয়েছে" : "Supplier added");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    }
  }

  async function pay() {
    try {
      await api.paySupplier(payId, { amount, method: "cash" });
      setMsg(bn ? "পেমেন্ট সেভ" : "Payment saved");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    }
  }

  return (
    <div className="space-y-5">
      <header>
        <h1 className="page-title">{bn ? "সাপ্লায়ার" : "Suppliers"}</h1>
        <p className="page-sub">
          {bn ? "বকেয়া ট্র্যাক ও পেমেন্ট।" : "Due tracking and payments."}
        </p>
      </header>
      {error ? <p className="text-[var(--coral)]">{error}</p> : null}
      {msg ? <p className="text-[var(--teal)]">{msg}</p> : null}

      <section className="panel flex flex-col gap-3 p-4 sm:flex-row">
        <input className="field" placeholder={bn ? "নাম" : "Name"} value={name} onChange={(e) => setName(e.target.value)} />
        <input className="field" placeholder={bn ? "ফোন" : "Phone"} value={phone} onChange={(e) => setPhone(e.target.value)} />
        <button className="btn btn-primary" type="button" onClick={() => void create()} disabled={!name.trim()}>
          {bn ? "যোগ" : "Add"}
        </button>
      </section>

      <section className="panel flex flex-col gap-3 p-4 sm:flex-row sm:items-end">
        <label className="flex-1 text-sm">
          {bn ? "পেমেন্ট" : "Pay supplier"}
          <select className="field mt-1" value={payId} onChange={(e) => setPayId(e.target.value)}>
            <option value="">{bn ? "বেছে নিন" : "Select"}</option>
            {items.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} · due {money(s.current_due)}
              </option>
            ))}
          </select>
        </label>
        <input className="field max-w-40" value={amount} onChange={(e) => setAmount(e.target.value)} />
        <button className="btn btn-ghost" type="button" disabled={!payId} onClick={() => void pay()}>
          {bn ? "পরিশোধ" : "Pay"}
        </button>
      </section>

      <div className="panel overflow-x-auto p-2">
        <table className="table">
          <thead>
            <tr>
              <th>{bn ? "নাম" : "Name"}</th>
              <th>{bn ? "ফোন" : "Phone"}</th>
              <th>{bn ? "বাকি" : "Due"}</th>
            </tr>
          </thead>
          <tbody>
            {items.map((s) => (
              <tr key={s.id}>
                <td>{s.name}</td>
                <td>{s.phone || "—"}</td>
                <td className={Number(s.current_due) > 0 ? "text-[var(--coral)]" : ""}>
                  {money(s.current_due)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { flushOfflineQueue, getOfflineQueue } from "@/lib/offline";
import { useI18n } from "@/lib/i18n";

export default function OpsPage() {
  const { lang } = useI18n();
  const bn = lang === "bn";
  const [offer, setOffer] = useState("Mirpur অফার: School Bag-এ ৫০ টাকা ছাড় আজ!");
  const [area, setArea] = useState("Mirpur");
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const [queueLen, setQueueLen] = useState(0);

  function refreshQueue() {
    setQueueLen(getOfflineQueue().length);
  }

  return (
    <div className="space-y-5">
      <header>
        <h1 className="page-title">{bn ? "SMS / অফার / অফলাইন" : "SMS / offers / offline"}</h1>
      </header>
      {error ? <p className="text-[var(--coral)]">{error}</p> : null}
      {msg ? <p className="text-[var(--teal)]">{msg}</p> : null}

      <section className="panel space-y-3 p-5">
        <h2 className="text-lg font-bold">{bn ? "দৈনিক SMS সারাংশ" : "Daily SMS summary"}</h2>
        <button
          className="btn btn-primary"
          type="button"
          onClick={() =>
            void api
              .dailySms()
              .then((r) => {
                const row = r as { to_phone?: string; body?: string; provider_status?: string };
                setMsg(
                  bn
                    ? `SMS গেছে → ${row.to_phone || "—"} (${row.provider_status || "ok"})`
                    : `SMS sent → ${row.to_phone || "—"} (${row.provider_status || "ok"})`,
                );
              })
              .catch((e) => setError(e.message))
          }
        >
          {bn ? "মালিককে SMS পাঠান" : "Send owner SMS"}
        </button>
      </section>

      <section className="panel space-y-3 p-5">
        <h2 className="text-lg font-bold">{bn ? "বকেয়া রিমাইন্ডার" : "Due reminders"}</h2>
        <button
          className="btn btn-ghost"
          type="button"
          onClick={() =>
            void api
              .dueReminders()
              .then((r) => setMsg(`Reminders: ${JSON.stringify(r).slice(0, 200)}`))
              .catch((e) => setError(e.message))
          }
        >
          {bn ? "সব বাকিতে SMS" : "SMS all dues"}
        </button>
      </section>

      <section className="panel space-y-3 p-5">
        <h2 className="text-lg font-bold">{bn ? "অফার নোটিফিকেশন" : "Offer notifications"}</h2>
        <input className="field" value={area} onChange={(e) => setArea(e.target.value)} placeholder="Area" />
        <textarea className="field min-h-24" value={offer} onChange={(e) => setOffer(e.target.value)} />
        <button
          className="btn btn-primary"
          type="button"
          onClick={() =>
            void api
              .sendOffers({ area: area || null, message: offer, only_opt_in: true })
              .then((r) => setMsg(JSON.stringify(r)))
              .catch((e) => setError(e.message))
          }
        >
          {bn ? "অপ্ট-ইন কাস্টমারদের পাঠান" : "Send to opted-in"}
        </button>
      </section>

      <section className="panel space-y-3 p-5">
        <h2 className="text-lg font-bold">{bn ? "অফলাইন কিউ" : "Offline queue"}</h2>
        <p className="text-sm opacity-70">
          {bn ? "নেট না থাকলে POS কিউতে রাখে; অনলাইনে সিঙ্ক হয়।" : "POS queues sales offline; sync when online."}
        </p>
        <p className="text-sm">
          {bn ? "অপেক্ষমাণ" : "Pending"}: {queueLen}
        </p>
        <div className="flex gap-2">
          <button className="btn btn-ghost" type="button" onClick={refreshQueue}>
            {bn ? "রিফ্রেশ" : "Refresh"}
          </button>
          <button
            className="btn btn-primary"
            type="button"
            onClick={() =>
              void flushOfflineQueue()
                .then((r) => {
                  setMsg(`Synced ${r.synced}, failed ${r.failed}`);
                  refreshQueue();
                })
                .catch((e) => setError(e.message))
            }
          >
            {bn ? "এখন সিঙ্ক" : "Sync now"}
          </button>
        </div>
      </section>
    </div>
  );
}

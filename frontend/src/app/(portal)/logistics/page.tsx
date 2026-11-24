"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { Delivery, Van } from "@/lib/types";

export default function LogisticsPage() {
  const { lang } = useI18n();
  const bn = lang === "bn";
  const [vans, setVans] = useState<Van[]>([]);
  const [deliveries, setDeliveries] = useState<Delivery[]>([]);
  const [name, setName] = useState("");
  const [plate, setPlate] = useState("");
  const [vanId, setVanId] = useState("");
  const [dest, setDest] = useState("");
  const [error, setError] = useState("");

  async function load() {
    const [v, d] = await Promise.all([api.vans(), api.deliveries()]);
    setVans(v);
    setDeliveries(d);
    if (!vanId && v[0]) setVanId(v[0].id);
  }

  useEffect(() => {
    void load().catch((e) => setError(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="space-y-5">
      <header>
        <h1 className="page-title">{bn ? "ভ্যান ও ডেলিভারি" : "Vans & deliveries"}</h1>
      </header>
      {error ? <p className="text-[var(--coral)]">{error}</p> : null}

      <section className="panel flex flex-col gap-2 p-4 sm:flex-row">
        <input className="field" placeholder={bn ? "ভ্যানের নাম" : "Van name"} value={name} onChange={(e) => setName(e.target.value)} />
        <input className="field" placeholder="Plate" value={plate} onChange={(e) => setPlate(e.target.value)} />
        <button
          className="btn btn-primary"
          type="button"
          onClick={() =>
            void api
              .createVan({ name, plate_no: plate || null, driver_name: null })
              .then(load)
              .catch((e) => setError(e.message))
          }
        >
          {bn ? "ভ্যান যোগ" : "Add van"}
        </button>
      </section>

      <section className="panel flex flex-col gap-2 p-4 sm:flex-row">
        <select className="field" value={vanId} onChange={(e) => setVanId(e.target.value)}>
          {vans.map((v) => (
            <option key={v.id} value={v.id}>
              {v.name}
            </option>
          ))}
        </select>
        <input className="field" placeholder={bn ? "গন্তব্য" : "Destination"} value={dest} onChange={(e) => setDest(e.target.value)} />
        <button
          className="btn btn-ghost"
          type="button"
          disabled={!vanId}
          onClick={() =>
            void api
              .createDelivery({ van_id: vanId, destination: dest })
              .then(load)
              .catch((e) => setError(e.message))
          }
        >
          {bn ? "ডেলিভারি" : "Create delivery"}
        </button>
      </section>

      <div className="panel overflow-x-auto p-2">
        <table className="table">
          <thead>
            <tr>
              <th>Van</th>
              <th>{bn ? "গন্তব্য" : "Destination"}</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {deliveries.map((d) => (
              <tr key={d.id}>
                <td>{vans.find((v) => v.id === d.van_id)?.name || d.van_id.slice(0, 8)}</td>
                <td>{d.destination || "—"}</td>
                <td>{d.status}</td>
                <td>
                  <button
                    className="btn btn-ghost text-xs"
                    type="button"
                    onClick={() =>
                      void api
                        .updateDelivery(d.id, {
                          status: d.status === "pending" ? "in_transit" : "delivered",
                        })
                        .then(load)
                    }
                  >
                    {bn ? "আপডেট" : "Advance"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

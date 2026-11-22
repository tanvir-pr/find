"use client";

import { useEffect, useState } from "react";
import { api, money } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { Customer } from "@/lib/types";

export default function CustomersPage() {
  const { t } = useI18n();
  const [area, setArea] = useState("");
  const [items, setItems] = useState<Customer[]>([]);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState<string | null>(null);

  async function load(filter = area) {
    setError("");
    try {
      setItems(await api.customers(filter || undefined));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.failed"));
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function toggleOffer(customer: Customer) {
    setSaving(customer.id);
    try {
      const updated = await api.updateCustomer(customer.id, {
        offer_opt_in: !customer.offer_opt_in,
      });
      setItems((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("customers.updateFailed"));
    } finally {
      setSaving(null);
    }
  }

  return (
    <div className="fade-up space-y-5">
      <header>
        <h1 className="text-3xl">{t("customers.title")}</h1>
        <p className="mt-1 text-sm opacity-70">{t("customers.subtitle")}</p>
      </header>

      <form
        className="panel flex flex-col gap-3 p-4 sm:flex-row"
        onSubmit={(e) => {
          e.preventDefault();
          void load();
        }}
      >
        <input
          className="field"
          value={area}
          onChange={(e) => setArea(e.target.value)}
          placeholder={t("customers.areaPlaceholder")}
        />
        <button className="btn btn-primary" type="submit">
          {t("customers.filter")}
        </button>
        <button
          className="btn btn-ghost"
          type="button"
          onClick={() => {
            setArea("");
            void load("");
          }}
        >
          {t("customers.clear")}
        </button>
      </form>

      {error ? <p className="text-[var(--coral)]">{error}</p> : null}

      <div className="panel overflow-x-auto p-2">
        <table className="table">
          <thead>
            <tr>
              <th>{t("dash.name")}</th>
              <th>{t("customers.phone")}</th>
              <th>{t("customers.area")}</th>
              <th>{t("customers.due")}</th>
              <th>{t("customers.limit")}</th>
              <th>{t("customers.offers")}</th>
            </tr>
          </thead>
          <tbody>
            {items.map((c) => (
              <tr key={c.id}>
                <td>{c.name}</td>
                <td>{c.phone}</td>
                <td>{c.area || "—"}</td>
                <td className={Number(c.current_due) > 0 ? "text-[var(--coral)]" : ""}>
                  {money(c.current_due)}
                </td>
                <td>{money(c.credit_limit)}</td>
                <td>
                  <button
                    className="btn btn-ghost text-sm"
                    type="button"
                    disabled={saving === c.id}
                    onClick={() => void toggleOffer(c)}
                  >
                    {c.offer_opt_in ? t("customers.optedIn") : t("customers.optIn")}
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

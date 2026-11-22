"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { LanguageSwitch, useI18n } from "@/lib/i18n";

export default function LoginPage() {
  const { user, loading, login } = useAuth();
  const { t } = useI18n();
  const router = useRouter();
  const [email, setEmail] = useState("admin@dokan.example");
  const [password, setPassword] = useState("Admin123!");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!loading && user) router.replace("/dashboard");
  }, [loading, user, router]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email.trim(), password);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("login.failed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="relative min-h-screen overflow-hidden">
      <div
        className="absolute inset-0 opacity-40"
        style={{
          backgroundImage:
            "linear-gradient(rgba(11,31,42,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(11,31,42,0.04) 1px, transparent 1px)",
          backgroundSize: "28px 28px",
        }}
      />
      <div className="absolute right-4 top-4 z-10 md:right-8 md:top-8">
        <LanguageSwitch />
      </div>
      <div className="relative mx-auto flex min-h-screen max-w-6xl flex-col justify-center gap-10 px-5 py-12 md:flex-row md:items-center md:gap-16">
        <section className="fade-up max-w-xl flex-1">
          <p className="mb-3 inline-flex items-center gap-2 text-sm font-semibold tracking-wide text-[var(--teal)]">
            <span className="pulse-dot" /> {t("login.badge")}
          </p>
          <h1 className="brand text-5xl leading-tight md:text-6xl">Dokan Assistant</h1>
          <p className="mt-4 max-w-md text-base leading-relaxed text-[var(--ink-soft)]/80">
            {t("login.tagline")}
          </p>
        </section>

        <form
          onSubmit={onSubmit}
          className="panel fade-up w-full max-w-md flex-1 p-7 md:p-8"
          style={{ animationDelay: "0.08s" }}
        >
          <h2 className="text-2xl">{t("login.title")}</h2>
          <p className="mt-1 text-sm opacity-70">{t("login.subtitle")}</p>

          <label className="mt-6 block text-sm font-medium">
            {t("login.email")}
            <input
              className="field mt-2"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="username"
            />
          </label>

          <label className="mt-4 block text-sm font-medium">
            {t("login.password")}
            <input
              className="field mt-2"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </label>

          {error ? (
            <p className="mt-4 rounded-xl bg-[rgba(196,92,62,0.12)] px-3 py-2 text-sm text-[var(--coral)]">
              {error}
            </p>
          ) : null}

          <button className="btn btn-primary mt-6 w-full" type="submit" disabled={busy}>
            {busy ? t("login.submitting") : t("login.submit")}
          </button>

          <p className="mt-4 text-xs leading-relaxed opacity-60">{t("login.hint")}</p>
        </form>
      </div>
    </main>
  );
}

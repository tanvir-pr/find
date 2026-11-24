"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { LanguageSwitch, useI18n } from "@/lib/i18n";
import { ThemeSwitch } from "@/lib/theme";
import { Alert } from "@/components/ui";

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
    <main className="min-h-screen bg-[var(--canvas)]">
      <div className="absolute right-4 top-4 flex items-center gap-2 md:right-6 md:top-6">
        <ThemeSwitch />
        <LanguageSwitch />
      </div>

      <div className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-5 py-10">
        <div className="mb-8">
          <p className="brand text-2xl">Dokan</p>
          <p className="mt-1 text-sm text-[var(--muted)]">{t("login.tagline")}</p>
        </div>

        <form onSubmit={onSubmit} className="panel p-6">
          <h1 className="text-lg font-semibold">{t("login.title")}</h1>
          <p className="mt-1 text-sm text-[var(--muted)]">{t("login.subtitle")}</p>

          <label className="field-label mt-5">
            {t("login.email")}
            <input
              className="field mt-1.5"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="username"
            />
          </label>

          <label className="field-label mt-3">
            {t("login.password")}
            <input
              className="field mt-1.5"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </label>

          {error ? (
            <div className="mt-3">
              <Alert>{error}</Alert>
            </div>
          ) : null}

          <button className="btn btn-primary mt-5 w-full" type="submit" disabled={busy}>
            {busy ? t("login.submitting") : t("login.submit")}
          </button>

          <p className="mt-3 text-xs text-[var(--muted)]">{t("login.hint")}</p>
        </form>
      </div>
    </main>
  );
}

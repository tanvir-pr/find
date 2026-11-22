"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth";
import { LanguageSwitch, useI18n, type MsgKey } from "@/lib/i18n";

const NAV: { href: string; labelKey: MsgKey }[] = [
  { href: "/dashboard", labelKey: "nav.dashboard" },
  { href: "/products", labelKey: "nav.products" },
  { href: "/pos", labelKey: "nav.pos" },
  { href: "/sales", labelKey: "nav.sales" },
  { href: "/customers", labelKey: "nav.customers" },
  { href: "/stock", labelKey: "nav.stock" },
  { href: "/chat", labelKey: "nav.chat" },
];

export function PortalShell({ children }: { children: React.ReactNode }) {
  const { user, loading, logout } = useAuth();
  const { t } = useI18n();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  if (loading || !user) {
    return (
      <main className="grid min-h-screen place-items-center">
        <p className="text-sm opacity-70">{t("nav.checkingSession")}</p>
      </main>
    );
  }

  return (
    <div className="min-h-screen md:grid md:grid-cols-[240px_1fr]">
      <aside className="border-b border-[var(--line)] bg-[rgba(11,31,42,0.92)] text-[var(--sand)] md:min-h-screen md:border-b-0 md:border-r">
        <div className="px-5 py-5">
          <Link href="/dashboard" className="brand text-2xl text-white">
            Dokan
          </Link>
          <p className="mt-1 text-xs opacity-70">
            {user.name} · {user.role}
          </p>
          <LanguageSwitch className="mt-3" tone="dark" />
        </div>
        <nav className="flex gap-1 overflow-x-auto px-3 pb-4 md:flex-col md:overflow-visible">
          {NAV.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`whitespace-nowrap rounded-xl px-3 py-2 text-sm transition ${
                  active
                    ? "bg-[var(--teal)] text-white"
                    : "text-white/75 hover:bg-white/10 hover:text-white"
                }`}
              >
                {t(item.labelKey)}
              </Link>
            );
          })}
        </nav>
        <div className="hidden px-4 pb-6 md:block">
          <button className="btn btn-ghost w-full border-white/20 text-white" onClick={logout}>
            {t("nav.signOut")}
          </button>
        </div>
      </aside>
      <div className="px-4 py-5 md:px-8 md:py-7">
        <div className="mb-4 flex items-center justify-between gap-3 md:hidden">
          <p className="truncate text-sm opacity-70">{user.email}</p>
          <div className="flex items-center gap-2">
            <LanguageSwitch />
            <button className="btn btn-ghost text-sm" onClick={logout}>
              {t("nav.signOut")}
            </button>
          </div>
        </div>
        {children}
      </div>
    </div>
  );
}

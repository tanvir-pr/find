"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { useAuth } from "@/lib/auth";
import { LanguageSwitch, useI18n } from "@/lib/i18n";
import { ThemeSwitch } from "@/lib/theme";
import { flushOfflineQueue, getOfflineQueue } from "@/lib/offline";

type NavItem = { href: string; en: string; bn: string };

const GROUPS: { en: string; bn: string; items: NavItem[] }[] = [
  {
    en: "Sell",
    bn: "বিক্রি",
    items: [
      { href: "/dashboard", en: "Dashboard", bn: "ড্যাশবোর্ড" },
      { href: "/pos", en: "Quick sale", bn: "দ্রুত বিক্রি" },
      { href: "/sales", en: "Sales", bn: "বিক্রি" },
      { href: "/returns", en: "Returns", bn: "রিটার্ন" },
    ],
  },
  {
    en: "Stock",
    bn: "স্টক",
    items: [
      { href: "/products", en: "Products", bn: "পণ্য" },
      { href: "/purchases", en: "Purchases", bn: "কেনা" },
      { href: "/suppliers", en: "Suppliers", bn: "সাপ্লায়ার" },
      { href: "/stock", en: "Stock count", bn: "স্টক গণনা" },
    ],
  },
  {
    en: "People",
    bn: "মানুষ",
    items: [
      { href: "/customers", en: "Customers", bn: "কাস্টমার" },
      { href: "/shifts", en: "Shifts", bn: "শিফট" },
      { href: "/commissions", en: "Commission", bn: "কমিশন" },
    ],
  },
  {
    en: "More",
    bn: "আরও",
    items: [
      { href: "/insights", en: "Insights", bn: "ইনসাইট" },
      { href: "/logistics", en: "Vans", bn: "ভ্যান" },
      { href: "/ops", en: "SMS / Import", bn: "SMS / ইমপোর্ট" },
      { href: "/automation", en: "AI Actions", bn: "AI অ্যাকশন" },
      { href: "/chat", en: "AI helper", bn: "AI সহায়ক" },
    ],
  },
];

export function PortalShell({ children }: { children: ReactNode }) {
  const { user, loading, logout } = useAuth();
  const { lang, t } = useI18n();
  const pathname = usePathname();
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [queued, setQueued] = useState(0);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  useEffect(() => {
    const sync = () => {
      setQueued(getOfflineQueue().length);
      void flushOfflineQueue()
        .then(() => setQueued(getOfflineQueue().length))
        .catch(() => undefined);
    };
    sync();
    window.addEventListener("online", sync);
    return () => window.removeEventListener("online", sync);
  }, []);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  if (loading || !user) {
    return (
      <main className="grid min-h-screen place-items-center">
        <p className="text-sm text-[var(--muted)]">{t("nav.checkingSession")}</p>
      </main>
    );
  }

  const nav = (
    <>
      <div className="border-b border-[var(--sidebar-border)] px-4 py-4">
        <Link href="/dashboard" className="brand text-lg text-[var(--sidebar-text)]">
          Dokan
        </Link>
        <div className="shell-user-card mt-3">
          <p className="text-sm font-medium text-[var(--sidebar-text)]">{user.name}</p>
          <p className="text-xs capitalize text-[var(--sidebar-muted)]">{user.role}</p>
        </div>
        {queued > 0 ? (
          <p className="mt-2 text-xs font-medium text-[var(--warn)]">Offline queue: {queued}</p>
        ) : null}
        <div className="mt-3 flex flex-wrap gap-2">
          <LanguageSwitch />
          <ThemeSwitch />
        </div>
      </div>

      <nav className="flex-1 space-y-4 overflow-y-auto px-2 py-3">
        {GROUPS.map((group) => (
          <div key={group.en}>
            <p className="shell-section-label mb-1 px-2 text-[0.7rem] font-medium uppercase tracking-wide">
              {lang === "bn" ? group.bn : group.en}
            </p>
            <div className="space-y-0.5">
              {group.items.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="nav-link"
                  data-active={pathname === item.href}
                >
                  {lang === "bn" ? item.bn : item.en}
                </Link>
              ))}
            </div>
          </div>
        ))}
      </nav>

      <div className="border-t border-[var(--sidebar-border)] p-3">
        <button className="btn btn-ghost w-full" onClick={logout} type="button">
          {t("nav.signOut")}
        </button>
      </div>
    </>
  );

  return (
    <div className="min-h-screen md:grid md:grid-cols-[220px_1fr]">
      <aside className="shell-aside hidden flex-col md:flex">{nav}</aside>

      {mobileOpen ? (
        <div className="fixed inset-0 z-40 md:hidden">
          <button
            type="button"
            className="shell-backdrop absolute inset-0"
            aria-label="Close menu"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="shell-aside-mobile relative z-10 flex h-full w-[min(82vw,250px)] flex-col">
            {nav}
          </aside>
        </div>
      ) : null}

      <div className="flex min-w-0 flex-col">
        <div className="shell-topbar flex items-center justify-between gap-3 px-3 py-2.5 md:hidden">
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => setMobileOpen(true)}>
            Menu
          </button>
          <Link href="/dashboard" className="brand text-base">
            Dokan
          </Link>
          <div className="flex items-center gap-2">
            <ThemeSwitch />
            <LanguageSwitch />
            <button className="btn btn-ghost btn-sm" onClick={logout} type="button">
              {t("nav.signOut")}
            </button>
          </div>
        </div>
        <div className="mx-auto w-full max-w-[1120px] flex-1 px-4 py-5 md:px-7 md:py-6">{children}</div>
      </div>
    </div>
  );
}

"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type Lang = "en" | "bn";

const STORAGE_KEY = "dokan_lang";

const dict = {
  en: {
    // nav
    "nav.dashboard": "Dashboard",
    "nav.products": "Products",
    "nav.pos": "Quick sale",
    "nav.sales": "Sales",
    "nav.customers": "Customers",
    "nav.stock": "Stock count",
    "nav.chat": "AI chat",
    "nav.signOut": "Sign out",
    "nav.checkingSession": "Checking session…",

    // login
    "login.badge": "Shop portal",
    "login.tagline": "Admin and manager access for sales, stock, and shop help.",
    "login.title": "Sign in",
    "login.subtitle": "Admin or manager account.",
    "login.email": "Email",
    "login.password": "Password",
    "login.submit": "Sign in",
    "login.submitting": "Signing in…",
    "login.hint": "Demo: admin@dokan.example / Admin123!",
    "login.failed": "Login failed",

    // dashboard
    "dash.title": "Dashboard",
    "dash.subtitle": "Today’s sales, low stock, and near-expiry items.",
    "dash.todaySales": "Today sales",
    "dash.todayProfit": "Today profit (est.)",
    "dash.billsToday": "Bills today",
    "dash.monthSales": "Month sales",
    "dash.paymentMix": "Payment mix (today)",
    "dash.staffToday": "Staff today",
    "dash.name": "Name",
    "dash.bills": "Bills",
    "dash.total": "Total",
    "dash.noSales": "No sales yet today",
    "dash.lowStock": "Low stock",
    "dash.allGood": "All good",
    "dash.expiring": "Expiring ≤ 30 days",
    "dash.noneSoon": "None soon",
    "dash.loadFailed": "Failed to load dashboard",
    "pay.cash": "Cash",
    "pay.bkash": "bKash",
    "pay.nagad": "Nagad",
    "pay.credit": "Credit",

    // products
    "products.title": "Products",
    "products.subtitle": "Search by name or barcode for stock and prices.",
    "products.nameBarcode": "Name / barcode",
    "products.placeholder": "e.g. School Bag, Ball Pen Red",
    "products.lowOnly": "Low stock only",
    "products.search": "Search",
    "products.searching": "Searching…",
    "products.count": "{n} products",
    "products.product": "Product",
    "products.variant": "Variant",
    "products.barcode": "Barcode",
    "products.stock": "Stock",
    "products.retail": "Retail",
    "products.dealer": "Dealer",

    // pos
    "pos.title": "Quick sale",
    "pos.subtitle": "Find a product, add to cart, set qty, then complete the sale.",
    "pos.searchPlaceholder": "Name or barcode — e.g. School Bag",
    "pos.find": "Find",
    "pos.add": "Add",
    "pos.noBarcode": "no barcode",
    "pos.stock": "stock",
    "pos.cart": "Cart",
    "pos.empty": "Nothing added yet",
    "pos.payment": "Payment",
    "pos.txnId": "Txn id",
    "pos.complete": "Complete sale",
    "pos.saving": "Saving…",
    "pos.saleSaved": "Sale saved · bill {bill} · {total}",
    "pos.searchFailed": "Search failed",
    "pos.saleFailed": "Sale failed",
    "pos.categories": "Categories",
    "pos.invoiceContact": "Invoice contact",
    "pos.printInvoice": "Print invoice",

    // sales
    "sales.title": "Sales & receipts",
    "sales.subtitle": "Find a bill and reprint the receipt.",
    "sales.billPlaceholder": "Bill no — e.g. TODAY-20261122-0001",
    "sales.lookup": "Lookup",
    "sales.recent": "Recent sales",
    "sales.bill": "Bill",
    "sales.when": "When",
    "sales.receipt": "Receipt",
    "sales.selectBill": "Select or lookup a bill",
    "sales.logCopy": "Log receipt copy",
    "sales.print": "Print",
    "sales.notFound": "Not found",
    "sales.receiptFailed": "Receipt failed",

    // customers
    "customers.title": "Customers",
    "customers.subtitle": "Customers by area, dues and offer opt-in.",
    "customers.areaPlaceholder": "Area — e.g. Mirpur, Dhanmondi",
    "customers.filter": "Filter",
    "customers.clear": "Clear",
    "customers.phone": "Phone",
    "customers.area": "Area",
    "customers.due": "Due",
    "customers.limit": "Limit",
    "customers.offers": "Offers",
    "customers.optedIn": "Opted in ✓",
    "customers.optIn": "Opt in",
    "customers.updateFailed": "Update failed",

    // stock
    "stock.title": "Stock count",
    "stock.subtitle": "Count shelf stock and match it with the system.",
    "stock.apply": "Apply stock adjustments for differences",
    "stock.system": "System",
    "stock.counted": "Counted",
    "stock.diff": "Diff",
    "stock.save": "Save stock count",
    "stock.saving": "Saving…",
    "stock.saved": "Count saved{adj}. Lines: {n}",
    "stock.withAdj": " with adjustments",
    "stock.failed": "Count failed",

    // chat
    "chat.title": "AI shop helper",
    "chat.subtitle": "Ask about stock, sales, dues and shop rules.",
    "chat.empty": "Ask about stock, sales, dues, or store policy.",
    "chat.tools": "Tools",
    "chat.thinking": "Thinking…",
    "chat.placeholder": "Type in Bangla or English…",
    "chat.send": "Send",
    "chat.failed": "Chat failed",
    "chat.s1": "How much did we sell today?",
    "chat.s2": "What is low stock?",
    "chat.s3": "Can we take back a duplicate pen?",
    "chat.s4": "How much does Karim owe?",
    "chat.s5": "What is selling this month?",

    "common.failed": "Failed",
  },
  bn: {
    "nav.dashboard": "ড্যাশবোর্ড",
    "nav.products": "পণ্য",
    "nav.pos": "দ্রুত বিক্রি",
    "nav.sales": "বিক্রি",
    "nav.customers": "কাস্টমার",
    "nav.stock": "স্টক গণনা",
    "nav.chat": "AI চ্যাট",
    "nav.signOut": "সাইন আউট",
    "nav.checkingSession": "সেশন চেক হচ্ছে…",

    "login.badge": "শপ পোর্টাল",
    "login.tagline": "বিক্রি, স্টক ও দোকানের কাজের জন্য অ্যাডমিন/ম্যানেজার লগইন।",
    "login.title": "সাইন ইন",
    "login.subtitle": "অ্যাডমিন বা ম্যানেজার অ্যাকাউন্ট।",
    "login.email": "ইমেইল",
    "login.password": "পাসওয়ার্ড",
    "login.submit": "সাইন ইন",
    "login.submitting": "সাইন ইন হচ্ছে…",
    "login.hint": "ডেমো: admin@dokan.example / Admin123!",
    "login.failed": "লগইন ব্যর্থ",

    "dash.title": "ড্যাশবোর্ড",
    "dash.subtitle": "আজকের বিক্রি, লো স্টক ও মেয়াদ শেষের আইটেম।",
    "dash.todaySales": "আজকের বিক্রি",
    "dash.todayProfit": "আজকের লাভ (আনুমানিক)",
    "dash.billsToday": "আজকের বিল",
    "dash.monthSales": "মাসের বিক্রি",
    "dash.paymentMix": "পেমেন্ট ভাগ (আজ)",
    "dash.staffToday": "আজকের স্টাফ",
    "dash.name": "নাম",
    "dash.bills": "বিল",
    "dash.total": "মোট",
    "dash.noSales": "আজ এখনো বিক্রি নেই",
    "dash.lowStock": "লো স্টক",
    "dash.allGood": "সব ঠিক আছে",
    "dash.expiring": "৩০ দিনের মধ্যে মেয়াদ",
    "dash.noneSoon": "কাছাকাছি নেই",
    "dash.loadFailed": "ড্যাশবোর্ড লোড হয়নি",
    "pay.cash": "ক্যাশ",
    "pay.bkash": "বিকাশ",
    "pay.nagad": "নগদ",
    "pay.credit": "বাকি",

    "products.title": "পণ্য",
    "products.subtitle": "নাম বা বারকোড দিয়ে স্টক ও দাম দেখুন।",
    "products.nameBarcode": "নাম / বারকোড",
    "products.placeholder": "যেমন: School Bag, Ball Pen Red",
    "products.lowOnly": "শুধু লো স্টক",
    "products.search": "খুঁজুন",
    "products.searching": "খোঁজা হচ্ছে…",
    "products.count": "{n}টি পণ্য",
    "products.product": "পণ্য",
    "products.variant": "ভ্যারিয়েন্ট",
    "products.barcode": "বারকোড",
    "products.stock": "স্টক",
    "products.retail": "রিটেইল",
    "products.dealer": "ডিলার",

    "pos.title": "দ্রুত বিক্রি",
    "pos.subtitle": "পণ্য খুঁজে কার্টে যোগ করুন, পরিমাণ ঠিক করে বিক্রি সম্পন্ন করুন।",
    "pos.searchPlaceholder": "নাম বা বারকোড — যেমন School Bag",
    "pos.find": "খুঁজুন",
    "pos.add": "যোগ",
    "pos.noBarcode": "বারকোড নেই",
    "pos.stock": "স্টক",
    "pos.cart": "কার্ট",
    "pos.empty": "এখনো কিছু যোগ হয়নি",
    "pos.payment": "পেমেন্ট",
    "pos.txnId": "ট্রানজেকশন আইডি",
    "pos.complete": "বিক্রি সম্পন্ন",
    "pos.saving": "সেভ হচ্ছে…",
    "pos.saleSaved": "বিক্রি হয়েছে · বিল {bill} · {total}",
    "pos.searchFailed": "খোঁজা যায়নি",
    "pos.saleFailed": "বিক্রি হয়নি",
    "pos.categories": "ক্যাটাগরি",
    "pos.invoiceContact": "ইনভয়েস যোগাযোগ",
    "pos.printInvoice": "ইনভয়েস প্রিন্ট",

    "sales.title": "বিক্রি ও রসিদ",
    "sales.subtitle": "বিল খুঁজে রসিদ আবার প্রিন্ট করুন।",
    "sales.billPlaceholder": "বিল নম্বর — যেমন TODAY-20261122-0001",
    "sales.lookup": "খুঁজুন",
    "sales.recent": "সাম্প্রতিক বিক্রি",
    "sales.bill": "বিল",
    "sales.when": "সময়",
    "sales.receipt": "রসিদ",
    "sales.selectBill": "একটি বিল বেছে নিন বা খুঁজুন",
    "sales.logCopy": "রসিদ কপি লগ",
    "sales.print": "প্রিন্ট",
    "sales.notFound": "পাওয়া যায়নি",
    "sales.receiptFailed": "রসিদ পাওয়া যায়নি",

    "customers.title": "কাস্টমার",
    "customers.subtitle": "এলাকা অনুযায়ী কাস্টমার, বাকি হিসাব ও অফার অপ্ট-ইন।",
    "customers.areaPlaceholder": "এলাকা — যেমন Mirpur, Dhanmondi",
    "customers.filter": "ফিল্টার",
    "customers.clear": "মুছুন",
    "customers.phone": "ফোন",
    "customers.area": "এলাকা",
    "customers.due": "বাকি",
    "customers.limit": "লিমিট",
    "customers.offers": "অফার",
    "customers.optedIn": "অপ্ট-ইন ✓",
    "customers.optIn": "অপ্ট-ইন",
    "customers.updateFailed": "আপডেট হয়নি",

    "stock.title": "স্টক গণনা",
    "stock.subtitle": "শেলফে গণনা করে সিস্টেম স্টকের সাথে মিলিয়ে নিন।",
    "stock.apply": "পার্থক্য থাকলে স্টক অ্যাডজাস্টমেন্ট প্রয়োগ করুন",
    "stock.system": "সিস্টেম",
    "stock.counted": "গণনা",
    "stock.diff": "পার্থক্য",
    "stock.save": "স্টক গণনা সেভ",
    "stock.saving": "সেভ হচ্ছে…",
    "stock.saved": "গণনা সেভ হয়েছে{adj}। লাইন: {n}",
    "stock.withAdj": " (অ্যাডজাস্টমেন্টসহ)",
    "stock.failed": "গণনা সেভ হয়নি",

    "chat.title": "AI শপ হেল্পার",
    "chat.subtitle": "স্টক, বিক্রি, বাকি ও দোকানের নিয়ম নিয়ে প্রশ্ন করুন।",
    "chat.empty": "স্টক, বিক্রি, বাকি বা পলিসি নিয়ে জিজ্ঞাসা করুন।",
    "chat.tools": "টুল",
    "chat.thinking": "ভাবছি…",
    "chat.placeholder": "বাংলা বা ইংরেজিতে লিখুন…",
    "chat.send": "পাঠান",
    "chat.failed": "চ্যাট ব্যর্থ",
    "chat.s1": "আজ কত বিক্রি হলো?",
    "chat.s2": "কী কী লো স্টক?",
    "chat.s3": "ডুপ্লিকেট কলম কি ফেরত নেওয়া যায়?",
    "chat.s4": "করিম সাহেবের বাকি কত?",
    "chat.s5": "এই মাসে কী বেশি বিক্রি হচ্ছে?",

    "common.failed": "ব্যর্থ",
  },
} as const;

export type MsgKey = keyof typeof dict.en;

type I18nState = {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: (key: MsgKey, vars?: Record<string, string | number>) => string;
};

const I18nContext = createContext<I18nState | null>(null);

function format(template: string, vars?: Record<string, string | number>) {
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (_, key: string) => String(vars[key] ?? ""));
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>("bn");

  useEffect(() => {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (saved === "en" || saved === "bn") setLangState(saved);
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang === "bn" ? "bn" : "en";
  }, [lang]);

  const setLang = useCallback((next: Lang) => {
    setLangState(next);
    window.localStorage.setItem(STORAGE_KEY, next);
  }, []);

  const t = useCallback(
    (key: MsgKey, vars?: Record<string, string | number>) =>
      format(dict[lang][key] ?? dict.en[key] ?? key, vars),
    [lang],
  );

  const value = useMemo(() => ({ lang, setLang, t }), [lang, setLang, t]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used within LanguageProvider");
  return ctx;
}

export function LanguageSwitch({
  className = "",
  tone = "light",
}: {
  className?: string;
  tone?: "light" | "dark";
}) {
  const { lang, setLang } = useI18n();
  const shell =
    tone === "dark" ? "border-white/20 bg-transparent" : "border-[var(--line-strong)] bg-[var(--surface)]";
  const active =
    tone === "dark" ? "bg-white text-[var(--ink)]" : "bg-[var(--ink)] text-white";
  const idle =
    tone === "dark" ? "text-white/70 hover:bg-white/10" : "text-[var(--muted)] hover:bg-[var(--surface-2)]";

  return (
    <div
      className={`inline-flex border text-xs font-medium ${shell} ${className}`}
      role="group"
      aria-label="Language"
    >
      <button
        type="button"
        className={`px-2 py-1 ${lang === "en" ? active : idle}`}
        onClick={() => setLang("en")}
      >
        EN
      </button>
      <button
        type="button"
        className={`px-2 py-1 ${lang === "bn" ? active : idle}`}
        onClick={() => setLang("bn")}
      >
        বাং
      </button>
    </div>
  );
}

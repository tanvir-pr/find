import type {
  AgentAction,
  AutomationScanResult,
  AutomationSettings,
  Branch,
  ChatResponse,
  ChatTurn,
  Customer,
  CustomerHistoryItem,
  Delivery,
  ExpiringItem,
  LowStockItem,
  Product,
  Purchase,
  Sale,
  SalesSummary,
  Shift,
  ShiftSummary,
  Supplier,
  User,
  Van,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") || "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("dokan_token");
}

export function setToken(value: string | null) {
  if (typeof window === "undefined") return;
  if (value) localStorage.setItem("dokan_token", value);
  else localStorage.removeItem("dokan_token");
}

async function readError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail)) {
      return data.detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join(", ");
    }
    return data.message || res.statusText;
  } catch {
    return res.statusText || "Request failed";
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  auth = true,
): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (auth) {
    const t = getToken();
    if (t) headers.set("Authorization", `Bearer ${t}`);
  }
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    throw new ApiError(res.status, await readError(res));
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string; token_type: string }>(
      "/api/v1/auth/login",
      { method: "POST", body: JSON.stringify({ email, password }) },
      false,
    ),

  me: () => request<User>("/api/v1/auth/me"),

  salesSummary: (from: string, to: string) =>
    request<SalesSummary>(
      `/api/v1/reports/sales-summary?from_date=${from}&to_date=${to}`,
    ),

  lowStock: () => request<LowStockItem[]>("/api/v1/reports/low-stock"),

  expiring: (withinDays = 30) =>
    request<ExpiringItem[]>(`/api/v1/reports/expiring?within_days=${withinDays}`),

  reorder: (coverDays = 14) =>
    request<{ suggestions: Record<string, unknown>[] }>(
      `/api/v1/reports/reorder?cover_days=${coverDays}`,
    ),

  seasonal: (season = "winter_start") =>
    request<{ items: Record<string, unknown>[] }>(
      `/api/v1/reports/seasonal?season=${encodeURIComponent(season)}`,
    ),

  products: (q?: string, lowStock?: boolean, category?: string, pageSize = 100) => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (lowStock) params.set("low_stock", "true");
    if (category) params.set("category", category);
    params.set("page_size", String(pageSize));
    return request<{ items: Product[]; total: number }>(
      `/api/v1/products?${params.toString()}`,
    );
  },

  productCategories: () =>
    request<{ categories: string[] }>("/api/v1/products/meta/categories"),

  customers: (area?: string) => {
    const q = area ? `?area=${encodeURIComponent(area)}` : "";
    return request<Customer[]>(`/api/v1/customers${q}`);
  },

  lookupCustomer: (phone?: string, email?: string) => {
    const params = new URLSearchParams();
    if (phone?.trim()) params.set("phone", phone.trim());
    if (email?.trim()) params.set("email", email.trim());
    return request<Customer | null>(`/api/v1/customers/lookup?${params.toString()}`);
  },

  updateCustomer: (id: string, body: Partial<Customer>) =>
    request<Customer>(`/api/v1/customers/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  customerHistory: (id: string) =>
    request<CustomerHistoryItem[]>(`/api/v1/customers/${id}/history`),

  collectDue: (id: string, body: unknown) =>
    request<Customer>(`/api/v1/customers/${id}/collections`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  dueReminders: () =>
    request("/api/v1/customers/due-reminders/run", { method: "POST" }),

  sales: (limit = 30) => request<Sale[]>(`/api/v1/sales?limit=${limit}`),

  saleByBill: (billNo: string) =>
    request<Sale>(`/api/v1/sales/by-bill/${encodeURIComponent(billNo)}`),

  reprintReceipt: (billNo: string) =>
    request<{ bill_no: string; payload: Record<string, unknown>; is_copy: boolean }>(
      `/api/v1/sales/by-bill/${encodeURIComponent(billNo)}/receipt`,
      { method: "POST" },
    ),

  createSale: (body: unknown) =>
    request<Sale>("/api/v1/sales", { method: "POST", body: JSON.stringify(body) }),

  createReturn: (body: unknown) =>
    request("/api/v1/returns", { method: "POST", body: JSON.stringify(body) }),

  createStockCount: (body: unknown) =>
    request("/api/v1/stock/counts", { method: "POST", body: JSON.stringify(body) }),

  suppliers: () => request<Supplier[]>("/api/v1/suppliers"),

  createSupplier: (body: unknown) =>
    request<Supplier>("/api/v1/suppliers", { method: "POST", body: JSON.stringify(body) }),

  paySupplier: (id: string, body: unknown) =>
    request(`/api/v1/suppliers/${id}/payments`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  purchases: () => request<Purchase[]>("/api/v1/purchases"),

  createPurchase: (body: unknown) =>
    request<Purchase>("/api/v1/purchases", { method: "POST", body: JSON.stringify(body) }),

  openShift: (openingCash: string) =>
    request<Shift>("/api/v1/shifts/open", {
      method: "POST",
      body: JSON.stringify({ opening_cash: openingCash }),
    }),

  myOpenShift: () => request<Shift | null>("/api/v1/shifts/mine/open"),

  shiftSummary: (id: string) => request<ShiftSummary>(`/api/v1/shifts/${id}/summary`),

  closeShift: (id: string, countedCash: string, note?: string) =>
    request<Shift>(`/api/v1/shifts/${id}/close`, {
      method: "POST",
      body: JSON.stringify({ counted_cash: countedCash, note }),
    }),

  branches: () => request<Branch[]>("/api/v1/branches"),

  vans: () => request<Van[]>("/api/v1/logistics/vans"),

  createVan: (body: unknown) =>
    request<Van>("/api/v1/logistics/vans", { method: "POST", body: JSON.stringify(body) }),

  deliveries: () => request<Delivery[]>("/api/v1/logistics/deliveries"),

  createDelivery: (body: unknown) =>
    request<Delivery>("/api/v1/logistics/deliveries", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  updateDelivery: (id: string, body: unknown) =>
    request<Delivery>(`/api/v1/logistics/deliveries/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  commissionRules: () => request("/api/v1/commissions/rules"),

  createCommissionRule: (body: unknown) =>
    request("/api/v1/commissions/rules", { method: "POST", body: JSON.stringify(body) }),

  commissionEntries: () => request("/api/v1/commissions/entries"),

  dailySms: (toPhone?: string) => {
    const q = toPhone ? `?to_phone=${encodeURIComponent(toPhone)}` : "";
    return request(`/api/v1/ops/sms/daily-summary${q}`, { method: "POST" });
  },

  sendOffers: (body: unknown) =>
    request("/api/v1/ops/sms/offers", { method: "POST", body: JSON.stringify(body) }),

  importCsv: (body: unknown) =>
    request<Purchase>("/api/v1/ops/purchases/import-csv", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  ocrInvoice: (body: unknown) =>
    request("/api/v1/ops/invoices/ocr", { method: "POST", body: JSON.stringify(body) }),

  syncSales: (body: unknown) =>
    request("/api/v1/sync/sales", { method: "POST", body: JSON.stringify(body) }),

  chat: (message: string, history: ChatTurn[]) => {
    const ctrl = new AbortController();
    const timer = window.setTimeout(() => ctrl.abort(), 90_000);
    return request<ChatResponse>("/api/v1/chat", {
      method: "POST",
      body: JSON.stringify({ message, history }),
      signal: ctrl.signal,
    }).finally(() => window.clearTimeout(timer));
  },

  automationSettings: () => request<AutomationSettings>("/api/v1/automation/settings"),

  updateAutomationSettings: (body: Partial<AutomationSettings>) =>
    request<AutomationSettings>("/api/v1/automation/settings", {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  automationActions: (status?: string) => {
    const q = status ? `?status=${encodeURIComponent(status)}` : "";
    return request<AgentAction[]>(`/api/v1/automation/actions${q}`);
  },

  automationScan: () =>
    request<AutomationScanResult>("/api/v1/automation/scan", { method: "POST" }),

  approveAction: (id: string) =>
    request<AgentAction>(`/api/v1/automation/actions/${id}/approve`, { method: "POST" }),

  rejectAction: (id: string) =>
    request<AgentAction>(`/api/v1/automation/actions/${id}/reject`, { method: "POST" }),
};

export function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

export function monthStartISO() {
  const d = new Date();
  return new Date(d.getFullYear(), d.getMonth(), 1).toISOString().slice(0, 10);
}

export function money(v: string | number | undefined) {
  const n = Number(v || 0);
  return `৳${n.toLocaleString("en-BD", { maximumFractionDigits: 2 })}`;
}

export function deviceId() {
  if (typeof window === "undefined") return "server";
  const key = "dokan_device_id";
  let id = localStorage.getItem(key);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(key, id);
  }
  return id;
}

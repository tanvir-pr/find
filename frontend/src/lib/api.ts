import type {
  ChatResponse,
  ChatTurn,
  Customer,
  ExpiringItem,
  LowStockItem,
  Product,
  Sale,
  SalesSummary,
  User,
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
  if (!headers.has("Content-Type") && options.body) {
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

  products: (q?: string, lowStock?: boolean) => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (lowStock) params.set("low_stock", "true");
    params.set("page_size", "50");
    return request<{ items: Product[]; total: number }>(
      `/api/v1/products?${params.toString()}`,
    );
  },

  customers: (area?: string) => {
    const q = area ? `?area=${encodeURIComponent(area)}` : "";
    return request<Customer[]>(`/api/v1/customers${q}`);
  },

  updateCustomer: (id: string, body: Partial<Customer>) =>
    request<Customer>(`/api/v1/customers/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

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

  createStockCount: (body: unknown) =>
    request("/api/v1/stock/counts", { method: "POST", body: JSON.stringify(body) }),

  chat: (message: string, history: ChatTurn[]) =>
    request<ChatResponse>("/api/v1/chat", {
      method: "POST",
      body: JSON.stringify({ message, history }),
    }),
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

export type UserRole = "admin" | "manager" | "staff";

export type User = {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
};

export type SalesSummary = {
  from_date: string;
  to_date: string;
  total_sales: string;
  total_discount: string;
  total_points_discount: string;
  bill_count: number;
  cash: string;
  bkash: string;
  nagad: string;
  credit: string;
  estimated_profit: string;
  by_staff: {
    user_id: string;
    name: string;
    bill_count: number;
    total: string;
    points_discount?: string;
    points_redeemed?: number;
    bill_discount?: string;
  }[];
};

export type LowStockItem = {
  variant_id: string;
  product_name: string;
  variant_name: string;
  barcode: string | null;
  current_stock: string;
  low_stock_threshold: string;
};

export type ExpiringItem = {
  batch_id: string;
  variant_id: string;
  product_name: string;
  variant_name: string;
  expiry_date: string | null;
  remaining_qty: string;
};

export type Variant = {
  id: string;
  product_id: string;
  name: string;
  barcode: string | null;
  retail_price: string;
  dealer_price: string;
  low_stock_threshold: string;
  is_active: boolean;
  current_stock: string;
};

export type Product = {
  id: string;
  name: string;
  category: string | null;
  unit: string;
  tracks_expiry: boolean;
  is_active: boolean;
  variants: Variant[];
};

export type Customer = {
  id: string;
  name: string;
  phone: string;
  email: string;
  area: string | null;
  credit_limit: string;
  offer_opt_in: boolean;
  loyalty_points: number;
  current_due: string;
};

export type CustomerHistoryItem = {
  sale_id: string;
  bill_no: string;
  total: string;
  created_at: string;
};

export type InvoiceDelivery = {
  sms_sent: boolean;
  email_sent: boolean;
  phone: string | null;
  email: string | null;
  detail: string | null;
};

export type Sale = {
  id: string;
  bill_no: string;
  customer_id: string | null;
  user_id: string;
  subtotal: string;
  discount: string;
  points_discount?: string;
  points_redeemed?: number;
  total: string;
  created_at: string;
  items: {
    id: string;
    variant_id: string;
    qty: string;
    unit_price: string;
    discount: string;
  }[];
  payments: {
    id: string;
    method: string;
    amount: string;
    txn_id: string | null;
  }[];
  invoice_delivery?: InvoiceDelivery | null;
  loyalty?: {
    points_redeemed: number;
    points_earned: number;
    points_balance: number;
    points_discount: string;
  } | null;
};

export type Supplier = {
  id: string;
  name: string;
  phone: string | null;
  address: string | null;
  current_due: string;
};

export type Purchase = {
  id: string;
  supplier_id: string;
  invoice_no: string;
  invoice_date: string;
  total_amount: string;
  batches: {
    id: string;
    variant_id: string;
    initial_qty: string;
    cost_price: string;
    expiry_date: string | null;
  }[];
};

export type Shift = {
  id: string;
  user_id: string;
  opened_at: string;
  closed_at: string | null;
  opening_cash: string;
  cash_closing: {
    expected_cash: string;
    counted_cash: string;
    difference: string;
    note: string | null;
  } | null;
};

export type ShiftSummary = {
  shift_id: string;
  opening_cash: string;
  cash_sales: string;
  bkash_sales: string;
  nagad_sales: string;
  credit_sales: string;
  points_discount?: string;
  bill_discount?: string;
  expected_cash: string;
  bill_count: number;
};

export type Van = {
  id: string;
  name: string;
  plate_no: string | null;
  driver_name: string | null;
  is_active: boolean;
};

export type Delivery = {
  id: string;
  van_id: string;
  customer_id: string | null;
  sale_id: string | null;
  destination: string | null;
  status: string;
  note: string | null;
  created_at: string;
};

export type Branch = {
  id: string;
  name: string;
  code: string | null;
  address: string | null;
  phone: string | null;
  is_active: boolean;
};

export type ChatTurn = { role: "user" | "assistant"; content: string };

export type ChatResponse = {
  reply: string;
  tools_used: { name: string; arguments: Record<string, unknown>; result_preview: string }[];
  provider: string;
};

export type AutomationSettings = {
  autopilot_enabled: boolean;
  auto_due_reminders: boolean;
  auto_daily_sms: boolean;
  auto_low_stock_alerts: boolean;
  auto_expiring_alerts: boolean;
  auto_reorder_draft: boolean;
  owner_phone: string | null;
};

export type AgentAction = {
  id: string;
  kind: string;
  mode: "auto" | "approval" | string;
  status: string;
  title: string;
  summary: string;
  payload?: Record<string, unknown> | null;
  result?: Record<string, unknown> | null;
  error_message?: string | null;
  created_at: string;
  decided_at?: string | null;
  executed_at?: string | null;
};

export type AutomationScanResult = {
  created: AgentAction[];
  auto_executed: AgentAction[];
  message: string;
};

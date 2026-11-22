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
  bill_count: number;
  cash: string;
  bkash: string;
  nagad: string;
  credit: string;
  estimated_profit: string;
  by_staff: { user_id: string; name: string; bill_count: number; total: string }[];
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
  area: string | null;
  credit_limit: string;
  offer_opt_in: boolean;
  email: string | null;
  current_due: string;
};

export type Sale = {
  id: string;
  bill_no: string;
  customer_id: string | null;
  user_id: string;
  subtotal: string;
  discount: string;
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
};

export type ChatTurn = { role: "user" | "assistant"; content: string };

export type ChatResponse = {
  reply: string;
  tools_used: { name: string; arguments: Record<string, unknown>; result_preview: string }[];
  provider: string;
};

import { api, deviceId } from "./api";

const QUEUE_KEY = "dokan_offline_sales";

export type QueuedSale = {
  client_id: string;
  device_id: string;
  created_at: string;
  sale: Record<string, unknown>;
};

export function getOfflineQueue(): QueuedSale[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(QUEUE_KEY) || "[]") as QueuedSale[];
  } catch {
    return [];
  }
}

function saveQueue(items: QueuedSale[]) {
  localStorage.setItem(QUEUE_KEY, JSON.stringify(items));
}

export function enqueueOfflineSale(sale: Record<string, unknown>): QueuedSale {
  const item: QueuedSale = {
    client_id: crypto.randomUUID(),
    device_id: deviceId(),
    created_at: new Date().toISOString(),
    sale,
  };
  const q = getOfflineQueue();
  q.push(item);
  saveQueue(q);
  return item;
}

export async function flushOfflineQueue(): Promise<{ synced: number; failed: number }> {
  const q = getOfflineQueue();
  if (!q.length) return { synced: 0, failed: 0 };
  if (typeof navigator !== "undefined" && !navigator.onLine) {
    return { synced: 0, failed: q.length };
  }
  const res = await api.syncSales({
    device_id: deviceId(),
    items: q.map((item) => ({
      client_id: item.client_id,
      device_id: item.device_id,
      created_at: item.created_at,
      sale: item.sale,
    })),
  });
  const results = (res as { results: { client_id: string; status: string }[] }).results || [];
  const ok = new Set(
    results.filter((r) => r.status === "synced" || r.status === "already_synced").map((r) => r.client_id),
  );
  const remaining = q.filter((item) => !ok.has(item.client_id));
  saveQueue(remaining);
  return { synced: q.length - remaining.length, failed: remaining.length };
}

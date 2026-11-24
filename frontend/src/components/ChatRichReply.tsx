"use client";

import { useMemo } from "react";
import { useI18n } from "@/lib/i18n";

type ToolUsed = {
  name: string;
  arguments: Record<string, unknown>;
  result_preview: string;
};

const HIDDEN_KEYS = new Set([
  "found",
  "message",
  "distance",
  "chunk_index",
  "match",
  "meta",
  "error",
  "query",
  "variant_id",
  "product_id",
  "user_id",
  "batch_id",
  "id",
]);

function tryParseJson(raw: string): unknown | null {
  const text = raw.trim();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    const repaired = text.replace(/,\s*$/, "").replace(/,\s*[{\[]?$/, "");
    for (const candidate of [repaired + "}", repaired + "]}", repaired + '"]}']) {
      try {
        return JSON.parse(candidate);
      } catch {
        /* continue */
      }
    }
    const match = text.match(/\{[\s\S]*\}|\[[\s\S]*\]/);
    if (match) {
      try {
        return JSON.parse(match[0]);
      } catch {
        return null;
      }
    }
    return null;
  }
}

function extractJsonBlocks(text: string): { prose: string; blocks: unknown[] } {
  const blocks: unknown[] = [];
  let prose = text;
  const re = /(?:^|\n)([a-z_]+):\s*(\{[\s\S]*?\})(?=\n[a-z_]+:|\n*$)/gi;
  prose = prose.replace(re, (_full, _name: string, jsonPart: string) => {
    const parsed = tryParseJson(jsonPart);
    if (parsed) blocks.push(parsed);
    return "";
  });
  prose = prose.replace(/(\{[\s\S]*\}|\[[\s\S]*\])/g, (chunk) => {
    const parsed = tryParseJson(chunk);
    if (parsed) {
      blocks.push(parsed);
      return "";
    }
    return chunk;
  });
  prose = prose
    .replace(/টুল থেকে পাওয়া তথ্য:\s*/gi, "")
    .replace(/Tool results?:\s*/gi, "")
    .replace(/নিচের ডকুমেন্ট টুকরো থেকে উত্তর দিন[^\n]*/gi, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
  return { prose, blocks };
}

function toolTitle(name: string, bn: boolean): string {
  const map: Record<string, [string, string]> = {
    low_stock_list: ["Low stock", "লো স্টক"],
    check_stock: ["Stock", "স্টক"],
    expiring_items: ["Expiring soon", "মেয়াদ শেষ হচ্ছে"],
    sales_summary: ["Sales", "বিক্রি"],
    customer_due: ["Customer dues", "কাস্টমার বাকি"],
    search_policy: ["Store rules", "দোকানের নিয়ম"],
    seasonal_top_products: ["Seasonal top", "মৌসুমি টপ"],
    reorder_suggestion: ["Reorder ideas", "অর্ডার সাজেশন"],
  };
  const pair = map[name];
  if (!pair) return name.replace(/_/g, " ");
  return bn ? pair[1] : pair[0];
}

function asRows(data: unknown): Record<string, unknown>[] {
  if (!data || typeof data !== "object") return [];
  const obj = data as Record<string, unknown>;
  for (const key of ["items", "matches", "suggestions", "rows", "results", "customers", "hits"]) {
    if (Array.isArray(obj[key])) return obj[key] as Record<string, unknown>[];
  }
  if (Array.isArray(data)) return data as Record<string, unknown>[];
  return [];
}

function isPolicyPayload(data: unknown): boolean {
  if (!data || typeof data !== "object" || Array.isArray(data)) return false;
  const obj = data as Record<string, unknown>;
  return Array.isArray(obj.hits) || typeof obj.found === "boolean";
}

/** Strip markdown noise and keep one language section when possible. */
function cleanPolicyText(raw: string, preferBn: boolean): string {
  let text = raw.replace(/\r/g, "");
  // Prefer Bangla or English section if both exist
  const bnMatch = text.match(/##\s*Bangla\s*([\s\S]*?)(?=##\s*English|$)/i);
  const enMatch = text.match(/##\s*English\s*([\s\S]*?)$/i);
  if (preferBn && bnMatch?.[1]) text = bnMatch[1];
  else if (!preferBn && enMatch?.[1]) text = enMatch[1];
  else if (bnMatch?.[1] && enMatch?.[1]) text = preferBn ? bnMatch[1] : enMatch[1];

  return text
    .replace(/^#+\s*/gm, "")
    .replace(/\*\*/g, "")
    .replace(/^---+$/gm, "")
    .replace(/বিষয়:\s*\w+/gi, "")
    .replace(/Subject:\s*\w+/gi, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function extractFocusedAnswer(text: string, preferBn: boolean): string | null {
  const lines = text
    .split("\n")
    .map((l) => l.replace(/^[-*•]\s*/, "").trim())
    .filter(Boolean);

  const dup = lines.filter((l) => /ডুপ্লিকেট|duplicate/i.test(l));
  if (dup.length) {
    return preferBn
      ? dup.find((l) => /[\u0980-\u09FF]/.test(l)) || dup[0]
      : dup.find((l) => /[A-Za-z]/.test(l)) || dup[0];
  }
  return null;
}

function docLabel(name: unknown, bn: boolean): string {
  const raw = String(name || "").replace(/\.(md|txt)$/i, "");
  const map: Record<string, [string, string]> = {
    "01_return_policy": ["Return policy", "রিটার্ন পলিসি"],
    return_policy: ["Return policy", "রিটার্ন পলিসি"],
    "04_product_guide": ["Product guide", "পণ্য গাইড"],
    product_guide: ["Product guide", "পণ্য গাইড"],
    "02_credit_policy": ["Credit policy", "বাকি পলিসি"],
    "03_cash_closing": ["Cash closing", "ক্যাশ ক্লোজিং"],
  };
  const key = raw.toLowerCase();
  const hit = map[key] || map[raw];
  if (hit) return bn ? hit[1] : hit[0];
  return raw.replace(/^\d+_/, "").replace(/_/g, " ");
}

function PolicyCard({
  data,
  bn,
  userQuery,
}: {
  data: Record<string, unknown>;
  bn: boolean;
  userQuery?: string;
}) {
  const hits = Array.isArray(data.hits) ? (data.hits as Record<string, unknown>[]) : [];
  const found = data.found !== false && hits.length > 0;

  if (!found) {
    return (
      <div className="chat-data-card">
        <div className="chat-data-head">
          <h3>{bn ? "দোকানের নিয়ম" : "Store rules"}</h3>
        </div>
        <p className="px-3 py-3 text-sm leading-relaxed text-[var(--muted)]">
          {bn
            ? "এই বিষয়ে দোকানের ডকুমেন্টে স্পষ্ট তথ্য পাইনি। দরকার হলে মালিকের সাথে কথা বলুন।"
            : "No clear store document covered this. Please ask the owner if needed."}
        </p>
      </div>
    );
  }

  // Dedupe by document_name — keep richest chunk
  const byDoc = new Map<string, Record<string, unknown>>();
  for (const hit of hits) {
    const key = String(hit.document_name || hit.topic || Math.random());
    const prev = byDoc.get(key);
    const len = String(hit.text || "").length;
    if (!prev || len > String(prev.text || "").length) byDoc.set(key, hit);
  }
  const unique = [...byDoc.values()].slice(0, 3);

  const joined = unique.map((h) => cleanPolicyText(String(h.text || ""), bn)).join("\n");
  const focused =
    extractFocusedAnswer(joined, bn) ||
    (userQuery && /ডুপ্লিকেট|duplicate|ফেরত|return|take\s*back/i.test(userQuery)
      ? extractFocusedAnswer(joined, bn)
      : null);

  return (
    <div className="chat-data-card">
      <div className="chat-data-head">
        <h3>{bn ? "দোকানের নিয়ম" : "Store rules"}</h3>
      </div>

      {focused ? (
        <div className="border-b border-[var(--line)] px-3 py-3">
          <p className="text-sm font-semibold leading-relaxed text-[var(--ink)]">{focused}</p>
        </div>
      ) : null}

      <ul className="chat-data-list">
        {unique.map((hit, i) => {
          const body = cleanPolicyText(String(hit.text || ""), bn);
          // Keep answer short: max ~8 bullet-ish lines
          const short = body
            .split("\n")
            .map((l) => l.trim())
            .filter(Boolean)
            .filter((l) => !/^return policy/i.test(l) && !/^রিটার্ন/i.test(l))
            .slice(0, 8)
            .join("\n");
          return (
            <li key={i} className="!items-start !flex-col gap-1.5">
              <p className="chat-data-title">{docLabel(hit.document_name || hit.topic, bn)}</p>
              {short ? (
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-[var(--ink-soft)]">
                  {short}
                </p>
              ) : null}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function pickLabel(row: Record<string, unknown>): string {
  const parts = [row.product, row.product_name, row.name, row.variant, row.variant_name, row.title, row.bill_no]
    .filter(Boolean)
    .map(String);
  if (parts.length >= 2) return `${parts[0]} · ${parts[1]}`;
  if (parts.length === 1) return parts[0];
  return "Item";
}

function pickMeta(row: Record<string, unknown>, bn: boolean): string {
  const bits: string[] = [];
  if (row.barcode) bits.push(String(row.barcode));
  if (row.category) bits.push(String(row.category));
  if (row.area) bits.push(String(row.area));
  if (row.phone) bits.push(String(row.phone));
  if (row.expiry_date) bits.push(`${bn ? "মেয়াদ" : "Expiry"} ${row.expiry_date}`);
  return bits.join(" · ");
}

function pickValue(
  row: Record<string, unknown>,
  bn: boolean,
): { text: string; tone?: "danger" | "warn" | "ok" } | null {
  if (row.current_stock != null && row.low_stock_threshold != null) {
    return { text: `${row.current_stock} / ${row.low_stock_threshold}`, tone: "danger" };
  }
  if (row.current_stock != null || row.stock != null || row.qty != null) {
    return { text: `${bn ? "স্টক" : "Stock"} ${row.current_stock ?? row.stock ?? row.qty}` };
  }
  if (row.remaining_qty != null) return { text: `${row.remaining_qty}`, tone: "warn" };
  if (row.due != null || row.current_due != null) {
    return { text: `৳${row.due ?? row.current_due}`, tone: "danger" };
  }
  if (row.total != null || row.total_sales != null) {
    return { text: `৳${row.total ?? row.total_sales}` };
  }
  if (row.retail_price != null) return { text: `৳${row.retail_price}` };
  return null;
}

function SummaryChips({ data, bn }: { data: unknown; bn: boolean }) {
  if (!data || typeof data !== "object" || Array.isArray(data)) return null;
  const obj = data as Record<string, unknown>;
  // Don't show empty stock search as confusing chips
  if (obj.count === 0 && obj.query) return null;
  const chips: { label: string; value: string }[] = [];
  const labels: Record<string, [string, string]> = {
    count: ["Count", "সংখ্যা"],
    total_sales: ["Sales", "বিক্রি"],
    estimated_profit: ["Profit", "লাভ"],
    bill_count: ["Bills", "বিল"],
    cash: ["Cash", "ক্যাশ"],
    bkash: ["bKash", "bKash"],
    nagad: ["Nagad", "Nagad"],
    credit: ["Credit", "বাকি"],
    period: ["Period", "সময়"],
  };
  for (const [key, pair] of Object.entries(labels)) {
    if (obj[key] == null || Array.isArray(obj[key])) continue;
    chips.push({ label: bn ? pair[1] : pair[0], value: String(obj[key]) });
  }
  if (!chips.length) return null;
  return (
    <div className="chat-chip-row">
      {chips.map((c) => (
        <div key={c.label} className="chat-chip">
          <span>{c.label}</span>
          <strong>{c.value}</strong>
        </div>
      ))}
    </div>
  );
}

function DataCard({
  title,
  data,
  bn,
  toolName,
  userQuery,
}: {
  title: string;
  data: unknown;
  bn: boolean;
  toolName?: string;
  userQuery?: string;
}) {
  if (toolName === "search_policy" || isPolicyPayload(data)) {
    return (
      <PolicyCard
        data={(data || {}) as Record<string, unknown>}
        bn={bn}
        userQuery={userQuery}
      />
    );
  }

  // Empty stock search — friendly empty, not "Count 0 / query ..."
  if (toolName === "check_stock" && data && typeof data === "object") {
    const obj = data as Record<string, unknown>;
    const rows = asRows(data);
    if (!rows.length || obj.count === 0) {
      return (
        <div className="chat-data-card">
          <div className="chat-data-head">
            <h3>{title}</h3>
          </div>
          <p className="px-3 py-3 text-sm text-[var(--muted)]">
            {bn
              ? "এই খোঁজে কোনো পণ্য পাওয়া যায়নি। নাম বা বারকোড বলে আবার চেষ্টা করুন।"
              : "No products matched. Try another name or barcode."}
          </p>
        </div>
      );
    }
  }

  const rows = asRows(data).filter(
    (row) => row.product || row.name || row.product_name || row.variant || row.bill_no,
  );

  return (
    <div className="chat-data-card">
      <div className="chat-data-head">
        <h3>{title}</h3>
        {rows.length ? (
          <span className="badge badge-muted">
            {rows.length} {bn ? "টি" : ""}
          </span>
        ) : null}
      </div>
      <SummaryChips data={data} bn={bn} />
      {rows.length ? (
        <ul className="chat-data-list">
          {rows.slice(0, 20).map((row, i) => {
            const value = pickValue(row, bn);
            const meta = pickMeta(row, bn);
            return (
              <li key={i}>
                <div className="min-w-0">
                  <p className="chat-data-title">{pickLabel(row)}</p>
                  {meta ? <p className="chat-data-meta">{meta}</p> : null}
                </div>
                {value ? (
                  <span className={`chat-data-value tone-${value.tone || "ok"}`}>{value.text}</span>
                ) : null}
              </li>
            );
          })}
        </ul>
      ) : typeof data === "object" && data && !Array.isArray(data) ? (
        <dl className="chat-kv">
          {Object.entries(data as Record<string, unknown>)
            .filter(
              ([k, v]) =>
                v != null && typeof v !== "object" && !HIDDEN_KEYS.has(k) && !k.endsWith("_id"),
            )
            .slice(0, 12)
            .map(([k, v]) => (
              <div key={k}>
                <dt>{prettyKey(k, bn)}</dt>
                <dd>{formatValue(k, v)}</dd>
              </div>
            ))}
        </dl>
      ) : (
        <p className="chat-data-meta px-3 py-3">
          {bn ? "দেখানোর মতো তথ্য নেই" : "Nothing to show"}
        </p>
      )}
    </div>
  );
}

function prettyKey(key: string, bn: boolean): string {
  const map: Record<string, [string, string]> = {
    total_sales: ["Sales", "বিক্রি"],
    estimated_profit: ["Profit", "লাভ"],
    bill_count: ["Bills", "বিল"],
    from_date: ["From", "থেকে"],
    to_date: ["To", "পর্যন্ত"],
    period: ["Period", "সময়"],
    count: ["Count", "সংখ্যা"],
  };
  const pair = map[key];
  if (pair) return bn ? pair[1] : pair[0];
  return key.replace(/_/g, " ");
}

function formatValue(key: string, value: unknown): string {
  if (typeof value === "string" || typeof value === "number") {
    if (
      key.includes("sales") ||
      key.includes("profit") ||
      key.includes("cash") ||
      key.includes("due") ||
      key.includes("amount") ||
      ["bkash", "nagad", "credit", "total"].includes(key)
    ) {
      const n = Number(value);
      if (!Number.isNaN(n)) return `৳${n.toLocaleString("en-BD")}`;
    }
  }
  return String(value);
}

export function ChatRichReply({
  content,
  tools,
  userQuery,
}: {
  content: string;
  tools?: ToolUsed[];
  userQuery?: string;
}) {
  const { lang } = useI18n();
  const bn = lang === "bn";

  const rendered = useMemo(() => {
    const fromTools =
      (tools
        ?.map((tool) => {
          const parsed = tryParseJson(tool.result_preview);
          return parsed
            ? { title: toolTitle(tool.name, bn), data: parsed, toolName: tool.name }
            : null;
        })
        .filter(Boolean) as { title: string; data: unknown; toolName?: string }[]) || [];

    const { prose, blocks } = extractJsonBlocks(content);
    const fromBlocks = blocks.map((data, i) => ({
      title: bn ? `ফলাফল ${i + 1}` : `Result ${i + 1}`,
      data,
      toolName: isPolicyPayload(data) ? "search_policy" : undefined,
    }));

    const cards = fromTools.length ? fromTools : fromBlocks;

    // Prefer a real short answer; hide generic filler if policy card will highlight the rule
    let cleanProse = prose;
    if (
      !cleanProse ||
      /^search_policy\b/i.test(cleanProse) ||
      cleanProse.includes("নিচের ডকুমেন্ট টুকরো") ||
      cleanProse === "Results:" ||
      cleanProse === "এখানে ফলাফল:"
    ) {
      cleanProse = "";
    }
    if (!cleanProse && cards.some((c) => c.toolName === "search_policy" || isPolicyPayload(c.data))) {
      cleanProse = ""; // card has the answer highlight
    }

    return { prose: cleanProse, cards };
  }, [content, tools, bn]);

  return (
    <div className="space-y-2.5">
      {rendered.prose ? (
        <p className="whitespace-pre-wrap text-sm leading-relaxed">{rendered.prose}</p>
      ) : null}
      {rendered.cards.map((card, idx) => (
        <DataCard
          key={`${card.title}-${idx}`}
          title={card.title}
          data={card.data}
          bn={bn}
          toolName={card.toolName}
          userQuery={userQuery}
        />
      ))}
    </div>
  );
}

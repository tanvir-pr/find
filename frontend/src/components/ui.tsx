import type { ReactNode } from "react";

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="flex flex-col gap-3 pb-1 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="page-title">{title}</h1>
        {subtitle ? <p className="page-sub">{subtitle}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </header>
  );
}

export function StatCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "default" | "accent" | "warn" | "danger";
}) {
  return (
    <article className="panel p-4">
      <p className="text-[0.8125rem] text-[var(--muted)]">{label}</p>
      <p className="stat-value mt-1.5">{value}</p>
      {hint ? <p className="mt-1 text-xs text-[var(--muted)]">{hint}</p> : null}
    </article>
  );
}

export function EmptyState({ title, detail }: { title: string; detail?: string }) {
  return (
    <div className="empty">
      <p>{title}</p>
      {detail ? <p className="mt-1 text-[0.8125rem]">{detail}</p> : null}
    </div>
  );
}

export function Alert({
  children,
  tone = "error",
}: {
  children: ReactNode;
  tone?: "error" | "ok";
}) {
  return <div className={`alert ${tone === "ok" ? "alert-ok" : "alert-error"}`}>{children}</div>;
}

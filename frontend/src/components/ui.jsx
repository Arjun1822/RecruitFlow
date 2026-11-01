import { AlertCircle, CheckCircle2, Clock3, XCircle } from "lucide-react";

export function StatusBadge({ value }) {
  const text = String(value ?? "Unknown");
  const lower = text.toLowerCase();
  const tone = lower.includes("approved") || lower.includes("accepted") || lower.includes("completed") || lower.includes("hired") || lower.includes("active") || lower === "passed"
    ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300"
    : lower.includes("reject") || lower.includes("closed") || lower.includes("cancel") || lower.includes("critical") || lower === "failed"
      ? "bg-rose-50 text-rose-700 dark:bg-rose-950/50 dark:text-rose-300"
      : lower.includes("pending") || lower.includes("scheduled") || lower.includes("warning") || lower.includes("draft")
        ? "bg-amber-50 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300"
        : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300";
  const Icon = lower.includes("approved") || lower.includes("accepted") || lower.includes("completed") || lower === "passed" ? CheckCircle2 : lower.includes("reject") || lower.includes("critical") || lower === "failed" ? XCircle : lower.includes("pending") || lower.includes("scheduled") ? Clock3 : AlertCircle;
  return <span className={`status-badge ${tone}`}><Icon size={13}/>{text}</span>;
}

export function Avatar({ name = "User", size = "md" }) {
  const initials = name.split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase();
  return <span className={`inline-flex shrink-0 items-center justify-center rounded-full bg-indigo-100 font-bold text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300 ${size === "sm" ? "h-7 w-7 text-[10px]" : "h-9 w-9 text-xs"}`}>{initials}</span>;
}

export function MetricCard({ label, value, icon: Icon, tone = "indigo", detail }) {
  const tones = { indigo: "bg-indigo-50 text-indigo-600 dark:bg-indigo-950/50 dark:text-indigo-300", emerald: "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/50 dark:text-emerald-300", amber: "bg-amber-50 text-amber-600 dark:bg-amber-950/50 dark:text-amber-300", rose: "bg-rose-50 text-rose-600 dark:bg-rose-950/50 dark:text-rose-300" };
  return <div className="card flex items-start justify-between"><div><p className="text-sm font-medium text-slate-500 dark:text-slate-400">{label}</p><p className="mt-2 text-2xl font-bold text-slate-900 dark:text-white">{value ?? "—"}</p>{detail && <p className="mt-1 text-xs text-slate-400">{detail}</p>}</div><span className={`rounded-xl p-3 ${tones[tone]}`}><Icon size={20}/></span></div>;
}

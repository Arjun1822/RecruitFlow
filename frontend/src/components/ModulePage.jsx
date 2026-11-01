import { useEffect, useMemo, useState } from "react";
import { Plus, RefreshCw, Search } from "lucide-react";
import api from "../services/api";
import { StatusBadge } from "./ui";

export default function ModulePage({ title, description, endpoint, submitEndpoint = endpoint, columns, fields = [], actions = [], children }) {
  const [rows, setRows] = useState([]);
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);
  const [form, setForm] = useState({});
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const load = () => {
    setLoading(true);
    api.get(endpoint, { params: { skip: page * 25, limit: 25 } })
      .then(({ data }) => setRows(Array.isArray(data) ? data : data.checks || data.departments || []))
      .catch((e) => setError(e.response?.data?.detail || e.message))
      .finally(() => setLoading(false));
  };
  useEffect(load, [endpoint, page]);
  const filtered = useMemo(() => rows.filter((row) => JSON.stringify(row).toLowerCase().includes(query.toLowerCase())), [rows, query]);
  const submit = async (event) => {
    event.preventDefault();
    setError(""); setMessage("");
    try {
      await api.post(submitEndpoint, form);
      setForm({}); setMessage("Saved successfully."); load();
    } catch (e) { setError(e.response?.data?.detail || e.message); }
  };
  const runAction = async (action, row) => {
    try { await action.run(row); setMessage(action.success || "Updated successfully."); load(); }
    catch (e) { setError(e.response?.data?.detail || e.message); }
  };
  return <div className="space-y-7">
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div><p className="eyebrow">RecruitFlow workspace</p><h1 className="mt-2 text-3xl font-bold">{title}</h1><p className="mt-2 text-sm text-slate-500">{description}</p></div>
      <button className="button-secondary flex items-center gap-2" onClick={load}><RefreshCw size={16}/> Refresh</button>
    </div>
    {message && <div className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-700">{message}</div>}
    {error && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>}
    {fields.length > 0 && <form onSubmit={submit} className="card"><div className="mb-4 flex items-center justify-between"><div><h2 className="font-bold">Create new record</h2><p className="mt-1 text-xs text-slate-500">Enter the required details below. Business rules are validated by the API.</p></div><Plus size={20} className="text-indigo-500"/></div><div className="grid gap-4 md:grid-cols-3">
      {fields.map((field) => <label className="text-sm font-semibold text-slate-700 dark:text-slate-300" key={field.name}>{field.label}{field.required !== false && <span className="ml-1 text-rose-500">*</span>}<input required={field.required !== false} type={field.type || "text"} className="input mt-1.5" value={form[field.name] ?? ""} onChange={(e) => setForm({ ...form, [field.name]: field.type === "number" ? Number(e.target.value) : e.target.value })} placeholder={field.placeholder}/></label>)}</div>
      <div className="mt-5 flex justify-end"><button className="button-primary flex items-center gap-2"><Plus size={16}/> Create record</button></div>
    </form>}
    {children}
    <section className="card">
      <div className="relative mb-4 max-w-md"><Search className="absolute left-3 top-2.5 text-slate-400" size={18}/><input className="input pl-10" placeholder={`Search ${title.toLowerCase()}`} value={query} onChange={(e) => { setQuery(e.target.value); setPage(0); }}/></div>
      {loading ? <p className="text-slate-500">Loading records...</p> : filtered.length === 0 ? <div className="py-12 text-center"><p className="font-semibold">No records found</p><p className="mt-1 text-sm text-slate-400">Try adjusting your search or create a new record.</p></div> : <div className="overflow-auto"><table className="w-full min-w-[720px] text-left text-sm"><thead><tr className="border-b border-slate-100 text-[11px] uppercase tracking-wider text-slate-400 dark:border-slate-800">{columns.map((column) => <th className="px-3 py-3 font-bold" key={column.key}>{column.label}</th>)}{actions.length > 0 && <th className="px-3 py-3 font-bold">Actions</th>}</tr></thead><tbody>{filtered.map((row, index) => <tr className="table-row" key={row.id || row.issue_id || index}>{columns.map((column) => <td className="whitespace-nowrap px-3 py-3.5 text-slate-600 dark:text-slate-300" key={column.key}>{column.render ? column.render(row) : column.key === "status" || column.key === "severity" || column.key === "resolved" ? <StatusBadge value={row[column.key]} /> : String(row[column.key] ?? "—")}</td>)}{actions.length > 0 && <td className="flex gap-2 px-3 py-3.5">{actions.map((action) => <button className="rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-semibold text-slate-600 hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700 dark:border-slate-700 dark:text-slate-300" onClick={() => runAction(action, row)} key={action.label}>{action.label}</button>)}</td>}</tr>)}</tbody></table></div>}
      <div className="mt-4 flex justify-end gap-2"><button className="rounded-md border px-3 py-1 text-sm disabled:opacity-40" disabled={page === 0} onClick={() => setPage(page - 1)}>Previous</button><span className="px-3 py-1 text-sm text-slate-500">Page {page + 1}</span><button className="rounded-md border px-3 py-1 text-sm disabled:opacity-40" disabled={rows.length < 25} onClick={() => setPage(page + 1)}>Next</button></div>
    </section>
  </div>;
}

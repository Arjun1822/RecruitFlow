import { useEffect, useMemo, useState } from "react";
import { CalendarDays, ChevronLeft, ChevronRight, Clock3, RefreshCw, UserCheck, X } from "lucide-react";
import api from "../services/api";
import { StatusBadge } from "../components/ui";

const pad = (value) => String(value).padStart(2, "0");
const localInput = (date) => `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
const dayKey = (value) => { const date = new Date(value); return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`; };
const displayDate = (value, options = {}) => new Date(value).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short", ...options });

export default function Interviews() {
  const [rows, setRows] = useState([]);
  const [interviewers, setInterviewers] = useState([]);
  const [applications, setApplications] = useState([]);
  const [candidates, setCandidates] = useState([]);
  const [view, setView] = useState("week");
  const [cursor, setCursor] = useState(new Date());
  const [selected, setSelected] = useState(null);
  const [availability, setAvailability] = useState(null);
  const [form, setForm] = useState({ application_id: "", interviewer_id: "", starts_at: "", ends_at: "", round_number: 1 });
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const load = async () => {
    try {
      const [interviewResponse, interviewerResponse, applicationResponse, candidateResponse] = await Promise.all([api.get("/api/interviews"), api.get("/api/interviewers"), api.get("/api/applications", { params: { limit: 100 } }), api.get("/api/candidates", { params: { limit: 100 } })]);
      setRows(interviewResponse.data); setInterviewers(interviewerResponse.data); setApplications(applicationResponse.data); setCandidates(candidateResponse.data);
    } catch (e) { setError(e.response?.data?.detail || e.message); }
  };
  useEffect(() => { load(); }, []);

  const weekStart = useMemo(() => {
    const date = new Date(cursor); date.setHours(0, 0, 0, 0);
    date.setDate(date.getDate() - date.getDay()); return date;
  }, [cursor]);
  const days = useMemo(() => Array.from({ length: view === "day" ? 1 : 7 }, (_, index) => {
    const date = new Date(weekStart); date.setDate(date.getDate() + index); return date;
  }), [weekStart, view]);
  const monthDays = useMemo(() => {
    if (view !== "month") return [];
    const first = new Date(cursor.getFullYear(), cursor.getMonth(), 1);
    const start = new Date(first); start.setDate(1 - first.getDay());
    return Array.from({ length: 42 }, (_, index) => { const date = new Date(start); date.setDate(start.getDate() + index); return date; });
  }, [cursor, view]);
  const visibleDays = view === "month" ? monthDays : days;
  const visibleRows = rows.filter((row) => row.status !== "Cancelled");
  const moveCursor = (amount) => {
    const next = new Date(cursor);
    if (view === "month") next.setMonth(next.getMonth() + amount);
    else next.setDate(next.getDate() + amount * (view === "day" ? 1 : 7));
    setCursor(next);
  };
  const create = async (event) => {
    event.preventDefault(); setError(""); setMessage("");
    try {
      await api.post("/api/interviews", { ...form, interviewer_id: Number(form.interviewer_id), starts_at: new Date(form.starts_at).toISOString(), ends_at: new Date(form.ends_at).toISOString() });
      setMessage("Interview scheduled."); setForm({ application_id: "", interviewer_id: "", starts_at: "", ends_at: "", round_number: 1 }); load();
    } catch (e) { setError(e.response?.data?.detail || e.message); }
  };
  const update = async (payload, success) => {
    if (!selected) return;
    try { await api.put(`/api/interviews/${selected.id}`, payload); setMessage(success); setSelected(null); await load(); }
    catch (e) { setError(e.response?.data?.detail || e.message); }
  };
  const checkAvailability = async (interviewerId, start, end) => {
    if (!interviewerId || !start || !end) return;
    try {
      const { data } = await api.get(`/api/interviewers/${interviewerId}/availability`, { params: { starts_at: new Date(start).toISOString(), ends_at: new Date(end).toISOString() } });
      setAvailability(data);
    } catch (e) { setError(e.response?.data?.detail || e.message); }
  };
  const title = view === "month" ? cursor.toLocaleString(undefined, { month: "long", year: "numeric" }) : view === "day" ? cursor.toLocaleDateString(undefined, { dateStyle: "full" }) : `${days[0].toLocaleDateString()} – ${days[6].toLocaleDateString()}`;
  const interviewsFor = (date) => visibleRows.filter((row) => dayKey(row.starts_at) === dayKey(date));

  return <div className="space-y-7">
    <div className="flex flex-wrap items-end justify-between gap-4"><div><p className="eyebrow">Recruitment workspace</p><h1 className="mt-2 text-3xl font-bold">Interview calendar</h1><p className="mt-2 text-sm text-slate-500">Schedule, inspect availability, and resolve conflicts from live interview data.</p></div><button className="button-secondary flex items-center gap-2" onClick={load}><RefreshCw size={16}/> Refresh</button></div>
    {error && <div className="card flex items-center justify-between text-rose-600">{error}<button onClick={() => setError("")}><X size={16}/></button></div>}{message && <div className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-700">{message}</div>}
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_330px]">
      <section className="card">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4"><div className="flex items-center gap-2"><button className="rounded-lg border p-2" aria-label="Previous period" onClick={() => moveCursor(-1)}><ChevronLeft size={16}/></button><button className="rounded-lg border p-2" aria-label="Next period" onClick={() => moveCursor(1)}><ChevronRight size={16}/></button><button className="button-secondary ml-1" onClick={() => setCursor(new Date())}>Today</button><h2 className="ml-2 font-bold">{title}</h2></div><div className="flex rounded-lg border p-1 text-xs font-semibold">{["day", "week", "month"].map((item) => <button key={item} className={`rounded-md px-3 py-1.5 capitalize ${view === item ? "bg-indigo-600 text-white" : "text-slate-500"}`} onClick={() => setView(item)}>{item}</button>)}</div></div>
        {visibleRows.length === 0 ? <div className="flex min-h-[300px] flex-col items-center justify-center rounded-xl border border-dashed border-slate-200 text-center"><CalendarDays className="text-slate-300" size={34}/><p className="mt-3 font-semibold">No interviews scheduled</p><p className="mt-1 text-sm text-slate-400">Schedule an interview to populate this calendar.</p></div> : <div className={`mt-5 grid ${view === "month" ? "grid-cols-7" : view === "day" ? "grid-cols-1" : "grid-cols-7"} overflow-hidden rounded-xl border border-slate-200`}>{visibleDays.map((date) => <div className={`min-h-[150px] border-b border-r border-slate-100 p-2 ${date.getMonth() !== cursor.getMonth() && view === "month" ? "bg-slate-50/70" : ""}`} key={date.toISOString()}><div className="mb-2 flex items-center justify-between text-xs font-bold"><span className={dayKey(date) === dayKey(new Date()) ? "rounded-full bg-indigo-600 px-2 py-1 text-white" : "text-slate-500"}>{date.toLocaleDateString(undefined, { weekday: "short", day: "numeric" })}</span><span className="text-slate-400">{interviewsFor(date).length || ""}</span></div>{interviewsFor(date).map((row) => <button key={row.id} onClick={() => setSelected(row)} className="mb-1.5 w-full rounded-lg border border-indigo-100 bg-indigo-50 p-2 text-left text-xs hover:border-indigo-400"><p className="font-bold text-indigo-700">{new Date(row.starts_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} · {row.id}</p><p className="mt-1 truncate text-slate-600">Application {row.application_id}</p><StatusBadge value={row.status}/></button>)}</div>)}</div>}
      </section>
      <aside className="space-y-6"><section className="card"><div className="flex items-center gap-2"><CalendarDays size={18} className="text-indigo-600"/><h2 className="font-bold">Schedule interview</h2></div><form onSubmit={create} className="mt-4 space-y-3"><label className="text-xs font-semibold text-slate-500">Application / candidate<input className="input mt-1" required list="application-options" placeholder="Search application or candidate" value={form.application_id} onChange={(e) => setForm({ ...form, application_id: e.target.value })}/><datalist id="application-options">{applications.map((item) => { const candidate = candidates.find((row) => row.id === item.candidate_id); return <option key={item.id} value={item.id}>{candidate ? `${candidate.first_name} ${candidate.last_name}` : item.candidate_id} · {item.status}</option>; })}</datalist></label><label className="text-xs font-semibold text-slate-500">Interviewer<select className="input mt-1" required value={form.interviewer_id} onChange={(e) => setForm({ ...form, interviewer_id: e.target.value })}><option value="">Select interviewer</option>{interviewers.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.email}</option>)}</select></label><label className="text-xs font-semibold text-slate-500">Start time<input className="input mt-1" required type="datetime-local" value={form.starts_at} onChange={(e) => setForm({ ...form, starts_at: e.target.value })}/></label><label className="text-xs font-semibold text-slate-500">End time<input className="input mt-1" required type="datetime-local" value={form.ends_at} onChange={(e) => setForm({ ...form, ends_at: e.target.value })}/></label><label className="text-xs font-semibold text-slate-500">Interview type / round<select className="input mt-1" value={form.round_number} onChange={(e) => setForm({ ...form, round_number: Number(e.target.value) })}><option value="1">Screening</option><option value="2">Technical</option><option value="3">Final</option></select></label><div className="flex gap-2"><button type="button" className="button-secondary flex-1" onClick={() => checkAvailability(form.interviewer_id, form.starts_at, form.ends_at)}>Check availability</button><button className="button-primary flex-1">Schedule</button></div></form>{availability && <div className={`mt-3 rounded-lg p-3 text-xs ${availability.available ? "bg-emerald-50 text-emerald-700" : "bg-rose-50 text-rose-700"}`}>{availability.available ? "Interviewer is available." : `Conflict with ${availability.bookings.map((item) => item.id).join(", ")}.`}</div>}</section>
      <section className="card"><div className="flex items-center gap-2"><UserCheck size={18} className="text-indigo-600"/><h2 className="font-bold">Active interviewers</h2></div><div className="mt-3 space-y-2">{interviewers.slice(0, 6).map((item) => <div className="flex items-center justify-between rounded-lg bg-slate-50 p-2.5 text-xs" key={item.id}><span className="font-semibold">{item.name}</span><span className="text-slate-400">{rows.filter((row) => row.interviewer_id === item.id && row.status !== "Cancelled").length} booked</span></div>)}</div></section></aside>
    </div>
    {selected && <div className="card border-indigo-200"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="eyebrow">Selected interview</p><h2 className="mt-1 font-bold">{selected.id}</h2><p className="mt-1 text-sm text-slate-500"><Clock3 className="mr-1 inline" size={14}/>{displayDate(selected.starts_at)} – {new Date(selected.ends_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</p></div><button onClick={() => setSelected(null)}><X size={18}/></button></div><div className="mt-4 flex flex-wrap gap-2"><button className="button-secondary" onClick={() => update({ status: "Cancelled" }, "Interview cancelled.")}>Cancel interview</button><button className="button-secondary" onClick={() => update({ status: "Rescheduled", starts_at: new Date(new Date(selected.starts_at).getTime() + 86400000).toISOString(), ends_at: new Date(new Date(selected.ends_at).getTime() + 86400000).toISOString() }, "Interview rescheduled by one day.")}>Reschedule +1 day</button>{selected.status !== "Completed" && <button className="button-primary" onClick={() => update({ status: "Completed" }, "Interview completed.")}>Mark completed</button>}</div></div>}
  </div>;
}

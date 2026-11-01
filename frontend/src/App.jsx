import { useEffect, useMemo, useState } from "react";
import { BrowserRouter, NavLink, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { Activity, BarChart3, BriefcaseBusiness, CalendarDays, CheckCircle2, ChevronDown, ChevronLeft, FileText, LayoutDashboard, LogOut, Menu, Moon, PanelLeft, Search, Settings, ShieldAlert, Sun, Users, X } from "lucide-react";
import api from "./services/api";
import { Avatar, MetricCard } from "./components/ui";
import Requisitions from "./pages/Requisitions";
import Departments from "./pages/Departments";
import Candidates from "./pages/Candidates";
import CandidateProfile from "./pages/CandidateProfile";
import Applications from "./pages/Applications";
import Screening from "./pages/Screening";
import Interviews from "./pages/Interviews";
import InterviewPanel from "./pages/InterviewPanel";
import Feedback from "./pages/Feedback";
import Offers from "./pages/Offers";
import { Exceptions, Validation, Analytics, Administration } from "./pages/SimpleModules";

const groups = [
  { label: "Workspace", items: [["Dashboard", "/", LayoutDashboard]] },
  { label: "Recruitment", items: [["Requisitions", "/requisitions", BriefcaseBusiness], ["Departments", "/departments", BriefcaseBusiness], ["Candidates", "/candidates", Users], ["Applications", "/applications", FileText], ["Screening", "/screening", CheckCircle2]] },
  { label: "Management", items: [["Interviews", "/interviews", CalendarDays], ["Interview panel", "/interview-panel", Users], ["Feedback", "/feedback", CheckCircle2], ["Offers", "/offers", BriefcaseBusiness], ["Exceptions", "/exceptions", ShieldAlert]] },
  { label: "Analytics", items: [["Validation", "/validation", CheckCircle2], ["Analytics", "/analytics", BarChart3]] },
  { label: "Administration", items: [["Administration", "/administration", Settings]] },
];

function formatApiError(error, fallback) {
  const detail = error.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item?.msg || "Invalid input").join("; ");
  }
  return fallback;
}

export function Login({ onLogin }) {
  const [form, setForm] = useState({ username: "", password: "" });
  const [registration, setRegistration] = useState({ available: false, open: false, password: "", confirmation: "" });
  const [error, setError] = useState("");
  useEffect(() => {
    api.get("/api/auth/register-admin/status")
      .then(({ data }) => setRegistration((current) => ({ ...current, available: data.available })))
      .catch(() => {});
  }, []);
  const submit = async (event) => {
    event.preventDefault(); setError("");
    try { const { data } = await api.post("/api/auth/login", form); localStorage.setItem("rms_token", data.token); onLogin(data.user); }
    catch (e) { setError(formatApiError(e, "Unable to sign in")); }
  };
  const register = async (event) => {
    event.preventDefault(); setError("");
    try {
      await api.post("/api/auth/register-admin", {
        username: form.username,
        password: registration.password,
        password_confirmation: registration.confirmation,
      });
      setRegistration({ available: false, open: false, password: "", confirmation: "" });
      setError("Administrator registered. Sign in with your new password.");
    } catch (e) { setError(formatApiError(e, "Unable to register administrator")); }
  };
  if (registration.open) return <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-slate-950 p-6">
    <form onSubmit={register} className="relative w-full max-w-md rounded-3xl border border-white/10 bg-white p-8 shadow-2xl shadow-black/30">
      <h1 className="text-2xl font-bold text-slate-900">Create administrator</h1>
      <p className="mt-2 text-sm text-slate-500">This one-time setup is available only from localhost.</p>
      {error && <div className="mt-5 rounded-xl border border-rose-100 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}
      <div className="mt-6 space-y-4">
        <label className="block text-sm font-semibold text-slate-700">Username<input className="input mt-2" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} autoComplete="username"/></label>
        <label className="block text-sm font-semibold text-slate-700">Password<input className="input mt-2" type="password" value={registration.password} onChange={(e) => setRegistration({ ...registration, password: e.target.value })} autoComplete="new-password"/></label>
        <label className="block text-sm font-semibold text-slate-700">Confirm password<input className="input mt-2" type="password" value={registration.confirmation} onChange={(e) => setRegistration({ ...registration, confirmation: e.target.value })} autoComplete="new-password"/></label>
      </div>
      <button className="button-primary mt-6 w-full">Create administrator</button>
      <button type="button" className="mt-3 w-full text-sm text-slate-500" onClick={() => { setError(""); setRegistration({ ...registration, open: false }); }}>Back to sign in</button>
    </form>
  </main>;
  return <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-slate-950 p-6">
    <div className="absolute -left-32 -top-32 h-96 w-96 rounded-full bg-indigo-600/20 blur-3xl"/><div className="absolute -bottom-48 -right-32 h-96 w-96 rounded-full bg-violet-500/10 blur-3xl"/>
    <form onSubmit={submit} className="relative w-full max-w-md rounded-3xl border border-white/10 bg-white p-8 shadow-2xl shadow-black/30">
      <div className="mb-8 flex items-center gap-3"><span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-indigo-600 text-lg font-black text-white">R</span><div><p className="font-bold text-slate-900">RecruitFlow</p><p className="text-xs text-slate-500">Talent operations, simplified.</p></div></div>
      <h1 className="text-2xl font-bold text-slate-900">Welcome back</h1><p className="mt-2 text-sm text-slate-500">Sign in to your recruitment workspace.</p>
      {error && <div className="mt-5 rounded-xl border border-rose-100 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}
      <div className="mt-6 space-y-4"><label className="block text-sm font-semibold text-slate-700">Username<input className="input mt-2" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} placeholder="Enter your username" autoComplete="username"/></label><label className="block text-sm font-semibold text-slate-700">Password<input className="input mt-2" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder="Enter your password" autoComplete="current-password"/></label></div>
      <button className="button-primary mt-6 w-full">Sign in to RecruitFlow</button>
      {registration.available && <button type="button" className="mt-3 w-full text-sm font-semibold text-indigo-600" onClick={() => { setError(""); setRegistration({ ...registration, open: true }); }}>Create the first administrator</button>}
      <p className="mt-5 text-center text-xs text-slate-400">Protected enterprise workspace</p>
    </form>
  </main>;
}

function Dashboard() {
  const [metrics, setMetrics] = useState(null); const [stats, setStats] = useState({}); const [error, setError] = useState("");
  useEffect(() => { Promise.all([api.get("/api/dashboard/metrics"), api.get("/api/dashboard/application-stats")]).then(([metricResponse, statsResponse]) => { setMetrics(metricResponse.data); setStats(statsResponse.data); }).catch((e) => setError(e.response?.data?.detail || e.message)); }, []);
  const cards = [["Total candidates", "total_candidates", Users, "indigo"], ["Active requisitions", "open_requisitions", BriefcaseBusiness, "emerald"], ["Total applications", "total_applications", FileText, "amber"], ["Interviews scheduled", "interviews_scheduled", CalendarDays, "indigo"], ["Offers released", "offers_released", BriefcaseBusiness, "rose"], ["Hiring conversion", "hiring_conversion_rate", Activity, "emerald"]];
  const totalStatuses = Object.values(stats).reduce((sum, value) => sum + value, 0);
  return <div className="space-y-7"><div className="flex flex-wrap items-end justify-between gap-4"><div><p className="eyebrow">Workspace overview</p><h1 className="mt-2 text-3xl font-bold">Good morning, {metrics ? "team" : "there"}.</h1><p className="mt-2 text-sm text-slate-500">A real-time view of your recruitment pipeline and hiring performance.</p></div><div className="text-right text-xs text-slate-400">Data refreshed live<br/><span className="font-semibold text-emerald-600">● Operational</span></div></div>
    {error && <div className="card text-rose-600">{error}</div>}{!metrics ? <div className="card animate-pulse text-slate-400">Loading live workspace metrics...</div> : <><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{cards.map(([label, key, Icon, tone]) => <MetricCard key={key} label={label} value={`${metrics[key] ?? 0}${key.includes("rate") ? "%" : ""}`} icon={Icon} tone={tone} detail={key.includes("rate") ? "Database-derived rate" : "Current total"} />)}</div><div className="grid gap-5 xl:grid-cols-[1.4fr_1fr]"><section className="card"><div className="flex items-center justify-between"><div><h2 className="font-bold">Application funnel</h2><p className="mt-1 text-xs text-slate-500">Current application distribution by stage</p></div><span className="rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-500 dark:bg-slate-800">{totalStatuses} total</span></div><div className="mt-6 space-y-4">{Object.entries(stats).slice(0, 6).map(([stage, count]) => <div key={stage}><div className="mb-1.5 flex justify-between text-xs font-semibold"><span className="text-slate-600 dark:text-slate-300">{stage}</span><span className="text-slate-400">{count}</span></div><div className="h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800"><div className="h-full rounded-full bg-indigo-600" style={{ width: `${totalStatuses ? Math.max(3, count / totalStatuses * 100) : 0}%` }}/></div></div>)}</div></section><section className="card"><div className="flex items-center justify-between"><div><h2 className="font-bold">Hiring health</h2><p className="mt-1 text-xs text-slate-500">Key conversion signals</p></div><BarChart3 size={20} className="text-indigo-500"/></div><div className="mt-5 space-y-4">{[["Screening pass rate", metrics.screening_pass_rate], ["Interview completion", metrics.interview_completion_rate], ["Offer acceptance", metrics.offer_acceptance_rate]].map(([label, value]) => <div className="flex items-center justify-between rounded-xl bg-slate-50 p-3 dark:bg-slate-800/60" key={label}><span className="text-sm text-slate-600 dark:text-slate-300">{label}</span><span className="font-bold text-indigo-600">{value ?? 0}%</span></div>)}</div></section></div></>}</div>;
}

function Shell({ user, setUser }) {
  const [collapsed, setCollapsed] = useState(false); const [mobileOpen, setMobileOpen] = useState(false); const [dark, setDark] = useState(() => localStorage.getItem("rms_theme") === "dark"); const location = useLocation();
  useEffect(() => { localStorage.setItem("rms_theme", dark ? "dark" : "light"); }, [dark]);
  const current = groups.flatMap((group) => group.items).find(([, path]) => path === location.pathname)?.[0] || "Workspace";
  const logout = () => { localStorage.removeItem("rms_token"); setUser(null); };
  return <div className={dark ? "dark" : ""}><div className="flex min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
    {mobileOpen && <button aria-label="Close navigation" className="fixed inset-0 z-30 bg-slate-950/40 md:hidden" onClick={() => setMobileOpen(false)}/>}
    <aside className={`${collapsed ? "md:w-[76px]" : "md:w-64"} ${mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"} fixed inset-y-0 z-40 w-72 shrink-0 overflow-hidden border-r border-slate-200 bg-white transition-all duration-200 dark:border-slate-800 dark:bg-slate-900 md:relative`}><div className="flex h-20 items-center justify-between px-5"><div className={`flex min-w-0 items-center gap-3 ${collapsed ? "md:mx-auto" : ""}`}><span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-600 font-black text-white shadow-lg shadow-indigo-200">R</span>{!collapsed && <span className="truncate font-bold tracking-tight">Recruit<span className="text-indigo-600">Flow</span></span>}</div><button className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 md:hidden" onClick={() => setMobileOpen(false)}><X size={18}/></button></div><nav className="space-y-6 px-3 py-3">{groups.map((group) => <div key={group.label}>{!collapsed && <p className="mb-2 px-3 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400">{group.label}</p>}{group.items.map(([label, path, Icon]) => <NavLink onClick={() => setMobileOpen(false)} key={path} to={path} title={collapsed ? label : undefined} className={({ isActive }) => `group relative mb-1 flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition ${isActive ? "bg-indigo-50 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300" : "text-slate-500 hover:bg-slate-50 hover:text-slate-800 dark:hover:bg-slate-800"} ${collapsed ? "md:justify-center md:px-2" : ""}`}><Icon size={17}/>{!collapsed && <span className="truncate">{label}</span>}</NavLink>)}</div>)}</nav><div className="absolute bottom-0 left-0 right-0 overflow-hidden border-t border-slate-100 p-4 dark:border-slate-800"><div className={`flex min-w-0 items-center gap-3 ${collapsed ? "md:justify-center" : ""}`}><Avatar name={user.username}/>{!collapsed && <div className="min-w-0 overflow-hidden"><p className="truncate text-sm font-bold">{user.username}</p><p className="truncate text-xs text-slate-400">{user.role}</p></div>}</div></div></aside>
    <section className="min-w-0 flex-1"><header className="sticky top-0 z-20 flex h-20 items-center justify-between border-b border-slate-200/80 bg-slate-50/90 px-4 backdrop-blur md:px-8 dark:border-slate-800 dark:bg-slate-950/90"><div className="flex items-center gap-3"><button className="rounded-xl border border-slate-200 bg-white p-2 text-slate-500 md:hidden dark:border-slate-700 dark:bg-slate-900" onClick={() => setMobileOpen(true)}><Menu size={19}/></button><button className="hidden rounded-xl border border-slate-200 bg-white p-2 text-slate-500 md:block dark:border-slate-700 dark:bg-slate-900" onClick={() => setCollapsed(!collapsed)}>{collapsed ? <PanelLeft size={18}/> : <ChevronLeft size={18}/>}</button><div className="hidden items-center gap-2 text-sm md:flex"><span className="text-slate-400">Workspace</span><ChevronDown size={14} className="text-slate-300"/><span className="font-semibold">{current}</span></div></div><div className="flex items-center gap-2"><div className="hidden items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-400 lg:flex dark:border-slate-700 dark:bg-slate-900"><Search size={16}/><span>Search anything</span><kbd className="ml-8 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] dark:bg-slate-800">⌘ K</kbd></div><button aria-label="Toggle theme" onClick={() => setDark(!dark)} className="rounded-xl border border-slate-200 bg-white p-2.5 text-slate-500 hover:text-indigo-600 dark:border-slate-700 dark:bg-slate-900">{dark ? <Sun size={17}/> : <Moon size={17}/>}</button><button aria-label="Logout" onClick={logout} className="rounded-xl border border-slate-200 bg-white p-2.5 text-slate-500 hover:text-rose-600 dark:border-slate-700 dark:bg-slate-900"><LogOut size={17}/></button><Avatar name={user.username} size="sm"/></div></header><main className="mx-auto max-w-[1600px] p-4 md:p-8"><Routes><Route path="/" element={<Dashboard/>}/><Route path="/requisitions" element={<Requisitions/>}/><Route path="/departments" element={<Departments/>}/><Route path="/candidates" element={<Candidates/>}/><Route path="/candidates/:id" element={<CandidateProfile/>}/><Route path="/applications" element={<Applications/>}/><Route path="/screening" element={<Screening/>}/><Route path="/interviews" element={<Interviews/>}/><Route path="/interview-panel" element={<InterviewPanel/>}/><Route path="/feedback" element={<Feedback/>}/><Route path="/offers" element={<Offers/>}/><Route path="/exceptions" element={<Exceptions/>}/><Route path="/validation" element={<Validation/>}/><Route path="/analytics" element={<Analytics/>}/><Route path="/administration" element={<Administration/>}/><Route path="*" element={<Navigate to="/" replace/>}/></Routes></main></section>
  </div></div>;
}

export default function App() {
  const [user, setUser] = useState(null);
  useEffect(() => {
    const expire = () => setUser(null);
    window.addEventListener("rms:auth-expired", expire);
    if (localStorage.getItem("rms_token")) {
      api.get("/api/auth/me").then(({ data }) => setUser(data)).catch(() => {
        localStorage.removeItem("rms_token");
        setUser(null);
      });
    }
    return () => window.removeEventListener("rms:auth-expired", expire);
  }, []);
  return <BrowserRouter>{user ? <Shell user={user} setUser={setUser}/> : <Login onLogin={setUser}/>}</BrowserRouter>;
}

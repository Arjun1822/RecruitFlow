import { useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import api from "../services/api";
export default function CandidateProfile() {
  const { id } = useParams();
  const [candidate, setCandidate] = useState(null);
  const [resumes, setResumes] = useState([]);
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const load = () => Promise.all([api.get(`/api/candidates/${id}`), api.get(`/api/candidates/${id}/resumes`)])
    .then(([candidateResponse, resumeResponse]) => { setCandidate(candidateResponse.data); setResumes(resumeResponse.data); })
    .catch((e) => setError(e.response?.data?.detail || e.message));
  useEffect(load, [id]);
  const submit = async (event) => {
    event.preventDefault(); setError(""); setMessage("");
    if (!file) { setError("Select a PDF resume first."); return; }
    const body = new FormData(); body.append("file", file);
    try { await api.post(`/api/candidates/${id}/resumes/upload`, body, { headers: { "Content-Type": "multipart/form-data" } }); setFile(null); event.target.reset(); setMessage("Resume uploaded securely."); load(); }
    catch (e) { setError(e.response?.data?.detail || e.message); }
  };
  const download = async (resume) => {
    try { const response = await api.get(`/api/candidates/${id}/resumes/${resume.id}/download`, { responseType: "blob" }); const url = URL.createObjectURL(response.data); const anchor = document.createElement("a"); anchor.href = url; anchor.download = resume.filename; anchor.click(); URL.revokeObjectURL(url); }
    catch (e) { setError(e.response?.data?.detail || "Unable to download resume"); }
  };
  return <div className="space-y-7"><div><p className="eyebrow">Candidate workspace</p><h1 className="mt-2 text-3xl font-bold">Candidate profile</h1><p className="mt-2 text-sm text-slate-500">Review candidate details and registered resume artifacts.</p></div>{error && <div className="card text-rose-600">{error}</div>}{message && <div className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-700">{message}</div>}{candidate && <div className="card grid gap-4 md:grid-cols-2">{Object.entries(candidate).map(([key, value]) => <div key={key}><p className="text-xs font-bold uppercase tracking-wider text-slate-400">{key.replaceAll("_", " ")}</p><p className="mt-1 font-semibold">{String(value ?? "—")}</p></div>)}</div>}<form onSubmit={submit} className="card"><h2 className="font-bold">Upload resume</h2><p className="mt-1 text-xs text-slate-500">PDF only, maximum 5 MB. Files are stored outside public web directories.</p><div className="mt-4 flex flex-wrap items-end gap-4"><label className="text-sm font-semibold">PDF resume<input required accept="application/pdf,.pdf" type="file" className="input mt-1.5" onChange={(e) => setFile(e.target.files?.[0] || null)}/></label><button className="button-primary">Upload securely</button></div></form><section className="card"><h2 className="font-bold">Resume history</h2>{resumes.length === 0 ? <p className="mt-4 text-sm text-slate-500">No resume artifacts registered.</p> : <div className="mt-4 overflow-auto"><table className="w-full text-left text-sm"><thead><tr className="border-b text-xs uppercase text-slate-400"><th className="px-3 py-3">Filename</th><th className="px-3 py-3">Version</th><th className="px-3 py-3">Access</th></tr></thead><tbody>{resumes.map((resume) => <tr className="table-row" key={resume.id}><td className="px-3 py-3">{resume.filename}</td><td className="px-3 py-3">{resume.version}</td><td className="px-3 py-3">{resume.storage_path?.endsWith(".pdf") ? <button className="font-semibold text-indigo-600" onClick={() => download(resume)}>Download</button> : <span className="text-slate-400">Registered reference</span>}</td></tr>)}</tbody></table></div>}</section></div>;
}

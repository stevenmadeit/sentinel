import Link from "next/link";

interface IncidentSummary {
  id: number;
  service_name: string;
  alert_message: string;
  status: string;
  created_at: string;
}

const BACKEND_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

async function fetchIncidents() {
  const res = await fetch(`${BACKEND_BASE}/incidents`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error("Failed to fetch incidents");
  }
  return (await res.json()) as IncidentSummary[];
}

export default async function Home() {
  const incidents = await fetchIncidents();

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
        <header className="mb-10 flex flex-col gap-4 rounded-3xl border border-slate-800/80 bg-slate-900/80 p-8 shadow-lg shadow-slate-950/30 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.18em] text-slate-500">Sentinel Dashboard</p>
            <h1 className="mt-3 text-4xl font-semibold text-white">Incident overview</h1>
            <p className="mt-2 max-w-2xl text-slate-400">Track generated alerts, inspect AI analysis, and resolve incidents with one click.</p>
          </div>
          <Link
            href="/incidents/new"
            className="inline-flex items-center justify-center rounded-2xl bg-slate-100 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-slate-200"
          >
            New Test Alert
          </Link>
        </header>

        <div className="grid gap-6">
          {incidents.length === 0 ? (
            <div className="rounded-3xl border border-slate-800/80 bg-slate-900/80 p-8 text-center text-slate-400">No incidents found.</div>
          ) : (
            incidents.map((incident) => (
              <Link
                key={incident.id}
                href={`/incidents/${incident.id}`}
                className="group rounded-3xl border border-slate-800/80 bg-slate-900/80 p-6 transition hover:border-slate-700 hover:bg-slate-900"
              >
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-sm text-slate-400">{incident.service_name}</p>
                    <h2 className="mt-1 text-xl font-semibold text-white">{incident.alert_message}</h2>
                  </div>
                  <div className="flex flex-wrap items-center gap-3 text-sm text-slate-400">
                    <span className={
                      `rounded-full px-3 py-1 font-semibold ${incident.status === "resolved" ? "bg-emerald-500/15 text-emerald-300" : "bg-rose-500/15 text-rose-300"}`
                    }>
                      {incident.status === "resolved" ? "Resolved" : "Active"}
                    </span>
                    <span>{new Date(incident.created_at).toLocaleString()}</span>
                  </div>
                </div>
              </Link>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

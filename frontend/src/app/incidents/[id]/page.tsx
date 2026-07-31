import { notFound } from "next/navigation";
import ReactMarkdown from "react-markdown";
import ResolveIncidentButton from "@/components/ResolveIncidentButton";

interface Incident {
  id: number;
  service_name: string;
  alert_message: string;
  status: string;
  created_at: string;
  resolved_at: string | null;
  ai_summary: string | null;
  likely_commit: string | null;
  slack_message: string | null;
  postmortem: string | null;
}

const BACKEND_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

async function fetchIncident(id: string) {
  const res = await fetch(`${BACKEND_BASE}/incidents/${id}`, { cache: "no-store" });
  if (!res.ok) {
    return null;
  }
  return (await res.json()) as Incident;
}

function parseAISummary(summary: string) {
  const lines = summary.split("\n").map((line) => line.trim()).filter(Boolean);
  const result: Record<string, string> = { cause: "", impact: "", fix: "" };
  let current = "";
  for (const line of lines) {
    if (/^likely root cause[:\-]/i.test(line) || /^cause[:\-]/i.test(line)) {
      current = "cause";
      result.cause = line.replace(/^[^:]+[:\-]\s*/i, "");
    } else if (/^estimated user impact[:\-]/i.test(line) || /^impact[:\-]/i.test(line)) {
      current = "impact";
      result.impact = line.replace(/^[^:]+[:\-]\s*/i, "");
    } else if (/^suggested fix[:\-]/i.test(line) || /^fix[:\-]/i.test(line)) {
      current = "fix";
      result.fix = line.replace(/^[^:]+[:\-]\s*/i, "");
    } else if (current) {
      result[current] += ` ${line}`;
    }
  }
  return result;
}

export default async function IncidentDetail({ params }: { params: { id: string } }) {
  const incident = await fetchIncident(params.id);
  if (!incident) {
    notFound();
  }

  const ai = incident.ai_summary ? parseAISummary(incident.ai_summary) : null;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm text-slate-400">Incident Detail</p>
            <h1 className="text-3xl font-semibold text-white">#{incident.id} {incident.service_name}</h1>
          </div>
          <div className={`rounded-full px-4 py-2 text-sm font-semibold ${incident.status === "resolved" ? "bg-emerald-500/15 text-emerald-300" : "bg-rose-500/15 text-rose-300"}`}>
            {incident.status === "resolved" ? "Resolved" : "Active"}
          </div>
        </div>

        <div className="grid gap-6 xl:grid-cols-[1.4fr_0.8fr]">
          <section className="space-y-6">
            <div className="rounded-3xl border border-slate-800/80 bg-slate-900/80 p-6 shadow-lg shadow-slate-950/20">
              <div className="mb-5 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm text-slate-400">Alert message</p>
                  <h2 className="text-xl font-semibold text-white">{incident.alert_message}</h2>
                </div>
                <p className="text-sm text-slate-500">{new Date(incident.created_at).toLocaleString()}</p>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="rounded-2xl bg-slate-950/70 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Service</p>
                  <p className="mt-2 text-lg font-semibold text-white">{incident.service_name}</p>
                </div>
                <div className="rounded-2xl bg-slate-950/70 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Likely commit</p>
                  <p className="mt-2 text-lg font-semibold text-white">{incident.likely_commit || "None"}</p>
                </div>
              </div>
            </div>

            <div className="grid gap-6 lg:grid-cols-3">
              <div className="rounded-3xl border border-slate-800/80 bg-slate-900/80 p-6">
                <p className="text-sm uppercase tracking-[0.18em] text-slate-500">Likely cause</p>
                <p className="mt-3 text-base text-slate-100">{ai?.cause || "Not available"}</p>
              </div>
              <div className="rounded-3xl border border-slate-800/80 bg-slate-900/80 p-6">
                <p className="text-sm uppercase tracking-[0.18em] text-slate-500">Estimated impact</p>
                <p className="mt-3 text-base text-slate-100">{ai?.impact || "Not available"}</p>
              </div>
              <div className="rounded-3xl border border-slate-800/80 bg-slate-900/80 p-6">
                <p className="text-sm uppercase tracking-[0.18em] text-slate-500">Suggested fix</p>
                <p className="mt-3 text-base text-slate-100">{ai?.fix || "Not available"}</p>
              </div>
            </div>

            <div className="rounded-3xl border border-slate-800/80 bg-slate-900/80 p-6">
              <p className="text-sm uppercase tracking-[0.18em] text-slate-500">Slack preview</p>
              <div className="mt-4 rounded-3xl border border-slate-700/90 bg-slate-950/95 p-5 text-slate-100 shadow-lg shadow-slate-950/40">
                <pre className="whitespace-pre-wrap text-sm leading-6">{incident.slack_message || "Slack preview unavailable"}</pre>
              </div>
            </div>

            {incident.status === "resolved" && incident.postmortem ? (
              <div className="rounded-3xl border border-slate-800/80 bg-slate-900/80 p-6">
                <div className="mb-4 flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm uppercase tracking-[0.18em] text-slate-500">Postmortem</p>
                    <h2 className="text-xl font-semibold text-white">Review</h2>
                  </div>
                </div>
                <article className="prose prose-invert max-w-none">
                  <ReactMarkdown>{incident.postmortem}</ReactMarkdown>
                </article>
              </div>
            ) : (
              <div className="rounded-3xl border border-slate-800/80 bg-slate-900/80 p-6">
                <p className="text-sm text-slate-400">This incident has not been resolved yet.</p>
                <div className="mt-4">
                  <ResolveIncidentButton incidentId={incident.id} />
                </div>
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

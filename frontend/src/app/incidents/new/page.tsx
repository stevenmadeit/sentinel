"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const BACKEND_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

const SERVICE_OPTIONS = [
  "payments-service",
  "inventory-service",
  "auth-service",
  "notifications-service",
];

export default function NewIncidentPage() {
  const [serviceName, setServiceName] = useState(SERVICE_OPTIONS[0]);
  const [alertMessage, setAlertMessage] = useState("High error rate detected in /checkout API");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createdIncidentId, setCreatedIncidentId] = useState<number | null>(null);
  const router = useRouter();

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      const response = await fetch(`${BACKEND_BASE}/alert`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          service_name: serviceName,
          alert_message: alertMessage,
        }),
      });

      if (!response.ok) {
        const result = await response.json();
        throw new Error(result.detail || "Failed to create alert.");
      }

      const incident = await response.json();
      setCreatedIncidentId(incident.id);
      router.push(`/incidents/${incident.id}`);
    } catch (err) {
      setError((err as Error).message || "Unable to create alert.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-3xl px-4 py-10 sm:px-6 lg:px-8">
        <div className="mb-8 rounded-3xl border border-slate-800/80 bg-slate-900/80 p-8 shadow-lg shadow-slate-950/20">
          <p className="text-sm uppercase tracking-[0.18em] text-slate-500">Create Alert</p>
          <h1 className="mt-3 text-4xl font-semibold text-white">Send a simulated incident</h1>
          <p className="mt-2 text-slate-400">Generate an alert and let Sentinel enrich it with AI analysis, commit context, and Slack-style messaging.</p>
        </div>

        <form onSubmit={handleSubmit} className="grid gap-6 rounded-3xl border border-slate-800/80 bg-slate-900/80 p-8 shadow-lg shadow-slate-950/20">
          <div className="grid gap-2">
            <label htmlFor="serviceName" className="text-sm font-semibold text-slate-200">Service</label>
            <select
              id="serviceName"
              value={serviceName}
              onChange={(event) => setServiceName(event.target.value)}
              className="rounded-2xl border border-slate-700/90 bg-slate-950/80 px-4 py-3 text-slate-100 focus:border-slate-500 focus:outline-none"
            >
              {SERVICE_OPTIONS.map((service) => (
                <option key={service} value={service}>{service}</option>
              ))}
            </select>
          </div>

          <div className="grid gap-2">
            <label htmlFor="alertMessage" className="text-sm font-semibold text-slate-200">Alert message</label>
            <textarea
              id="alertMessage"
              rows={4}
              value={alertMessage}
              onChange={(event) => setAlertMessage(event.target.value)}
              className="rounded-3xl border border-slate-700/90 bg-slate-950/80 px-4 py-3 text-slate-100 focus:border-slate-500 focus:outline-none"
            />
          </div>

          {error ? <p className="text-sm text-rose-300">{error}</p> : null}

          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center justify-center rounded-2xl bg-slate-100 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-slate-200 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSubmitting ? "Sending alert..." : "Send alert"}
            </button>
            <button
              type="button"
              onClick={() => router.push("/")}
              className="inline-flex items-center justify-center rounded-2xl border border-slate-700/80 bg-transparent px-5 py-3 text-sm font-semibold text-slate-200 transition hover:border-slate-500 hover:text-white"
            >
              Back to dashboard
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

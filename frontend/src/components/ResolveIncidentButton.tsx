"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const BACKEND_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

interface ResolveIncidentButtonProps {
  incidentId: number;
}

export default function ResolveIncidentButton({ incidentId }: ResolveIncidentButtonProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const handleResolve = async () => {
    setIsSubmitting(true);
    setError(null);

    try {
      const response = await fetch(`${BACKEND_BASE}/incidents/${incidentId}/resolve`, {
        method: "POST",
      });
      if (!response.ok) {
        throw new Error("Failed to resolve incident.");
      }
      router.refresh();
    } catch (err) {
      setError((err as Error).message || "Unable to resolve incident.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-3">
      <button
        type="button"
        onClick={handleResolve}
        disabled={isSubmitting}
        className="inline-flex items-center justify-center rounded-2xl bg-slate-100 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-slate-200 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isSubmitting ? "Resolving..." : "Resolve Incident"}
      </button>
      {error ? <p className="text-sm text-rose-300">{error}</p> : null}
    </div>
  );
}

import { useState } from "react";
import { analyzeJD } from "../api";
import StatTile from "../components/StatTile";
import type { AnalyzeResponse } from "../types";

interface JDStepProps {
  analysis: AnalyzeResponse | null;
  onAnalyzed: (result: AnalyzeResponse) => void;
  onContinue: () => void;
}

const coverageDisplay: Record<0 | 1 | 2, { label: string; className: string }> = {
  0: { label: "0 · Missing", className: "bg-red-100 text-red-700 border-red-300" },
  1: {
    label: "1 · Partial",
    className: "bg-amber-100 text-amber-700 border-amber-300",
  },
  2: {
    label: "2 · Covered",
    className: "bg-emerald-100 text-emerald-700 border-emerald-300",
  },
};

export default function JDStep({ analysis, onAnalyzed, onContinue }: JDStepProps) {
  const [jdText, setJdText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleAnalyze() {
    if (!jdText.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await analyzeJD(jdText);
      onAnalyzed(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed.");
    } finally {
      setLoading(false);
    }
  }

  const report = analysis?.report ?? null;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">
          Paste the job description
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          We'll score how well your resume already matches it and propose
          edits to close the gaps.
        </p>
      </div>

      <textarea
        value={jdText}
        onChange={(e) => setJdText(e.target.value)}
        rows={12}
        placeholder="Paste the full job description here..."
        className="w-full rounded-md border border-slate-300 p-3 text-sm text-slate-900 focus:border-indigo-400 focus:outline-none"
      />

      {error && (
        <div className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="flex justify-end">
        <button
          type="button"
          onClick={handleAnalyze}
          disabled={loading || !jdText.trim()}
          className="rounded-md bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {loading ? "Analyzing..." : "Analyze"}
        </button>
      </div>

      {loading && (
        <div className="flex items-center gap-3 rounded-md border border-indigo-200 bg-indigo-50 p-4 text-sm text-indigo-700">
          <svg
            className="h-5 w-5 animate-spin text-indigo-500"
            viewBox="0 0 24 24"
            fill="none"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
            />
          </svg>
          <span>
            Running the match against your resume — this calls the LLM
            server-side and can take a little while. Hang tight.
          </span>
        </div>
      )}

      {report && (
        <div className="space-y-4">
          <div className="flex gap-4">
            <StatTile label="Keyword coverage" value={report.keyword_coverage_pct} />
            <StatTile label="Substantive fit score" value={report.substantive_fit_score} />
          </div>

          {report.must_have_gaps.length > 0 ? (
            <div className="rounded-md border border-amber-300 bg-amber-50 p-4">
              <h3 className="text-sm font-semibold text-amber-800">
                Must-have gaps
              </h3>
              <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-amber-800">
                {report.must_have_gaps.map((gap) => (
                  <li key={gap}>{gap}</li>
                ))}
              </ul>
            </div>
          ) : (
            <div className="rounded-md border border-emerald-300 bg-emerald-50 p-4 text-sm font-medium text-emerald-800">
              No must-have gaps — your resume covers every required
              qualification.
            </div>
          )}

          <div className="overflow-hidden rounded-lg border border-slate-200">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-100 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-4 py-2">Requirement</th>
                  <th className="px-4 py-2">Coverage</th>
                  <th className="px-4 py-2">Reasoning</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {report.per_requirement.map((row) => (
                  <tr key={row.requirement}>
                    <td className="px-4 py-3 align-top font-medium text-slate-800">
                      {row.requirement}
                    </td>
                    <td className="px-4 py-3 align-top">
                      <span
                        className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-semibold ${coverageDisplay[row.coverage].className}`}
                      >
                        {coverageDisplay[row.coverage].label}
                      </span>
                    </td>
                    <td className="px-4 py-3 align-top text-slate-500">
                      {row.reasoning}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex justify-end">
            <button
              type="button"
              onClick={onContinue}
              className="rounded-md bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500"
            >
              Review proposed changes
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

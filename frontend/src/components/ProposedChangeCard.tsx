import { useState } from "react";
import type { ChangeType, ProposedChange } from "../types";

export interface ChangeReviewState {
  accepted: boolean;
  text: string;
  confirmed: boolean; // only meaningful for tech_swap
}

interface ProposedChangeCardProps {
  change: ProposedChange;
  state: ChangeReviewState;
  onChange: (next: ChangeReviewState) => void;
}

const badgeConfig: Record<
  ChangeType,
  { label: string; className: string }
> = {
  rewrite: {
    label: "Rewrite",
    className: "bg-slate-100 text-slate-700 border-slate-300",
  },
  keyword_injection: {
    label: "Keyword added",
    className: "bg-amber-100 text-amber-800 border-amber-300",
  },
  tech_swap: {
    label: "Tech swap",
    className: "bg-red-100 text-red-800 border-red-300",
  },
};

export default function ProposedChangeCard({
  change,
  state,
  onChange,
}: ProposedChangeCardProps) {
  const [editing, setEditing] = useState(false);
  const badge = badgeConfig[change.change_type];
  const needsConfirmation = change.requires_confirmation;
  const canAccept = !needsConfirmation || state.confirmed;

  function setAccepted(accepted: boolean) {
    onChange({ ...state, accepted: accepted && canAccept });
  }

  function setText(text: string) {
    onChange({ ...state, text });
  }

  function setConfirmed(confirmed: boolean) {
    // Answering "No" (or resetting) revokes acceptance for a tech_swap,
    // since accepted state must not survive a confirmation reversal.
    onChange({
      ...state,
      confirmed,
      accepted: confirmed ? state.accepted : false,
    });
  }

  return (
    <div
      className={`rounded-xl border p-4 shadow-sm ${
        state.accepted
          ? "border-emerald-300 bg-emerald-50/40"
          : "border-slate-200 bg-white"
      }`}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span
          className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${badge.className}`}
        >
          {badge.label}
        </span>
        <div className="flex items-center gap-2">
          <span
            className={`text-xs font-medium ${
              state.accepted ? "text-emerald-700" : "text-slate-400"
            }`}
          >
            {state.accepted ? "Accepted" : "Not accepted"}
          </span>
          <div className="flex overflow-hidden rounded-md border border-slate-300">
            <button
              type="button"
              onClick={() => setAccepted(true)}
              disabled={!canAccept}
              className={`px-3 py-1 text-xs font-semibold transition ${
                state.accepted
                  ? "bg-emerald-600 text-white"
                  : "bg-white text-slate-600 hover:bg-slate-50"
              } ${!canAccept ? "cursor-not-allowed opacity-50" : ""}`}
            >
              Accept
            </button>
            <button
              type="button"
              onClick={() => setAccepted(false)}
              className={`border-l border-slate-300 px-3 py-1 text-xs font-semibold transition ${
                !state.accepted
                  ? "bg-red-500 text-white"
                  : "bg-white text-slate-600 hover:bg-slate-50"
              }`}
            >
              Reject
            </button>
          </div>
        </div>
      </div>

      <div className="mt-3 space-y-2">
        <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
          <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
            Original
          </div>
          <p className="text-sm text-slate-500 line-through decoration-slate-400">
            {change.original_text}
          </p>
        </div>

        <div
          className={`rounded-md border p-3 ${
            change.change_type === "tech_swap"
              ? "border-red-200 bg-red-50"
              : change.change_type === "keyword_injection"
                ? "border-amber-200 bg-amber-50"
                : "border-slate-200 bg-slate-50"
          }`}
        >
          <div className="mb-1 flex items-center justify-between">
            <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
              Proposed
            </div>
            <button
              type="button"
              onClick={() => setEditing((e) => !e)}
              className="text-xs font-medium text-indigo-600 hover:underline"
            >
              {editing ? "Done editing" : "Edit"}
            </button>
          </div>
          {editing ? (
            <textarea
              value={state.text}
              onChange={(e) => setText(e.target.value)}
              rows={3}
              className="w-full rounded-md border border-slate-300 p-2 text-sm text-slate-900 focus:border-indigo-400 focus:outline-none"
            />
          ) : (
            <p className="text-sm font-medium text-slate-900">{state.text}</p>
          )}
        </div>
      </div>

      <div className="mt-3 space-y-1 text-xs text-slate-500">
        <p>
          <span className="font-semibold text-slate-600">Rationale: </span>
          {change.rationale}
        </p>
        {change.related_requirement && (
          <p>
            <span className="font-semibold text-slate-600">
              Related requirement:{" "}
            </span>
            {change.related_requirement}
          </p>
        )}
      </div>

      {needsConfirmation && (
        <div className="mt-3 rounded-md border border-red-200 bg-red-50 p-3">
          <p className="text-sm font-medium text-red-900">
            {change.confirmation_prompt ??
              "This change swaps in a technology you don't have prior evidence for. Confirm you can honestly claim this?"}
          </p>
          <div className="mt-2 flex gap-2">
            <button
              type="button"
              onClick={() => setConfirmed(true)}
              className={`rounded-md border px-3 py-1 text-xs font-semibold transition ${
                state.confirmed
                  ? "border-emerald-600 bg-emerald-600 text-white"
                  : "border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
              }`}
            >
              Yes
            </button>
            <button
              type="button"
              onClick={() => setConfirmed(false)}
              className={`rounded-md border px-3 py-1 text-xs font-semibold transition ${
                !state.confirmed
                  ? "border-red-600 bg-red-600 text-white"
                  : "border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
              }`}
            >
              No
            </button>
          </div>
          {!state.confirmed && (
            <p className="mt-2 text-xs text-red-700">
              Accept is disabled until you confirm "Yes".
            </p>
          )}
        </div>
      )}
    </div>
  );
}

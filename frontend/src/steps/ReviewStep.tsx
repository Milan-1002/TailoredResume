import ProposedChangeCard, {
  type ChangeReviewState,
} from "../components/ProposedChangeCard";
import type { ProposedChange } from "../types";
import { groupByEmployerRole } from "../utils/groupBy";

interface ReviewStepProps {
  changes: ProposedChange[];
  states: Record<string, ChangeReviewState>;
  onStateChange: (changeId: string, next: ChangeReviewState) => void;
  onFinalize: () => void;
  finalizing: boolean;
  error: string | null;
}

export default function ReviewStep({
  changes,
  states,
  onStateChange,
  onFinalize,
  finalizing,
  error,
}: ReviewStepProps) {
  const acceptedCount = changes.filter((c) => states[c.id]?.accepted).length;

  const groups = groupByEmployerRole(
    changes,
    (c) => c.employer,
    (c) => c.role
  );

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">
          Review proposed changes
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Accept, reject, or edit each proposed change. Tech-swap changes
          need explicit confirmation before they can be accepted.
        </p>
      </div>

      {changes.length === 0 ? (
        <div className="rounded-md border border-slate-200 bg-slate-50 p-6 text-center text-sm text-slate-500">
          No changes were proposed — your resume already matches this job
          description well.
        </div>
      ) : (
        <div className="space-y-8">
          {groups.map((group) => (
            <div key={`${group.employer}__${group.role}`} className="space-y-3">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                {group.role} &middot; {group.employer}
              </h2>
              <div className="space-y-4">
                {group.items.map((change) => {
                  const state = states[change.id];
                  if (!state) return null;
                  return (
                    <ProposedChangeCard
                      key={change.id}
                      change={change}
                      state={state}
                      onChange={(next) => onStateChange(change.id, next)}
                    />
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}

      {error && (
        <div className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="sticky bottom-4 flex items-center justify-between rounded-lg border border-slate-200 bg-white/95 p-4 shadow-lg backdrop-blur">
        <span className="text-sm font-medium text-slate-700">
          {acceptedCount} of {changes.length} changes accepted
        </span>
        <button
          type="button"
          onClick={onFinalize}
          disabled={finalizing}
          className="rounded-md bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {finalizing ? "Generating..." : "Generate final resume"}
        </button>
      </div>
    </div>
  );
}

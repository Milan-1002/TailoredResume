import { useMemo, useState } from "react";
import { finalizeResume } from "./api";
import type { ChangeReviewState } from "./components/ProposedChangeCard";
import DoneStep from "./steps/DoneStep";
import JDStep from "./steps/JDStep";
import ReviewStep from "./steps/ReviewStep";
import UploadStep from "./steps/UploadStep";
import type {
  AnalyzeResponse,
  FinalizeResponse,
  ResumeBullet,
  Step,
} from "./types";

const STEP_LABELS: { key: Step; label: string }[] = [
  { key: "upload", label: "1. Upload resume" },
  { key: "jd", label: "2. Job description" },
  { key: "review", label: "3. Review changes" },
  { key: "done", label: "4. Download" },
];

function initialChangeState(): Record<string, ChangeReviewState> {
  return {};
}

export default function App() {
  const [step, setStep] = useState<Step>("upload");
  const [bullets, setBullets] = useState<ResumeBullet[]>([]);
  const [hasDocx, setHasDocx] = useState<boolean | null>(null);
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);
  const [changeStates, setChangeStates] = useState<
    Record<string, ChangeReviewState>
  >(initialChangeState());
  const [finalizing, setFinalizing] = useState(false);
  const [finalizeError, setFinalizeError] = useState<string | null>(null);
  const [finalizeResult, setFinalizeResult] = useState<FinalizeResponse | null>(
    null
  );

  const stepIndex = STEP_LABELS.findIndex((s) => s.key === step);

  function handleBulletsLoaded(
    newBullets: ResumeBullet[],
    docxFlag: boolean | null
  ) {
    setBullets(newBullets);
    if (docxFlag !== null) setHasDocx(docxFlag);
  }

  function handleAnalyzed(result: AnalyzeResponse) {
    setAnalysis(result);
    const initial: Record<string, ChangeReviewState> = {};
    for (const change of result.proposed_changes) {
      initial[change.id] = {
        // tech_swap defaults to NOT accepted until confirmed; everything
        // else defaults to accepted per spec.
        accepted: change.change_type !== "tech_swap",
        text: change.proposed_text,
        confirmed: false,
      };
    }
    setChangeStates(initial);
  }

  function handleChangeState(changeId: string, next: ChangeReviewState) {
    setChangeStates((prev) => ({ ...prev, [changeId]: next }));
  }

  const finalizePayload = useMemo(() => {
    if (!analysis) return [];
    return analysis.proposed_changes
      .filter((c) => changeStates[c.id]?.accepted)
      .map((c) => ({ bullet_id: c.bullet_id, text: changeStates[c.id].text }));
  }, [analysis, changeStates]);

  async function handleFinalize() {
    setFinalizing(true);
    setFinalizeError(null);
    try {
      const result = await finalizeResume({ bullets: finalizePayload });
      setFinalizeResult(result);
      setStep("done");
    } catch (err) {
      setFinalizeError(
        err instanceof Error ? err.message : "Finalizing failed."
      );
    } finally {
      setFinalizing(false);
    }
  }

  function handleStartOver() {
    setAnalysis(null);
    setChangeStates(initialChangeState());
    setFinalizeResult(null);
    setFinalizeError(null);
    setStep("jd");
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-4xl px-4 py-4">
          <h1 className="text-lg font-bold text-slate-900">Resume Tailor</h1>
          <nav className="mt-3 flex gap-4 text-sm">
            {STEP_LABELS.map((s, i) => (
              <span
                key={s.key}
                className={
                  i === stepIndex
                    ? "font-semibold text-indigo-600"
                    : i < stepIndex
                      ? "text-slate-500"
                      : "text-slate-300"
                }
              >
                {s.label}
              </span>
            ))}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-4 py-8">
        {step === "upload" && (
          <UploadStep
            bullets={bullets}
            onBulletsLoaded={handleBulletsLoaded}
            onContinue={() => setStep("jd")}
          />
        )}
        {step === "jd" && (
          <JDStep
            analysis={analysis}
            onAnalyzed={handleAnalyzed}
            onContinue={() => setStep("review")}
          />
        )}
        {step === "review" && analysis && (
          <ReviewStep
            changes={analysis.proposed_changes}
            states={changeStates}
            onStateChange={handleChangeState}
            onFinalize={handleFinalize}
            finalizing={finalizing}
            error={finalizeError}
          />
        )}
        {step === "done" && finalizeResult && (
          <DoneStep result={finalizeResult} onStartOver={handleStartOver} />
        )}
      </main>

      {hasDocx === false && step !== "upload" && (
        <div className="mx-auto max-w-4xl px-4 pb-4 text-xs text-slate-400">
          Note: your uploaded resume wasn't a .docx, so downloadable exports
          won't be available at the end.
        </div>
      )}
    </div>
  );
}

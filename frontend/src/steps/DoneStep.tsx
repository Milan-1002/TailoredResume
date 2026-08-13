import { downloadUrl } from "../api";
import type { FinalizeResponse } from "../types";

interface DoneStepProps {
  result: FinalizeResponse;
  onStartOver: () => void;
}

export default function DoneStep({ result, onStartOver }: DoneStepProps) {
  const noFilesAvailable = !result.docx_url && !result.pdf_url;

  return (
    <div className="mx-auto max-w-2xl space-y-6 text-center">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">
          Your tailored resume is ready
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          {result.edited_count} bullet{result.edited_count === 1 ? "" : "s"}{" "}
          updated, {result.skipped_count} left unchanged.
        </p>
      </div>

      {noFilesAvailable ? (
        <div className="rounded-md border border-amber-300 bg-amber-50 p-4 text-sm text-amber-800">
          No download is available because the original upload wasn't a
          .docx file. Downloadable .docx/.pdf export requires uploading the
          original .docx so formatting can be preserved and edited in place.
        </div>
      ) : (
        <div className="flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
          {result.docx_url && (
            <a
              href={downloadUrl(result.docx_url)}
              className="rounded-md bg-indigo-600 px-6 py-3 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500"
            >
              Download .docx
            </a>
          )}
          {result.pdf_url && (
            <a
              href={downloadUrl(result.pdf_url)}
              className="rounded-md bg-slate-800 px-6 py-3 text-sm font-semibold text-white shadow-sm hover:bg-slate-700"
            >
              Download .pdf
            </a>
          )}
        </div>
      )}

      <div>
        <button
          type="button"
          onClick={onStartOver}
          className="text-sm font-medium text-indigo-600 hover:underline"
        >
          Start a new tailoring pass
        </button>
      </div>
    </div>
  );
}

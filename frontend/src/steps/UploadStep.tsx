import { useEffect, useRef, useState } from "react";
import { getResumeBullets, uploadResume } from "../api";
import BulletCard from "../components/BulletCard";
import type { ResumeBullet } from "../types";
import { groupByEmployerRole } from "../utils/groupBy";

interface UploadStepProps {
  bullets: ResumeBullet[];
  onBulletsLoaded: (bullets: ResumeBullet[], hasDocx: boolean | null) => void;
  onContinue: () => void;
}

export default function UploadStep({
  bullets,
  onBulletsLoaded,
  onContinue,
}: UploadStepProps) {
  const [loadingInitial, setLoadingInitial] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const loadedOnce = useRef(false);

  useEffect(() => {
    if (loadedOnce.current) return;
    loadedOnce.current = true;
    (async () => {
      try {
        const existing = await getResumeBullets();
        if (existing.length > 0) {
          onBulletsLoaded(existing, null);
        }
      } catch {
        // No stored resume yet, or backend not reachable — fine, user can upload.
      } finally {
        setLoadingInitial(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleFile(file: File) {
    setUploading(true);
    setError(null);
    try {
      const result = await uploadResume(file);
      onBulletsLoaded(result.bullets, result.has_docx);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  function onDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) void handleFile(file);
  }

  const groups = groupByEmployerRole(
    bullets,
    (b) => b.employer,
    (b) => b.role
  );

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">
          Upload your master resume
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          We'll parse it into individual bullets tagged by employer, role,
          and skills. You only need to do this once.
        </p>
      </div>

      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={onDrop}
        className="flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed border-slate-300 bg-slate-50 p-10 text-center transition hover:border-indigo-400"
      >
        <p className="text-sm text-slate-600">
          Drag and drop your resume here, or
        </p>
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 disabled:opacity-50"
        >
          {uploading ? "Uploading..." : "Choose a file"}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".docx,.pdf,.txt"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) void handleFile(file);
            e.target.value = "";
          }}
        />
        <p className="text-xs text-slate-400">Accepted formats: .docx, .pdf, .txt</p>
      </div>

      {error && (
        <div className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {loadingInitial && (
        <p className="text-sm text-slate-400">Checking for an existing resume...</p>
      )}

      {bullets.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-slate-800">
            Parsed bullets ({bullets.length})
          </h2>
          {groups.map((group) => {
            const key = `${group.employer}__${group.role}`;
            const isCollapsed = collapsed[key] ?? false;
            return (
              <div
                key={key}
                className="overflow-hidden rounded-lg border border-slate-200"
              >
                <button
                  type="button"
                  onClick={() =>
                    setCollapsed((c) => ({ ...c, [key]: !isCollapsed }))
                  }
                  className="flex w-full items-center justify-between bg-slate-100 px-4 py-3 text-left"
                >
                  <span className="font-medium text-slate-800">
                    {group.role} &middot; {group.employer}
                  </span>
                  <span className="text-xs text-slate-500">
                    {group.items.length} bullet
                    {group.items.length === 1 ? "" : "s"} {isCollapsed ? "▸" : "▾"}
                  </span>
                </button>
                {!isCollapsed && (
                  <div className="space-y-2 p-4">
                    {group.items.map((bullet) => (
                      <BulletCard key={bullet.id} bullet={bullet} />
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      <div className="flex justify-end">
        <button
          type="button"
          onClick={onContinue}
          disabled={bullets.length === 0}
          className="rounded-md bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Continue
        </button>
      </div>
    </div>
  );
}

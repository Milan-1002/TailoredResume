import type { ResumeBullet } from "../types";

export default function BulletCard({ bullet }: { bullet: ResumeBullet }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-sm text-slate-800">{bullet.text}</p>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {bullet.skills.map((skill) => (
          <span
            key={skill}
            className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600"
          >
            {skill}
          </span>
        ))}
      </div>
      {(bullet.seniority_signal || bullet.quantified_outcome) && (
        <div className="mt-3 space-y-1 border-t border-slate-100 pt-2 text-xs text-slate-500">
          {bullet.seniority_signal && (
            <div>
              <span className="font-semibold text-slate-600">Seniority: </span>
              {bullet.seniority_signal}
            </div>
          )}
          {bullet.quantified_outcome && (
            <div>
              <span className="font-semibold text-slate-600">Outcome: </span>
              {bullet.quantified_outcome}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

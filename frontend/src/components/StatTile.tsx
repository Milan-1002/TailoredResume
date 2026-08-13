interface StatTileProps {
  label: string;
  value: number;
  suffix?: string;
  tone?: "default" | "good" | "warn" | "bad";
}

const toneClasses: Record<NonNullable<StatTileProps["tone"]>, string> = {
  default: "bg-slate-50 border-slate-200 text-slate-900",
  good: "bg-emerald-50 border-emerald-200 text-emerald-900",
  warn: "bg-amber-50 border-amber-200 text-amber-900",
  bad: "bg-red-50 border-red-200 text-red-900",
};

function toneForScore(value: number): NonNullable<StatTileProps["tone"]> {
  if (value >= 75) return "good";
  if (value >= 45) return "warn";
  return "bad";
}

export default function StatTile({
  label,
  value,
  suffix = "%",
  tone,
}: StatTileProps) {
  const resolvedTone = tone ?? toneForScore(value);
  return (
    <div
      className={`flex-1 rounded-xl border p-5 shadow-sm ${toneClasses[resolvedTone]}`}
    >
      <div className="text-sm font-medium opacity-70">{label}</div>
      <div className="mt-1 text-4xl font-semibold tabular-nums">
        {Math.round(value)}
        <span className="text-xl align-top">{suffix}</span>
      </div>
    </div>
  );
}

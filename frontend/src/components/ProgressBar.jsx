export default function ProgressBar({ value, max = 100, color = 'amber' }) {
  const pct = Math.min(100, Math.round((value / max) * 100))
  const colors = {
    amber:   'bg-amber-400',
    emerald: 'bg-emerald-400',
    sky:     'bg-sky-400',
    rose:    'bg-rose-400',
  }
  return (
    <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
      <div
        className={`h-full rounded-full transition-all duration-700 ${colors[color] ?? colors.amber}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}
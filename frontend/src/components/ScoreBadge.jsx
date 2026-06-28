export default function ScoreBadge({ score, max = 20, size = 'md' }) {
  if (score === null || score === undefined) {
    return <span className="badge bg-slate-800 text-slate-400">Pending</span>
  }
  const pct = (score / max) * 100
  const { bg, text, ring } =
    pct >= 100 ? { bg: 'bg-amber-500/15', text: 'text-amber-300', ring: 'ring-amber-500/30' } :
    pct >= 90  ? { bg: 'bg-emerald-500/15',text: 'text-emerald-300',ring: 'ring-emerald-500/30'}:
    pct >= 75  ? { bg: 'bg-sky-500/15',    text: 'text-sky-300',    ring: 'ring-sky-500/30'   }:
    pct >= 50  ? { bg: 'bg-slate-700/50',  text: 'text-slate-300',  ring: 'ring-slate-600'    }:
                 { bg: 'bg-rose-500/15',   text: 'text-rose-300',   ring: 'ring-rose-500/30'  }

  const sz = size === 'lg' ? 'px-3 py-1 text-sm' : 'px-2 py-0.5 text-xs'
  return (
    <span className={`badge ring-1 font-mono ${bg} ${text} ${ring} ${sz}`}>
      {score}/{max}
    </span>
  )
}
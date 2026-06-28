import { Loader2, CheckCircle, XCircle, Clock, AlertCircle, Zap } from 'lucide-react'

const STATUS_MAP = {
  pending:     { label: 'Pending',     color: 'text-slate-400 bg-slate-800',           icon: Clock },
  queued:      { label: 'Queued',      color: 'text-sky-300 bg-sky-500/10',             icon: Zap },
  compiling:   { label: 'Compiling',   color: 'text-amber-300 bg-amber-500/10',         icon: Loader2, spin: true },
  running:     { label: 'Running',     color: 'text-sky-300 bg-sky-500/10',             icon: Loader2, spin: true },
  evaluating:  { label: 'Evaluating',  color: 'text-amber-300 bg-amber-500/10',         icon: Loader2, spin: true },
  completed:   { label: 'Completed',   color: 'text-emerald-300 bg-emerald-500/10',     icon: CheckCircle },
  failed:      { label: 'Failed',      color: 'text-rose-300 bg-rose-500/10',           icon: XCircle },
  compile_error:{ label:'Compile Error',color:'text-rose-300 bg-rose-500/10',           icon: AlertCircle },
  timeout:     { label: 'Timeout',     color: 'text-orange-300 bg-orange-500/10',       icon: Clock },
}

export default function StatusBadge({ status }) {
  const cfg = STATUS_MAP[status] || STATUS_MAP.pending
  const Icon = cfg.icon
  return (
    <span className={`badge ring-1 ring-current/20 ${cfg.color}`}>
      <Icon size={11} className={cfg.spin ? 'animate-spin' : ''} />
      {cfg.label}
    </span>
  )
}
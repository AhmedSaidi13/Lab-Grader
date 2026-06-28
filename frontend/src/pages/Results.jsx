import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  CheckCircle, XCircle, Clock, ChevronLeft,
  Terminal, Code2, AlertTriangle, BarChart3,
  ChevronDown, ChevronUp
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { submissionsAPI } from '../api/client'
import ScoreBadge  from '../components/ScoreBadge'
import StatusBadge from '../components/StatusBadge'
import ProgressBar from '../components/ProgressBar'

const POLLING_INTERVAL = 2000
const DONE_STATUSES = ['completed', 'compile_error', 'failed', 'timeout']

function TestRow({ result }) {
  const [open, setOpen] = useState(false)
  return (
    <div className={`rounded-lg border transition-colors
      ${result.passed
        ? 'border-emerald-500/20 bg-emerald-500/5'
        : 'border-rose-500/20 bg-rose-500/5'}`}>
      <button onClick={() => setOpen(v => !v)}
        className="w-full flex items-center gap-3 p-3 text-left">
        {result.passed
          ? <CheckCircle size={14} className="text-emerald-400 shrink-0" />
          : result.timed_out
            ? <Clock size={14} className="text-orange-400 shrink-0" />
            : <XCircle size={14} className="text-rose-400 shrink-0" />}
        <div className="flex-1 min-w-0">
          <p className="text-sm text-slate-200 font-medium truncate">{result.description}</p>
          <p className="text-xs text-slate-500 font-mono">
            {result.execution_time_ms?.toFixed(0)}ms ·
            {result.points_earned}/{result.points_possible}pt
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {result.timed_out && (
            <span className="badge bg-orange-500/10 text-orange-300 text-xs">Timeout</span>
          )}
          {open ? <ChevronUp size={13} className="text-slate-500" />
                : <ChevronDown size={13} className="text-slate-500" />}
        </div>
      </button>

      {open && (
        <div className="px-3 pb-3 space-y-2 border-t border-slate-800/50 pt-2">
          <div className="grid grid-cols-2 gap-2 text-xs font-mono">
            <div>
              <p className="text-slate-500 mb-1">Input</p>
              <pre className="bg-slate-950 rounded p-2 text-slate-300 overflow-x-auto
                              whitespace-pre-wrap text-xs">
                {result.input || '(none)'}
              </pre>
            </div>
            <div>
              <p className="text-slate-500 mb-1">Expected</p>
              <pre className="bg-slate-950 rounded p-2 text-emerald-300/80 overflow-x-auto
                              whitespace-pre-wrap text-xs">
                {result.expected_output}
              </pre>
            </div>
          </div>
          {!result.passed && (
            <div>
              <p className="text-xs text-slate-500 font-mono mb-1">Your Output</p>
              <pre className="bg-slate-950 rounded p-2 text-rose-300/80 overflow-x-auto
                              whitespace-pre-wrap text-xs font-mono">
                {result.actual_output || '(empty)'}
              </pre>
              {result.diff_hint && (
                <p className="text-xs text-orange-400 mt-1 flex items-start gap-1">
                  <AlertTriangle size={10} className="mt-0.5 shrink-0" />
                  {result.diff_hint}
                </p>
              )}
            </div>
          )}
          {result.stderr && (
            <div>
              <p className="text-xs text-slate-500 font-mono mb-1">Stderr</p>
              <pre className="bg-slate-950 rounded p-2 text-slate-500 overflow-x-auto
                              whitespace-pre-wrap text-xs font-mono">
                {result.stderr}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function ScoreGauge({ score, max }) {
  const pct = max > 0 ? Math.round((score / max) * 100) : 0
  const color =
    pct >= 100 ? '#f59e0b' :
    pct >= 90  ? '#10b981' :
    pct >= 75  ? '#0ea5e9' :
    pct >= 50  ? '#94a3b8' : '#f43f5e'
  const r = 52
  const circ = 2 * Math.PI * r
  const dash = (pct / 100) * circ

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-32 h-32">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 120 120">
          <circle cx="60" cy="60" r={r} stroke="#1e293b" strokeWidth="10" fill="none" />
          <circle cx="60" cy="60" r={r} stroke={color} strokeWidth="10" fill="none"
            strokeDasharray={`${dash} ${circ}`}
            strokeLinecap="round"
            style={{ transition: 'stroke-dasharray 1s ease' }} />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-display text-2xl text-slate-100">{score}</span>
          <span className="text-xs text-slate-500 font-mono">/{max}</span>
        </div>
      </div>
    </div>
  )
}

const LEVEL_STYLES = {
  success: {
    border: 'border-emerald-500/20',
    bg:     'bg-emerald-500/5',
    icon:   <CheckCircle size={14} className="text-emerald-400 shrink-0 mt-0.5" />,
    title:  'text-emerald-300',
  },
  error: {
    border: 'border-rose-500/20',
    bg:     'bg-rose-500/5',
    icon:   <XCircle size={14} className="text-rose-400 shrink-0 mt-0.5" />,
    title:  'text-rose-300',
  },
  warning: {
    border: 'border-amber-500/20',
    bg:     'bg-amber-500/5',
    icon:   <AlertTriangle size={14} className="text-amber-400 shrink-0 mt-0.5" />,
    title:  'text-amber-300',
  },
  tip: {
    border: 'border-sky-500/20',
    bg:     'bg-sky-500/5',
    icon:   <Code2 size={14} className="text-sky-400 shrink-0 mt-0.5" />,
    title:  'text-sky-300',
  },
  info: {
    border: 'border-slate-700',
    bg:     'bg-slate-800/40',
    icon:   <Terminal size={14} className="text-slate-400 shrink-0 mt-0.5" />,
    title:  'text-slate-300',
  },
}

function FeedbackSectionCard({ section }) {
  const [codeOpen, setCodeOpen] = useState(false)
  const style = LEVEL_STYLES[section.level] ?? LEVEL_STYLES.info

  // Minimal markdown: bold (**text**) and code (`text`)
  const renderBody = text =>
    text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**'))
        return <strong key={i} className="text-slate-200 font-semibold">
          {part.slice(2, -2)}
        </strong>
      if (part.startsWith('`') && part.endsWith('`'))
        return <code key={i} className="font-mono text-amber-300 bg-slate-900
                                         px-1 py-0.5 rounded text-xs">
          {part.slice(1, -1)}
        </code>
      return <span key={i}>{part}</span>
    })

  return (
    <div className={`rounded-xl border p-4 ${style.border} ${style.bg}`}>
      <div className="flex items-start gap-2 mb-2">
        {style.icon}
        <h3 className={`text-sm font-semibold ${style.title}`}>{section.title}</h3>
      </div>
      <div className="text-sm text-slate-400 leading-relaxed space-y-1 pl-5">
        {section.body.split('\n').map((line, i) => (
          <p key={i}>{renderBody(line)}</p>
        ))}
      </div>

      {/* Code hint toggle */}
      {section.code && (
        <div className="mt-3 pl-5">
          <button
            onClick={() => setCodeOpen(v => !v)}
            className="text-xs text-sky-400 hover:text-sky-300 flex items-center gap-1
                       transition-colors">
            <Code2 size={11} />
            {codeOpen ? 'Hide' : 'Show'} code hint
            {codeOpen
              ? <ChevronUp size={11} />
              : <ChevronDown size={11} />}
          </button>
          {codeOpen && (
            <pre className="mt-2 bg-slate-950 rounded-lg p-3 text-xs font-mono
                            text-slate-300 overflow-x-auto whitespace-pre border
                            border-slate-800 leading-relaxed">
              {section.code}
            </pre>
          )}
        </div>
      )}
    </div>
  )
}

export default function Results() {
  const { id } = useParams()
  const [polling, setPolling] = useState(true)

  const { data: sub, refetch } = useQuery({
    queryKey: ['submission', id],
    queryFn:  () => submissionsAPI.get(id).then(r => r.data),
    refetchInterval: polling ? POLLING_INTERVAL : false,
  })

  const { data: report } = useQuery({
    queryKey: ['report', id],
    queryFn:  () => submissionsAPI.report(id).then(r => r.data),
    enabled:  !!sub && DONE_STATUSES.includes(sub.status),
  })

  const { data: liveStatus } = useQuery({
    queryKey: ['sub-status', id],
    queryFn:  () => submissionsAPI.status(id).then(r => r.data),
    refetchInterval: polling ? POLLING_INTERVAL : false,
  })

  useEffect(() => {
    if (sub && DONE_STATUSES.includes(sub.status)) {
      setPolling(false)
    }
  }, [sub])

  const isDone    = sub && DONE_STATUSES.includes(sub.status)
  const progress  = liveStatus?.celery?.progress
  const testResults = report?.test_results ?? []
  const passed    = testResults.filter(t => t.passed).length
  const sa        = report?.static_analysis ?? {}

  const { data: feedbackData, refetch: refetchFeedback } = useQuery({
    queryKey: ['feedback', id],
    queryFn:  () => submissionsAPI.getFeedback(id).then(r => r.data),
    enabled:  isDone,
    retry:    false,
  })

  return (
    <div className="space-y-6 animate-fade-up max-w-3xl mx-auto">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm">
        <Link to={`/assignments/${sub?.assignment_id}`}
          className="text-slate-500 hover:text-slate-300 flex items-center gap-1">
          <ChevronLeft size={14} /> Assignment
        </Link>
        <span className="text-slate-700">/</span>
        <span className="text-slate-400 font-mono">submission #{id}</span>
      </div>

      {/* Status card */}
      <div className="card p-6">
        <div className="flex items-start justify-between gap-6">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <h1 className="font-display text-xl text-slate-100">Evaluation Results</h1>
              {sub && <StatusBadge status={sub.status} />}
            </div>
            {sub && (
              <p className="text-xs text-slate-500 font-mono">
                Submitted {formatDistanceToNow(new Date(sub.submitted_at), { addSuffix: true })}
                {sub.is_late && (
                  <span className="ml-2 text-orange-400">[late submission]</span>
                )}
              </p>
            )}

            {/* Live progress */}
            {!isDone && progress && (
              <div className="mt-4 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400 font-mono">{progress.message}</span>
                  <span className="text-amber-400 font-mono">{progress.percent}%</span>
                </div>
                <ProgressBar value={progress.percent} color="amber" />
              </div>
            )}
            {!isDone && !progress && (
              <div className="mt-4 flex items-center gap-2 text-sm text-slate-500">
                <div className="w-3.5 h-3.5 border-2 border-amber-500 border-t-transparent
                                rounded-full animate-spin" />
                Waiting for evaluation…
              </div>
            )}
          </div>

          {/* Score gauge — show when done */}
          {isDone && sub?.score !== null && sub?.score !== undefined && (
            <ScoreGauge score={sub.score} max={report?.score?.max ?? 20} />
          )}
        </div>

        {/* Score breakdown */}
        {isDone && report && (
          <div className="mt-4 pt-4 border-t border-slate-800 grid grid-cols-3 gap-4 text-center">
            <div>
              <p className="text-xs text-slate-500 mb-1">Tests Passed</p>
              <p className="font-display text-lg text-slate-200">
                {passed}/{testResults.length}
              </p>
              <ProgressBar
                value={testResults.length > 0 ? (passed / testResults.length) * 100 : 0}
                color="emerald"
              />
            </div>
            <div>
              <p className="text-xs text-slate-500 mb-1">Final Score</p>
              <ScoreBadge score={sub.score} max={report?.score?.max ?? 20} size="lg" />
            </div>
            <div>
              <p className="text-xs text-slate-500 mb-1">Grade</p>
              <p className={`font-display text-lg
                ${sub.score >= (report?.score?.max ?? 20)   ? 'text-amber-400'  :
                  sub.score >= (report?.score?.max ?? 20)*0.9 ? 'text-emerald-400':
                  sub.score >= (report?.score?.passing ?? 10) ? 'text-sky-400'  :
                                                                 'text-rose-400'  }`}>
                {sub.score >= (report?.score?.max ?? 20)     ? 'Perfect'    :
                 sub.score >= (report?.score?.max ?? 20)*0.9  ? 'Excellent'  :
                 sub.score >= (report?.score?.max ?? 20)*0.75 ? 'Good'       :
                 sub.score >= (report?.score?.passing ?? 10)  ? 'Pass'       :
                 sub.score >= (report?.score?.max ?? 20)*0.4  ? 'Needs Work' :
                                                                 'Fail'        }
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Compile output */}
      {isDone && report?.compile_output && (
        <div className="card p-5">
          <h2 className="font-semibold text-slate-200 flex items-center gap-2 mb-3">
            <Terminal size={14} className="text-amber-400" /> Compiler Output
          </h2>
          <pre className={`text-xs font-mono p-3 rounded-lg overflow-x-auto whitespace-pre-wrap
            ${sub?.status === 'compile_error'
              ? 'bg-rose-950/30 text-rose-300 border border-rose-500/20'
              : 'bg-slate-800 text-emerald-300/80'}`}>
            {report.compile_output}
          </pre>
        </div>
      )}

      {/* Feedback */}
      {isDone && feedbackData && (
        <div className="card p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-slate-200 flex items-center gap-2">
              <Code2 size={14} className="text-amber-400" /> Feedback
            </h2>
            {feedbackData.generated_by_llm && (
              <span className="badge bg-sky-500/10 text-sky-300 text-xs">
                AI-enhanced
              </span>
            )}
            {feedbackData.teacher_override && (
              <span className="badge bg-amber-500/10 text-amber-300 text-xs">
                Teacher note
              </span>
            )}
          </div>

          {feedbackData.sections?.map((section, i) => (
            <FeedbackSectionCard key={i} section={section} />
          ))}
        </div>
      )}

      {/* Test results */}
      {isDone && testResults.length > 0 && (
        <div className="card p-5">
          <h2 className="font-semibold text-slate-200 flex items-center gap-2 mb-4">
            <BarChart3 size={14} className="text-amber-400" />
            Test Results
            <span className="ml-auto text-xs font-mono text-slate-500">
              {passed}/{testResults.length} passed
            </span>
          </h2>
          <div className="space-y-2">
            {testResults.map((r, i) => <TestRow key={i} result={r} />)}
          </div>
        </div>
      )}

      {/* Static analysis */}
      {isDone && sa && Object.keys(sa).length > 0 && (
        <div className="card p-5">
          <h2 className="font-semibold text-slate-200 flex items-center gap-2 mb-4">
            <Code2 size={14} className="text-amber-400" /> Static Analysis
          </h2>
          <div className="grid sm:grid-cols-2 gap-4 text-xs font-mono">
            <div className="space-y-1">
              <p className="text-slate-500">Functions
                <span className="text-slate-200 ml-2">
                  {sa.function_names?.join(', ') || '—'}
                </span>
              </p>
              <p className="text-slate-500">Lines
                <span className="text-slate-200 ml-2">{sa.line_count}</span>
              </p>
              <p className="text-slate-500">Complexity
                <span className="text-slate-200 ml-2">{sa.cyclomatic_complexity}</span>
              </p>
              <p className="text-slate-500">Loops
                <span className="text-slate-200 ml-2">
                  {sa.control_flow?.loops ?? 0}
                </span>
              </p>
            </div>
            <div className="space-y-1">
              <p className="text-slate-500">Includes
                <span className="text-slate-200 ml-2">
                  {sa.includes?.join(', ') || '—'}
                </span>
              </p>
              <p className="text-slate-500">Recursion
                <span className="text-slate-200 ml-2">
                  {sa.control_flow?.recursions > 0 ? 'Yes' : 'No'}
                </span>
              </p>
              <p className="text-slate-500">Uses malloc
                <span className="text-slate-200 ml-2">
                  {sa.io_patterns?.malloc ? 'Yes' : 'No'}
                </span>
              </p>
            </div>
          </div>
          {sa.warnings?.length > 0 && (
            <div className="mt-3 space-y-1">
              {sa.warnings.map((w, i) => (
                <p key={i} className="text-xs text-orange-400 flex items-start gap-1.5">
                  <AlertTriangle size={11} className="mt-0.5 shrink-0" /> {w}
                </p>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}


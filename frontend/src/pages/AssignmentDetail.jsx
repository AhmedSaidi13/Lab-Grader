import { useState, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Upload, Download, Zap, BarChart3, RefreshCw,
  ChevronLeft, FlaskConical, Users, FileCode,
  CheckCircle, AlertCircle, Clock, Eye, EyeOff,
  Trash2, BookOpen
} from 'lucide-react'
import { format, formatDistanceToNow } from 'date-fns'
import toast from 'react-hot-toast'
import useAuthStore from '../store/authStore'
import { assignmentsAPI, submissionsAPI } from '../api/client'
import ScoreBadge  from '../components/ScoreBadge'
import StatusBadge from '../components/StatusBadge'
import ProgressBar from '../components/ProgressBar'

// ── File upload button ────────────────────────────────────────

function UploadBtn({ label, accept, onUpload, loading }) {
  const ref = useRef()
  return (
    <div>
      <input
        ref={ref}
        type="file"
        accept={accept}
        className="hidden"
        onChange={e => e.target.files[0] && onUpload(e.target.files[0])}
      />
      <button
        onClick={() => ref.current.click()}
        disabled={loading}
        className="btn-secondary flex items-center gap-2 text-xs"
      >
        <Upload size={13} />
        {loading ? 'Uploading…' : label}
      </button>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────

export default function AssignmentDetail() {
  const { id }        = useParams()
  const { isTeacher } = useAuthStore()
  const qc            = useQueryClient()

  const [genLoading, setGenLoading] = useState(false)
  const [analysis,   setAnalysis]   = useState(null)

  // ── Data queries ────────────────────────────────────────────

  const { data: assignment, isLoading } = useQuery({
    queryKey: ['assignment', id],
    queryFn:  () => assignmentsAPI.get(id).then(r => r.data),
  })

  const { data: testCases } = useQuery({
    queryKey: ['test-cases', id],
    queryFn:  () => assignmentsAPI.listTestCases(id).then(r => r.data),
    enabled:  !!isTeacher(),
  })

  const { data: stats } = useQuery({
    queryKey: ['stats', id],
    queryFn:  () => submissionsAPI.stats(id).then(r => r.data),
    enabled:  !!isTeacher(),
  })

  const { data: leaderboard = [] } = useQuery({
    queryKey: ['leaderboard', id],
    queryFn:  () => submissionsAPI.leaderboard(id).then(r => r.data),
    enabled:  !!isTeacher(),
  })

  const { data: mySub } = useQuery({
    queryKey: ['my-sub', id],
    queryFn:  () => submissionsAPI.mySubmissionFor(id).then(r => r.data),
    enabled:  !isTeacher(),
    retry:    false,
  })

  // ── Mutations ───────────────────────────────────────────────

  const togglePublish = useMutation({
    mutationFn: () => assignmentsAPI.update(id, {
      is_published: !assignment?.is_published,
    }),
    onSuccess: () => {
      toast.success(
        assignment?.is_published ? 'Assignment unpublished' : 'Assignment published!'
      )
      qc.invalidateQueries({ queryKey: ['assignment', id] })
      qc.invalidateQueries({ queryKey: ['assignments'] })
    },
  })

  const bulkReevaluate = useMutation({
    mutationFn: () => submissionsAPI.bulkReevaluate(id),
    onSuccess:  r  => toast.success(
      `Re-evaluation started (task: ${r.data.task_id?.slice(0, 8)}…)`
    ),
  })

  // ── File upload handler ─────────────────────────────────────

  const uploadFile = (type) => async (file) => {
    const form = new FormData()
    form.append('file', file)
    try {
      if (type === 'solution') await assignmentsAPI.uploadSolution(id, form)
      if (type === 'label')    await assignmentsAPI.uploadLabel(id, form)
      if (type === 'subject')  await assignmentsAPI.uploadSubject(id, form)
      toast.success('File uploaded successfully!')
      qc.invalidateQueries({ queryKey: ['assignment', id] })
    } catch { /* interceptor handles error toast */ }
  }

  // ── Auto-generate tests ─────────────────────────────────────

  const generateTests = async () => {
    setGenLoading(true)
    try {
      const res = await assignmentsAPI.generateTests(id)
      toast.success(`Generated ${res.data.count} test cases!`)
      qc.invalidateQueries({ queryKey: ['test-cases', id] })
      qc.invalidateQueries({ queryKey: ['assignment', id] })
    } catch { }
    finally { setGenLoading(false) }
  }

  // ── Analyse reference solution ──────────────────────────────

  const analyseRef = async () => {
    try {
      const res = await assignmentsAPI.analyseReference(id)
      setAnalysis(res.data)
    } catch { }
  }

  // ── Download subject file ───────────────────────────────────

  const download = async () => {
    try {
      const res = await assignmentsAPI.downloadSubject(id)
      const url = URL.createObjectURL(res.data)
      const a   = document.createElement('a')
      a.href    = url
      a.download = `assignment-${id}-subject`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      toast.error('No subject file available')
    }
  }

  // ── Loading / not found ─────────────────────────────────────

  if (isLoading) return (
    <div className="flex items-center justify-center h-64">
      <div className="w-6 h-6 border-2 border-amber-500 border-t-transparent
                      rounded-full animate-spin" />
    </div>
  )

  if (!assignment) return (
    <div className="text-center py-16 text-slate-500">
      <BookOpen size={32} className="mx-auto mb-3 opacity-40" />
      <p>Assignment not found</p>
    </div>
  )

  // ── Derived values ──────────────────────────────────────────

  const deadline    = assignment.deadline ? new Date(assignment.deadline) : null
  const isPast      = deadline && deadline < new Date()
  const hoursLeft   = deadline ? (deadline - Date.now()) / 36e5 : null
  const urgent      = hoursLeft !== null && hoursLeft > 0 && hoursLeft < 48
  const tcCount     = testCases?.count ?? assignment.test_case_count ?? 0

  // ── Render ──────────────────────────────────────────────────

  return (
    <div className="space-y-6 animate-fade-up">

      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm">
        <Link to="/assignments"
          className="text-slate-500 hover:text-slate-300
                     flex items-center gap-1 transition-colors">
          <ChevronLeft size={14} /> Assignments
        </Link>
        <span className="text-slate-700">/</span>
        <span className="text-slate-400 truncate">{assignment.title}</span>
      </div>

      {/* ── Header card ── */}
      <div className="card p-6">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex-1 min-w-0">

            {/* Title + status badges */}
            <div className="flex items-center gap-2 flex-wrap mb-2">
              <h1 className="font-display text-2xl text-slate-100">
                {assignment.title}
              </h1>
              <span className={`badge ${
                assignment.is_published
                  ? 'text-emerald-300 bg-emerald-500/10'
                  : 'text-slate-400 bg-slate-800'
              }`}>
                {assignment.is_published ? 'Published' : 'Draft'}
              </span>
              {urgent && (
                <span className="badge bg-rose-500/10 text-rose-400">
                  Urgent
                </span>
              )}
              {isPast && (
                <span className="badge bg-slate-800 text-slate-500">
                  Closed
                </span>
              )}
            </div>

            {/* Description */}
            <p className="text-slate-400 text-sm leading-relaxed">
              {assignment.description}
            </p>

            {/* Instructions */}
            {assignment.instructions && (
              <p className="text-slate-500 text-sm mt-2 border-l-2
                            border-slate-700 pl-3 italic">
                {assignment.instructions}
              </p>
            )}
          </div>

          {/* Score display */}
          <div className="shrink-0 text-right">
            <p className="font-mono text-3xl text-amber-400">20</p>
            <p className="text-slate-600 text-xs">points</p>
          </div>
        </div>

        {/* Meta row */}
        <div className="flex flex-wrap items-center gap-4 mt-4 pt-4
                        border-t border-slate-800 text-xs text-slate-500 font-mono">

          {deadline ? (
            <span className={`flex items-center gap-1.5 ${
              isPast   ? 'text-slate-600' :
              urgent   ? 'text-rose-400'  : 'text-slate-400'
            }`}>
              <Clock size={12} />
              {isPast
                ? `Closed ${formatDistanceToNow(deadline, { addSuffix: true })}`
                : `Due ${formatDistanceToNow(deadline, { addSuffix: true })}`
              }
              <span className="text-slate-600">
                ({format(deadline, 'PPp')})
              </span>
            </span>
          ) : (
            <span className="text-slate-600 flex items-center gap-1">
              <Clock size={12} /> No deadline
            </span>
          )}

          <span>{tcCount} test case{tcCount !== 1 ? 's' : ''}</span>
          <span>Pass: {assignment.passing_score}/20</span>
          <span>
            Max files: {assignment.max_files || 1}
          </span>

          {assignment.allow_late_submission && (
            <span className="badge bg-amber-500/10 text-amber-400">
              Late: -{assignment.late_penalty_percent}%
            </span>
          )}
        </div>

        {/* Deadline progress bar */}
        {!isPast && deadline && hoursLeft !== null && (
          <div className="mt-3 max-w-xs">
            <ProgressBar
              value={Math.max(0, 100 - (hoursLeft / 168) * 100)}
              color={urgent ? 'rose' : 'sky'}
            />
          </div>
        )}

        {/* Student CTA */}
        {!isTeacher() && (
          <div className="flex flex-wrap gap-3 mt-5">
            {!isPast ? (
              <Link
                to={`/assignments/${id}/submit`}
                className="btn-primary flex items-center gap-2"
              >
                <FileCode size={14} />
                {mySub ? 'Replace Solution' : 'Submit Solution'}
              </Link>
            ) : (
              <div className="flex items-center gap-2 text-sm text-slate-500">
                <Clock size={14} className="text-rose-400" />
                Deadline passed — evaluation runs automatically
              </div>
            )}
            {assignment.assignment_file_path && (
              <button
                onClick={download}
                className="btn-secondary flex items-center gap-2"
              >
                <Download size={14} /> Download Subject
              </button>
            )}
          </div>
        )}

        {/* Teacher quick actions */}
        {isTeacher() && (
          <div className="flex flex-wrap gap-2 mt-5">
            <button
              onClick={() => togglePublish.mutate()}
              disabled={togglePublish.isPending}
              className={`flex items-center gap-2 text-xs px-3 py-1.5 rounded-lg
                         border transition-all ${
                assignment.is_published
                  ? 'border-slate-700 text-slate-400 hover:text-rose-400 hover:border-rose-400/30'
                  : 'border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10'
              }`}
            >
              {assignment.is_published
                ? <><EyeOff size={13} /> Unpublish</>
                : <><Eye    size={13} /> Publish</>
              }
            </button>
          </div>
        )}
      </div>

      {/* ── Student: my current submission ── */}
      {!isTeacher() && mySub && (
        <div className={`card p-5 border ${
          mySub.status === 'completed'
            ? 'border-emerald-500/20'
            : 'border-amber-500/20'
        }`}>
          <h2 className="font-semibold text-slate-200 flex items-center gap-2 mb-3">
            <FileCode size={15} className="text-amber-400" />
            My Submission
            <span className="text-xs text-slate-600 font-mono">
              v{mySub.version || 1}
            </span>
          </h2>
          <div className="flex items-center justify-between gap-4">
            <div>
              {(mySub.files?.length > 0
                ? mySub.files
                : [{ original_filename: mySub.original_filename }]
              ).map((f, i) => (
                <p key={i} className="text-sm font-mono text-slate-300">
                  {f.original_filename}
                </p>
              ))}
              <p className="text-xs text-slate-600 mt-1">
                {formatDistanceToNow(
                  new Date(mySub.submitted_at), { addSuffix: true }
                )}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <StatusBadge status={mySub.status} />
              {mySub.score !== null && mySub.score !== undefined && (
                <ScoreBadge score={mySub.score} />
              )}
              <Link
                to={`/submissions/${mySub.id}`}
                className="text-xs text-amber-400 hover:text-amber-300"
              >
                View →
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* ════════════════════════════════════════════════════════
          TEACHER PANELS
      ════════════════════════════════════════════════════════ */}

      {isTeacher() && (
        <>
          {/* ── Files & uploads ── */}
          <div className="card p-5">
            <h2 className="font-semibold text-slate-200 flex items-center
                           gap-2 mb-4">
              <Upload size={15} className="text-amber-400" />
              Files & Resources
            </h2>
            <div className="grid sm:grid-cols-3 gap-4">
              {[
                {
                  type:   'solution',
                  label:  'Reference Solution (.c)',
                  accept: '.c',
                  status: assignment.reference_solution_path
                    ? '✓ uploaded' : 'Not uploaded',
                  btnLabel: 'Upload .c',
                },
                {
                  type:   'subject',
                  label:  'Subject File (PDF / TXT)',
                  accept: '.pdf,.txt,.md',
                  status: assignment.assignment_file_path
                    ? '✓ uploaded' : 'Not uploaded',
                  btnLabel: 'Upload Subject',
                },
                {
                  type:   'label',
                  label:  'Label / Cover',
                  accept: '.pdf,.png,.jpg,.jpeg',
                  status: assignment.label_file_path
                    ? '✓ uploaded' : 'Not uploaded',
                  btnLabel: 'Upload Label',
                },
              ].map(item => (
                <div key={item.type}
                  className="p-3 rounded-lg bg-slate-800/50 space-y-2">
                  <p className="text-xs text-slate-400 font-medium">
                    {item.label}
                  </p>
                  <p className="text-xs text-slate-600 font-mono">
                    {item.status}
                  </p>
                  <UploadBtn
                    label={item.btnLabel}
                    accept={item.accept}
                    onUpload={uploadFile(item.type)}
                  />
                </div>
              ))}
            </div>
          </div>

          {/* ── Test generation ── */}
          <div className="card p-5">
            <h2 className="font-semibold text-slate-200 flex items-center
                           gap-2 mb-4">
              <FlaskConical size={15} className="text-amber-400" />
              Test Case Generation
            </h2>

            <div className="flex flex-wrap items-center gap-3 mb-4">
              <button
                onClick={generateTests}
                disabled={genLoading || !assignment.reference_solution_path}
                className="btn-primary flex items-center gap-2"
              >
                <Zap size={13} />
                {genLoading ? 'Generating…' : 'Auto-Generate Tests'}
              </button>

              <button
                onClick={analyseRef}
                disabled={!assignment.reference_solution_path}
                className="btn-secondary flex items-center gap-2 text-xs"
              >
                <BarChart3 size={13} /> Analyse Reference
              </button>

              <button
                onClick={() => bulkReevaluate.mutate()}
                disabled={bulkReevaluate.isPending}
                className="btn-secondary flex items-center gap-2 text-xs ml-auto"
              >
                <RefreshCw
                  size={13}
                  className={bulkReevaluate.isPending ? 'animate-spin' : ''}
                />
                Re-evaluate All
              </button>
            </div>

            {!assignment.reference_solution_path && (
              <p className="text-xs text-slate-600 mb-3">
                Upload a reference solution above to enable test generation.
              </p>
            )}

            {/* Test case list */}
            {testCases && testCases.count > 0 && (
              <div className="mt-2 space-y-1 max-h-60 overflow-y-auto
                              rounded-lg border border-slate-800 p-2">
                {testCases.test_cases.map(tc => (
                  <div key={tc.id}
                    className="flex items-center justify-between px-3 py-2
                               rounded-lg bg-slate-800/50 text-xs font-mono">
                    <span className="text-slate-400 truncate max-w-[35%]">
                      #{tc.id} {tc.description}
                    </span>
                    <span className="text-slate-600 truncate mx-2">
                      in: {tc.input || '(none)'}
                    </span>
                    <span className="text-emerald-400 truncate max-w-[25%]">
                      → {tc.expected_output}
                    </span>
                    <span className="text-slate-600 ml-2 shrink-0">
                      {tc.weight?.toFixed(2)}pt
                    </span>
                  </div>
                ))}
              </div>
            )}

            {/* Static analysis result */}
            {analysis && (
              <div className="mt-4 p-4 rounded-lg bg-slate-800/50
                              text-xs font-mono space-y-1">
                <p className="text-amber-400 font-semibold mb-2">
                  Static Analysis
                </p>
                <p className="text-slate-400">
                  Functions:{' '}
                  <span className="text-slate-200">
                    {analysis.function_names?.join(', ') || '—'}
                  </span>
                </p>
                <p className="text-slate-400">
                  Complexity:{' '}
                  <span className="text-slate-200">
                    {analysis.cyclomatic_complexity}
                  </span>
                </p>
                <p className="text-slate-400">
                  Includes:{' '}
                  <span className="text-slate-200">
                    {analysis.includes?.join(', ') || '—'}
                  </span>
                </p>
                <p className="text-slate-400">
                  Loops:{' '}
                  <span className="text-slate-200">
                    {analysis.control_flow?.loops ?? 0}
                  </span>
                </p>
                <p className="text-slate-400">
                  Recursion:{' '}
                  <span className="text-slate-200">
                    {analysis.control_flow?.recursions > 0 ? 'Yes' : 'No'}
                  </span>
                </p>
                {analysis.warnings?.length > 0 && (
                  <div className="mt-2 space-y-0.5">
                    {analysis.warnings.map((w, i) => (
                      <p key={i} className="text-orange-400 flex items-start gap-1">
                        <AlertCircle size={10} className="mt-0.5 shrink-0" />
                        {w}
                      </p>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* ── Submission statistics ── */}
          {stats && (
            <div className="card p-5">
              <h2 className="font-semibold text-slate-200 flex items-center
                             gap-2 mb-4">
                <BarChart3 size={15} className="text-amber-400" />
                Submission Statistics
              </h2>
              <div className="grid grid-cols-3 sm:grid-cols-6 gap-3">
                {[
                  { label: 'Total',         value: stats.total },
                  { label: 'Completed',     value: stats.completed,
                    color: 'text-emerald-400' },
                  { label: 'Pending',       value: stats.pending,
                    color: 'text-sky-400' },
                  { label: 'Failed',        value: stats.failed,
                    color: 'text-rose-400' },
                  { label: 'Avg Score',
                    value: stats.average_score !== null
                      ? `${stats.average_score}/20` : '—',
                    color: 'text-amber-400' },
                  { label: 'Pass Rate',
                    value: stats.pass_rate !== null
                      ? `${stats.pass_rate}%` : '—',
                    color: 'text-emerald-400' },
                ].map(s => (
                  <div key={s.label}
                    className="text-center p-3 rounded-lg bg-slate-800/50">
                    <p className={`text-xl font-display
                                   ${s.color || 'text-slate-200'}`}>
                      {s.value}
                    </p>
                    <p className="text-xs text-slate-600 mt-0.5">{s.label}</p>
                  </div>
                ))}
              </div>
              {stats.late_count > 0 && (
                <p className="text-xs text-orange-400 mt-3">
                  ⏰ {stats.late_count} late submission
                  {stats.late_count !== 1 ? 's' : ''}
                </p>
              )}
            </div>
          )}

          {/* ── Leaderboard ── */}
          {leaderboard.length > 0 && (
            <div className="card p-5">
              <h2 className="font-semibold text-slate-200 flex items-center
                             gap-2 mb-4">
                <Users size={15} className="text-amber-400" />
                Leaderboard
              </h2>
              <div className="space-y-2">
                {leaderboard.map(row => (
                  <div key={row.student_id}
                    className="flex items-center gap-3 p-3 rounded-lg
                               bg-slate-800/50">
                    <span className={`w-6 h-6 rounded-full flex items-center
                                       justify-center text-xs font-bold shrink-0
                      ${row.rank === 1
                        ? 'bg-amber-500 text-slate-950'
                        : row.rank === 2
                          ? 'bg-slate-400 text-slate-950'
                          : row.rank === 3
                            ? 'bg-amber-700 text-slate-100'
                            : 'bg-slate-700 text-slate-400'}`}>
                      {row.rank}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-slate-200 font-medium">
                        {row.full_name}
                      </p>
                      <p className="text-xs text-slate-600 font-mono">
                        @{row.username} · {row.attempts} attempt
                        {row.attempts !== 1 ? 's' : ''}
                      </p>
                    </div>
                    <ScoreBadge score={row.best_score} />
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
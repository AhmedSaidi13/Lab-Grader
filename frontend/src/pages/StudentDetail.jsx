import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  ChevronLeft, Award, CheckCircle,
  XCircle, Clock, TrendingUp
} from 'lucide-react'
import { usersAPI } from '../api/client'
import ScoreBadge  from '../components/ScoreBadge'
import ProgressBar from '../components/ProgressBar'

export default function StudentDetail() {
  const { id } = useParams()

  const { data, isLoading } = useQuery({
    queryKey: ['student-scores', id],
    queryFn:  () => usersAPI.studentScores(id).then(r => r.data),
  })

  if (isLoading) return (
    <div className="flex items-center justify-center h-64">
      <div className="w-6 h-6 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
    </div>
  )
  if (!data) return <p className="text-slate-500">Student not found</p>

  const { student, summary, scores } = data

  return (
    <div className="space-y-6 animate-fade-up max-w-3xl mx-auto">

      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm">
        <Link to="/students"
          className="text-slate-500 hover:text-slate-300 flex items-center gap-1">
          <ChevronLeft size={14} /> Students
        </Link>
        <span className="text-slate-700">/</span>
        <span className="text-slate-400">{student.full_name}</span>
      </div>

      {/* Student header */}
      <div className="card p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-slate-800 flex items-center
                            justify-center text-lg font-display text-amber-400">
              {student.full_name.charAt(0).toUpperCase()}
            </div>
            <div>
              <h1 className="font-display text-xl text-slate-100">{student.full_name}</h1>
              <p className="text-slate-500 text-sm font-mono">@{student.username}</p>
              <p className="text-slate-600 text-xs">{student.email}</p>
            </div>
          </div>

          {/* Overall score */}
          {summary.total_max > 0 && (
            <div className="text-right">
              <p className="text-xs text-slate-500 mb-1">Overall</p>
              <p className="font-display text-2xl text-amber-400">
                {summary.total_score}
                <span className="text-slate-600 text-lg">/{summary.total_max}</span>
              </p>
              <ProgressBar
                value={summary.total_score}
                max={summary.total_max}
                color="amber"
              />
            </div>
          )}
        </div>

        {/* Summary stats */}
        <div className="grid grid-cols-3 gap-4 mt-5 pt-5 border-t border-slate-800">
          <div className="text-center">
            <p className="font-display text-xl text-emerald-400">{summary.pass_count}</p>
            <p className="text-xs text-slate-500 mt-0.5">Passed</p>
          </div>
          <div className="text-center">
            <p className="font-display text-xl text-slate-300">
              {summary.total_assignments}
            </p>
            <p className="text-xs text-slate-500 mt-0.5">Assignments</p>
          </div>
          <div className="text-center">
            <p className="font-display text-xl text-sky-400">
              {summary.completion_rate}%
            </p>
            <p className="text-xs text-slate-500 mt-0.5">Completion</p>
          </div>
        </div>
      </div>

      {/* Per-assignment scores */}
      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-800">
          <h2 className="font-semibold text-slate-200 flex items-center gap-2">
            <TrendingUp size={15} className="text-amber-400" />
            Score per Assignment
          </h2>
        </div>

        <div className="divide-y divide-slate-800">
          {scores.map(s => (
            <div key={s.assignment_id} className="px-5 py-4">
              <div className="flex items-center justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <p className="text-sm font-medium text-slate-200 truncate">
                      {s.assignment_title}
                    </p>
                    {s.best_score !== null && (
                      s.passed
                        ? <CheckCircle size={13} className="text-emerald-400 shrink-0" />
                        : <XCircle    size={13} className="text-rose-400 shrink-0" />
                    )}
                    {s.is_late && (
                      <span className="badge bg-orange-500/10 text-orange-400 text-xs">
                        Late
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 text-xs text-slate-500 font-mono">
                    <span>{s.attempts} attempt{s.attempts !== 1 ? 's' : ''}</span>
                    {s.deadline && (
                      <span className="flex items-center gap-1">
                        <Clock size={10} />
                        {new Date(s.deadline).toLocaleDateString()}
                      </span>
                    )}
                    {s.evaluated_at && (
                      <span>
                        Evaluated {new Date(s.evaluated_at).toLocaleDateString()}
                      </span>
                    )}
                  </div>

                  {s.best_score !== null && (
                    <div className="mt-2 max-w-[200px]">
                      <ProgressBar
                        value={s.best_score}
                        max={s.max_score}
                        color={s.passed ? 'emerald' : 'rose'}
                      />
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  {s.best_score !== null ? (
                    <ScoreBadge score={s.best_score} max={s.max_score} />
                  ) : (
                    <span className="badge bg-slate-800 text-slate-500 text-xs">
                      Not submitted
                    </span>
                  )}
                  {s.submission_id && (
                    <Link to={`/submissions/${s.submission_id}`}
                      className="text-xs text-amber-400 hover:text-amber-300 transition-colors">
                      View →
                    </Link>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
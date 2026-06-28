import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  BookOpen, Send, CheckCircle, TrendingUp,
  Clock, ChevronRight, Award
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import useAuthStore from '../store/authStore'
import { assignmentsAPI, submissionsAPI } from '../api/client'
import ScoreBadge  from '../components/ScoreBadge'
import StatusBadge from '../components/StatusBadge'
import ProgressBar from '../components/ProgressBar'

function StatCard({ icon: Icon, label, value, sub, color = 'amber' }) {
  const colors = {
    amber:   'text-amber-400 bg-amber-500/10',
    emerald: 'text-emerald-400 bg-emerald-500/10',
    sky:     'text-sky-400 bg-sky-500/10',
    rose:    'text-rose-400 bg-rose-500/10',
  }
  return (
    <div className="card p-5 animate-fade-up">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-slate-500 text-xs uppercase tracking-wider mb-1">{label}</p>
          <p className="text-2xl font-display text-slate-100">{value}</p>
          {sub && <p className="text-slate-500 text-xs mt-0.5">{sub}</p>}
        </div>
        <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${colors[color]}`}>
          <Icon size={17} />
        </div>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const { user, isTeacher } = useAuthStore()

  const { data: assignments = [] } = useQuery({
    queryKey: ['assignments'],
    queryFn:  () => assignmentsAPI.list().then(r => r.data),
  })

  const { data: mySubmissions = [] } = useQuery({
    queryKey: ['my-submissions'],
    queryFn:  () => submissionsAPI.mine().then(r => r.data),
    enabled:  !isTeacher(),
  })

  const completed  = mySubmissions.filter(s => s.status === 'completed')
  const avgScore   = completed.length
    ? (completed.reduce((a, s) => a + (s.score || 0), 0) / completed.length).toFixed(1)
    : '—'
  const bestScore  = completed.length
    ? Math.max(...completed.map(s => s.score || 0)).toFixed(1)
    : '—'

  const recentSubs = [...mySubmissions]
    .sort((a, b) => new Date(b.submitted_at) - new Date(a.submitted_at))
    .slice(0, 5)

  const upcoming = assignments
    .filter(a => a.deadline && new Date(a.deadline) > new Date())
    .sort((a, b) => new Date(a.deadline) - new Date(b.deadline))
    .slice(0, 3)

  return (
    <div className="space-y-8">
      {/* Greeting */}
      <div className="animate-fade-up">
        <h1 className="font-display text-3xl text-slate-100 mb-1">
          Hello, <span className="text-amber-400">{user?.full_name?.split(' ')[0]}</span>
        </h1>
        <p className="text-slate-500 text-sm">
          {isTeacher()
            ? `${assignments.length} assignment${assignments.length !== 1 ? 's' : ''} in your course`
            : `${assignments.length} assignment${assignments.length !== 1 ? 's' : ''} available`}
        </p>
      </div>

      {/* Stats */}
      {!isTeacher() ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard icon={BookOpen}    label="Assignments"  value={assignments.length} color="sky" />
          <StatCard icon={Send}        label="Submitted"    value={mySubmissions.length} color="amber" />
          <StatCard icon={CheckCircle} label="Completed"    value={completed.length} color="emerald" />
          <StatCard icon={TrendingUp}  label="Avg Score"    value={avgScore}
                    sub={completed.length ? `Best: ${bestScore}/20` : undefined} color="amber" />
        </div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
          <StatCard icon={BookOpen} label="Total Assignments" value={assignments.length} color="sky" />
          <StatCard icon={CheckCircle} label="Published" color="emerald"
                    value={assignments.filter(a => a.is_published).length} />
          <StatCard icon={Clock} label="With Deadline" color="amber"
                    value={assignments.filter(a => a.deadline).length} />
        </div>
      )}

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Recent submissions (student) */}
        {!isTeacher() && (
          <div className="lg:col-span-2 card p-5 animate-fade-up">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-slate-200 flex items-center gap-2">
                <Send size={15} className="text-amber-400" /> Recent Submissions
              </h2>
              <Link to="/assignments" className="text-xs text-amber-400 hover:text-amber-300">
                View all →
              </Link>
            </div>
            {recentSubs.length === 0 ? (
              <div className="py-10 text-center text-slate-600">
                <Send size={28} className="mx-auto mb-2 opacity-40" />
                <p className="text-sm">No submissions yet</p>
              </div>
            ) : (
              <div className="space-y-2">
                {recentSubs.map(sub => {
                  const assign = assignments.find(a => a.id === sub.assignment_id)
                  return (
                    <Link key={sub.id} to={`/submissions/${sub.id}`}
                      className="flex items-center justify-between p-3 rounded-lg
                                 bg-slate-800/50 hover:bg-slate-800 transition-colors group">
                      <div className="min-w-0">
                        <p className="text-sm text-slate-200 font-medium truncate">
                          {assign?.title ?? `Assignment #${sub.assignment_id}`}
                        </p>
                        <p className="text-xs text-slate-500 font-mono mt-0.5">
                          {formatDistanceToNow(new Date(sub.submitted_at), { addSuffix: true })}
                          {sub.is_late && <span className="ml-2 text-orange-400">[late]</span>}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 ml-3 shrink-0">
                        <StatusBadge status={sub.status} />
                        <ScoreBadge score={sub.score} />
                        <ChevronRight size={14} className="text-slate-600
                                       group-hover:text-slate-400 transition-colors" />
                      </div>
                    </Link>
                  )
                })}
              </div>
            )}
          </div>
        )}

        {/* Teacher: assignments overview */}
        {isTeacher() && (
          <div className="lg:col-span-2 card p-5 animate-fade-up">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-slate-200 flex items-center gap-2">
                <BookOpen size={15} className="text-amber-400" /> Your Assignments
              </h2>
              <Link to="/assignments" className="text-xs text-amber-400 hover:text-amber-300">
                Manage →
              </Link>
            </div>
            <div className="space-y-2">
              {assignments.slice(0, 5).map(a => (
                <Link key={a.id} to={`/assignments/${a.id}`}
                  className="flex items-center justify-between p-3 rounded-lg
                             bg-slate-800/50 hover:bg-slate-800 transition-colors group">
                  <div className="min-w-0">
                    <p className="text-sm text-slate-200 font-medium truncate">{a.title}</p>
                    <p className="text-xs text-slate-500 font-mono mt-0.5">
                      {a.test_case_count} test cases ·{' '}
                      {a.deadline
                        ? formatDistanceToNow(new Date(a.deadline), { addSuffix: true })
                        : 'No deadline'}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 ml-3 shrink-0">
                    <span className={`badge text-xs ${a.is_published
                      ? 'text-emerald-300 bg-emerald-500/10'
                      : 'text-slate-400 bg-slate-800'}`}>
                      {a.is_published ? 'Published' : 'Draft'}
                    </span>
                    <ChevronRight size={14} className="text-slate-600
                                   group-hover:text-slate-400 transition-colors" />
                  </div>
                </Link>
              ))}
            </div>
          </div>
        )}

        {/* Upcoming deadlines */}
        <div className="card p-5 animate-fade-up">
          <h2 className="font-semibold text-slate-200 flex items-center gap-2 mb-4">
            <Clock size={15} className="text-amber-400" /> Upcoming Deadlines
          </h2>
          {upcoming.length === 0 ? (
            <div className="py-8 text-center text-slate-600">
              <Award size={24} className="mx-auto mb-2 opacity-40" />
              <p className="text-xs">No upcoming deadlines</p>
            </div>
          ) : (
            <div className="space-y-3">
              {upcoming.map(a => {
                const dl   = new Date(a.deadline)
                const hoursLeft = (dl - Date.now()) / 36e5
                const urgent = hoursLeft < 24
                return (
                  <Link key={a.id} to={`/assignments/${a.id}`}
                    className="block p-3 rounded-lg bg-slate-800/50
                               hover:bg-slate-800 transition-colors">
                    <p className="text-sm text-slate-200 font-medium truncate">{a.title}</p>
                    <p className={`text-xs font-mono mt-1
                      ${urgent ? 'text-rose-400' : 'text-slate-500'}`}>
                      {formatDistanceToNow(dl, { addSuffix: true })}
                    </p>
                    <ProgressBar
                      value={Math.max(0, 100 - (hoursLeft / 168) * 100)}
                      color={urgent ? 'rose' : 'amber'}
                    />
                  </Link>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
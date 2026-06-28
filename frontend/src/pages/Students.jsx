import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Users, ChevronRight, TrendingUp, BookOpen, Search } from 'lucide-react'
import { usersAPI } from '../api/client'
import ProgressBar from '../components/ProgressBar'

export default function Students() {
  const [search, setSearch] = useState('')

  const { data: students = [], isLoading } = useQuery({
    queryKey: ['students'],
    queryFn:  () => usersAPI.listStudents().then(r => r.data),
  })

  const filtered = students.filter(s =>
    s.full_name.toLowerCase().includes(search.toLowerCase()) ||
    s.username.toLowerCase().includes(search.toLowerCase())
  )

  if (isLoading) return (
    <div className="flex items-center justify-center h-64">
      <div className="w-6 h-6 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
    </div>
  )

  return (
    <div className="space-y-6 animate-fade-up">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="section-title">Students</h1>
          <p className="text-slate-500 text-sm mt-0.5">
            {students.length} enrolled student{students.length !== 1 ? 's' : ''}
          </p>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
        <input
          className="input pl-9"
          placeholder="Search by name or username…"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>

      {/* Table */}
      {filtered.length === 0 ? (
        <div className="card p-16 text-center">
          <Users size={32} className="mx-auto text-slate-700 mb-3" />
          <p className="text-slate-500">No students found</p>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-900/50">
                <th className="text-left px-4 py-3 text-slate-500 font-medium text-xs uppercase tracking-wider">
                  Student
                </th>
                <th className="text-center px-4 py-3 text-slate-500 font-medium text-xs uppercase tracking-wider hidden sm:table-cell">
                  Submissions
                </th>
                <th className="text-center px-4 py-3 text-slate-500 font-medium text-xs uppercase tracking-wider hidden md:table-cell">
                  Assignments
                </th>
                <th className="text-center px-4 py-3 text-slate-500 font-medium text-xs uppercase tracking-wider">
                  Avg Score
                </th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {filtered.map((student, i) => (
                <tr key={student.id}
                  className="hover:bg-slate-800/30 transition-colors group"
                  style={{ animationDelay: `${i * 30}ms` }}>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      {/* Avatar */}
                      <div className="w-8 h-8 rounded-full overflow-hidden shrink-0 bg-slate-700
                                      flex items-center justify-center">
                        {student.avatar_path ? (
                          <img
                            src={`/api/v1/users/${student.id}/avatar`}
                            alt={student.full_name}
                            className="w-full h-full object-cover"
                            onError={e => {
                              e.target.style.display = 'none'
                              e.target.parentNode.innerHTML =
                                `<span class="text-slate-300 text-xs font-medium">
                                  ${student.full_name.charAt(0).toUpperCase()}
                                </span>`
                            }}
                          />
                        ) : (
                          <span className="text-slate-300 text-xs font-medium">
                            {student.full_name.charAt(0).toUpperCase()}
                          </span>
                        )}
                      </div>
                      <div>
                        <p className="text-slate-200 font-medium">{student.full_name}</p>
                        <p className="text-slate-500 text-xs font-mono">@{student.username}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center hidden sm:table-cell">
                    <span className="text-slate-400 font-mono text-xs">
                      {student.total_submissions}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center hidden md:table-cell">
                    <span className="text-slate-400 font-mono text-xs">
                      {student.assignments_attempted}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    {student.average_score !== null ? (
                      <div className="flex flex-col items-center gap-1">
                        <span className={`font-mono text-sm font-semibold
                          ${student.average_score >= 16 ? 'text-amber-400' :
                            student.average_score >= 10 ? 'text-emerald-400' :
                                                          'text-rose-400'}`}>
                          {student.average_score.toFixed(1)}
                        </span>
                        <div className="w-16">
                          <ProgressBar
                            value={student.average_score}
                            max={20}
                            color={student.average_score >= 10 ? 'emerald' : 'rose'}
                          />
                        </div>
                      </div>
                    ) : (
                      <span className="text-slate-600 text-xs">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <Link to={`/students/${student.id}`}
                      className="flex items-center justify-end text-slate-600
                                 group-hover:text-amber-400 transition-colors">
                      <ChevronRight size={15} />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
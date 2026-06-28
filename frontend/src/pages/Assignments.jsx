import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  Plus, BookOpen, Clock, ChevronRight,
  CheckSquare, Square, Trash2, Eye, EyeOff
} from 'lucide-react'
import { formatDistanceToNow, format } from 'date-fns'
import toast from 'react-hot-toast'
import useAuthStore from '../store/authStore'
import { assignmentsAPI } from '../api/client'
import ProgressBar from '../components/ProgressBar'

function CreateModal({ onClose }) {
  const qc = useQueryClient()
  const [form, setForm] = useState({
  title:                 '',
  description:           '',
  instructions:          '',
  deadline:              '',
  passing_score:         10,
  allow_late_submission: false,
  late_penalty_percent:  20,
  max_files:             1,
})
  const [files, setFiles] = useState({
    reference_solution: null,
    subject_file:       null,
    label_file:         null,
  })
  const [isPending, setIsPending] = useState(false)

  const set    = k => e => setForm(f => ({
    ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value,
  }))
  const setFile = k => e => setFiles(f => ({ ...f, [k]: e.target.files[0] || null }))
  const minDeadline = () => {
  const d = new Date(Date.now() + 5 * 60 * 1000)  // minimum 5 min from now
  return d.toISOString().slice(0, 16)
}

  const handleCreate = async () => {
    setIsPending(true)
    try {
      const formData = new FormData()
      formData.append('title',                form.title)
      formData.append('description',          form.description)
      formData.append('instructions',         form.instructions || '')
      formData.append('passing_score',        form.passing_score)
      formData.append('allow_late_submission', form.allow_late_submission)
      formData.append('late_penalty_percent', form.late_penalty_percent)
      formData.append('max_files',            form.max_files)
      if (form.deadline)
        formData.append('deadline', new Date(form.deadline).toISOString())
      if (files.reference_solution)
        formData.append('reference_solution', files.reference_solution)
      if (files.subject_file)
        formData.append('subject_file', files.subject_file)
      if (files.label_file)
        formData.append('label_file', files.label_file)

      await assignmentsAPI.createWithFiles(formData)
      toast.success(
        'Assignment created!' +
        (files.reference_solution ? ' Test generation queued.' : '')
      )
      qc.invalidateQueries({ queryKey: ['assignments'] })
      onClose()
    } catch { }
    finally { setIsPending(false) }
  }

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center
                    justify-center z-50 p-4" onClick={onClose}>
      <div className="card w-full max-w-lg p-6 animate-fade-up max-h-[90vh] overflow-y-auto"
           onClick={e => e.stopPropagation()}>
        <h2 className="font-display text-xl text-slate-100 mb-5">New Assignment</h2>

        <div className="space-y-4">
          {/* Basic fields */}
          <div>
            <label className="label">Title *</label>
            <input className="input" placeholder="TP1 — Linked Lists"
              value={form.title} onChange={set('title')} required />
          </div>
          <div>
            <label className="label">Description *</label>
            <textarea className="input min-h-[70px] resize-y"
              placeholder="What students must implement…"
              value={form.description} onChange={set('description')} required />
          </div>
          <div>
            <label className="label">Instructions</label>
            <textarea className="input min-h-[50px] resize-y"
              placeholder="Additional notes…"
              value={form.instructions} onChange={set('instructions')} />
          </div>
          {/*<div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Passing Score (out of 20)</label>
              <input className="input" type="number" min="0" max="20"
                value={form.passing_score}
                onChange={e => setForm(f => ({ ...f, passing_score: +e.target.value }))} />
            </div>
          </div>*/}
          <div>
            <label className="label">Max Files per Student</label>
            <div className="flex items-center gap-3">
              <input
                className="input w-20 text-center"
                type="number" min="1" max="10"
                value={form.max_files}
                onChange={set('max_files')}
              />
              <span className="text-slate-500 text-xs">
                {form.max_files === 1
                  ? 'Students upload 1 .c file (default)'
                  : `Students upload up to ${form.max_files} .c files`}
              </span>
            </div>
          </div>
          <div>
            <label className="label">Deadline</label>
            <input
              className="input"
              type="datetime-local"
              min={minDeadline()}
              value={form.deadline}
              onChange={e => {
                const chosen = new Date(e.target.value)
                if (chosen <= new Date()) {
                  toast.error('Deadline must be in the future')
                  return
                }
                setForm(f => ({ ...f, deadline: e.target.value }))
              }}
            />
            {form.deadline && new Date(form.deadline) <= new Date() && (
              <p className="text-rose-400 text-xs mt-1">
                Deadline must be in the future
              </p>
            )}
          </div>
          <div className="flex items-center gap-3">
            <input type="checkbox" id="late" className="accent-amber-500"
              checked={form.allow_late_submission}
              onChange={set('allow_late_submission')} />
            <label htmlFor="late" className="text-sm text-slate-400 cursor-pointer">
              Allow late submissions
            </label>
            {form.allow_late_submission && (
              <div className="ml-auto flex items-center gap-2">
                <input className="input w-20" type="number" min="0" max="100"
                  value={form.late_penalty_percent}
                  onChange={set('late_penalty_percent')} />
                <span className="text-slate-500 text-sm">% penalty</span>
              </div>
            )}
          </div>

          {/* File attachments */}
          <div className="border-t border-slate-800 pt-4">
            <p className="label mb-3">Attachments (optional)</p>
            <div className="space-y-3">
              {[
                { key: 'reference_solution', label: 'Reference Solution (.c)',
                  accept: '.c', hint: 'Auto-generates test cases after creation' },
                { key: 'subject_file',       label: 'Subject / Problem Statement',
                  accept: '.pdf,.txt,.md', hint: 'Students can download this' },
               /* { key: 'label_file',         label: 'Label / Cover Image',
                  accept: '.pdf,.png,.jpg,.jpeg', hint: '' },*/
              ].map(({ key, label, accept, hint }) => (
                <div key={key} className="flex items-center justify-between
                                          p-3 rounded-lg bg-slate-800/50">
                  <div className="min-w-0">
                    <p className="text-xs text-slate-300 font-medium">{label}</p>
                    {hint && <p className="text-xs text-slate-600 mt-0.5">{hint}</p>}
                    {files[key] && (
                      <p className="text-xs text-amber-400 font-mono mt-0.5 truncate">
                        {files[key].name}
                      </p>
                    )}
                  </div>
                  <label className="btn-secondary text-xs cursor-pointer ml-3 shrink-0">
                    {files[key] ? 'Change' : 'Upload'}
                    <input type="file" accept={accept} className="hidden"
                      onChange={setFile(key)} />
                  </label>
                </div>
              ))}
            </div>
          </div>

          <div className="flex gap-3 pt-2">
            <button onClick={onClose} className="btn-secondary flex-1">Cancel</button>
            <button onClick={handleCreate}
              disabled={isPending || !form.title || !form.description}
              className="btn-primary flex-1">
              {isPending ? 'Creating…' : 'Create Assignment'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function Assignments() {
  const { isTeacher } = useAuthStore()
  const qc = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)

  const { data: assignments = [], isLoading } = useQuery({
    queryKey: ['assignments'],
    queryFn:  () => assignmentsAPI.list().then(r => r.data),
  })

  const togglePublish = useMutation({
    mutationFn: a => assignmentsAPI.update(a.id, { is_published: !a.is_published }),
    onSuccess: (_, a) => {
      toast.success(a.is_published ? 'Assignment unpublished' : 'Assignment published!')
      qc.invalidateQueries({ queryKey: ['assignments'] })
    },
  })

  const deleteAssign = useMutation({
    mutationFn: id => assignmentsAPI.delete(id),
    onSuccess: () => {
      toast.success('Assignment deleted')
      qc.invalidateQueries({ queryKey: ['assignments'] })
    },
  })

  if (isLoading) return (
    <div className="flex items-center justify-center h-64">
      <div className="w-6 h-6 border-2 border-amber-500 border-t-transparent
                      rounded-full animate-spin" />
    </div>
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between animate-fade-up">
        <div>
          <h1 className="section-title">Assignments</h1>
          <p className="text-slate-500 text-sm mt-0.5">
            {assignments.length} assignment{assignments.length !== 1 ? 's' : ''} available
          </p>
        </div>
        {isTeacher() && (
          <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2">
            <Plus size={15} /> New Assignment
          </button>
        )}
      </div>

      {/* List */}
      {assignments.length === 0 ? (
        <div className="card p-16 text-center animate-fade-up">
          <BookOpen size={36} className="mx-auto text-slate-700 mb-3" />
          <p className="text-slate-500">No assignments yet</p>
          {isTeacher() && (
            <button onClick={() => setShowCreate(true)}
              className="btn-primary mt-4 inline-flex items-center gap-2">
              <Plus size={14} /> Create First Assignment
            </button>
          )}
        </div>
      ) : (
        <div className="grid gap-3">
          {assignments.map((a, i) => {
            const deadline   = a.deadline ? new Date(a.deadline) : null
            const isPast     = deadline && deadline < new Date()
            const hoursLeft  = deadline ? (deadline - Date.now()) / 36e5 : null
            const urgent     = hoursLeft !== null && hoursLeft > 0 && hoursLeft < 48

            return (
              <div key={a.id}
                className="card-hover p-5 flex items-start justify-between gap-4 animate-fade-up"
                style={{ animationDelay: `${i * 40}ms` }}>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <Link to={`/assignments/${a.id}`}
                      className="font-semibold text-slate-200 hover:text-amber-400
                                 transition-colors truncate">
                      {a.title}
                    </Link>
                    {!a.is_published && isTeacher() && (
                      <span className="badge bg-slate-800 text-slate-500 text-xs">Draft</span>
                    )}
                    {urgent && (
                      <span className="badge bg-rose-500/10 text-rose-400 text-xs">Urgent</span>
                    )}
                  </div>
                  <p className="text-slate-500 text-sm line-clamp-2 mb-3">{a.description}</p>
                  <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500">
                    <span className="flex items-center gap-1 font-mono">
                      <CheckSquare size={11} className="text-amber-400" />
                      {a.test_case_count} tests
                    </span>
                    <span className="font-mono">{a.max_score} pts</span>
                    {deadline ? (
                      <span className={`flex items-center gap-1
                        ${isPast ? 'text-slate-600' : urgent ? 'text-rose-400' : 'text-slate-500'}`}>
                        <Clock size={11} />
                        {isPast
                          ? `Ended ${formatDistanceToNow(deadline, { addSuffix: true })}`
                          : `Due ${formatDistanceToNow(deadline, { addSuffix: true })}`}
                      </span>
                    ) : (
                      <span className="text-slate-600">No deadline</span>
                    )}
                  </div>
                  {!isPast && deadline && (
                    <div className="mt-3 max-w-xs">
                      <ProgressBar
                        value={Math.max(0, 100 - (hoursLeft / 168) * 100)}
                        color={urgent ? 'rose' : 'sky'}
                      />
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 shrink-0">
                  {isTeacher() ? (
                    <>
                      <button onClick={() => togglePublish.mutate(a)}
                        title={a.is_published ? 'Unpublish' : 'Publish'}
                        className={`p-2 rounded-lg transition-all
                          ${a.is_published
                            ? 'text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20'
                            : 'text-slate-500 hover:text-slate-300 hover:bg-slate-800'}`}>
                        {a.is_published ? <Eye size={15} /> : <EyeOff size={15} />}
                      </button>
                      <button onClick={() => {
                        if (confirm('Delete this assignment?')) deleteAssign.mutate(a.id)
                      }} className="p-2 rounded-lg text-slate-600 hover:text-rose-400
                                    hover:bg-rose-400/10 transition-all">
                        <Trash2 size={15} />
                      </button>
                    </>
                  ) : (
                    !isPast && (
                      <Link to={`/assignments/${a.id}/submit`} className="btn-primary text-xs">
                        Submit
                      </Link>
                    )
                  )}
                  <Link to={`/assignments/${a.id}`}
                    className="p-2 rounded-lg text-slate-500 hover:text-amber-400
                               hover:bg-amber-400/10 transition-all">
                    <ChevronRight size={15} />
                  </Link>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {showCreate && <CreateModal onClose={() => setShowCreate(false)} />}
    </div>
  )
}
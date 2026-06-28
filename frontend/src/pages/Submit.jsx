import { useState, useRef, useCallback } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Upload, FileCode, ChevronLeft, AlertCircle,
  CheckCircle, X, RefreshCw, Trash2, Clock
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import toast from 'react-hot-toast'
import { assignmentsAPI, submissionsAPI } from '../api/client'

function FileDropZone({ files, onAdd, onRemove, maxFiles, disabled }) {
  const [drag, setDrag] = useState(false)
  const inputRef = useRef()

  const onDrop = useCallback(e => {
    e.preventDefault()
    setDrag(false)
    if (disabled) return
    const dropped = Array.from(e.dataTransfer.files)
    const cFiles  = dropped.filter(f => f.name.endsWith('.c'))
    if (cFiles.length !== dropped.length) {
      toast.error('Only .c files are accepted')
    }
    onAdd(cFiles)
  }, [disabled, onAdd])

  const onPick = e => {
    onAdd(Array.from(e.target.files))
    e.target.value = ''
  }

  const remaining = maxFiles - files.length
  const full      = remaining <= 0

  return (
    <div className="space-y-3">
      {/* Drop zone */}
      {!full && (
        <div
          onClick={() => !disabled && inputRef.current.click()}
          onDragOver={e => { e.preventDefault(); if (!disabled) setDrag(true) }}
          onDragLeave={() => setDrag(false)}
          onDrop={onDrop}
          className={`border-2 border-dashed rounded-xl p-8 text-center
                     transition-all duration-200 cursor-pointer
                     ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
                     ${drag
                       ? 'border-amber-500 bg-amber-500/5'
                       : 'border-slate-700 hover:border-slate-600 bg-slate-900/50'}`}>
          <input
            ref={inputRef}
            type="file"
            accept=".c"
            multiple={maxFiles > 1}
            className="hidden"
            onChange={onPick}
            disabled={disabled}
          />
          <div className="space-y-2">
            <div className="w-10 h-10 rounded-xl bg-slate-800 flex items-center
                            justify-center mx-auto">
              <FileCode size={20} className="text-slate-500" />
            </div>
            <p className="text-slate-300 text-sm font-medium">
              {maxFiles > 1
                ? `Drop .c files here (${files.length}/${maxFiles})`
                : 'Drop your .c file here'}
            </p>
            <p className="text-slate-600 text-xs">or click to browse</p>
          </div>
        </div>
      )}

      {/* File list */}
      {files.length > 0 && (
        <div className="space-y-2">
          {files.map((f, i) => (
            <div key={i}
              className="flex items-center justify-between p-3 rounded-lg
                         bg-slate-800/50 border border-emerald-500/20">
              <div className="flex items-center gap-2 min-w-0">
                <CheckCircle size={14} className="text-emerald-400 shrink-0" />
                <span className="font-mono text-sm text-slate-200 truncate">
                  {f.name}
                </span>
                <span className="text-slate-600 text-xs shrink-0">
                  {(f.size / 1024).toFixed(1)} KB
                </span>
              </div>
              {!disabled && (
                <button onClick={() => onRemove(i)}
                  className="p-1 text-slate-600 hover:text-rose-400 transition-colors">
                  <X size={14} />
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function Submit() {
  const { id }    = useParams()
  const navigate  = useNavigate()
  const [files,   setFiles]   = useState([])
  const [loading, setLoading] = useState(false)

  const { data: assignment } = useQuery({
    queryKey: ['assignment', id],
    queryFn:  () => assignmentsAPI.get(id).then(r => r.data),
  })

  const { data: existingSub, refetch: refetchSub } = useQuery({
    queryKey: ['my-sub', id],
    queryFn:  () => submissionsAPI.mySubmissionFor(id).then(r => r.data),
    retry:    false,
  })

  const maxFiles   = assignment?.max_files ?? 1
  const deadline   = assignment?.deadline ? new Date(assignment.deadline) : null
  const deadlinePassed = deadline && deadline < new Date()
  const isLate     = deadlinePassed && assignment?.allow_late_submission

  const addFiles = newFiles => {
    setFiles(prev => {
      const combined = [...prev, ...newFiles]
      if (combined.length > maxFiles) {
        toast.error(`Maximum ${maxFiles} file(s) allowed`)
        return prev
      }
      // Deduplicate by name
      const seen = new Set()
      return combined.filter(f => {
        if (seen.has(f.name)) return false
        seen.add(f.name)
        return true
      })
    })
  }

  const removeFile = idx => {
    setFiles(prev => prev.filter((_, i) => i !== idx))
  }

  const handleSubmit = async () => {
    if (files.length === 0) {
      toast.error('Please add at least one .c file')
      return
    }
    setLoading(true)
    try {
      const form = new FormData()
      files.forEach(f => form.append('files', f))

      await submissionsAPI.submit(id, form)

      if (existingSub) {
        toast.success(`Solution updated (v${(existingSub.version || 1) + 1})`)
      } else {
        toast.success('Solution submitted! Evaluation starts after deadline.')
      }

      await refetchSub()
      navigate(`/assignments/${id}`)
    } catch { }
    finally { setLoading(false) }
  }

  const handleDelete = async () => {
    if (!existingSub) return
    if (!confirm('Delete your submission? You can re-submit before the deadline.')) return
    try {
      await submissionsAPI.delete(existingSub.id)
      toast.success('Submission deleted')
      setFiles([])
      await refetchSub()
    } catch { }
  }

  const canSubmit = !deadlinePassed || (isLate)

  return (
    <div className="max-w-xl mx-auto space-y-6 animate-fade-up">

      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm">
        <Link to={`/assignments/${id}`}
          className="text-slate-500 hover:text-slate-300 flex items-center gap-1">
          <ChevronLeft size={14} /> {assignment?.title ?? 'Assignment'}
        </Link>
        <span className="text-slate-700">/</span>
        <span className="text-slate-400">Submit</span>
      </div>

      <div>
        <h1 className="section-title">
          {existingSub ? 'Replace Solution' : 'Submit Solution'}
        </h1>
        <p className="text-slate-500 text-sm mt-1">
          Upload {maxFiles === 1 ? 'your' : `up to ${maxFiles}`}{' '}
          <code className="font-mono text-amber-400 text-xs">.c</code>
          {maxFiles > 1 ? ' files' : ' file'}
        </p>
      </div>

      {/* Assignment info */}
      {assignment && (
        <div className="card p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-slate-200 text-sm">{assignment.title}</p>
              <p className="text-xs text-slate-500 font-mono mt-0.5">
                Max score: 20 ·
                Pass: {assignment.passing_score} ·
                Files: {maxFiles}
              </p>
            </div>
            {deadline && (
              <div className="text-right">
                <p className="text-xs text-slate-500 flex items-center gap-1">
                  <Clock size={11} />
                  {deadlinePassed
                    ? 'Deadline passed'
                    : `Due ${formatDistanceToNow(deadline, { addSuffix: true })}`}
                </p>
                <p className={`text-xs font-mono ${
                  deadlinePassed ? 'text-rose-400' : 'text-slate-400'
                }`}>
                  {deadline.toLocaleDateString()}
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Existing submission */}
      {existingSub && (
        <div className={`card p-4 border ${
          existingSub.status === 'completed'
            ? 'border-emerald-500/20 bg-emerald-500/5'
            : 'border-amber-500/20 bg-amber-500/5'
        }`}>
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-sm font-medium text-slate-200 flex items-center gap-2">
                <RefreshCw size={13} className="text-amber-400" />
                Current submission (v{existingSub.version})
              </p>
              <div className="mt-1 space-y-0.5">
                {(existingSub.files?.length > 0
                  ? existingSub.files
                  : [{ original_filename: existingSub.original_filename }]
                ).map((f, i) => (
                  <p key={i} className="text-xs font-mono text-slate-400 truncate">
                    {f.original_filename}
                  </p>
                ))}
              </div>
              <p className="text-xs text-slate-600 mt-1">
                Submitted {formatDistanceToNow(
                  new Date(existingSub.submitted_at), { addSuffix: true }
                )}
              </p>
            </div>
            <div className="flex flex-col items-end gap-1 shrink-0">
              <span className={`badge text-xs ${
                existingSub.status === 'completed'
                  ? 'bg-emerald-500/10 text-emerald-300'
                  : existingSub.status === 'pending'
                    ? 'bg-slate-800 text-slate-400'
                    : 'bg-amber-500/10 text-amber-300'
              }`}>
                {existingSub.status}
              </span>
              {existingSub.score !== null && (
                <span className="font-mono text-xs text-amber-400">
                  {existingSub.score}/20
                </span>
              )}
            </div>
          </div>

          {canSubmit && (
            <div className="mt-3 pt-3 border-t border-slate-800/50">
              <p className="text-xs text-slate-500">
                You can replace your files below before the deadline.
                This will reset your evaluation.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Deadline passed — no more submissions */}
      {deadlinePassed && !assignment?.allow_late_submission ? (
        <div className="card p-6 text-center">
          <Clock size={28} className="mx-auto text-rose-400 mb-2" />
          <p className="text-slate-300 font-medium">Deadline has passed</p>
          <p className="text-slate-500 text-sm mt-1">
            Submissions are closed. Your solution will be evaluated automatically.
          </p>
          {existingSub && (
            <Link to={`/submissions/${existingSub.id}`}
              className="btn-secondary mt-4 inline-flex items-center gap-2 text-xs">
              View Submission →
            </Link>
          )}
        </div>
      ) : (
        <>
          {/* Late warning */}
          {isLate && (
            <div className="flex items-start gap-2 p-3 rounded-lg
                            bg-orange-500/10 border border-orange-500/20
                            text-orange-300 text-xs">
              <AlertCircle size={14} className="shrink-0 mt-0.5" />
              Late submission — {assignment?.late_penalty_percent}% penalty applies.
            </div>
          )}

          {/* File upload */}
          <div className="card p-5 space-y-4">
            <h2 className="font-semibold text-slate-200 text-sm">
              {existingSub ? 'Replace with new file(s)' : 'Upload file(s)'}
            </h2>
            <FileDropZone
              files={files}
              onAdd={addFiles}
              onRemove={removeFile}
              maxFiles={maxFiles}
              disabled={loading}
            />
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            <Link to={`/assignments/${id}`} className="btn-secondary flex-1 text-center">
              Cancel
            </Link>

            {existingSub && canSubmit && (
              <button
                onClick={handleDelete}
                className="btn-danger flex items-center gap-1">
                <Trash2 size={13} /> Delete
              </button>
            )}

            <button
              onClick={handleSubmit}
              disabled={files.length === 0 || loading}
              className="btn-primary flex-1 flex items-center justify-center gap-2">
              {loading ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-slate-900/40
                                   border-t-slate-900 rounded-full animate-spin" />
                  Submitting…
                </>
              ) : existingSub ? (
                <><RefreshCw size={14} /> Replace</>
              ) : (
                <><Upload size={14} /> Submit</>
              )}
            </button>
          </div>
        </>
      )}
    </div>
  )
}
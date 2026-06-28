import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { User, Mail, Lock, Camera, CheckCircle, Eye, EyeOff, Upload } from 'lucide-react'
import toast from 'react-hot-toast'
import { usersAPI } from '../api/client'
import useAuthStore from '../store/authStore'

function Avatar({ user, size = 20 }) {
  const [imgError, setImgError] = useState(false)
  const sz = `w-${size} h-${size}`

  if (user?.avatar_path && !imgError) {
    return (
      <img
        src={`/api/v1/users/${user.id}/avatar`}
        alt={user.full_name}
        onError={() => setImgError(true)}
        className={`${sz} rounded-full object-cover border-2 border-slate-700`}
      />
    )
  }

  return (
    <div className={`${sz} rounded-full bg-slate-700 flex items-center
                     justify-center border-2 border-slate-600`}>
      <span className="text-slate-300 font-display text-2xl">
        {user?.full_name?.charAt(0).toUpperCase() ?? '?'}
      </span>
    </div>
  )
}

export default function Profile() {
  const { user, login }  = useAuthStore()
  const qc               = useQueryClient()
  const avatarRef        = useRef()

  const [emailForm, setEmailForm] = useState({ email: user?.email || '' })
  const [passForm,  setPassForm]  = useState({
    current_password: '',
    new_password:     '',
    confirm:          '',
  })
  const [showCurrent, setShowCurrent] = useState(false)
  const [showNew,     setShowNew]     = useState(false)
  const [avatarPreview, setAvatarPreview] = useState(null)

  const { data: profile } = useQuery({
    queryKey: ['profile'],
    queryFn:  () => usersAPI.getProfile().then(r => r.data),
  })

  const updateMutation = useMutation({
    mutationFn: data => usersAPI.updateProfile(data),
    onSuccess:  res  => {
      toast.success('Profile updated!')
      const token = useAuthStore.getState().token
      login(token, { ...user, ...res.data })
      qc.invalidateQueries({ queryKey: ['profile'] })
    },
  })

  const avatarMutation = useMutation({
    mutationFn: form => usersAPI.uploadAvatar(form),
    onSuccess:  res  => {
      toast.success('Profile photo updated!')
      const token = useAuthStore.getState().token
      login(token, { ...user, ...res.data })
      qc.invalidateQueries({ queryKey: ['profile'] })
      setAvatarPreview(null)
    },
  })

  const handleAvatarChange = e => {
    const file = e.target.files[0]
    if (!file) return
    if (file.size > 2 * 1024 * 1024) {
      toast.error('Image must be under 2MB')
      return
    }
    // Preview
    const reader = new FileReader()
    reader.onload = ev => setAvatarPreview(ev.target.result)
    reader.readAsDataURL(file)
    // Upload immediately
    const form = new FormData()
    form.append('file', file)
    avatarMutation.mutate(form)
  }

  const handleEmailSave = () => {
    if (!emailForm.email) return
    updateMutation.mutate({ email: emailForm.email })
  }

  const handlePasswordSave = () => {
    if (passForm.new_password !== passForm.confirm) {
      toast.error('Passwords do not match')
      return
    }
    if (passForm.new_password.length < 8) {
      toast.error('Minimum 8 characters')
      return
    }
    updateMutation.mutate({
      current_password: passForm.current_password,
      new_password:     passForm.new_password,
    })
    setPassForm({ current_password: '', new_password: '', confirm: '' })
  }

  const data = profile || user

  return (
    <div className="max-w-xl mx-auto space-y-6 animate-fade-up">

      <div>
        <h1 className="section-title">My Profile</h1>
        <p className="text-slate-500 text-sm mt-1">Manage your account settings</p>
      </div>

      {/* Avatar + identity card */}
      <div className="card p-6">
        <div className="flex items-center gap-5">

          {/* Avatar with upload overlay */}
          <div className="relative group shrink-0">
            <div className="w-20 h-20">
              {avatarPreview ? (
                <img src={avatarPreview} alt="preview"
                     className="w-20 h-20 rounded-full object-cover border-2 border-amber-500" />
              ) : data?.avatar_path ? (
                <img
                  src={`/api/v1/users/${data.id}/avatar?t=${Date.now()}`}
                  alt={data?.full_name}
                  className="w-20 h-20 rounded-full object-cover border-2 border-slate-700"
                  onError={e => { e.target.style.display='none' }}
                />
              ) : (
                <div className="w-20 h-20 rounded-full bg-slate-700 border-2
                                border-slate-600 flex items-center justify-center">
                  <span className="font-display text-3xl text-amber-400">
                    {data?.full_name?.charAt(0).toUpperCase() ?? '?'}
                  </span>
                </div>
              )}
            </div>

            {/* Upload overlay */}
            <button
              onClick={() => avatarRef.current.click()}
              disabled={avatarMutation.isPending}
              className="absolute inset-0 rounded-full bg-black/50 opacity-0
                         group-hover:opacity-100 transition-opacity flex items-center
                         justify-center cursor-pointer">
              {avatarMutation.isPending
                ? <div className="w-5 h-5 border-2 border-white/60 border-t-white
                                  rounded-full animate-spin" />
                : <Camera size={18} className="text-white" />}
            </button>

            <input
              ref={avatarRef}
              type="file"
              accept=".jpg,.jpeg,.png,.webp"
              className="hidden"
              onChange={handleAvatarChange}
            />

            {/* Upload badge */}
            <div className="absolute -bottom-1 -right-1 w-6 h-6 bg-amber-500
                            rounded-full flex items-center justify-center
                            cursor-pointer hover:bg-amber-400 transition-colors"
                 onClick={() => avatarRef.current.click()}>
              <Upload size={11} className="text-slate-950" />
            </div>
          </div>

          <div className="flex-1 min-w-0">
            <p className="font-display text-xl text-slate-100 truncate">
              {data?.full_name}
            </p>
            <p className="text-slate-500 text-sm font-mono">@{data?.username}</p>
            <p className="text-slate-600 text-xs mt-0.5">{data?.email}</p>
            <span className={`badge mt-2 capitalize text-xs
              ${data?.role === 'teacher' || data?.role === 'admin'
                ? 'bg-amber-500/10 text-amber-400'
                : 'bg-sky-500/10 text-sky-400'}`}>
              {data?.role}
            </span>
          </div>
        </div>

        <p className="text-xs text-slate-600 mt-3">
          Click the photo to upload a new one · JPG, PNG, WEBP · Max 2MB
        </p>
      </div>

      {/* Email */}
      <div className="card p-6 space-y-4">
        <h2 className="font-semibold text-slate-200 flex items-center gap-2">
          <Mail size={15} className="text-amber-400" /> Email Address
        </h2>
        <div>
          <label className="label">Email</label>
          <input
            className="input"
            type="email"
            value={emailForm.email}
            onChange={e => setEmailForm({ email: e.target.value })}
            placeholder="your@email.com"
          />
        </div>
        <button
          onClick={handleEmailSave}
          disabled={updateMutation.isPending || emailForm.email === data?.email}
          className="btn-primary flex items-center gap-2">
          <CheckCircle size={14} />
          {updateMutation.isPending ? 'Saving…' : 'Save Email'}
        </button>
      </div>

      {/* Password */}
      <div className="card p-6 space-y-4">
        <h2 className="font-semibold text-slate-200 flex items-center gap-2">
          <Lock size={15} className="text-amber-400" /> Change Password
        </h2>

        {[
          { key: 'current_password', label: 'Current Password',
            show: showCurrent, toggle: () => setShowCurrent(v => !v) },
          { key: 'new_password',     label: 'New Password',
            show: showNew,     toggle: () => setShowNew(v => !v) },
        ].map(({ key, label, show, toggle }) => (
          <div key={key}>
            <label className="label">{label}</label>
            <div className="relative">
              <input
                className="input pr-10"
                type={show ? 'text' : 'password'}
                value={passForm[key]}
                onChange={e => setPassForm(f => ({ ...f, [key]: e.target.value }))}
                placeholder="••••••••"
              />
              <button type="button" onClick={toggle}
                className="absolute right-3 top-1/2 -translate-y-1/2
                           text-slate-500 hover:text-slate-300">
                {show ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
          </div>
        ))}

        <div>
          <label className="label">Confirm New Password</label>
          <input
            className="input"
            type="password"
            value={passForm.confirm}
            onChange={e => setPassForm(f => ({ ...f, confirm: e.target.value }))}
            placeholder="Repeat new password"
          />
          {passForm.new_password && passForm.confirm &&
           passForm.new_password !== passForm.confirm && (
            <p className="text-rose-400 text-xs mt-1">Passwords do not match</p>
          )}
        </div>

        <button
          onClick={handlePasswordSave}
          disabled={
            updateMutation.isPending ||
            !passForm.current_password ||
            !passForm.new_password ||
            passForm.new_password !== passForm.confirm
          }
          className="btn-primary flex items-center gap-2">
          <Lock size={14} />
          {updateMutation.isPending ? 'Updating…' : 'Update Password'}
        </button>
      </div>
    </div>
  )
}
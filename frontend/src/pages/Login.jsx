import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Code2, Eye, EyeOff } from 'lucide-react'
import toast from 'react-hot-toast'
import { authAPI } from '../api/client'
import useAuthStore from '../store/authStore'

export default function Login() {
  const navigate = useNavigate()
  const login    = useAuthStore(s => s.login)

  const [mode,     setMode]     = useState('login')   // 'login' | 'register'
  const [loading,  setLoading]  = useState(false)
  const [showPass, setShowPass] = useState(false)

  const [form, setForm] = useState({
    username: '', password: '', email: '', full_name: '', role: 'student',
  })

  const set = k => e => setForm(f => ({ ...f, [k]: e.target.value }))

  const handleSubmit = async e => {
    e.preventDefault()
    setLoading(true)
    try {
      if (mode === 'login') {
        const res = await authAPI.login({ username: form.username, password: form.password })
        login(res.data.access_token, res.data.user)
        toast.success(`Welcome back, ${res.data.user.full_name}!`)
        navigate('/dashboard')
      } else {
        await authAPI.register(form)
        toast.success('Account created! Please log in.')
        setMode('login')
      }
    } catch { /* interceptor handles error toast */ }
    finally { setLoading(false) }
  }

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center px-4">
      {/* Background grid */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(30,41,59,0.4)_1px,transparent_1px),linear-gradient(90deg,rgba(30,41,59,0.4)_1px,transparent_1px)]
                      bg-[size:48px_48px] pointer-events-none" />

      <div className="relative w-full max-w-md animate-fade-up">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 bg-amber-500
                          rounded-2xl mb-4 shadow-lg shadow-amber-500/20">
            <Code2 size={24} className="text-slate-950" strokeWidth={2.5} />
          </div>
          <h1 className="font-display text-3xl text-slate-100 mb-1">Lab-Grader</h1>
          <p className="text-slate-500 text-sm">
            Automatic C programming assignment evaluation
          </p>
        </div>

        {/* Card */}
        <div className="card p-8 shadow-2xl shadow-black/50">
          {/* Tabs */}
          <div className="flex gap-1 mb-6 bg-slate-800 p-1 rounded-lg">
            {['login', 'register'].map(m => (
              <button key={m} onClick={() => setMode(m)}
                className={`flex-1 py-1.5 rounded-md text-sm font-medium transition-all
                  ${mode === m
                    ? 'bg-slate-700 text-slate-100 shadow-sm'
                    : 'text-slate-500 hover:text-slate-300'}`}>
                {m === 'login' ? 'Sign In' : 'Register'}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === 'register' && (
              <>
                <div>
                  <label className="label">Full Name</label>
                  <input className="input" placeholder="Ali Benali"
                    value={form.full_name} onChange={set('full_name')} required />
                </div>
                <div>
                  <label className="label">Email</label>
                  <input className="input" type="email" placeholder="ali@univ.dz"
                    value={form.email} onChange={set('email')} required />
                </div>
                <div>
                  <label className="label">Role</label>
                  <select className="input" value={form.role} onChange={set('role')}>
                    <option value="student">Student</option>
                    <option value="teacher">Teacher</option>
                  </select>
                </div>
              </>
            )}

            <div>
              <label className="label">Username</label>
              <input className="input" placeholder="username"
                value={form.username} onChange={set('username')} required />
            </div>

            <div>
              <label className="label">Password</label>
              <div className="relative">
                <input className="input pr-10"
                  type={showPass ? 'text' : 'password'}
                  placeholder="••••••••"
                  value={form.password} onChange={set('password')} required />
                <button type="button"
                  onClick={() => setShowPass(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500
                             hover:text-slate-300 transition-colors">
                  {showPass ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            <button type="submit" disabled={loading}
              className="btn-primary w-full py-2.5 mt-2">
              {loading
                ? <span className="flex items-center justify-center gap-2">
                    <span className="w-3.5 h-3.5 border-2 border-slate-900/40
                                     border-t-slate-900 rounded-full animate-spin" />
                    {mode === 'login' ? 'Signing in…' : 'Creating account…'}
                  </span>
                : mode === 'login' ? 'Sign In' : 'Create Account'
              }
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
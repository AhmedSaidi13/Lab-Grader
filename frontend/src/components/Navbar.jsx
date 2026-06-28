import { Link, useLocation } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, useRef, useEffect } from 'react'
import {
  Code2, LayoutDashboard, BookOpen,
  LogOut, User, Users, Bell, CheckCheck,
  Award, Clock, AlertCircle
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import useAuthStore from '../store/authStore'
import { notificationsAPI } from '../api/client'

function NotificationPanel({ onClose }) {
  const qc = useQueryClient()

  const { data: notifications = [] } = useQuery({
    queryKey: ['notifications'],
    queryFn:  () => notificationsAPI.list().then(r => r.data),
    refetchInterval: 30_000,
  })

  const markAll = useMutation({
    mutationFn: () => notificationsAPI.markAllRead(),
    onSuccess:  () => {
      qc.invalidateQueries({ queryKey: ['notifications'] })
      qc.invalidateQueries({ queryKey: ['unread-count'] })
    },
  })

  const markOne = useMutation({
    mutationFn: id => notificationsAPI.markRead(id),
    onSuccess:  () => {
      qc.invalidateQueries({ queryKey: ['notifications'] })
      qc.invalidateQueries({ queryKey: ['unread-count'] })
    },
  })

  const typeIcon = type => {
    if (type === 'evaluation_complete') return <Award size={13} className="text-amber-400" />
    if (type === 'deadline_passed')     return <Clock size={13} className="text-rose-400" />
    return <AlertCircle size={13} className="text-sky-400" />
  }

  return (
    <div className="absolute right-0 top-full mt-2 w-80 card shadow-2xl shadow-black/50
                    border border-slate-700 z-50 animate-fade-up overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
        <span className="text-sm font-semibold text-slate-200">Notifications</span>
        <button
          onClick={() => markAll.mutate()}
          className="text-xs text-amber-400 hover:text-amber-300 flex items-center gap-1">
          <CheckCheck size={12} /> Mark all read
        </button>
      </div>

      <div className="max-h-80 overflow-y-auto">
        {notifications.length === 0 ? (
          <div className="py-8 text-center text-slate-600">
            <Bell size={24} className="mx-auto mb-2 opacity-40" />
            <p className="text-xs">No notifications</p>
          </div>
        ) : (
          notifications.map(n => (
            <div
              key={n.id}
              onClick={() => {
                if (!n.is_read) markOne.mutate(n.id)
                if (n.link)    window.location.href = n.link
                onClose()
              }}
              className={`px-4 py-3 border-b border-slate-800/50 cursor-pointer
                         hover:bg-slate-800/50 transition-colors
                         ${!n.is_read ? 'bg-slate-800/30' : ''}`}>
              <div className="flex items-start gap-2">
                <div className="mt-0.5 shrink-0">{typeIcon(n.type)}</div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className={`text-xs font-medium truncate
                      ${!n.is_read ? 'text-slate-100' : 'text-slate-400'}`}>
                      {n.title}
                    </p>
                    {!n.is_read && (
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-400
                                       shrink-0 animate-pulse" />
                    )}
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">
                    {n.message}
                  </p>
                  <p className="text-xs text-slate-700 mt-1">
                    {formatDistanceToNow(new Date(n.created_at), { addSuffix: true })}
                  </p>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default function Navbar() {
  const { user, logout, isTeacher } = useAuthStore()
  const location  = useLocation()
  const [showNotifs, setShowNotifs] = useState(false)
  const bellRef   = useRef()

  const { data: unreadData } = useQuery({
    queryKey:       ['unread-count'],
    queryFn:        () => notificationsAPI.unreadCount().then(r => r.data),
    refetchInterval: 30_000,
  })
  const unread = unreadData?.count ?? 0

  // Close on outside click
  useEffect(() => {
    const handler = e => {
      if (bellRef.current && !bellRef.current.contains(e.target)) {
        setShowNotifs(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const links = [
    { to: '/dashboard',   label: 'Dashboard',  icon: LayoutDashboard },
    { to: '/assignments', label: 'Assignments', icon: BookOpen },
    ...(isTeacher()
      ? [{ to: '/students', label: 'Students', icon: Users }]
      : []),
  ]

  const active = to => location.pathname.startsWith(to)

  return (
    <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-sm
                       sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex
                      items-center justify-between">

        {/* Logo */}
        <Link to="/dashboard" className="flex items-center gap-2.5 group">
          <div className="w-8 h-8 bg-amber-500 rounded-lg flex items-center
                          justify-center group-hover:bg-amber-400 transition-colors">
            <Code2 size={16} className="text-slate-950" strokeWidth={2.5} />
          </div>
          <span className="font-display text-lg text-slate-100 tracking-tight">
            Lab-<span className="text-amber-400">Grader</span>
          </span>
        </Link>

        {/* Nav */}
        <nav className="hidden sm:flex items-center gap-1">
          {links.map(({ to, label, icon: Icon }) => (
            <Link key={to} to={to}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm
                         font-medium transition-all duration-150
                         ${active(to)
                           ? 'bg-slate-800 text-amber-400'
                           : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'}`}>
              <Icon size={15} />
              {label}
            </Link>
          ))}
        </nav>

        {/* Right side */}
        <div className="flex items-center gap-2">

          {/* Notification bell */}
          <div className="relative" ref={bellRef}>
            <button
              onClick={() => setShowNotifs(v => !v)}
              className="relative p-1.5 rounded-lg text-slate-500
                         hover:text-slate-200 hover:bg-slate-800 transition-all">
              <Bell size={16} />
              {unread > 0 && (
                <span className="absolute -top-0.5 -right-0.5 min-w-[16px] h-4
                                 bg-amber-500 text-slate-950 text-[10px] font-bold
                                 rounded-full flex items-center justify-center px-0.5">
                  {unread > 9 ? '9+' : unread}
                </span>
              )}
            </button>
            {showNotifs && (
              <NotificationPanel onClose={() => setShowNotifs(false)} />
            )}
          </div>

          {/* Profile link */}
          <Link to="/profile"
            className="hidden sm:flex items-center gap-2 text-sm
                       hover:text-amber-400 transition-colors group px-2 py-1
                       rounded-lg hover:bg-slate-800">
            <div className="w-6 h-6 rounded-full bg-slate-700 flex items-center
                            justify-center overflow-hidden">
              {user?.avatar_path ? (
                <img src={`/api/v1/users/${user.id}/avatar`} alt=""
                     className="w-full h-full object-cover"
                     onError={e => e.target.style.display='none'} />
              ) : (
                <User size={12} className="text-slate-300" />
              )}
            </div>
            <div className="flex flex-col leading-tight">
              <span className="text-slate-300 font-medium text-xs">
                {user?.full_name?.split(' ')[0]}
              </span>
              <span className={`text-xs font-mono capitalize
                ${isTeacher() ? 'text-amber-400' : 'text-sky-400'}`}>
                {user?.role}
              </span>
            </div>
          </Link>

          <button onClick={logout}
            className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400
                       hover:bg-rose-400/10 transition-all">
            <LogOut size={15} />
          </button>
        </div>
      </div>
    </header>
  )
}
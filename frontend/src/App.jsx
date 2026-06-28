import { Routes, Route, Navigate } from 'react-router-dom'
import useAuthStore    from './store/authStore'
import Layout          from './components/Layout'
import Login           from './pages/Login'
import Dashboard       from './pages/Dashboard'
import Assignments     from './pages/Assignments'
import AssignmentDetail from './pages/AssignmentDetail'
import Submit          from './pages/Submit'
import Results         from './pages/Results'
import Profile         from './pages/Profile'
import Students        from './pages/Students'
import StudentDetail   from './pages/StudentDetail'

function ProtectedRoute({ children }) {
  const token = useAuthStore(s => s.token)
  return token ? children : <Navigate to="/login" replace />
}

// Redirects already-authenticated users away from the login page
function PublicRoute({ children }) {
  const token = useAuthStore(s => s.token)
  return token ? <Navigate to="/dashboard" replace /> : children
}

export default function App() {
  return (
    <Routes>
      {/* Login is only accessible when NOT authenticated */}
      <Route
        path="/login"
        element={
          <PublicRoute>
            <Login />
          </PublicRoute>
        }
      />

      {/* All other routes require authentication */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index                           element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard"                element={<Dashboard />} />
        <Route path="assignments"              element={<Assignments />} />
        <Route path="assignments/:id"          element={<AssignmentDetail />} />
        <Route path="assignments/:id/submit"   element={<Submit />} />
        <Route path="submissions/:id"          element={<Results />} />
        <Route path="profile"                  element={<Profile />} />
        <Route path="students"                 element={<Students />} />
        <Route path="students/:id"             element={<StudentDetail />} />
      </Route>

      {/* Catch-all redirect */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}
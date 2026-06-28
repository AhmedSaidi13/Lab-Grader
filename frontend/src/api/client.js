import axios from 'axios'
import toast from 'react-hot-toast'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30_000,
})

// ── Attach JWT ────────────────────────────────────────────────
api.interceptors.request.use(config => {
  const raw = localStorage.getItem('auth-storage')
  if (raw) {
    try {
      const { state } = JSON.parse(raw)
      if (state?.token) {
        config.headers.Authorization = `Bearer ${state.token}`
      }
    } catch { /* ignore */ }
  }
  return config
})

// ── Global error handler ──────────────────────────────────────
api.interceptors.response.use(
  res => res,
  err => {
    const msg = err.response?.data?.detail || err.message || 'Request failed'
    if (err.response?.status === 401) {
      localStorage.removeItem('auth-storage')
      window.location.href = '/login'
    } else if (err.response?.status !== 404) {
      toast.error(typeof msg === 'string' ? msg : JSON.stringify(msg))
    }
    return Promise.reject(err)
  }
)

// ── Auth ─────────────────────────────────────────────────────
export const authAPI = {
  login:    data => api.post('/auth/login', data),
  register: data => api.post('/auth/register', data),
  me:       ()   => api.get('/auth/me'),
}

// ── Assignments ───────────────────────────────────────────────
export const assignmentsAPI = {
  list:             ()        => api.get('/assignments'),
  get:              id        => api.get(`/assignments/${id}`),
  create:           data      => api.post('/assignments', data),
  update:           (id, data)=> api.patch(`/assignments/${id}`, data),
  delete:           id        => api.delete(`/assignments/${id}`),
  uploadSolution:   (id, form)=> api.post(`/assignments/${id}/reference-solution`, form),
  uploadLabel:      (id, form)=> api.post(`/assignments/${id}/label`, form),
  uploadSubject:    (id, form)=> api.post(`/assignments/${id}/subject-file`, form),
  downloadSubject:  id        => api.get(`/assignments/${id}/download`, { responseType: 'blob' }),
  generateTests:    (id, n)   => api.post(`/assignments/${id}/generate-tests?desired_count=${n}`),
  generateTestsAsync:(id, n)  => api.post(`/submissions/assignment/${id}/generate-tests-async?desired_count=${n}`),
  generateFromInputs:(id, body)=> api.post(`/assignments/${id}/generate-tests-from-inputs`, body),
  listTestCases:    id        => api.get(`/assignments/${id}/test-cases`),
  replaceTestCases: (id, body)=> api.put(`/assignments/${id}/test-cases`, body),
  clearTestCases:   id        => api.delete(`/assignments/${id}/test-cases`),
  analyseReference: id        => api.post(`/assignments/${id}/analyse-reference`),
  createWithFiles: (form) => api.post('/assignments/create-with-files', form),
}

// ── Submissions ───────────────────────────────────────────────
export const submissionsAPI = {
  submit:              (assignmentId, form) =>
                         api.post(`/submissions?assignment_id=${assignmentId}`, form),
  mySubmissionFor:     (assignmentId) =>
                         api.get(`/submissions/my-submission/${assignmentId}`),
  mine:                (assignmentId) =>
                         api.get(`/submissions/mine${assignmentId
                           ? `?assignment_id=${assignmentId}` : ''}`),
  get:                 id  => api.get(`/submissions/${id}`),
  status:              id  => api.get(`/submissions/${id}/status`),
  report:              id  => api.get(`/submissions/${id}/report`),
  getFeedback:         id  => api.get(`/submissions/${id}/feedback`),
  delete:              id  => api.delete(`/submissions/${id}`),
  taskProgress:        tid => api.get(`/submissions/tasks/${tid}/progress`),
  assignmentSubs:      id  => api.get(`/submissions/assignment/${id}`),
  stats:               id  => api.get(`/submissions/assignment/${id}/stats`),
  leaderboard:         id  => api.get(`/submissions/assignment/${id}/leaderboard`),
  bulkReevaluate:      id  => api.post(`/submissions/assignment/${id}/reevaluate`),
}

// usersAPI:
export const usersAPI = {
  getProfile:       ()         => api.get('/users/profile'),
  updateProfile:    (data)     => api.patch('/users/profile', data),
  uploadAvatar:     (form)     => api.post('/users/profile/avatar', form),
  getMyAvatar:      ()         => api.get('/users/profile/avatar',
                                    { responseType: 'blob' }),
  getUserAvatar:    (id)       => `/api/v1/users/${id}/avatar`,
  listStudents:     ()         => api.get('/users/students'),
  studentScores:    (id)       => api.get(`/users/students/${id}/scores`),
}

export const notificationsAPI = {
  list:        (unread_only = false) =>
                 api.get(`/notifications?unread_only=${unread_only}`),
  unreadCount: ()      => api.get('/notifications/unread-count'),
  markRead:    (id)    => api.patch(`/notifications/${id}/read`),
  markAllRead: ()      => api.patch('/notifications/read-all'),
}

export default api
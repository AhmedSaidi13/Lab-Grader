import { create } from 'zustand'
import { persist } from 'zustand/middleware'

const useAuthStore = create(
  persist(
    (set, get) => ({
      user:  null,
      token: null,

      login: (token, user) => set({ token, user }),
      logout: () => {
        set({ token: null, user: null })
        window.location.href = '/login'
      },
      isTeacher: () => {
        const role = get().user?.role
        return role === 'teacher' || role === 'admin'
      },
      isAdmin: () => get().user?.role === 'admin',
    }),
    { name: 'auth-storage' }
  )
)

export default useAuthStore
import { createContext, useContext, useState, useCallback } from 'react'
import { api } from '../api/client'

const AuthCtx = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem('tk_user')) } catch { return null }
  })

  const login = useCallback(async (email, password) => {
    const data = await api.login(email, password)
    localStorage.setItem('tk_token', data.access_token)
    // Decode JWT payload for role
    const payload = JSON.parse(atob(data.access_token.split('.')[1]))
    const u = { email, role: payload.role, id: payload.sub }
    localStorage.setItem('tk_user', JSON.stringify(u))
    setUser(u)
    return u
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('tk_token')
    localStorage.removeItem('tk_user')
    setUser(null)
  }, [])

  return <AuthCtx.Provider value={{ user, login, logout }}>{children}</AuthCtx.Provider>
}

export const useAuth = () => useContext(AuthCtx)
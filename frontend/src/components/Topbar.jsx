import { useAuth } from './AuthContext'
import { useNavigate } from 'react-router-dom'

export default function Topbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <div className="topbar">
      <div className="topbar-brand">
        Recruitment <span>/ Dashboard</span>
      </div>
      <div className="topbar-right">
        {user && (
          <>
            <span style={{ color: 'var(--muted)', fontSize: 12 }}>{user.email}</span>
            <span className={`badge-role ${user.role}`}>{user.role}</span>
            <button className="btn btn-ghost btn-sm" onClick={handleLogout}>Sign out</button>
          </>
        )}
      </div>
    </div>
  )
}
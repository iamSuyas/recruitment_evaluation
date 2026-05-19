import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './components/AuthContext'
import LoginPage from './pages/LoginPage'
import CandidateListPage from './pages/CandidateListPage'
import CandidateDetailPage from './pages/CandidateDetailPage'
import './index.css'

function PrivateRoute({ children }) {
  const { user } = useAuth()
  return user ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/candidates" element={<PrivateRoute><CandidateListPage /></PrivateRoute>} />
          <Route path="/candidates/:id" element={<PrivateRoute><CandidateDetailPage /></PrivateRoute>} />
          <Route path="*" element={<Navigate to="/candidates" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
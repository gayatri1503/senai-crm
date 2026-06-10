import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import Inbox from './pages/Inbox'
import Analytics from './pages/Analytics'
import { LayoutDashboard, Inbox as InboxIcon, BarChart3 } from 'lucide-react'
import './index.css'

export default function App() {
  return (
    <BrowserRouter>
      <div style={{ display: 'flex', minHeight: '100vh' }}>
        {/* Sidebar */}
        <nav style={{
          width: '220px',
          background: '#1a1f2e',
          borderRight: '1px solid #2d3748',
          padding: '24px 0',
          display: 'flex',
          flexDirection: 'column',
          gap: '4px',
          flexShrink: 0,
        }}>
          {/* Logo */}
          <div style={{
            padding: '0 20px 24px',
            borderBottom: '1px solid #2d3748',
            marginBottom: '8px',
          }}>
            <div style={{ fontSize: '18px', fontWeight: 700, color: '#6366f1' }}>
              SenAI CRM
            </div>
            <div style={{ fontSize: '11px', color: '#6b7280', marginTop: '2px' }}>
              Agentic Intelligence
            </div>
          </div>

          <NavItem to="/" icon={<InboxIcon size={16} />} label="Inbox" />
          <NavItem to="/analytics" icon={<BarChart3 size={16} />} label="Analytics" />
        </nav>

        {/* Main content */}
        <main style={{ flex: 1, overflow: 'auto' }}>
          <Routes>
            <Route path="/" element={<Inbox />} />
            <Route path="/analytics" element={<Analytics />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

function NavItem({ to, icon, label }) {
  return (
    <NavLink
      to={to}
      end
      style={({ isActive }) => ({
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        padding: '10px 20px',
        color: isActive ? '#6366f1' : '#9ca3af',
        background: isActive ? '#1e2237' : 'transparent',
        borderRight: isActive ? '2px solid #6366f1' : '2px solid transparent',
        textDecoration: 'none',
        fontSize: '14px',
        fontWeight: isActive ? 600 : 400,
        transition: 'all 0.15s',
      })}
    >
      {icon}
      {label}
    </NavLink>
  )
}
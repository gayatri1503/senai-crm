import { useState, useEffect } from 'react'
import { fetchDashboardStats } from '../utils/api'
import EmailList from '../components/EmailList'
import ThreadWorkspace from '../components/ThreadWorkspace'

export default function Inbox() {
  const [stats, setStats] = useState(null)
  const [selectedEmail, setSelectedEmail] = useState(null)
  const [activeTab, setActiveTab] = useState('all')

  useEffect(() => {
    fetchDashboardStats()
      .then(r => setStats(r.data))
      .catch(console.error)
  }, [])

  const tabs = [
    { id: 'all', label: 'All' },
    { id: 'human', label: 'Needs Human' },
    { id: 'escalated', label: 'Escalated' },
    { id: 'replied', label: 'Auto-Replied' },
    { id: 'spam', label: 'Spam' },
  ]

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div style={{
        padding: '20px 24px',
        borderBottom: '1px solid #2d3748',
        background: '#1a1f2e',
      }}>
        <h1 style={{ fontSize: '20px', fontWeight: 700, marginBottom: '16px' }}>
          Mission Control
        </h1>

        {/* Stats row */}
        {stats && (
          <div style={{ display: 'flex', gap: '16px', marginBottom: '16px', flexWrap: 'wrap' }}>
            <StatPill label="Total" value={stats.total} color="#6366f1" />
            <StatPill label="Needs Human" value={stats.needs_human} color="#f59e0b" />
            <StatPill label="Critical" value={stats.critical} color="#ef4444" />
            <StatPill label="Escalated" value={stats.by_status.escalated} color="#f97316" />
            <StatPill label="Spam Filtered" value={stats.spam_filtered} color="#6b7280" />
            <StatPill label="Security" value={stats.security_threats} color="#dc2626" />
          </div>
        )}

        {/* Tabs */}
        <div style={{ display: 'flex', gap: '4px' }}>
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                padding: '6px 14px',
                borderRadius: '6px',
                border: 'none',
                cursor: 'pointer',
                fontSize: '13px',
                fontWeight: activeTab === tab.id ? 600 : 400,
                background: activeTab === tab.id ? '#6366f1' : '#2d3748',
                color: activeTab === tab.id ? '#fff' : '#9ca3af',
                transition: 'all 0.15s',
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        <EmailList
          activeTab={activeTab}
          selectedEmail={selectedEmail}
          onSelect={setSelectedEmail}
        />
        {selectedEmail ? (
          <ThreadWorkspace email={selectedEmail} />
        ) : (
          <div style={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#4b5563',
            fontSize: '14px',
          }}>
            Select an email to view the thread workspace
          </div>
        )}
      </div>
    </div>
  )
}

function StatPill({ label, value, color }) {
  return (
    <div style={{
      background: '#0f1117',
      border: `1px solid ${color}40`,
      borderRadius: '8px',
      padding: '8px 14px',
      minWidth: '80px',
    }}>
      <div style={{ fontSize: '20px', fontWeight: 700, color }}>{value}</div>
      <div style={{ fontSize: '11px', color: '#6b7280', marginTop: '1px' }}>{label}</div>
    </div>
  )
}
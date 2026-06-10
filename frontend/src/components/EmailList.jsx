import { useState, useEffect } from 'react'
import { fetchAllEmails } from '../utils/api'

export default function EmailList({ activeTab, selectedEmail, onSelect }) {
  const [emails, setEmails] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  useEffect(() => {
    setLoading(true)
    const status = activeTab === 'all' ? null : activeTab
    fetchAllEmails(status)
      .then(r => {
        setEmails(r.data.emails)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [activeTab])

  const filtered = emails.filter(e => {
    if (!search) return true
    const q = search.toLowerCase()
    return (
      (e.subject || '').toLowerCase().includes(q) ||
      (e.sender || '').toLowerCase().includes(q) ||
      (e.body || '').toLowerCase().includes(q)
    )
  })

  return (
    <div style={{
      width: '380px',
      borderRight: '1px solid #2d3748',
      display: 'flex',
      flexDirection: 'column',
      flexShrink: 0,
    }}>
      {/* Search */}
      <div style={{ padding: '12px', borderBottom: '1px solid #2d3748' }}>
        <input
          type="text"
          placeholder="Search emails..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{
            width: '100%',
            padding: '8px 12px',
            background: '#0f1117',
            border: '1px solid #374151',
            borderRadius: '6px',
            color: '#e2e8f0',
            fontSize: '13px',
            outline: 'none',
          }}
        />
      </div>

      {/* Email list */}
      <div style={{ overflowY: 'auto', flex: 1 }}>
        {loading ? (
          <div style={{ padding: '20px', color: '#6b7280', fontSize: '13px' }}>
            Loading emails...
          </div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: '20px', color: '#6b7280', fontSize: '13px' }}>
            No emails found
          </div>
        ) : (
          filtered.map(email => (
            <EmailRow
              key={email.id}
              email={email}
              isSelected={selectedEmail?.id === email.id}
              onClick={() => onSelect(email)}
            />
          ))
        )}
      </div>

      {/* Footer count */}
      <div style={{
        padding: '8px 12px',
        borderTop: '1px solid #2d3748',
        fontSize: '11px',
        color: '#6b7280',
      }}>
        {filtered.length} emails
      </div>
    </div>
  )
}

function EmailRow({ email, isSelected, onClick }) {
  const urgencyColor = {
    Critical: '#ef4444',
    High: '#f59e0b',
    Medium: '#6366f1',
    Low: '#10b981',
  }[email.urgency] || '#6b7280'

  const sentimentColor = {
    Positive: '#10b981',
    Negative: '#ef4444',
    Neutral: '#6b7280',
    Mixed: '#f59e0b',
  }[email.sentiment] || '#6b7280'

  const sentimentLabel = {
    Positive: '+',
    Negative: '-',
    Neutral: '~',
    Mixed: '+/-',
  }[email.sentiment] || ''

  return (
    <div
      onClick={onClick}
      style={{
        padding: '12px 14px',
        borderBottom: '1px solid #1f2937',
        cursor: 'pointer',
        background: isSelected ? '#1e2237' : 'transparent',
        borderLeft: `3px solid ${isSelected ? '#6366f1' : urgencyColor + '60'}`,
        transition: 'background 0.1s',
      }}
      onMouseEnter={e => {
        if (!isSelected) e.currentTarget.style.background = '#161b27'
      }}
      onMouseLeave={e => {
        if (!isSelected) e.currentTarget.style.background = 'transparent'
      }}
    >
      {/* Row 1: sender + time */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '4px',
      }}>
        <span style={{
          fontSize: '13px',
          fontWeight: 600,
          color: email.is_spam ? '#6b7280' : '#e2e8f0',
          maxWidth: '220px',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}>
          {email.sender}
        </span>
        <span style={{ fontSize: '11px', color: '#4b5563', flexShrink: 0 }}>
          {formatTime(email.timestamp)}
        </span>
      </div>

      {/* Row 2: subject */}
      <div style={{
        fontSize: '12px',
        color: '#9ca3af',
        marginBottom: '6px',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
      }}>
        {email.subject || '(no subject)'}
      </div>

      {/* Row 3: badges */}
      <div style={{
        display: 'flex',
        gap: '4px',
        flexWrap: 'wrap',
        alignItems: 'center',
      }}>
        {email.urgency && (
          <span style={{
            fontSize: '10px',
            padding: '1px 6px',
            borderRadius: '10px',
            background: urgencyColor + '20',
            color: urgencyColor,
            fontWeight: 600,
          }}>
            {email.urgency}
          </span>
        )}
        {email.category && (
          <span style={{
            fontSize: '10px',
            padding: '1px 6px',
            borderRadius: '10px',
            background: '#1f2937',
            color: '#9ca3af',
          }}>
            {email.category}
          </span>
        )}
        {email.is_spam && (
          <span style={{
            fontSize: '10px',
            padding: '1px 6px',
            borderRadius: '10px',
            background: '#374151',
            color: '#9ca3af',
          }}>
            SPAM
          </span>
        )}
        {email.is_security_threat && (
          <span style={{
            fontSize: '10px',
            padding: '1px 6px',
            borderRadius: '10px',
            background: '#7f1d1d',
            color: '#fca5a5',
            fontWeight: 600,
          }}>
            SECURITY
          </span>
        )}
        {email.requires_human && !email.is_spam && (
          <span style={{
            fontSize: '10px',
            padding: '1px 6px',
            borderRadius: '10px',
            background: '#78350f20',
            color: '#fcd34d',
          }}>
            HUMAN
          </span>
        )}
        {email.sentiment && (
          <span style={{
            fontSize: '10px',
            padding: '1px 6px',
            borderRadius: '10px',
            background: sentimentColor + '20',
            color: sentimentColor,
            marginLeft: 'auto',
            fontWeight: 600,
          }}>
            {sentimentLabel} {email.sentiment}
          </span>
        )}
      </div>
    </div>
  )
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  const d = new Date(timestamp)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}
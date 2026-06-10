import { useState, useEffect } from 'react'
import { fetchThreads, runAgentDryRun, runAgent } from '../utils/api'

export default function ThreadWorkspace({ email }) {
  const [threadData, setThreadData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [agentResult, setAgentResult] = useState(null)
  const [agentLoading, setAgentLoading] = useState(false)
  const [showReasoning, setShowReasoning] = useState(false)
  const [activePanel, setActivePanel] = useState('thread')

  useEffect(() => {
    if (!email) return
    setLoading(true)
    setAgentResult(null)
    setThreadData(null)

    fetchThreads(email.sender)
      .then(r => {
        setThreadData(r.data)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [email])

  const handleDryRun = async () => {
    setAgentLoading(true)
    setShowReasoning(true)
    setActivePanel('agent')
    try {
      const r = await runAgentDryRun(email.id)
      setAgentResult(r.data)
    } catch (e) {
      setAgentResult({ error: e.message })
    }
    setAgentLoading(false)
  }

  const handleRunAgent = async () => {
    setAgentLoading(true)
    setShowReasoning(true)
    setActivePanel('agent')
    try {
      const r = await runAgent(email.id)
      setAgentResult(r.data)
    } catch (e) {
      setAgentResult({ error: e.message })
    }
    setAgentLoading(false)
  }

  if (loading) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#6b7280' }}>
        Loading thread...
      </div>
    )
  }

  const contact = threadData?.contact
  const threads = threadData?.threads || []
  const allEmails = threads.flatMap(t => t.emails).sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))

  return (
    <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>

      {/* Center — thread timeline */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

        {/* Header */}
        <div style={{
          padding: '16px 20px',
          borderBottom: '1px solid #2d3748',
          background: '#1a1f2e',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
        }}>
          <div>
            <div style={{ fontSize: '15px', fontWeight: 700, marginBottom: '4px' }}>
              {email.subject || '(no subject)'}
            </div>
            <div style={{ fontSize: '12px', color: '#6b7280' }}>
              {email.sender} &bull; {threads.length} thread(s) &bull; {allEmails.length} emails
            </div>
          </div>

          {/* Action buttons */}
          <div style={{ display: 'flex', gap: '8px', flexShrink: 0 }}>
            <button
              onClick={handleDryRun}
              disabled={agentLoading}
              style={{
                padding: '6px 12px',
                background: '#1f2937',
                border: '1px solid #374151',
                borderRadius: '6px',
                color: '#9ca3af',
                fontSize: '12px',
                cursor: 'pointer',
              }}
            >
              Dry Run
            </button>
            <button
              onClick={handleRunAgent}
              disabled={agentLoading}
              style={{
                padding: '6px 12px',
                background: '#4338ca',
                border: 'none',
                borderRadius: '6px',
                color: '#fff',
                fontSize: '12px',
                cursor: 'pointer',
                fontWeight: 600,
              }}
            >
              {agentLoading ? 'Running...' : 'Run Agent'}
            </button>
          </div>
        </div>

        {/* Panel tabs */}
        <div style={{
          display: 'flex',
          gap: '0',
          borderBottom: '1px solid #2d3748',
          background: '#1a1f2e',
        }}>
          {['thread', 'agent'].map(panel => (
            <button
              key={panel}
              onClick={() => setActivePanel(panel)}
              style={{
                padding: '8px 16px',
                border: 'none',
                background: 'transparent',
                color: activePanel === panel ? '#6366f1' : '#6b7280',
                borderBottom: activePanel === panel ? '2px solid #6366f1' : '2px solid transparent',
                cursor: 'pointer',
                fontSize: '13px',
                fontWeight: activePanel === panel ? 600 : 400,
                textTransform: 'capitalize',
              }}
            >
              {panel === 'thread' ? 'Thread' : 'Agent Reasoning'}
            </button>
          ))}
        </div>

        {/* Panel content */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px' }}>
          {activePanel === 'thread' && (
            <ThreadPanel emails={allEmails} />
          )}
          {activePanel === 'agent' && (
            <AgentPanel result={agentResult} loading={agentLoading} />
          )}
        </div>
      </div>

      {/* Right — contact profile */}
      <div style={{
        width: '260px',
        borderLeft: '1px solid #2d3748',
        padding: '16px',
        overflowY: 'auto',
        flexShrink: 0,
      }}>
        <ContactProfile contact={contact} email={email} />
      </div>
    </div>
  )
}


function ThreadPanel({ emails }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {emails.map((e, i) => (
        <div key={e.id || i} style={{
          background: '#1a1f2e',
          border: '1px solid #2d3748',
          borderRadius: '8px',
          overflow: 'hidden',
        }}>
          {/* Email header */}
          <div style={{
            padding: '10px 14px',
            borderBottom: '1px solid #2d3748',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            background: '#161b27',
          }}>
            <div>
              <span style={{ fontSize: '13px', fontWeight: 600, color: '#e2e8f0' }}>
                {e.sender}
              </span>
              <span style={{ fontSize: '11px', color: '#6b7280', marginLeft: '8px' }}>
                {new Date(e.timestamp).toLocaleString()}
              </span>
            </div>
            <div style={{ display: 'flex', gap: '4px' }}>
              {e.urgency && (
                <UrgencyBadge urgency={e.urgency} />
              )}
              {e.sentiment && (
                <SentimentBadge sentiment={e.sentiment} score={e.sentiment_score} />
              )}
            </div>
          </div>

          {/* Email body */}
          <div style={{ padding: '12px 14px' }}>
            <div style={{ fontSize: '12px', fontWeight: 600, color: '#9ca3af', marginBottom: '6px' }}>
              {e.subject}
            </div>
            <div style={{ fontSize: '13px', color: '#d1d5db', lineHeight: '1.6', whiteSpace: 'pre-wrap' }}>
              {e.body}
            </div>
          </div>

          {/* Classification */}
          {e.category && (
            <div style={{
              padding: '8px 14px',
              borderTop: '1px solid #2d3748',
              background: '#0f1117',
              display: 'flex',
              gap: '6px',
              flexWrap: 'wrap',
              alignItems: 'center',
            }}>
              <span style={{ fontSize: '11px', color: '#6b7280' }}>AI:</span>
              <Tag color="#1f2937" text={e.category} />
              {e.confidence && (
                <span style={{ fontSize: '11px', color: '#4b5563' }}>
                  {Math.round(e.confidence * 100)}% confidence
                </span>
              )}
              {e.escalation_reason && (
                <span style={{ fontSize: '11px', color: '#f59e0b', marginLeft: '4px' }}>
                  {e.escalation_reason}
                </span>
              )}
            </div>
          )}

          {/* Suggested reply */}
          {e.suggested_reply && (
            <div style={{
              padding: '10px 14px',
              borderTop: '1px solid #2d3748',
              background: '#0a1628',
            }}>
              <div style={{ fontSize: '11px', color: '#6b7280', marginBottom: '4px', fontWeight: 600 }}>
                SUGGESTED REPLY
              </div>
              <div style={{ fontSize: '12px', color: '#93c5fd', lineHeight: '1.5' }}>
                {e.suggested_reply}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}


function AgentPanel({ result, loading }) {
  if (loading) {
    return (
      <div style={{ color: '#6b7280', fontSize: '13px' }}>
        Agent is reasoning... this may take 10-20 seconds.
      </div>
    )
  }

  if (!result) {
    return (
      <div style={{ color: '#6b7280', fontSize: '13px' }}>
        Click "Dry Run" or "Run Agent" to see the reasoning trace.
      </div>
    )
  }

  if (result.error) {
    return (
      <div style={{ color: '#ef4444', fontSize: '13px' }}>
        Error: {result.error}
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      {/* Summary */}
      <div style={{
        background: '#1a1f2e',
        border: '1px solid #2d3748',
        borderRadius: '8px',
        padding: '12px 14px',
      }}>
        <div style={{ fontSize: '11px', color: '#6b7280', marginBottom: '6px', fontWeight: 600 }}>
          FINAL ANSWER
        </div>
        <div style={{ fontSize: '13px', color: '#e2e8f0', lineHeight: '1.6' }}>
          {result.final_answer}
        </div>
        <div style={{ fontSize: '11px', color: '#4b5563', marginTop: '8px' }}>
          Steps taken: {result.steps_taken} &bull; Dry run: {result.dry_run ? 'Yes' : 'No'}
        </div>
      </div>

      {/* Reasoning trace */}
      <div style={{ fontSize: '12px', color: '#6b7280', fontWeight: 600, marginBottom: '4px' }}>
        REASONING TRACE
      </div>
      {result.reasoning_trace?.map((step, i) => (
        <ReasoningStep key={i} step={step} />
      ))}
    </div>
  )
}


function ReasoningStep({ step }) {
  const colors = {
    thought: { bg: '#1a1f2e', border: '#374151', label: 'THOUGHT', labelColor: '#9ca3af' },
    action: { bg: '#0a1628', border: '#1e3a5f', label: 'ACTION', labelColor: '#93c5fd' },
    observation: { bg: '#0a1a0a', border: '#1a3a1a', label: 'OBSERVATION', labelColor: '#86efac' },
    final: { bg: '#1a1400', border: '#3a2f00', label: 'FINAL', labelColor: '#fcd34d' },
  }

  const style = colors[step.type] || colors.thought

  return (
    <div style={{
      background: style.bg,
      border: `1px solid ${style.border}`,
      borderRadius: '6px',
      padding: '10px 12px',
    }}>
      <div style={{ fontSize: '10px', color: style.labelColor, fontWeight: 700, marginBottom: '6px' }}>
        STEP {step.step} &bull; {style.label}
        {step.action && (
          <span style={{ color: '#93c5fd', marginLeft: '6px' }}>
            [{step.action}]
          </span>
        )}
      </div>
      <div style={{ fontSize: '12px', color: '#d1d5db', lineHeight: '1.5', whiteSpace: 'pre-wrap' }}>
        {step.content || JSON.stringify(step.result, null, 2)}
      </div>
    </div>
  )
}


function ContactProfile({ contact, email }) {
  if (!contact) return null

  const churnRisk = contact.churn_risk_score || 0
  const churnColor = churnRisk > 0.7 ? '#ef4444' : churnRisk > 0.4 ? '#f59e0b' : '#10b981'

  return (
    <div>
      <div style={{ fontSize: '12px', color: '#6b7280', fontWeight: 600, marginBottom: '12px' }}>
        CONTACT PROFILE
      </div>

      <div style={{ marginBottom: '16px' }}>
        <div style={{ fontSize: '14px', fontWeight: 700, color: '#e2e8f0', marginBottom: '2px' }}>
          {contact.name || contact.email.split('@')[0]}
        </div>
        <div style={{ fontSize: '12px', color: '#6b7280' }}>
          {contact.email}
        </div>
        {contact.company && (
          <div style={{ fontSize: '12px', color: '#9ca3af', marginTop: '2px' }}>
            {contact.company}
          </div>
        )}
      </div>

      <ProfileRow label="Status" value={contact.status} />
      <ProfileRow label="Account Value" value={`$${contact.account_value?.toLocaleString() || 0}`} />
      <ProfileRow
        label="Churn Risk"
        value={`${Math.round(churnRisk * 100)}%`}
        valueColor={churnColor}
      />
      <ProfileRow label="Open Threads" value={contact.open_threads || 0} />
      <ProfileRow label="Total Threads" value={contact.total_threads || 0} />

      {contact.last_contact_at && (
        <ProfileRow
          label="Last Contact"
          value={new Date(contact.last_contact_at).toLocaleDateString()}
        />
      )}

      {/* Current email classification */}
      <div style={{
        marginTop: '16px',
        paddingTop: '16px',
        borderTop: '1px solid #2d3748',
      }}>
        <div style={{ fontSize: '12px', color: '#6b7280', fontWeight: 600, marginBottom: '8px' }}>
          THIS EMAIL
        </div>
        {email.urgency && <ProfileRow label="Urgency" value={email.urgency} />}
        {email.category && <ProfileRow label="Category" value={email.category} />}
        {email.confidence && (
          <ProfileRow label="Confidence" value={`${Math.round(email.confidence * 100)}%`} />
        )}
        {email.is_security_threat && (
          <div style={{
            marginTop: '8px',
            padding: '6px 10px',
            background: '#7f1d1d',
            borderRadius: '6px',
            fontSize: '12px',
            color: '#fca5a5',
            fontWeight: 600,
          }}>
            SECURITY THREAT
          </div>
        )}
      </div>
    </div>
  )
}


function ProfileRow({ label, value, valueColor }) {
  return (
    <div style={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: '4px 0',
      borderBottom: '1px solid #1f2937',
    }}>
      <span style={{ fontSize: '11px', color: '#6b7280' }}>{label}</span>
      <span style={{ fontSize: '12px', color: valueColor || '#e2e8f0', fontWeight: 500 }}>
        {value}
      </span>
    </div>
  )
}


function UrgencyBadge({ urgency }) {
  const colors = {
    Critical: { bg: '#7f1d1d', color: '#fca5a5' },
    High: { bg: '#78350f', color: '#fcd34d' },
    Medium: { bg: '#1e3a5f', color: '#93c5fd' },
    Low: { bg: '#1a3a2e', color: '#86efac' },
  }[urgency] || { bg: '#1f2937', color: '#9ca3af' }

  return (
    <span style={{
      fontSize: '10px',
      padding: '2px 6px',
      borderRadius: '10px',
      background: colors.bg,
      color: colors.color,
      fontWeight: 600,
    }}>
      {urgency}
    </span>
  )
}


function SentimentBadge({ sentiment, score }) {
  const colors = {
    Positive: { bg: '#1a3a2e', color: '#86efac' },
    Negative: { bg: '#4a1d1d', color: '#fca5a5' },
    Neutral: { bg: '#1f2937', color: '#9ca3af' },
    Mixed: { bg: '#2d1f00', color: '#fbbf24' },
  }[sentiment] || { bg: '#1f2937', color: '#9ca3af' }

  return (
    <span style={{
      fontSize: '10px',
      padding: '2px 6px',
      borderRadius: '10px',
      background: colors.bg,
      color: colors.color,
    }}>
      {score !== null ? score?.toFixed(1) : sentiment}
    </span>
  )
}


function Tag({ color, text }) {
  return (
    <span style={{
      fontSize: '10px',
      padding: '1px 6px',
      borderRadius: '10px',
      background: color,
      color: '#9ca3af',
    }}>
      {text}
    </span>
  )
}
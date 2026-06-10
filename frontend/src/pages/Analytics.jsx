import { useState, useEffect } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie,
  Cell, Legend, BarChart, Bar
} from 'recharts'
import {
  fetchSentimentTrend,
  fetchCategoryBreakdown,
  fetchAtRiskAccounts
} from '../utils/api'

export default function Analytics() {
  const [sentimentData, setSentimentData] = useState(null)
  const [categoryData, setCategoryData] = useState(null)
  const [atRisk, setAtRisk] = useState(null)
  const [loading, setLoading] = useState(true)
  const [selectedSender, setSelectedSender] = useState(null)

  useEffect(() => {
    Promise.all([
      fetchSentimentTrend(1000),
      fetchCategoryBreakdown(1000),
      fetchAtRiskAccounts(),
    ]).then(([s, c, a]) => {
      setSentimentData(s.data)
      setCategoryData(c.data)
      setAtRisk(a.data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div style={{ padding: '24px', color: '#6b7280' }}>
        Loading analytics...
      </div>
    )
  }

  const CATEGORY_COLORS = {
    'Complaint': '#ef4444',
    'Inquiry': '#6366f1',
    'Bug Report': '#a855f7',
    'Feature Request': '#10b981',
    'Compliance': '#f59e0b',
    'Legal': '#dc2626',
    'Billing': '#3b82f6',
    'Other': '#6b7280',
    'Internal': '#374151',
    'Spam': '#4b5563',
  }

  // Build sentiment timeline for selected sender or all
  const senderList = sentimentData?.all_trends || []
  const deteriorating = sentimentData?.deteriorating_senders || []

  const selectedTrend = selectedSender
    ? senderList.find(s => s.sender === selectedSender)
    : null

  const chartData = selectedTrend
    ? selectedTrend.data_points.map((dp, i) => ({
        name: new Date(dp.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        score: dp.sentiment_score,
        moving_avg: selectedTrend.moving_average[i],
      }))
    : []

  return (
    <div style={{ padding: '24px', overflowY: 'auto', height: '100vh' }}>
      <h1 style={{ fontSize: '20px', fontWeight: 700, marginBottom: '24px' }}>
        Analytics Dashboard
      </h1>

      {/* Top stats */}
      <div style={{ display: 'flex', gap: '16px', marginBottom: '28px', flexWrap: 'wrap' }}>
        <StatCard
          label="Total Senders Tracked"
          value={sentimentData?.total_senders || 0}
          color="#6366f1"
        />
        <StatCard
          label="Deteriorating Accounts"
          value={deteriorating.length}
          color="#ef4444"
        />
        <StatCard
          label="Categories Classified"
          value={categoryData?.total_classified || 0}
          color="#10b981"
        />
        <StatCard
          label="At Risk Accounts"
          value={atRisk?.total_at_risk || 0}
          color="#f59e0b"
        />
      </div>

      {/* Alert banner for deteriorating senders */}
      {deteriorating.length > 0 && (
        <div style={{
          background: '#4a1d1d',
          border: '1px solid #7f1d1d',
          borderRadius: '8px',
          padding: '12px 16px',
          marginBottom: '24px',
        }}>
          <div style={{ fontSize: '13px', fontWeight: 700, color: '#fca5a5', marginBottom: '6px' }}>
            DETERIORATION ALERT — {deteriorating.length} sender(s) with 3+ consecutive negative emails
          </div>
          {deteriorating.map(s => (
            <div key={s.sender} style={{ fontSize: '12px', color: '#f87171', marginTop: '4px' }}>
              {s.sender} — avg score: {s.average_sentiment_score} — {s.max_consecutive_negative} consecutive negative emails
            </div>
          ))}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginBottom: '24px' }}>

        {/* Category breakdown */}
        <div style={{
          background: '#1a1f2e',
          border: '1px solid #2d3748',
          borderRadius: '8px',
          padding: '16px',
        }}>
          <div style={{ fontSize: '14px', fontWeight: 600, marginBottom: '16px', color: '#e2e8f0' }}>
            Category Distribution
          </div>
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie
                data={categoryData?.breakdown || []}
                dataKey="count"
                nameKey="category"
                cx="50%"
                cy="50%"
                outerRadius={80}
                label={({ category, percentage }) => `${category} ${percentage}%`}
                labelLine={false}
              >
                {(categoryData?.breakdown || []).map((entry, index) => (
                  <Cell
                    key={index}
                    fill={CATEGORY_COLORS[entry.category] || '#6b7280'}
                  />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ background: '#1a1f2e', border: '1px solid #374151', borderRadius: '6px' }}
                labelStyle={{ color: '#e2e8f0' }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Category bar chart */}
        <div style={{
          background: '#1a1f2e',
          border: '1px solid #2d3748',
          borderRadius: '8px',
          padding: '16px',
        }}>
          <div style={{ fontSize: '14px', fontWeight: 600, marginBottom: '16px', color: '#e2e8f0' }}>
            Email Volume by Category
          </div>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={categoryData?.breakdown || []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2d3748" />
              <XAxis
                dataKey="category"
                tick={{ fill: '#6b7280', fontSize: 10 }}
                angle={-30}
                textAnchor="end"
                height={50}
              />
              <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: '#1a1f2e', border: '1px solid #374151', borderRadius: '6px' }}
                labelStyle={{ color: '#e2e8f0' }}
              />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {(categoryData?.breakdown || []).map((entry, index) => (
                  <Cell
                    key={index}
                    fill={CATEGORY_COLORS[entry.category] || '#6b7280'}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Sentiment trend */}
      <div style={{
        background: '#1a1f2e',
        border: '1px solid #2d3748',
        borderRadius: '8px',
        padding: '16px',
        marginBottom: '24px',
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '16px',
        }}>
          <div style={{ fontSize: '14px', fontWeight: 600, color: '#e2e8f0' }}>
            Sentiment Trend
          </div>
          <select
            value={selectedSender || ''}
            onChange={e => setSelectedSender(e.target.value || null)}
            style={{
              background: '#0f1117',
              border: '1px solid #374151',
              borderRadius: '6px',
              color: '#e2e8f0',
              padding: '4px 8px',
              fontSize: '12px',
              outline: 'none',
            }}
          >
            <option value="">Select a sender...</option>
            {senderList.map(s => (
              <option key={s.sender} value={s.sender}>
                {s.sender} (avg: {s.average_sentiment_score})
              </option>
            ))}
          </select>
        </div>

        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2d3748" />
              <XAxis dataKey="name" tick={{ fill: '#6b7280', fontSize: 11 }} />
              <YAxis domain={[-1, 1]} tick={{ fill: '#6b7280', fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: '#1a1f2e', border: '1px solid #374151', borderRadius: '6px' }}
                labelStyle={{ color: '#e2e8f0' }}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="score"
                stroke="#6366f1"
                strokeWidth={2}
                dot={{ fill: '#6366f1', r: 4 }}
                name="Sentiment Score"
              />
              <Line
                type="monotone"
                dataKey="moving_avg"
                stroke="#f59e0b"
                strokeWidth={2}
                strokeDasharray="5 5"
                dot={false}
                name="Moving Average"
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div style={{ color: '#6b7280', fontSize: '13px', padding: '20px 0' }}>
            Select a sender to view their sentiment trend
          </div>
        )}
      </div>

      {/* At risk accounts */}
      <div style={{
        background: '#1a1f2e',
        border: '1px solid #2d3748',
        borderRadius: '8px',
        padding: '16px',
      }}>
        <div style={{ fontSize: '14px', fontWeight: 600, color: '#e2e8f0', marginBottom: '16px' }}>
          At-Risk Accounts
        </div>
        {atRisk?.accounts?.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {atRisk.accounts.map((account, i) => (
              <div key={i} style={{
                background: '#0f1117',
                border: '1px solid #2d3748',
                borderRadius: '6px',
                padding: '10px 14px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}>
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 600, color: '#e2e8f0' }}>
                    {account.sender}
                  </div>
                  <div style={{ fontSize: '11px', color: '#6b7280', marginTop: '2px' }}>
                    {account.subject} — {account.risk_reason}
                  </div>
                </div>
                <div style={{ fontSize: '12px', color: '#f59e0b', fontWeight: 600 }}>
                  {account.hours_since_activity}h ago
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ color: '#6b7280', fontSize: '13px' }}>
            No at-risk accounts detected
          </div>
        )}
      </div>
    </div>
  )
}

function StatCard({ label, value, color }) {
  return (
    <div style={{
      background: '#1a1f2e',
      border: `1px solid ${color}40`,
      borderRadius: '8px',
      padding: '14px 18px',
      minWidth: '150px',
    }}>
      <div style={{ fontSize: '24px', fontWeight: 700, color }}>{value}</div>
      <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '2px' }}>{label}</div>
    </div>
  )
}
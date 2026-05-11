import { useState, useEffect } from 'react'
import { getAnalyticsCandidates, getRankings, getDashboardCharts } from '../services/api'

export default function AnalyticsPage() {
  const [rankings, setRankings] = useState([])
  const [charts, setCharts] = useState({})
  const [candidates, setCandidates] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => { loadData() }, [])

  async function loadData() {
    try {
      const [rankRes, chartRes, candRes] = await Promise.all([
        getRankings(),
        getDashboardCharts(),
        getAnalyticsCandidates(),
      ])
      setRankings(rankRes.data || [])
      setCharts(chartRes.data || {})
      setCandidates(candRes.data || [])
    } catch (err) {
      console.error('Analytics load error:', err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div className="loading"><div className="spinner" /></div>

  const scoreData = charts.score_distribution || {}
  const eduData = charts.education_levels || {}

  function buildScoreBuckets(list) {
    const buckets = { '0-20': 0, '20-40': 0, '40-60': 0, '60-80': 0, '80-100': 0 }
    list.forEach(c => {
      const score = c.overall_score || 0
      if (score < 20) buckets['0-20'] += 1
      else if (score < 40) buckets['20-40'] += 1
      else if (score < 60) buckets['40-60'] += 1
      else if (score < 80) buckets['60-80'] += 1
      else buckets['80-100'] += 1
    })
    return buckets
  }

  function buildEducationLevels(list) {
    return list.reduce((acc, c) => {
      const level = (c.highest_degree || c.highest_qualification || 'other').toLowerCase()
      acc[level] = (acc[level] || 0) + 1
      return acc
    }, {})
  }

  function buildExperienceBuckets(list) {
    const buckets = { '0-2 yrs': 0, '2-5 yrs': 0, '5-10 yrs': 0, '10-15 yrs': 0, '15+ yrs': 0 }
    list.forEach(c => {
      const years = c.total_experience_years ?? c.experience_years ?? 0
      if (years < 2) buckets['0-2 yrs'] += 1
      else if (years < 5) buckets['2-5 yrs'] += 1
      else if (years < 10) buckets['5-10 yrs'] += 1
      else if (years < 15) buckets['10-15 yrs'] += 1
      else buckets['15+ yrs'] += 1
    })
    return buckets
  }

  const computedScores = Object.keys(scoreData).length ? scoreData : buildScoreBuckets(candidates)
  const computedEdu = Object.keys(eduData).length ? eduData : buildEducationLevels(candidates)
  const expData = buildExperienceBuckets(candidates)

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Analytics & Insights</h1>
          <p className="page-subtitle">Comprehensive analysis across {candidates.length} candidates</p>
        </div>
      </div>

      <div className="stats-row">
        <div className="stat-card">
          <div className="stat-label">Total Candidates</div>
          <div className="stat-value">{candidates.length}</div>
          <div className="stat-sub">Analyzed profiles</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Top Score</div>
          <div className="stat-value">{rankings[0]?.overall_score?.toFixed(1) || '—'}</div>
          <div className="stat-sub"><span className="up">{rankings[0]?.full_name || '—'}</span></div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Average Score</div>
          <div className="stat-value">
            {rankings.length ? (rankings.reduce((s, r) => s + r.overall_score, 0) / rankings.length).toFixed(1) : '—'}
          </div>
          <div className="stat-sub">Overall performance</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Top Tier (%)</div>
          <div className="stat-value">
            {rankings.length ? Math.round(rankings.filter(r => r.overall_score >= 70).length / rankings.length * 100) : 0}%
          </div>
          <div className="stat-sub">Score ≥ 70</div>
        </div>
      </div>

      <div className="two-col">
        <div className="card">
          <div className="card-title">Score Distribution</div>
          <div className="card-subtitle" style={{ marginBottom: 16 }}>Candidates grouped by score range</div>
          {Object.entries(computedScores).map(([range, count]) => (
            <div key={range} className="pub-row">
              <span className="pub-label">{range}</span>
              <div style={{ flex: 1 }}>
                <div className="progress-bar">
                  <div className="progress-fill blue"
                    style={{ width: `${candidates.length ? (count / candidates.length) * 100 : 0}%` }} />
                </div>
              </div>
              <span className="pub-count">{count}</span>
            </div>
          ))}
        </div>

        <div className="card">
          <div className="card-title">Education Levels</div>
          <div className="card-subtitle" style={{ marginBottom: 16 }}>Degree distribution across pool</div>
          {Object.entries(computedEdu).map(([level, count]) => (
            <div key={level} className="pub-row">
              <span className="pub-label" style={{ textTransform: 'capitalize' }}>{level || 'other'}</span>
              <div style={{ flex: 1 }}>
                <div className="progress-bar">
                  <div className="progress-fill green"
                    style={{ width: `${candidates.length ? (count / candidates.length) * 100 : 0}%` }} />
                </div>
              </div>
              <span className="pub-count">{count}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="card" style={{ marginBottom: 22 }}>
        <div className="card-title">Experience Distribution</div>
        <div className="card-subtitle" style={{ marginBottom: 16 }}>Years of experience across the pool</div>
        {Object.entries(expData).map(([range, count]) => (
          <div key={range} className="pub-row">
            <span className="pub-label">{range}</span>
            <div style={{ flex: 1 }}>
              <div className="progress-bar">
                <div className="progress-fill yellow"
                  style={{ width: `${candidates.length ? (count / candidates.length) * 100 : 0}%` }} />
              </div>
            </div>
            <span className="pub-count">{count}</span>
          </div>
        ))}
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Rank</th>
              <th>Candidate</th>
              <th>Overall Score</th>
              <th>Highest Degree</th>
              <th>Experience</th>
              <th>Publications</th>
              <th>Applied For</th>
            </tr>
          </thead>
          <tbody>
            {rankings.map(r => (
              <tr key={r.candidate_id}>
                <td>
                  <span className={`rank-badge ${r.rank <= 3 ? 'top' : ''}`}>
                    {r.rank <= 3 ? ['🥇','🥈','🥉'][r.rank-1] : `#${r.rank}`}
                  </span>
                </td>
                <td><span style={{ fontWeight: 600 }}>{r.full_name || 'N/A'}</span></td>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div className="progress-bar" style={{ width: 80 }}>
                      <div className={`progress-fill ${r.overall_score >= 80 ? 'green' : r.overall_score >= 60 ? 'blue' : 'yellow'}`}
                        style={{ width: `${r.overall_score}%` }} />
                    </div>
                    <span style={{ fontSize: '0.82rem', fontWeight: 600 }}>{r.overall_score?.toFixed(1)}</span>
                  </div>
                </td>
                <td style={{ textTransform: 'capitalize', fontSize: '0.82rem' }}>{r.highest_degree || 'N/A'}</td>
                <td>{r.experience_years || 0} yrs</td>
                <td style={{ textAlign: 'center' }}>{r.publication_count || 0}</td>
                <td style={{ fontSize: '0.78rem', color: 'var(--clr-text-muted)' }}>{r.post_applied_for || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

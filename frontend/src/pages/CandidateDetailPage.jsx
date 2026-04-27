import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getFullAssessment, getMissingInfo, sendInfoRequest } from '../services/api'

export default function CandidateDetailPage() {
  const { candidateId } = useParams()
  const [assessment, setAssessment] = useState(null)
  const [activeTab, setActiveTab] = useState('overview')
  const [loading, setLoading] = useState(true)
  const [showEmailModal, setShowEmailModal] = useState(false)

  useEffect(() => {
    loadAssessment()
  }, [candidateId])

  async function loadAssessment() {
    setLoading(true)
    try {
      const res = await getFullAssessment(candidateId)
      setAssessment(res.data)
    } catch (err) {
      console.error('Failed to load assessment:', err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div className="loading"><div className="spinner"></div></div>
  if (!assessment) return <div className="card"><div className="empty-state"><h3>Assessment Not Found</h3><Link to="/candidates" className="btn btn-primary" style={{ marginTop: '16px' }}>Back to Candidates</Link></div></div>

  const pi = assessment.personal_info || {}
  const edu = assessment.educational_assessment || {}
  const emp = assessment.employment_assessment || {}
  const missing = assessment.missing_info || {}
  const timeline = assessment.timeline_analysis || {}

  const tabs = [
    { id: 'overview', label: '📋 Overview' },
    { id: 'education', label: '🎓 Education' },
    { id: 'employment', label: '💼 Employment' },
    { id: 'research', label: '🔬 Research' },
    { id: 'missing', label: `⚠️ Missing Info (${missing.total_missing_fields || 0})` },
  ]

  return (
    <div>
      <div className="page-header candidate-page-header">
        <div className="candidate-title-block">
          <Link to="/candidates" style={{ fontSize: '0.8125rem', color: 'var(--clr-text-muted)' }}>← Back to Candidates</Link>
          <h1 className="page-title">{pi.full_name || 'Unknown Candidate'}</h1>
          <p className="page-subtitle">{pi.source_file} • {pi.post_applied_for || 'Position not specified'}</p>
        </div>
        <div className="candidate-score-panel">
          <div className={`score-circle ${assessment.overall_tier || 'below_average'}`}>
            {(assessment.overall_score || 0).toFixed(1)}
            <small>/100</small>
          </div>
          <span className={`tier-badge ${assessment.overall_tier || 'below_average'}`}>
            {(assessment.overall_tier || 'N/A').replace('_', ' ')}
          </span>
        </div>
      </div>

      {/* Tabs */}
      <div className="tabs">
        {tabs.map(t => (
          <button key={t.id} className={`tab ${activeTab === t.id ? 'active' : ''}`} onClick={() => setActiveTab(t.id)}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && <OverviewTab assessment={assessment} />}
      {activeTab === 'education' && <EducationTab edu={edu} />}
      {activeTab === 'employment' && <EmploymentTab emp={emp} timeline={timeline} />}
      {activeTab === 'research' && <ResearchTab res={assessment.research_assessment || {}} />}
      {activeTab === 'missing' && <MissingInfoTab missing={missing} email={assessment.missing_info_email} onShowEmail={() => setShowEmailModal(true)} />}

      {/* Email Modal */}
      {showEmailModal && assessment.missing_info_email && (
        <EmailModal
          email={assessment.missing_info_email}
          candidateId={candidateId}
          onClose={() => setShowEmailModal(false)}
        />
      )}
    </div>
  )
}

/* ── Overview Tab ──────────────────────────────────────────── */
function OverviewTab({ assessment }) {
  const breakdown = assessment.score_breakdown || {}
  const components = [
    { label: 'Education (30%)', value: breakdown.educational_contribution, max: 30, color: 'blue' },
    { label: 'Employment (35%)', value: breakdown.professional_contribution, max: 35, color: 'green' },
    { label: 'Completeness (15%)', value: breakdown.completeness_contribution, max: 15, color: 'yellow' },
    { label: 'Skills (20%)', value: breakdown.skill_contribution, max: 20, color: 'blue' },
  ]

  return (
    <div>
      {/* Quick Profile */}
      <div className="card" style={{ marginBottom: 'var(--space-md)' }}>
        <h3 className="card-title">Quick Profile</h3>
        <p style={{ fontSize: '0.875rem', color: 'var(--clr-text-secondary)', lineHeight: 1.7 }}>
          {assessment.summary_report || 'No summary available.'}
        </p>
      </div>

      <div className="detail-grid">
        {/* Score Breakdown */}
        <div className="card">
          <h3 className="card-title">Score Breakdown</h3>
          {components.map(c => (
            <div key={c.label} style={{ marginBottom: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                <span className="detail-label">{c.label}</span>
                <span className="detail-value">{(c.value || 0).toFixed(1)}/{c.max}</span>
              </div>
              <div className="progress-bar">
                <div className={`progress-fill ${c.color}`} style={{ width: `${c.max > 0 ? ((c.value || 0) / c.max) * 100 : 0}%` }}></div>
              </div>
            </div>
          ))}
        </div>

        {/* Strengths & Concerns */}
        <div className="card">
          <h3 className="card-title">Strengths</h3>
          <ul className="info-list" style={{ marginBottom: '16px' }}>
            {(assessment.strengths || []).map((s, i) => <li key={i} className="strength-item">{s}</li>)}
          </ul>
          <h3 className="card-title">Concerns</h3>
          <ul className="info-list">
            {(assessment.concerns || []).map((c, i) => <li key={i} className="concern-item">{c}</li>)}
          </ul>
        </div>
      </div>

      {/* Recommendation */}
      <div className="card" style={{ marginTop: 'var(--space-md)' }}>
        <h3 className="card-title">Recommendation</h3>
        <p style={{ fontSize: '0.875rem', color: 'var(--clr-text-secondary)', lineHeight: 1.7 }}>
          {assessment.recommendation || 'No recommendation available.'}
        </p>
      </div>
    </div>
  )
}

/* ── Education Tab ─────────────────────────────────────────── */
function EducationTab({ edu }) {
  const school = edu.school_records || []
  const higher = edu.higher_education_records || []
  const gaps = edu.gaps || []
  const institutionQuality = edu.institution_quality || []

  function formatGapDuration(months) {
    const total = Number(months || 0)
    const years = Math.floor(total / 12)
    const remMonths = total % 12
    if (years > 0 && remMonths > 0) return `${years} year${years > 1 ? 's' : ''} ${remMonths} month${remMonths > 1 ? 's' : ''}`
    if (years > 0) return `${years} year${years > 1 ? 's' : ''}`
    return `${remMonths} month${remMonths !== 1 ? 's' : ''}`
  }

  function formatGapType(gapType) {
    if (!gapType) return 'Education Gap'
    return gapType.replace(/_to_/gi, ' → ').replace(/_/g, ' ')
  }

  return (
    <div>
      {/* Summary metrics */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon blue">🎓</div>
          <div>
            <div className="stat-value">{(edu.overall_educational_strength || 0).toFixed(1)}</div>
            <div className="stat-label">Educational Strength</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon green">📈</div>
          <div>
            <div className="stat-value" style={{ fontSize: '1.25rem', textTransform: 'capitalize' }}>{edu.performance_trend || 'N/A'}</div>
            <div className="stat-label">Performance Trend</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon yellow">🏛️</div>
          <div>
            <div className="stat-value" style={{ fontSize: '1.25rem', textTransform: 'uppercase' }}>{edu.highest_qualification_level || 'N/A'}</div>
            <div className="stat-label">Highest Qualification</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon blue">📊</div>
          <div>
            <div className="stat-value">{edu.average_score ? edu.average_score.toFixed(1) + '%' : 'N/A'}</div>
            <div className="stat-label">Average Score</div>
          </div>
        </div>
      </div>

      {/* Education Records */}
      {(school.length > 0 || higher.length > 0) && (
        <div className="card" style={{ marginBottom: 'var(--space-md)' }}>
          <h3 className="card-title">Education Timeline</h3>
          <div className="timeline">
            {[...school, ...higher].map((rec, i) => (
              <div key={i} className="timeline-item">
                <div className="timeline-title">{rec.degree_title_raw || rec.degree_title_normalized || 'N/A'}</div>
                <div className="timeline-subtitle">{rec.institution_name || rec.board_or_university || 'N/A'}</div>
                <div className="timeline-meta">
                  {rec.passing_year || rec.completion_year || 'Year N/A'}
                  {rec.score_normalized_percentage && ` • Score: ${rec.score_normalized_percentage}%`}
                  {rec.specialization && ` • ${rec.specialization}`}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Educational Gaps */}
      {gaps.length > 0 && (
        <div className="card">
          <h3 className="card-title">Educational Gaps</h3>
          {gaps.map((g, i) => (
            <div key={i} className="detail-item" style={{ alignItems: 'flex-start' }}>
              <div>
                <div style={{ fontWeight: 600, fontSize: '0.875rem' }}>{formatGapType(g.gap_type)}</div>
                <div style={{ fontSize: '0.8125rem', color: 'var(--clr-text-muted)' }}>
                  {formatGapDuration(g.duration_months)} ({g.start_date} – {g.end_date})
                </div>
                {g.justification_detail && (
                  <div style={{ fontSize: '0.75rem', color: 'var(--clr-text-secondary)', marginTop: '4px' }}>
                    {g.justification_detail}
                  </div>
                )}
              </div>
              <div>
                {g.is_flagged && !g.justified_by_experience && <span className="severity critical">Unexplained</span>}
                {g.is_flagged && g.justified_by_experience && <span className="severity useful">Justified</span>}
                {!g.is_flagged && <span style={{ color: 'var(--clr-success)', fontSize: '0.8125rem' }}>✓ OK</span>}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Institution Rankings */}
      {institutionQuality.length > 0 && (
        <div className="card" style={{ marginTop: 'var(--space-md)' }}>
          <h3 className="card-title">Institution Rankings (THE / QS)</h3>
          {institutionQuality.map((inst, i) => (
            <div key={i} className="detail-item" style={{ alignItems: 'flex-start' }}>
              <div>
                <div style={{ fontWeight: 600, fontSize: '0.875rem' }}>
                  {inst.institution_name || 'Unknown Institution'}
                </div>
                <div style={{ fontSize: '0.8125rem', color: 'var(--clr-text-muted)' }}>
                  THE: {inst.the_rank ? `#${inst.the_rank}` : 'Unavailable'}
                  {' • '}
                  QS: {inst.qs_rank ? `#${inst.qs_rank}` : 'Unavailable'}
                </div>
                {inst.unavailable_reason && (
                  <div style={{ fontSize: '0.75rem', color: 'var(--clr-text-secondary)', marginTop: '4px' }}>
                    {inst.unavailable_reason}
                  </div>
                )}
              </div>
              <div>
                <span className={`severity ${inst.ranking_status === 'both_available' ? 'useful' : inst.ranking_status === 'the_only' || inst.ranking_status === 'qs_only' ? 'important' : 'critical'}`}>
                  {(inst.ranking_status || 'unavailable').replace(/_/g, ' ')}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Narrative */}
      {edu.narrative_summary && (
        <div className="card" style={{ marginTop: 'var(--space-md)' }}>
          <h3 className="card-title">Assessment Narrative</h3>
          <p style={{ fontSize: '0.875rem', color: 'var(--clr-text-secondary)', lineHeight: 1.7 }}>{edu.narrative_summary}</p>
        </div>
      )}
    </div>
  )
}

/* ── Employment Tab ────────────────────────────────────────── */
function EmploymentTab({ emp, timeline }) {
  const records = emp.experience_records || []
  const gaps = emp.justified_gaps || []
  const overlaps = timeline.overlaps || []

  return (
    <div>
      {/* Summary metrics */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon blue">💼</div>
          <div>
            <div className="stat-value">{(emp.overall_professional_strength || 0).toFixed(1)}</div>
            <div className="stat-label">Professional Strength</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon green">📅</div>
          <div>
            <div className="stat-value">{(emp.total_years_of_experience || 0).toFixed(1)}</div>
            <div className="stat-label">Years of Experience</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon yellow">📈</div>
          <div>
            <div className="stat-value" style={{ fontSize: '1.25rem', textTransform: 'capitalize' }}>{emp.seniority_trajectory || 'N/A'}</div>
            <div className="stat-label">Career Trajectory</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon blue">🔄</div>
          <div>
            <div className="stat-value">{(emp.employment_continuity_score || 0).toFixed(1)}</div>
            <div className="stat-label">Continuity Score</div>
          </div>
        </div>
      </div>

      {/* Experience Records */}
      {records.length > 0 && (
        <div className="card" style={{ marginBottom: 'var(--space-md)' }}>
          <h3 className="card-title">Employment Timeline</h3>
          <div className="timeline">
            {records.map((rec, i) => (
              <div key={i} className="timeline-item">
                <div className="timeline-title">{rec.post_job_title || 'N/A'}</div>
                <div className="timeline-subtitle">{rec.organization || 'N/A'}{rec.location ? ` • ${rec.location}` : ''}</div>
                <div className="timeline-meta">
                  {rec.start_year || '?'} – {rec.end_year || 'Present'}
                  {rec.duration_years != null && ` (${rec.duration_years} yr${rec.duration_years !== 1 ? 's' : ''})`}
                  <span style={{ marginLeft: '8px' }} className={`severity ${rec.seniority_level === 'leadership' ? 'critical' : rec.seniority_level === 'senior' ? 'important' : 'useful'}`}>
                    {rec.seniority_level}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="detail-grid">
        {/* Gaps */}
        {gaps.length > 0 && (
          <div className="card">
            <h3 className="card-title">Employment Gaps</h3>
            {gaps.map((g, i) => (
              <div key={i} className="detail-item" style={{ flexDirection: 'column', alignItems: 'flex-start' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                  <span style={{ fontWeight: 600, fontSize: '0.875rem' }}>{g.gap_period} ({g.duration_months} months)</span>
                  <span className={`severity ${g.justification_type === 'unexplained' ? 'critical' : 'useful'}`}>
                    {g.justification_type}
                  </span>
                </div>
                <div style={{ fontSize: '0.8125rem', color: 'var(--clr-text-muted)', marginTop: '4px' }}>{g.justification_detail}</div>
              </div>
            ))}
          </div>
        )}

        {/* Timeline Anomalies */}
        {(timeline.anomalies || []).length > 0 && (
          <div className="card">
            <h3 className="card-title">Timeline Anomalies</h3>
            <ul className="info-list">
              {timeline.anomalies.map((a, i) => <li key={i} className="concern-item">{a}</li>)}
            </ul>
          </div>
        )}
      </div>

      {/* Narrative */}
      {emp.narrative_summary && (
        <div className="card" style={{ marginTop: 'var(--space-md)' }}>
          <h3 className="card-title">Assessment Narrative</h3>
          <p style={{ fontSize: '0.875rem', color: 'var(--clr-text-secondary)', lineHeight: 1.7 }}>{emp.narrative_summary}</p>
        </div>
      )}
    </div>
  )
}

/* ── Research Tab ──────────────────────────────────────────── */
function ResearchTab({ res }) {
  const pubs = res.publications || []
  const books = res.books || []
  const patents = res.patents || []

  return (
    <div>
      {/* Summary metrics */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon blue">🔬</div>
          <div>
            <div className="stat-value">{(res.total_publications || 0)}</div>
            <div className="stat-label">Publications</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon green">📚</div>
          <div>
            <div className="stat-value">{(res.total_books || 0)}</div>
            <div className="stat-label">Books</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon yellow">💡</div>
          <div>
            <div className="stat-value">{(res.total_patents || 0)}</div>
            <div className="stat-label">Patents</div>
          </div>
        </div>
      </div>

      {/* Publications */}
      {pubs.length > 0 && (
        <div className="card" style={{ marginBottom: 'var(--space-md)' }}>
          <h3 className="card-title">Publications</h3>
          <ul className="info-list">
            {pubs.map((rec, i) => (
              <li key={i} className="strength-item">
                <strong>{rec.paper_title || 'N/A'}</strong>
                <br/>
                <span style={{ fontSize: '0.8125rem', color: 'var(--clr-text-muted)' }}>
                  {rec.authors || 'Unknown authors'} • {(rec.publication_year || 'Year N/A')}
                  <br/>
                  <em>{rec.venue_name || 'Verification Pending'}</em>
                </span>
                {rec.publication_type && (
                  <span className={`severity useful`} style={{ marginLeft: '8px' }}>
                    {rec.publication_type}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Books and Patents */}
      <div className="detail-grid" style={{ marginBottom: 'var(--space-md)' }}>
        {books.length > 0 && (
          <div className="card">
            <h3 className="card-title">Books</h3>
            <ul className="info-list">
              {books.map((rec, i) => (
                <li key={i} className="detail-item" style={{display: 'block'}}>
                  <strong>{rec.book_title || 'N/A'}</strong>
                  <br/>
                  <span style={{ fontSize: '0.8125rem', color: 'var(--clr-text-muted)' }}>
                    {rec.publication_year || 'Year N/A'}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {patents.length > 0 && (
          <div className="card">
            <h3 className="card-title">Patents</h3>
            <ul className="info-list">
              {patents.map((rec, i) => (
                <li key={i} className="detail-item" style={{display: 'block'}}>
                  <strong>{rec.patent_title || 'N/A'}</strong>
                  <br/>
                  <span style={{ fontSize: '0.8125rem', color: 'var(--clr-text-muted)' }}>
                    Filing Year: {rec.filing_year || 'N/A'}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Narrative */}
      {res.narrative_summary && (
        <div className="card" style={{ marginTop: 'var(--space-md)' }}>
          <h3 className="card-title">Assessment Narrative</h3>
          <p style={{ fontSize: '0.875rem', color: 'var(--clr-text-secondary)', lineHeight: 1.7 }}>{res.narrative_summary}</p>
        </div>
      )}
    </div>
  )
}

/* ── Missing Info Tab ──────────────────────────────────────── */
function MissingInfoTab({ missing, email, onShowEmail }) {
  const fields = missing.fields || []

  return (
    <div>
      {/* Summary */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon red">📋</div>
          <div>
            <div className="stat-value">{missing.total_missing_fields || 0}</div>
            <div className="stat-label">Total Missing Fields</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon red">🚨</div>
          <div>
            <div className="stat-value">{missing.critical_count || 0}</div>
            <div className="stat-label">Critical Missing</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon green">✅</div>
          <div>
            <div className="stat-value">{(missing.completeness_percentage || 0).toFixed(0)}%</div>
            <div className="stat-label">Data Completeness</div>
          </div>
        </div>
      </div>

      {/* Email Button */}
      {email && (
        <div className="card" style={{ marginBottom: 'var(--space-md)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <h3 className="card-title">Missing Info Email Draft</h3>
            <p className="card-subtitle">A personalized email has been drafted for the candidate.</p>
          </div>
          <button className="btn btn-primary" onClick={onShowEmail}>📧 View Email Draft</button>
        </div>
      )}

      {/* Missing Fields List */}
      {fields.length > 0 ? (
        <div className="card">
          <h3 className="card-title">Missing Fields</h3>
          <div className="table-container" style={{ border: 'none' }}>
            <table>
              <thead>
                <tr>
                  <th>Section</th>
                  <th>Field</th>
                  <th>Severity</th>
                  <th>Detail</th>
                </tr>
              </thead>
              <tbody>
                {fields.map((f, i) => (
                  <tr key={i} style={{ cursor: 'default' }}>
                    <td style={{ textTransform: 'capitalize' }}>{f.section}</td>
                    <td>{f.field_name?.replace(/_/g, ' ')}</td>
                    <td><span className={`severity ${f.severity}`}>{f.severity}</span></td>
                    <td style={{ fontSize: '0.8125rem', color: 'var(--clr-text-secondary)' }}>{f.missing_detail}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="card">
          <div className="empty-state">
            <h3>All Information Complete</h3>
            <p>No missing fields detected for this candidate.</p>
          </div>
        </div>
      )}
    </div>
  )
}

/* ── Email Modal ───────────────────────────────────────────── */
function EmailModal({ email, candidateId, onClose }) {
  const [sending, setSending] = useState(false)
  const [sent, setSent] = useState(false)

  async function handleSend() {
    setSending(true)
    try {
      await sendInfoRequest(candidateId, {
        email_subject: email.subject,
        email_body: email.body,
        recipient: email.recipient,
      })
      setSent(true)
    } catch (err) {
      console.error('Failed to send email:', err)
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3 className="modal-title">📧 Email Draft</h3>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        <div style={{ marginBottom: '16px' }}>
          <div className="detail-item">
            <span className="detail-label">To:</span>
            <span className="detail-value">{email.recipient || 'N/A'}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Subject:</span>
            <span className="detail-value">{email.subject}</span>
          </div>
        </div>

        <div className="email-preview">{email.body}</div>

        <div style={{ display: 'flex', gap: '8px', marginTop: '16px', justifyContent: 'flex-end' }}>
          <button className="btn btn-secondary" onClick={onClose}>Close</button>
          {!sent ? (
            <button className="btn btn-success" onClick={handleSend} disabled={sending}>
              {sending ? 'Saving...' : '📤 Save as Draft'}
            </button>
          ) : (
            <span style={{ color: 'var(--clr-success)', fontWeight: 600, padding: '8px' }}>✓ Draft Saved</span>
          )}
        </div>
      </div>
    </div>
  )
}

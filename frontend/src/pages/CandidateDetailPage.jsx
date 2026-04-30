import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getFullAssessment, getMissingInfo, sendInfoRequest, updateCandidateStatus } from '../services/api'

function toDisplayText(value, { titleCase = false } = {}) {
  if (value === null || value === undefined) return ''
  const cleaned = String(value).replace(/_/g, ' ').trim()
  if (!titleCase) return cleaned
  return cleaned
    .split(' ')
    .filter(Boolean)
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

function splitSentences(text) {
  return String(text)
    .split(/[.!?]\s+/)
    .map(s => s.trim())
    .filter(Boolean)
}

function mergeInitialSentences(sentences) {
  const merged = []
  for (let i = 0; i < sentences.length; i += 1) {
    const current = sentences[i]
    const next = sentences[i + 1]
    if (/^[A-Za-z]\.$/.test(current) && next) {
      merged.push(`${current} ${next}`)
      i += 1
      continue
    }
    merged.push(current)
  }
  return merged
}

function buildQuickProfileLines(assessment) {
  const lines = []
  const pi = assessment.personal_info || {}
  const edu = assessment.educational_assessment || {}
  const emp = assessment.employment_assessment || {}
  const res = assessment.research_assessment || {}
  const missing = assessment.missing_info || {}

  if (assessment.summary_report) {
    const sentences = mergeInitialSentences(splitSentences(assessment.summary_report))
    sentences.slice(0, 2).forEach(s => lines.push(s.endsWith('.') ? s : `${s}.`))
  }

  const tier = toDisplayText(assessment.overall_tier)
  if (assessment.overall_score !== null && assessment.overall_score !== undefined) {
    lines.push(`Overall score ${assessment.overall_score.toFixed(1)}/100${tier ? ` (${tier})` : ''}.`)
  }

  if (emp.total_years_of_experience !== null && emp.total_years_of_experience !== undefined) {
    const trajectory = emp.seniority_trajectory ? `, trajectory ${toDisplayText(emp.seniority_trajectory)}` : ''
    lines.push(`Experience: ${emp.total_years_of_experience.toFixed(1)} years${trajectory}.`)
  }

  if (edu.highest_qualification_level) {
    lines.push(`Highest qualification: ${toDisplayText(edu.highest_qualification_level)}.`)
  }

  const researchParts = []
  if (res.total_publications !== null && res.total_publications !== undefined) researchParts.push(`${res.total_publications} publications`)
  if (res.total_books !== null && res.total_books !== undefined) researchParts.push(`${res.total_books} books`)
  if (res.total_patents !== null && res.total_patents !== undefined) researchParts.push(`${res.total_patents} patents`)
  if (researchParts.length > 0) {
    lines.push(`Research output: ${researchParts.join(', ')}.`)
  }

  if (missing.completeness_percentage !== null && missing.completeness_percentage !== undefined) {
    lines.push(`Profile completeness: ${Math.round(missing.completeness_percentage)}%.`)
  }

  if (pi.post_applied_for) {
    lines.push(`Applied for ${pi.post_applied_for}.`)
  }

  const unique = Array.from(new Set(lines.map(line => line.trim()).filter(Boolean)))
  if (unique.length < 4) {
    unique.push(pi.source_file ? `Source file: ${pi.source_file}.` : 'Additional details available in the full assessment.')
  }
  if (unique.length < 4) {
    unique.push('Review Education and Employment tabs for deeper context.')
  }

  return unique.slice(0, 5)
}

export default function CandidateDetailPage() {
  const { candidateId } = useParams()
  const [assessment, setAssessment] = useState(null)
  const [activeTab, setActiveTab] = useState('overview')
  const [loading, setLoading] = useState(true)
  const [showEmailModal, setShowEmailModal] = useState(false)
  const [pipelineStatus, setPipelineStatus] = useState('unreviewed')
  const [statusUpdating, setStatusUpdating] = useState(false)

  useEffect(() => {
    loadAssessment()
  }, [candidateId])

  async function loadAssessment() {
    setLoading(true)
    try {
      const res = await getFullAssessment(candidateId)
      setAssessment(res.data)
      setPipelineStatus(res.data?.pipeline_status || 'unreviewed')
    } catch (err) {
      console.error('Failed to load assessment:', err)
    } finally {
      setLoading(false)
    }
  }

  async function handleStatusUpdate(nextStatus) {
    setStatusUpdating(true)
    try {
      await updateCandidateStatus(candidateId, nextStatus)
      setPipelineStatus(nextStatus)
    } catch (err) {
      console.error('Failed to update status:', err)
      window.alert('Failed to update candidate status. Please try again.')
    } finally {
      setStatusUpdating(false)
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
    { id: 'coauthors', label: '🤝 Co-Authors' },
    { id: 'publications', label: '📄 Publications' },
    { id: 'missing', label: `⚠️ Missing (${missing.total_missing_fields || 0})` },
  ]

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <Link to="/candidates" className="back-link">← Back</Link>
          <h1 className="page-title">{pi.full_name || 'Unknown Candidate'}</h1>
          <p className="page-subtitle">{pi.source_file || 'Source file unavailable'} • {pi.post_applied_for || 'Position not specified'}</p>
          <div className="candidate-action-buttons">
            <button
              className="btn btn-success btn-sm"
              disabled={statusUpdating}
              onClick={() => handleStatusUpdate('shortlisted')}
            >
              Shortlist
            </button>
            <button
              className="btn btn-danger btn-sm"
              disabled={statusUpdating}
              onClick={() => handleStatusUpdate('rejected')}
            >
              Reject
            </button>
            <button
              className="btn btn-secondary btn-sm"
              disabled={statusUpdating}
              onClick={() => handleStatusUpdate('unreviewed')}
            >
              Clear
            </button>
          </div>
          <div className="candidate-status-row">
            <span className={`status-badge ${pipelineStatus}`}>{pipelineStatus.replace(/_/g, ' ')}</span>
          </div>
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
      {activeTab === 'coauthors' && <CoauthorsTab res={assessment.research_assessment || {}} />}
      {activeTab === 'publications' && <PublicationsTab res={assessment.research_assessment || {}} />}
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
        <ul className="info-list" style={{ marginTop: 8 }}>
          {buildQuickProfileLines(assessment).map((line, idx) => (
            <li key={idx} className="quick-profile-item">{line}</li>
          ))}
        </ul>
      </div>

      <div className="detail-grid">
        {/* Score Breakdown */}
        <div className="card">
          <h3 className="card-title">Score Breakdown</h3>
          {components.map(c => (
            <div key={c.label} style={{ marginBottom: '12px' }}>
              <div className="score-breakdown-row">
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
  const rankingItems = edu.institution_quality || []
  const rankingByName = new Map(
    rankingItems.map((r) => [r.institution_name, r])
  )
  const institutionRows = []
  const seen = new Set()
  ;[...higher].forEach((rec) => {
    const name = rec.institution_name || rec.board_or_university
    if (!name || seen.has(name)) return
    seen.add(name)
    const ranking = rec.institution_ranking || rankingByName.get(name) || {}
    institutionRows.push({
      institution_name: name,
      qs_display: ranking.qs_display || (ranking.qs_rank != null ? String(ranking.qs_rank) : 'Not Found'),
      the_display: ranking.the_display || (ranking.the_rank != null ? String(ranking.the_rank) : 'Not Found'),
    })
  })

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

      {institutionRows.length > 0 && (
        <div className="card" style={{ marginBottom: 'var(--space-md)' }}>
          <h3 className="card-title">Institution Rankings</h3>
          <div className="ranking-table">
            {institutionRows.map((row, i) => (
              <div key={i} className="ranking-row">
                <div className="ranking-name">{row.institution_name}</div>
                <div className="ranking-values">
                  <span><strong>QS:</strong> {row.qs_display}</span>
                  <span><strong>THE:</strong> {row.the_display}</span>
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
            <div key={i} className="gap-card">
              <div className="gap-transition">{g.gap_type?.replace(/_to_/g, ' → ').replace(/_/g, ' ')}</div>
              <div className="gap-duration">
                {(g.duration_years || ((g.duration_months || 0) / 12)).toFixed(1).replace('.0', '')} year{(g.duration_years || ((g.duration_months || 0) / 12)) > 1 ? 's' : ''} ({g.start_date} – {g.end_date})
              </div>
              <div>
                <span className={`severity ${g.justified_by_experience ? 'useful' : 'critical'}`}>
                  {g.justified_by_experience ? 'Justified' : 'Unexplained'}
                </span>
              </div>
              {g.justification_detail && (
                <div className="gap-justification">{g.justification_detail}</div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Narrative */}
      {edu.narrative_summary && (
        <div className="card" style={{ marginTop: 'var(--space-md)' }}>
          <h3 className="card-title">Assessment Narrative</h3>
          <p style={{ fontSize: '0.875rem', color: 'var(--clr-text-secondary)', lineHeight: 1.7 }}>
            {toDisplayText(edu.narrative_summary)}
          </p>
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
  const recruiterSummary = res.recruiter_summary || {}
  const keyIndicators = recruiterSummary.key_indicators || []
  const riskFlags = recruiterSummary.risk_flags || []
  const booksAnalysis = res.books_analysis || {}
  const patentsAnalysis = res.patents_analysis || {}

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

      {(keyIndicators.length > 0 || riskFlags.length > 0) && (
        <div className="card" style={{ marginBottom: 'var(--space-md)' }}>
          <h3 className="card-title">Recruiter-Facing Evidence Summary</h3>
          {recruiterSummary.profile_level && (
            <div className="detail-item">
              <span className="detail-label">Profile Level</span>
              <span className="detail-value">
                {toDisplayText(recruiterSummary.profile_level)}
              </span>
            </div>
          )}
          {keyIndicators.length > 0 && (
            <ul className="info-list" style={{ marginTop: 10, marginBottom: 10 }}>
              {keyIndicators.map((item, idx) => <li key={idx} className="strength-item">{item}</li>)}
            </ul>
          )}
          {riskFlags.length > 0 && (
            <>
              <div style={{ fontSize: '0.75rem', color: 'var(--clr-text-muted)', marginBottom: 8 }}>RISK FLAGS</div>
              <ul className="info-list">
                {riskFlags.map((item, idx) => <li key={idx} className="concern-item">{item}</li>)}
              </ul>
            </>
          )}
        </div>
      )}

      {/* Publications */}
      {pubs.length > 0 && (
        <div className="card" style={{ marginBottom: 'var(--space-md)' }}>
          <h3 className="card-title">Publications</h3>
          <div className="table-wrap" style={{ marginTop: 12 }}>
            <table>
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Authors</th>
                  <th>Year</th>
                  <th>Venue</th>
                  <th>Type</th>
                  <th>Rank</th>
                  <th>Quartile</th>
                </tr>
              </thead>
              <tbody>
                {pubs.map((rec, i) => {
                  const isJournal = rec.publication_type_normalized === 'journal'
                  const rank = isJournal
                    ? (rec.sjr_rank || 'Not Found')
                    : (rec.conference_rank_resolved || rec.conference_rank_reported || 'Not Found')
                  const quartile = isJournal ? (rec.quartile || 'Not Found') : '—'
                  return (
                    <tr key={i} style={{ cursor: 'default' }}>
                      <td style={{ fontWeight: 600 }}>{rec.paper_title || 'N/A'}</td>
                      <td style={{ fontSize: '0.78rem', color: 'var(--clr-text-muted)' }}>{rec.authors || 'Unknown authors'}</td>
                      <td>{rec.publication_year || 'Year N/A'}</td>
                      <td style={{ fontStyle: 'italic' }}>{rec.venue_name || 'Verification Pending'}</td>
                      <td>{toDisplayText(rec.publication_type || rec.publication_type_normalized || 'N/A')}</td>
                      <td>{rank}</td>
                      <td>{quartile}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Books and Patents */}
      <div className="detail-grid" style={{ marginBottom: 'var(--space-md)' }}>
        {books.length > 0 && (
          <div className="card">
            <h3 className="card-title">Books</h3>
            <div className="detail-item"><span className="detail-label">Books Score</span><span className="detail-value">{(booksAnalysis.books_score || 0).toFixed(1)}/100</span></div>
            <div className="detail-item"><span className="detail-label">Authorship Mix</span><span className="detail-value">{Object.keys(booksAnalysis.authorship_distribution || {}).length || 0} role type(s)</span></div>
            <div className="detail-item"><span className="detail-label">Publisher Quality</span><span className="detail-value">{(booksAnalysis.publisher_quality_interpretation || '—').replace(/_/g, ' ')}</span></div>
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
            <div className="detail-item"><span className="detail-label">Patents Score</span><span className="detail-value">{(patentsAnalysis.patents_score || 0).toFixed(1)}/100</span></div>
            <div className="detail-item"><span className="detail-label">Translation Capability</span><span className="detail-value">{(patentsAnalysis.research_translation_capability || '—').replace(/_/g, ' ')}</span></div>
            <div className="detail-item"><span className="detail-label">Innovation Orientation</span><span className="detail-value">{(patentsAnalysis.innovation_orientation || '—').replace(/_/g, ' ')}</span></div>
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

/* ── Co-Authors Tab (M3) ──────────────────────────────────── */
function CoauthorsTab({ res }) {
  const coauthor = res.coauthor_analysis || {}
  const topCollabs = coauthor.top_collaborators || []
  const patterns = coauthor.collaboration_patterns || {}

  return (
    <div>
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon blue">🤝</div>
          <div>
            <div className="stat-value">{coauthor.total_unique_coauthors || 0}</div>
            <div className="stat-label">Unique Co-Authors</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon green">📝</div>
          <div>
            <div className="stat-value">{coauthor.avg_authors_per_paper || 0}</div>
            <div className="stat-label">Avg Authors/Paper</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon yellow">👤</div>
          <div>
            <div className="stat-value">{coauthor.solo_authored_count || 0}</div>
            <div className="stat-label">Solo Authored</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon blue">⭐</div>
          <div>
            <div className="stat-value">{(coauthor.collaboration_score || 0).toFixed(0)}</div>
            <div className="stat-label">Collaboration Score</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon green">🧭</div>
          <div>
            <div className="stat-value">{(coauthor.collaboration_diversity_score || 0).toFixed(0)}</div>
            <div className="stat-label">Diversity Score</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon yellow">⏱️</div>
          <div>
            <div className="stat-value">{(coauthor.collaboration_consistency || 0).toFixed(0)}</div>
            <div className="stat-label">Consistency</div>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 'var(--space-md)' }}>
        <h3 className="card-title">Collaboration Pattern</h3>
        <div className="detail-item">
          <span className="detail-label">Leadership Pattern</span>
          <span className="detail-value">{(coauthor.leadership_pattern || 'insufficient_data').replace(/_/g, ' ')}</span>
        </div>
        <div className="detail-item">
          <span className="detail-label">Stable Groups</span>
          <span className="detail-value">{coauthor.stable_research_group_count || 0}</span>
        </div>
        <div className="detail-item">
          <span className="detail-label">Recurring Collaborators</span>
          <span className="detail-value">{patterns.recurring_collaborators || 0}</span>
        </div>
        <div className="detail-item">
          <span className="detail-label">One-time Collaborators</span>
          <span className="detail-value">{patterns.one_time_collaborators || 0}</span>
        </div>
        {coauthor.collaboration_interpretation && (
          <p style={{ fontSize: '0.85rem', color: 'var(--clr-text-secondary)', marginTop: 8 }}>
            {coauthor.collaboration_interpretation}
          </p>
        )}
      </div>

      {topCollabs.length > 0 && (
        <div className="card">
          <h3 className="card-title">Top Collaborators</h3>
          <div className="card-subtitle" style={{ marginBottom: 16 }}>Most frequent co-authors</div>
          {topCollabs.map((c, i) => (
            <div key={i} className="pub-row">
              <span className="pub-label" style={{ fontWeight: 600 }}>{c.name}</span>
              <div style={{ flex: 1 }}>
                <div className="progress-bar">
                  <div className="progress-fill blue" style={{ width: `${Math.min(100, c.paper_count * 20)}%` }} />
                </div>
              </div>
              <span className="pub-count">{c.paper_count} paper(s)</span>
            </div>
          ))}
        </div>
      )}

      {topCollabs.length === 0 && (
        <div className="card"><div className="empty-state"><h3>No co-author data available</h3></div></div>
      )}
    </div>
  )
}

/* ── Publications Detail Tab (M3) ─────────────────────────── */
function PublicationsTab({ res }) {
  const pubAnalysis = res.publication_analysis || {}
  const topicVar = res.topic_variability || {}
  const keywords = topicVar.topic_keywords || []
  const topicTimeline = topicVar.topic_evolution_timeline || []
  const topicPercentages = topicVar.topic_percentages || []

  return (
    <div>
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon blue">📰</div>
          <div>
            <div className="stat-value">{pubAnalysis.journal_count || 0}</div>
            <div className="stat-label">Journals</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon green">🎤</div>
          <div>
            <div className="stat-value">{pubAnalysis.conference_count || 0}</div>
            <div className="stat-label">Conferences</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon yellow">🏅</div>
          <div>
            <div className="stat-value">{pubAnalysis.first_author_count || 0}</div>
            <div className="stat-label">First Author</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon blue">📊</div>
          <div>
            <div className="stat-value">{(pubAnalysis.publication_quality_score || 0).toFixed(0)}</div>
            <div className="stat-label">Quality Score</div>
          </div>
        </div>
      </div>

      <div className="two-col">
        <div className="card">
          <h3 className="card-title">Indexing & Impact</h3>
          <div className="detail-item"><span className="detail-label">WoS Indexed</span><span className="detail-value">{pubAnalysis.wos_count || 0}</span></div>
          <div className="detail-item"><span className="detail-label">Scopus Indexed</span><span className="detail-value">{pubAnalysis.scopus_count || 0}</span></div>
          <div className="detail-item"><span className="detail-label">Avg Impact Factor</span><span className="detail-value">{pubAnalysis.avg_impact_factor || '—'}</span></div>
          <div className="detail-item"><span className="detail-label">Q1 Papers</span><span className="detail-value">{pubAnalysis.q1_count || 0}</span></div>
          <div className="detail-item"><span className="detail-label">Q2 Papers</span><span className="detail-value">{pubAnalysis.q2_count || 0}</span></div>
        </div>
        <div className="card">
          <h3 className="card-title">Topic Variability</h3>
          <div className="detail-item"><span className="detail-label">Dominant Topic</span><span className="detail-value">{toDisplayText(topicVar.dominant_topic_area || '—', { titleCase: true })}</span></div>
          <div className="detail-item"><span className="detail-label">Profile</span><span className="detail-value">{toDisplayText(topicVar.profile_classification || '—')}</span></div>
          <div className="detail-item"><span className="detail-label">Unique Venues</span><span className="detail-value">{topicVar.unique_venues || 0}</span></div>
          <div className="detail-item"><span className="detail-label">Research Breadth</span><span className="detail-value">{toDisplayText(topicVar.research_breadth || '—')}</span></div>
          <div className="detail-item"><span className="detail-label">Variability Score</span><span className="detail-value">{(topicVar.variability_score || 0).toFixed(0)}/100</span></div>
          <div className="detail-item"><span className="detail-label">Topic Transitions</span><span className="detail-value">{topicVar.topic_transition_count || 0}</span></div>
          {topicPercentages.length > 0 && (
            <div style={{ marginTop: 10 }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--clr-text-muted)', marginBottom: 6 }}>TOPIC SHARE</div>
              {topicPercentages.slice(0, 4).map((t, i) => (
                <div key={i} className="detail-item">
                  <span className="detail-label">{toDisplayText(t.domain, { titleCase: true })}</span>
                  <span className="detail-value">{t.percentage}%</span>
                </div>
              ))}
            </div>
          )}
          {keywords.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--clr-text-muted)', marginBottom: 6 }}>TOP KEYWORDS</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {keywords.slice(0, 8).map((k, i) => (
                  <span key={i} className="severity useful">{k.keyword} ({k.count})</span>
                ))}
              </div>
            </div>
          )}
          {topicTimeline.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--clr-text-muted)', marginBottom: 6 }}>TOPIC EVOLUTION</div>
              {topicTimeline.slice(0, 6).map((t, i) => (
                <div key={i} className="detail-item">
                  <span className="detail-label">{t.year}</span>
                  <span className="detail-value">{toDisplayText(t.dominant_domain || 'unknown', { titleCase: true })}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

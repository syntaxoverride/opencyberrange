<template>
  <div class="grading-report">
    <div class="report-header">
      <h2 class="report-title">Incident Review</h2>
      <p class="report-meta">
        Reviewed by: <strong>{{ report?.manager_name || 'Alex Rivera' }}, SOC Manager</strong>
      </p>
    </div>

    <!-- Overall -->
    <div class="report-overall" :class="'band--' + (report?.overall_band || '').toLowerCase().replace(' ', '-')">
      <div class="overall-band">{{ report?.overall_band || 'Pending' }}</div>
      <div class="overall-label">{{ report?.overall_label || '' }}</div>
      <div class="overall-score">{{ report?.overall_percentage || 0 }}%</div>
      <div class="overall-detail">
        {{ report?.adjusted_total || 0 }}/{{ report?.effective_max || 0 }} points
        ({{ report?.milestone_points || 0 }} milestones + {{ report?.documentation_score || 0 }} documentation - {{ report?.hint_penalties || 0 }} hints)
      </div>
    </div>

    <!-- Milestones -->
    <div class="report-section">
      <h3 class="section-title">Investigation Milestones</h3>
      <div v-for="ms in (report?.milestone_results || [])" :key="ms.milestone_id" class="milestone-row">
        <div class="milestone-icon">
          <span v-if="ms.status === 'met'" class="ms-check">&#10003;</span>
          <span v-else-if="ms.status === 'auto_answered'" class="ms-auto">A</span>
          <span v-else class="ms-pending">&#x25CB;</span>
        </div>
        <div class="milestone-body">
          <div class="milestone-desc">
            {{ ms.description }}
            <span v-if="ms.is_optional" class="ms-optional">(optional)</span>
          </div>
          <div class="milestone-detail">
            <span class="ms-score">{{ ms.points_awarded }}/{{ ms.points_possible }} pts</span>
            <span v-if="ms.met_at" class="ms-time">met at {{ ms.met_at }}</span>
            <span v-if="ms.hints_received === 1" class="ms-hint">nudge received</span>
            <span v-if="ms.hints_received === 2" class="ms-hint ms-hint--warn">guidance received (-1 pt)</span>
            <span v-if="ms.hints_received >= 3" class="ms-hint ms-hint--danger">answer provided (-3 pts)</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Documentation -->
    <div class="report-section">
      <h3 class="section-title">Documentation Quality</h3>
      <div class="doc-score">
        <span class="doc-score__value">{{ report?.documentation_score || 0 }}/{{ report?.documentation_max || 5 }}</span>
        <span class="doc-score__label">bonus points</span>
      </div>
      <p class="doc-notes">{{ report?.documentation_notes || '' }}</p>
      <p class="doc-detail">{{ report?.update_count || 0 }} ticket updates submitted.</p>
    </div>

    <!-- Expert Comparison (toggle) -->
    <div class="report-section">
      <details class="expert-toggle">
        <summary class="expert-summary">View Expert Investigation (for learning, not scoring)</summary>
        <div class="expert-body">
          <p>The expert investigation for this scenario would include:</p>
          <ul>
            <li>Immediate triage with alert count and severity breakdown</li>
            <li>Source IP identification using Suricata alert grouping</li>
            <li>Attack classification supported by Zeek conn_state analysis</li>
            <li>Complete IOC list with all attacker and target indicators</li>
            <li>Detection rule submission to prevent recurrence</li>
            <li>Response recommendation including host isolation and credential rotation</li>
          </ul>
          <p>Compare your ticket updates against this checklist. Which steps did you complete thoroughly? Which ones could you improve?</p>
        </div>
      </details>
    </div>
  </div>
</template>

<script setup>
defineProps({
  report: { type: Object, default: null },
  exercise: { type: Object, default: null },
})
</script>

<style scoped>
.grading-report { max-width: 800px; margin: 0 auto; }

.report-header { margin-bottom: 1.5rem; }
.report-title { font-size: 1.5rem; font-weight: 700; color: var(--text-primary); margin: 0 0 0.5rem; }
.report-meta { font-size: 0.85rem; color: var(--text-secondary); margin: 0; }

.report-overall {
  background: var(--bg-secondary); border: 1px solid var(--border-color);
  border-radius: 10px; padding: 1.5rem; margin-bottom: 1.5rem; text-align: center;
  border-left: 4px solid var(--text-muted);
}
.band--expert { border-left-color: #22c55e; }
.band--proficient { border-left-color: #1a8a6e; }
.band--developing { border-left-color: #f59e0b; }
.band--needs-review { border-left-color: #ef4444; }

.overall-band { font-size: 1.2rem; font-weight: 700; color: var(--text-primary); }
.overall-label { font-size: 0.85rem; color: var(--text-secondary); margin: 0.25rem 0; }
.overall-score { font-size: 2rem; font-weight: 700; color: #1a8a6e; margin: 0.5rem 0; }
.overall-detail { font-size: 0.75rem; color: var(--text-muted); }

.report-section { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 10px; padding: 1.25rem; margin-bottom: 1rem; }
.section-title { font-size: 0.95rem; font-weight: 600; color: var(--text-primary); margin: 0 0 1rem; }

.milestone-row { display: flex; gap: 0.75rem; padding: 0.5rem 0; border-bottom: 1px solid var(--border-color); }
.milestone-row:last-child { border-bottom: none; }

.milestone-icon { width: 24px; flex-shrink: 0; text-align: center; font-size: 0.9rem; padding-top: 0.1rem; }
.ms-check { color: #22c55e; }
.ms-auto { color: #f59e0b; font-weight: 700; font-size: 0.7rem; }
.ms-pending { color: var(--text-muted); }

.milestone-body { flex: 1; }
.milestone-desc { font-size: 0.85rem; color: var(--text-primary); }
.ms-optional { font-size: 0.7rem; color: var(--text-muted); font-style: italic; }
.milestone-detail { display: flex; flex-wrap: wrap; gap: 0.75rem; margin-top: 0.25rem; }
.ms-score { font-size: 0.75rem; font-weight: 600; color: var(--text-secondary); }
.ms-time { font-size: 0.7rem; color: var(--text-muted); font-family: monospace; }
.ms-hint { font-size: 0.7rem; color: var(--text-muted); }
.ms-hint--warn { color: #f59e0b; }
.ms-hint--danger { color: #ef4444; }

.doc-score { display: flex; align-items: baseline; gap: 0.5rem; margin-bottom: 0.5rem; }
.doc-score__value { font-size: 1.5rem; font-weight: 700; color: #1a8a6e; }
.doc-score__label { font-size: 0.8rem; color: var(--text-muted); }
.doc-notes { font-size: 0.8rem; color: var(--text-secondary); line-height: 1.5; margin: 0 0 0.5rem; }
.doc-detail { font-size: 0.75rem; color: var(--text-muted); margin: 0; }

.expert-toggle { cursor: pointer; }
.expert-summary { font-size: 0.85rem; font-weight: 600; color: #1a8a6e; padding: 0.25rem 0; }
.expert-body { margin-top: 0.75rem; font-size: 0.8rem; color: var(--text-secondary); line-height: 1.6; }
.expert-body ul { margin: 0.5rem 0; padding-left: 1.5rem; }
.expert-body li { margin-bottom: 0.3rem; }
</style>

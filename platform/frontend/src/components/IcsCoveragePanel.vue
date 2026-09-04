<template>
  <div class="ics-coverage">
    <div class="panel">
      <div class="section-header">
        <h2>ICS ATT&amp;CK Coverage</h2>
        <button class="btn btn--secondary btn--sm" @click="fetchCoverage" :disabled="loading">
          {{ loading ? 'Loading...' : 'Refresh' }}
        </button>
      </div>

      <div v-if="loading" class="loading">Loading coverage...</div>

      <div v-else-if="error" class="empty-state">
        <p>Could not load ICS coverage.</p>
        <p class="cov-error-detail">{{ error }}</p>
      </div>

      <div v-else-if="tracks.length === 0" class="empty-state">
        <p>No tagged OT tracks yet.</p>
      </div>

      <template v-else>
        <!-- Track selector -->
        <div v-if="tracks.length > 1" class="cov-track-tabs">
          <button
            v-for="t in tracks"
            :key="t.slug"
            class="cov-track-btn"
            :class="{ 'cov-track-btn--active': t.slug === selectedSlug }"
            @click="selectedSlug = t.slug"
          >{{ t.name }}</button>
        </div>

        <template v-if="selectedTrack">
          <!-- a) Summary -->
          <div class="cov-summary">
            <div class="cov-summary-item">
              <span class="cov-summary-num">{{ selectedTrack.labs_tagged }} / {{ selectedTrack.labs_total }}</span>
              <span class="cov-summary-label">Labs tagged</span>
            </div>
            <div class="cov-summary-item">
              <span class="cov-summary-num">{{ selectedTrack.techniques_covered }} / {{ selectedTrack.techniques_total }}</span>
              <span class="cov-summary-label">Techniques covered</span>
            </div>
            <div class="cov-summary-item">
              <span class="cov-summary-num">{{ selectedTrack.tactics_touched }} / {{ selectedTrack.tactics_total }}</span>
              <span class="cov-summary-label">Tactics touched</span>
            </div>
          </div>

          <!-- b) Tactic heatmap -->
          <h3 class="cov-h3">Tactic heatmap</h3>
          <div class="table-container">
            <table class="data-table cov-heatmap">
              <thead>
                <tr>
                  <th>Tactic</th>
                  <th>Covered</th>
                  <th>Labs</th>
                  <th class="cov-bar-col">Coverage</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="tac in selectedTrack.tactics" :key="tac.key">
                  <td class="cov-tactic-name">{{ tac.name }}</td>
                  <td>{{ tac.covered }} / {{ tac.total }}</td>
                  <td>{{ tac.lab_count }}</td>
                  <td class="cov-bar-col">
                    <div class="cov-bar-track">
                      <div
                        class="cov-bar-fill"
                        :class="barClass(tac)"
                        :style="{ width: pct(tac.covered, tac.total) + '%' }"
                      ></div>
                    </div>
                    <span class="cov-bar-pct">{{ pct(tac.covered, tac.total) }}%</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- c) Covered techniques grouped by tactic -->
          <h3 class="cov-h3">Covered techniques</h3>
          <div v-if="coveredTactics.length === 0" class="empty-state">
            <p>No techniques covered yet.</p>
          </div>
          <div v-else class="cov-tech-groups">
            <div v-for="tac in coveredTactics" :key="tac.key" class="cov-tech-group">
              <div class="cov-tech-group-title">{{ tac.name }}</div>
              <div
                v-for="tech in coveredTechniques(tac)"
                :key="tech.id"
                class="cov-tech-row"
              >
                <div class="cov-tech-head">
                  <span class="cov-tech-id">{{ tech.id }}</span>
                  <span class="cov-tech-name">{{ techLabel(tech) }}</span>
                </div>
                <div class="cov-tech-labs">
                  <span
                    v-for="lab in tech.labs"
                    :key="lab.slug"
                    class="cov-lab-pill"
                    :title="lab.note || ''"
                  >{{ lab.name }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- d) Gaps -->
          <h3 class="cov-h3">Gaps</h3>
          <div v-if="!selectedTrack.gaps || selectedTrack.gaps.length === 0" class="empty-state">
            <p>No gaps. Every technique in scope is covered.</p>
          </div>
          <div v-else class="cov-gaps">
            <div v-for="gap in selectedTrack.gaps" :key="gap.tactic" class="cov-gap-group">
              <div class="cov-gap-tactic">{{ gap.tactic }}</div>
              <div class="cov-gap-techs">
                <span
                  v-for="tech in gap.techniques"
                  :key="tech.id"
                  class="cov-gap-pill"
                >{{ tech.id }} {{ tech.name }}</span>
              </div>
            </div>
          </div>

          <!-- e) Untagged labs -->
          <h3 class="cov-h3">Untagged labs</h3>
          <div v-if="!selectedTrack.untagged_labs || selectedTrack.untagged_labs.length === 0" class="empty-state">
            <p>All labs in this track are tagged.</p>
          </div>
          <div v-else class="cov-untagged">
            <span
              v-for="lab in selectedTrack.untagged_labs"
              :key="lab.slug"
              class="cov-untagged-pill"
            >{{ lab.name }}</span>
          </div>
        </template>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from '../api/axios'

const loading = ref(false)
const error = ref('')
const tracks = ref([])
const selectedSlug = ref(null)

const selectedTrack = computed(() => {
  if (!tracks.value.length) return null
  return tracks.value.find(t => t.slug === selectedSlug.value) || tracks.value[0]
})

const coveredTactics = computed(() => {
  if (!selectedTrack.value) return []
  return selectedTrack.value.tactics.filter(tac => coveredTechniques(tac).length > 0)
})

function coveredTechniques(tac) {
  return (tac.techniques || []).filter(tech => (tech.labs || []).length > 0)
}

function pct(covered, total) {
  if (!total) return 0
  return Math.round((covered / total) * 100)
}

function barClass(tac) {
  const p = pct(tac.covered, tac.total)
  if (p === 0) return 'cov-bar-fill--none'
  if (p >= 75) return 'cov-bar-fill--high'
  if (p >= 34) return 'cov-bar-fill--mid'
  return 'cov-bar-fill--low'
}

function techLabel(tech) {
  if (tech.aliases && tech.aliases.length) {
    return tech.name + ' (' + tech.aliases.join(', ') + ')'
  }
  return tech.name
}

async function fetchCoverage() {
  loading.value = true
  error.value = ''
  try {
    const res = await axios.get('/dashboard/instructor/ics-coverage')
    tracks.value = (res.data && res.data.tracks) || []
    if (tracks.value.length && !tracks.value.find(t => t.slug === selectedSlug.value)) {
      selectedSlug.value = tracks.value[0].slug
    }
  } catch (e) {
    error.value = (e.response && e.response.data && e.response.data.detail) || e.message || 'Request failed'
    tracks.value = []
  } finally {
    loading.value = false
  }
}

onMounted(fetchCoverage)
</script>

<style scoped>
.panel {
  background: var(--bg-secondary);
  border-radius: 12px;
  padding: 1.5rem;
  border: 1px solid var(--border-color);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.section-header h2 {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
}

.loading { text-align: center; padding: 3rem; color: var(--text-muted); }
.empty-state { text-align: center; padding: 2rem; color: var(--text-muted); font-size: 0.85rem; }
.empty-state p { margin-bottom: 0.5rem; }
.cov-error-detail { font-size: 0.75rem; color: var(--danger); }

/* Track selector */
.cov-track-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  margin-bottom: 1.25rem;
}

.cov-track-btn {
  padding: 0.4rem 0.85rem;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-secondary);
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.cov-track-btn:hover { border-color: var(--accent); color: var(--accent); }

.cov-track-btn--active {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}

/* Summary */
.cov-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.cov-summary-item {
  flex: 1 1 160px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.cov-summary-num {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
}

.cov-summary-label {
  font-size: 0.75rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.cov-h3 {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 1.75rem 0 0.75rem;
}

/* Table reuse */
.table-container { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; }

.data-table th,
.data-table td {
  padding: 0.6rem 1rem;
  text-align: left;
  border-bottom: 1px solid var(--border-color);
}

.data-table th {
  font-size: 0.6875rem;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  background: var(--bg-primary);
}

.data-table td {
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.cov-tactic-name { color: var(--text-primary); font-weight: 500; }

/* Heatmap bar */
.cov-bar-col { width: 40%; min-width: 200px; }

.cov-bar-track {
  display: inline-block;
  width: calc(100% - 3rem);
  height: 12px;
  background: var(--bg-tertiary);
  border-radius: 6px;
  overflow: hidden;
  vertical-align: middle;
}

.cov-bar-fill {
  height: 100%;
  border-radius: 6px;
  transition: width 0.2s;
}

.cov-bar-fill--none { background: transparent; }
.cov-bar-fill--low { background: var(--danger); }
.cov-bar-fill--mid { background: var(--warning, #f59e0b); }
.cov-bar-fill--high { background: var(--success); }

.cov-bar-pct {
  display: inline-block;
  width: 2.5rem;
  text-align: right;
  font-size: 0.75rem;
  color: var(--text-muted);
  vertical-align: middle;
}

/* Covered techniques */
.cov-tech-groups { display: flex; flex-direction: column; gap: 1rem; }

.cov-tech-group {
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 0.85rem 1rem;
  background: var(--bg-tertiary);
}

.cov-tech-group-title {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 0.65rem;
}

.cov-tech-row {
  padding: 0.5rem 0;
  border-top: 1px solid var(--border-color);
}

.cov-tech-row:first-of-type { border-top: none; }

.cov-tech-head {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  margin-bottom: 0.4rem;
}

.cov-tech-id {
  font-family: monospace;
  font-size: 0.75rem;
  color: var(--text-muted);
  background: var(--bg-primary);
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
}

.cov-tech-name { font-size: 0.8125rem; color: var(--text-primary); }

.cov-tech-labs { display: flex; flex-wrap: wrap; gap: 0.35rem; }

.cov-lab-pill {
  font-size: 0.75rem;
  color: var(--text-secondary);
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 0.15rem 0.6rem;
  cursor: default;
}

/* Gaps */
.cov-gaps { display: flex; flex-direction: column; gap: 0.85rem; }

.cov-gap-group {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.5rem;
}

.cov-gap-tactic {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--text-primary);
  min-width: 130px;
}

.cov-gap-techs { display: flex; flex-wrap: wrap; gap: 0.35rem; }

.cov-gap-pill {
  font-size: 0.72rem;
  color: var(--danger);
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 12px;
  padding: 0.15rem 0.6rem;
}

/* Untagged */
.cov-untagged { display: flex; flex-wrap: wrap; gap: 0.4rem; }

.cov-untagged-pill {
  font-size: 0.75rem;
  color: var(--text-secondary);
  background: var(--bg-tertiary);
  border: 1px dashed var(--border-color);
  border-radius: 12px;
  padding: 0.15rem 0.6rem;
}
</style>

<template>
  <div class="student-dashboard">
    <div class="dashboard-header">
      <img src="/ocr-logo-dark.png" alt="OpenCyberRange" class="dashboard-logo" />
      <div class="dashboard-header__text">
        <h1 class="page-title">Welcome, {{ username }}</h1>
        <p class="page-subtitle">Your training dashboard</p>
      </div>
    </div>

    <div class="dashboard-grid">
      <!-- Next Objective -->
      <div class="card card--objective">
        <div class="card__header">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="card__icon card__icon--blue">
            <circle cx="12" cy="12" r="10"/>
            <polygon points="10 8 16 12 10 16 10 8"/>
          </svg>
          <h2 class="card__title">Next Objective</h2>
        </div>
        <div v-if="data.next_objective" class="objective-info">
          <span class="objective-track">{{ data.next_objective.track_name }} - {{ data.next_objective.level_name }}</span>
          <h3 class="objective-name">{{ data.next_objective.lab_name }}</h3>
          <router-link :to="resumeLink" class="btn btn--primary">
            Resume Training
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-icon">
              <line x1="5" y1="12" x2="19" y2="12"/>
              <polyline points="12 5 19 12 12 19"/>
            </svg>
          </router-link>
        </div>
        <div v-else class="objective-complete">
          <span class="complete-bar"></span>
          <p>All labs completed!</p>
        </div>
      </div>

      <!-- Progress -->
      <div class="card card--progress">
        <div class="card__header">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="card__icon card__icon--green">
            <line x1="12" y1="20" x2="12" y2="10"/>
            <line x1="18" y1="20" x2="18" y2="4"/>
            <line x1="6" y1="20" x2="6" y2="16"/>
          </svg>
          <h2 class="card__title">My Progress</h2>
        </div>
        <div class="progress-info">
          <div class="progress-bar-wrapper">
            <div class="progress-bar">
              <div class="progress-bar__fill" :style="{ width: data.progress_percent + '%' }"></div>
            </div>
            <span class="progress-percent">{{ data.progress_percent }}%</span>
          </div>
          <span class="progress-count">{{ data.completed_labs }} / {{ data.total_labs }} labs completed</span>
        </div>
      </div>

      <!-- VPN Status -->
      <div class="card card--vpn">
        <div class="card__header">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="card__icon card__icon--cyan">
            <path d="M12 2L3 7V12C3 16.97 7.02 21.45 12 22C16.98 21.45 21 16.97 21 12V7L12 2Z"/>
          </svg>
          <h2 class="card__title">VPN Status</h2>
        </div>
        <div class="vpn-info">
          <div class="vpn-row">
            <span class="vpn-dot" :class="data.vpn_status?.vpn_registered ? 'vpn-dot--on' : 'vpn-dot--off'"></span>
            <span class="vpn-text">{{ data.vpn_status?.vpn_registered ? 'Registered' : 'Not Configured' }}</span>
          </div>
          <span v-if="data.vpn_status?.client_ip" class="vpn-ip">{{ data.vpn_status.client_ip }}</span>
          <router-link to="/vpn-setup" class="btn btn--outline btn--sm">
            {{ data.vpn_status?.has_config ? 'Download Config' : 'Setup VPN' }}
          </router-link>
        </div>
      </div>

      <!-- Rank (only shown when enrolled in a course) -->
      <div v-if="data.scoreboard_rank" class="card card--rank">
        <div class="card__header">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="card__icon card__icon--amber">
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
          </svg>
          <h2 class="card__title">Your Rank</h2>
        </div>
        <div class="rank-info">
          <span class="rank-number">#{{ data.scoreboard_rank }}</span>
          <span class="rank-course" v-if="data.course_name">in {{ data.course_name }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from '../api/axios'

const data = ref({
  next_objective: null,
  progress_percent: 0,
  total_labs: 0,
  completed_labs: 0,
  vpn_status: null,
  scoreboard_rank: null,
  course_name: null,
})

const username = computed(() => {
  try {
    const user = JSON.parse(localStorage.getItem('user') || '{}')
    if (!user.username) return 'Student'
    return user.username.charAt(0).toUpperCase() + user.username.slice(1).toLowerCase()
  } catch {
    return 'Student'
  }
})

// Deep-link "Resume Training" straight to the next incomplete lab. The track
// page opens the lab panel from the labId query param. Older backends that do
// not send track_slug fall back to the exercises list.
const resumeLink = computed(() => {
  const obj = data.value.next_objective
  if (obj?.track_slug && obj?.lab_id) {
    return { path: `/exercises/${obj.track_slug}`, query: { labId: String(obj.lab_id) } }
  }
  return '/exercises'
})

const fetchDashboard = async () => {
  try {
    const res = await axios.get('/dashboard/student')
    data.value = res.data
  } catch (e) {
    console.error('Failed to fetch student dashboard:', e)
  }
}

onMounted(() => {
  fetchDashboard()
})
</script>

<style scoped>
.student-dashboard {
  max-width: 900px;
  margin: 0 auto;
  padding: 2rem;
}

.dashboard-header {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  margin-bottom: 2rem;
}

.dashboard-logo {
  width: 72px;
  height: 72px;
  flex-shrink: 0;
  background: var(--bg-primary);
  border-radius: 14px;
  padding: 5px;
}

.page-title {
  font-size: 2rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 0.25rem 0;
}

.page-subtitle {
  color: var(--text-muted);
  font-size: 0.9375rem;
  margin: 0;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

/* Cards */
.card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 1.5rem;
}

.card__header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.card__icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.card__icon--blue { color: var(--accent); }
.card__icon--green { color: var(--success); }
.card__icon--cyan { color: #06b6d4; }
.card__icon--amber { color: var(--warning); }

.card__title {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin: 0;
}

/* Objective */
.objective-track {
  font-size: 0.75rem;
  color: var(--text-muted);
  display: block;
  margin-bottom: 0.25rem;
}

.objective-name {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 1rem 0;
}

.objective-complete {
  text-align: center;
  padding: 1rem 0;
}

.complete-bar {
  display: inline-block;
  width: 40px;
  height: 4px;
  border-radius: 2px;
  background: var(--success);
  margin-bottom: 0.5rem;
}

.objective-complete p {
  color: var(--text-secondary);
  margin: 0;
}

/* Progress */
.progress-info {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.progress-bar-wrapper {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.progress-bar {
  flex: 1;
  height: 10px;
  background: var(--bg-tertiary);
  border-radius: 999px;
  overflow: hidden;
}

.progress-bar__fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #22c55e);
  border-radius: 999px;
  transition: width 0.6s ease;
}

.progress-percent {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text-primary);
  min-width: 3rem;
  text-align: right;
}

.progress-count {
  font-size: 0.8125rem;
  color: var(--text-muted);
}

/* VPN */
.vpn-info {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.vpn-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.vpn-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.vpn-dot--on {
  background: var(--success);
  box-shadow: 0 0 6px rgba(34, 197, 94, 0.5);
}

.vpn-dot--off {
  background: var(--nav-label);
}

.vpn-text {
  font-size: 0.9375rem;
  font-weight: 500;
  color: var(--text-primary);
}

.vpn-ip {
  font-family: monospace;
  font-size: 0.875rem;
  color: var(--accent);
}

/* Rank */
.rank-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.rank-number {
  font-size: 2rem;
  font-weight: 700;
  color: var(--warning);
  line-height: 1.2;
}

.rank-course {
  font-size: 0.8125rem;
  color: var(--text-muted);
}

/* Buttons */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1.25rem;
  font-size: 0.8125rem;
  font-weight: 600;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  text-decoration: none;
  transition: all 0.2s;
}

.btn--primary {
  background: linear-gradient(135deg, #3b82f6, #1d4ed8);
  color: white;
}

.btn--primary:hover {
  background: linear-gradient(135deg, #2563eb, #1e40af);
}

.btn--outline {
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
}

.btn--outline:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.btn--sm {
  padding: 0.375rem 0.875rem;
  font-size: 0.75rem;
}

.btn-icon {
  width: 16px;
  height: 16px;
}

/* Responsive */
@media (max-width: 768px) {
  .student-dashboard {
    padding: 1rem;
  }

  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}
</style>

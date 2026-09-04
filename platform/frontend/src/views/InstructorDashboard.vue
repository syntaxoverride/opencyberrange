<template>
  <div class="instructor-dashboard">
    <div class="dashboard-header">
      <img src="/ocr-logo-dark.png" alt="OpenCyberRange" class="dashboard-logo" />
      <div class="dashboard-header__text">
        <h1 class="page-title">Ops Center</h1>
        <p class="page-subtitle">Real-time platform overview</p>
      </div>
    </div>

    <!-- System Health (admin only) -->
    <div v-if="showHealthCard" class="health-bar" :class="dashboardHealthClass ? `health-bar--${dashboardHealthClass}` : ''" @click="goToSystemHealth">
      <template v-if="dashboardHealthLoaded">
        <span class="health-dot" :class="`health-dot--${dashboardHealthStatus === 'ok' ? 'green' : dashboardHealthStatus === 'warning' ? 'amber' : 'red'}`"></span>
        <span class="health-bar__label">System</span>
      </template>
      <span v-else class="health-bar__label">Checking...</span>
    </div>

    <!-- Stat Cards -->
    <div class="stats-grid">
      <!-- Flags Today -->
      <div class="rich-card">
        <div class="rich-card__header">
          <svg class="rich-card__icon rich-card__icon--flags" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/>
            <line x1="4" y1="22" x2="4" y2="15"/>
          </svg>
          <span class="rich-card__label">Flags Today</span>
        </div>
        <div class="rich-card__body">
          <span class="rich-card__value">{{ stats.flags_today }}</span>
          <div class="rich-card__sparkline" v-if="stats.flags_sparkline?.length">
            <svg :viewBox="`0 0 ${stats.flags_sparkline.length * 12} 32`" preserveAspectRatio="none">
              <polyline
                :points="sparklinePoints(stats.flags_sparkline)"
                fill="none" stroke="#22c55e" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"
              />
            </svg>
          </div>
        </div>
        <div class="rich-card__footer">
          <span v-if="stats.flag_students_today" class="rich-card__detail">
            {{ stats.flag_students_today }} student{{ stats.flag_students_today !== 1 ? 's' : '' }}
          </span>
        </div>
      </div>

      <!-- Active Exercises -->
      <div class="rich-card">
        <div class="rich-card__header">
          <svg class="rich-card__icon rich-card__icon--active" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="5 3 19 12 5 21 5 3"/>
          </svg>
          <span class="rich-card__label">Active Now</span>
        </div>
        <div class="rich-card__body">
          <span class="rich-card__value">{{ stats.active_count || 0 }}</span>
        </div>
        <div class="rich-card__footer">
          <span v-if="!stats.active_count" class="rich-card__detail rich-card__detail--muted">No active sessions</span>
        </div>
      </div>

      <!-- Avg Completion -->
      <div class="rich-card">
        <div class="rich-card__header">
          <svg class="rich-card__icon rich-card__icon--time" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <polyline points="12 6 12 12 16 14"/>
          </svg>
          <span class="rich-card__label">Avg Completion</span>
        </div>
        <div class="rich-card__body">
          <span class="rich-card__value" :class="avgTimeColor">
            {{ stats.avg_completion_min != null ? stats.avg_completion_min + 'm' : '-' }}
          </span>
        </div>
        <div class="rich-card__footer">
          <span v-if="stats.avg_completion_typical != null" class="rich-card__detail">
            typical: {{ stats.avg_completion_typical }}m
          </span>
          <span v-else class="rich-card__detail rich-card__detail--muted">no data yet</span>
        </div>
      </div>
    </div>

    <!-- Date Range Filter -->
    <div class="filter-bar">
      <div class="filter-bar__presets">
        <button
          v-for="preset in [
            { key: '1h', label: '1h' },
            { key: '6h', label: '6h' },
            { key: '24h', label: '24h' },
            { key: '7d', label: '7d' },
            { key: 'custom', label: 'Custom' },
          ]"
          :key="preset.key"
          class="filter-pill"
          :class="{ 'filter-pill--active': activePreset === preset.key }"
          @click="selectPreset(preset.key)"
        >
          {{ preset.label }}
        </button>
      </div>
      <div class="filter-bar__dropdowns">
        <select
          v-model="selectedCourse"
          class="filter-select"
          @change="onCourseChange"
        >
          <option :value="null">All Courses</option>
          <option v-for="c in filterCourses" :key="c.id" :value="c.id">
            {{ c.code }}
          </option>
        </select>
        <select
          v-model="selectedUser"
          class="filter-select"
          @change="onUserChange"
        >
          <option :value="null">All Students</option>
          <option v-for="s in filterStudents" :key="s.id" :value="s.id">
            {{ s.username }}
          </option>
        </select>
      </div>
      <div v-if="activePreset === 'custom'" class="filter-bar__custom">
        <input
          type="datetime-local"
          v-model="customStart"
          class="filter-datetime"
        />
        <span class="filter-separator">to</span>
        <input
          type="datetime-local"
          v-model="customEnd"
          class="filter-datetime"
        />
      </div>
      <div class="filter-bar__export">
        <select v-model="exportFormat" class="filter-select filter-select--compact" title="Report format">
          <option value="pdf">PDF</option>
          <option value="csv">CSV</option>
        </select>
        <button
          class="export-btn"
          :disabled="exportLoading"
          @click="downloadReport"
          :title="`Download filtered view as ${exportFormat.toUpperCase()}`"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          {{ exportLoading ? 'Generating...' : 'Download Report' }}
        </button>
      </div>
    </div>

    <!-- The Pulse Chart -->
    <div class="panel">
      <div class="panel__header">
        <h2 class="panel__title">The Pulse</h2>
        <span class="panel__subtitle">{{ filterSubtitle }}</span>
      </div>
      <div class="chart-container">
        <Line v-if="pulseData.labels.length" :data="pulseData" :options="chartOptions" />
        <div v-else class="chart-empty">No activity data yet</div>
      </div>
    </div>

    <!-- Live Operations Feed -->
    <div class="panel">
      <div class="panel__header">
        <h2 class="panel__title">Live Operations Feed</h2>
        <span class="panel__subtitle feed-count">{{ studentFeed.length }} events</span>
        <button @click="fetchFeed('refresh')" class="refresh-btn" title="Refresh">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" :class="{ 'spin': feedLoading }">
            <polyline points="23 4 23 10 17 10"/>
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
          </svg>
        </button>
      </div>
      <div class="feed-table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th>User</th>
              <th>Event</th>
              <th>Target</th>
              <th>Time</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="studentFeed.length === 0 && !feedLoading">
              <td colspan="4" class="empty-row">No activity events yet</td>
            </tr>
            <tr v-for="event in studentFeed" :key="event.id">
              <td class="user-cell">{{ event.actor_username ? maskUsername(event.actor_username) : 'System' }}</td>
              <td>
                <span class="event-badge" :class="'event-badge--' + event.event_type">
                  {{ event.event_label }}
                </span>
              </td>
              <td class="target-cell">{{ event.target_label || '-' }}</td>
              <td class="time-cell">{{ formatTime(event.created_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="feedHasMore" class="feed-load-more">
        <button @click="loadMoreFeed" class="load-more-btn" :disabled="feedLoadingMore">
          {{ feedLoadingMore ? 'Loading...' : 'Load More' }}
        </button>
      </div>
    </div>

    <!-- Diagnostic Log (admin only) -->
    <div v-if="diagnosticFeed.length && showHealthCard" class="panel panel--diagnostic">
      <div class="panel__header">
        <h2 class="panel__title" @click="showDiagnosticLog = !showDiagnosticLog" style="cursor: pointer;">
          Diagnostic Log
          <span class="diagnostic-chevron" :class="{ 'diagnostic-chevron--open': showDiagnosticLog }">&#9662;</span>
        </h2>
        <span class="panel__subtitle feed-count">{{ diagnosticFeed.length }} events</span>
      </div>
      <div v-if="showDiagnosticLog" class="feed-table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th>User</th>
              <th>Event</th>
              <th>Target</th>
              <th>Time</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="event in diagnosticFeed" :key="event.id" class="activity-row--diagnostic">
              <td class="user-cell">{{ event.actor_username || 'System' }}</td>
              <td>
                <span class="event-badge event-badge--diagnostic">{{ event.event_label }}</span>
              </td>
              <td class="target-cell">{{ event.target_label || '-' }}</td>
              <td class="time-cell">{{ formatTime(event.created_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend
} from 'chart.js'
import axios from '../api/axios'
import { usePrivacy } from '../composables/usePrivacy'
import { usePoll } from '../composables/usePoll'
import { isAdmin } from '../utils/roles'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip, Legend)

const router = useRouter()
const { maskUsername } = usePrivacy()
const showHealthCard = isAdmin()

const stats = ref({
  flags_today: 0, flags_yesterday: null, flag_students_today: 0, flags_sparkline: [],
  active_count: 0, active_users: [],
  avg_completion_min: null, avg_completion_typical: null,
})

const flagsTrend = computed(() => {
  const today = stats.value.flags_today || 0
  const yesterday = stats.value.flags_yesterday
  if (yesterday == null || yesterday === 0) {
    return { text: '', cls: '' }
  }
  const diff = today - yesterday
  if (diff > 0) return { text: `+${diff} vs yesterday`, cls: 'trend--up' }
  if (diff < 0) return { text: `${diff} vs yesterday`, cls: 'trend--down' }
  return { text: 'same as yesterday', cls: 'trend--flat' }
})

const avgTimeColor = computed(() => {
  const today = stats.value.avg_completion_min
  const typical = stats.value.avg_completion_typical
  if (today == null || typical == null) return ''
  if (today <= typical * 0.85) return 'avg--fast'
  if (today >= typical * 1.15) return 'avg--slow'
  return ''
})

const initials = (username) => {
  if (!username) return '?'
  // Handle snake_case names like jordan_patel → JP
  const parts = username.split(/[_\s-]+/)
  if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
  return username.slice(0, 2).toUpperCase()
}

const sparklinePoints = (data) => {
  if (!data || !data.length) return ''
  const max = Math.max(...data, 1)
  return data.map((v, i) => `${i * 12 + 6},${30 - (v / max) * 26}`).join(' ')
}
const feed = ref([])
const feedLoading = ref(false)
const feedOffset = ref(0)
const feedHasMore = ref(true)
const feedLoadingMore = ref(false)
const feedPageSize = 50
const showDiagnosticLog = ref(false)

const studentFeed = computed(() => feed.value.filter(e => !isDiagnosticEvent(e)))
const diagnosticFeed = computed(() => feed.value.filter(e => isDiagnosticEvent(e)))
const pulseRaw = ref([])

// System health state
const dashboardHealthStatus = ref('')
const dashboardHealthLoaded = ref(false)

// Date range filter state
const activePreset = ref('24h')
const customStart = ref('')
const customEnd = ref('')
const pulseGranularity = ref('hour')

// Course / user filter state
const selectedCourse = ref(null)
const selectedUser = ref(null)
const filterCourses = ref([])
const filterStudents = ref([])

const exportFormat = ref('pdf')
const exportLoading = ref(false)

const filterRange = computed(() => {
  const now = new Date()
  let start

  switch (activePreset.value) {
    case '1h':
      start = new Date(now.getTime() - 60 * 60 * 1000)
      break
    case '6h':
      start = new Date(now.getTime() - 6 * 60 * 60 * 1000)
      break
    case '24h':
      start = new Date(now.getTime() - 24 * 60 * 60 * 1000)
      break
    case '7d':
      start = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
      break
    case 'custom': {
      const s = customStart.value ? new Date(customStart.value) : null
      const e = customEnd.value ? new Date(customEnd.value) : null
      return {
        start: s ? s.toISOString() : null,
        end: e ? e.toISOString() : null,
      }
    }
    default:
      start = new Date(now.getTime() - 24 * 60 * 60 * 1000)
  }

  return { start: start.toISOString(), end: now.toISOString() }
})

const filterSubtitle = computed(() => {
  let base
  switch (activePreset.value) {
    case '1h': base = 'Last 1 hour'; break
    case '6h': base = 'Last 6 hours'; break
    case '24h': base = 'Last 24 hours'; break
    case '7d': base = 'Last 7 days'; break
    case 'custom': {
      const s = customStart.value ? new Date(customStart.value).toLocaleDateString() : '...'
      const e = customEnd.value ? new Date(customEnd.value).toLocaleDateString() : 'now'
      base = `${s} - ${e}`
      break
    }
    default: base = 'Last 24 hours'
  }
  const parts = [base]
  if (selectedCourse.value) {
    const c = filterCourses.value.find(x => x.id === selectedCourse.value)
    if (c) parts.push(c.code)
  }
  if (selectedUser.value) {
    const s = filterStudents.value.find(x => x.id === selectedUser.value)
    if (s) parts.push(s.username)
  }
  return parts.join(' / ')
})

const pulseData = computed(() => {
  if (!pulseRaw.value.length) return { labels: [], datasets: [] }

  return {
    labels: pulseRaw.value.map(p => {
      const d = new Date(p.hour)
      if (pulseGranularity.value === 'day') {
        return d.toLocaleDateString([], { month: 'short', day: 'numeric' })
      }
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }),
    datasets: [
      {
        label: 'Exercise Sessions',
        data: pulseRaw.value.map(p => p.concurrent_labs),
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        fill: true,
        tension: 0.4,
        pointRadius: 0,
        pointHoverRadius: 4,
      },
      {
        label: 'Flags Submitted',
        data: pulseRaw.value.map(p => p.flags_submitted),
        borderColor: '#22c55e',
        backgroundColor: 'rgba(34, 197, 94, 0.1)',
        fill: true,
        tension: 0.4,
        pointRadius: 0,
        pointHoverRadius: 4,
      },
    ],
  }
})

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  // No animation on data refresh: the 15s auto-refresh replaces the dataset,
  // and animating every swap makes the whole chart flash (the dashboard flicker).
  animation: false,
  interaction: { mode: 'index', intersect: false },
  plugins: {
    legend: {
      position: 'top',
      labels: { color: '#94a3b8', usePointStyle: true, pointStyle: 'circle', padding: 20 },
    },
    tooltip: {
      backgroundColor: '#1e293b',
      titleColor: '#f1f5f9',
      bodyColor: '#cbd5e1',
      borderColor: '#334155',
      borderWidth: 1,
    },
  },
  scales: {
    x: {
      grid: { color: '#334155', drawBorder: false },
      ticks: { color: '#64748b', maxTicksLimit: 12 },
    },
    y: {
      grid: { color: '#334155', drawBorder: false },
      ticks: { color: '#64748b', precision: 0 },
      beginAtZero: true,
    },
  },
}

const dashboardHealthClass = computed(() =>
  dashboardHealthStatus.value === 'ok' ? 'healthy' : dashboardHealthStatus.value
)

const goToSystemHealth = () => {
  router.push({ path: '/admin', query: { tab: 'system' } })
}

const fetchDashboardHealth = async () => {
  try {
    const { data } = await axios.get('/admin/system/status')
    dashboardHealthStatus.value = data.overall || 'error'
  } catch {
    dashboardHealthStatus.value = 'error'
  } finally {
    dashboardHealthLoaded.value = true
  }
}

const tzOffset = -(new Date().getTimezoneOffset())  // minutes east of UTC (e.g. -300 for CDT)

const fetchStats = async () => {
  try {
    const res = await axios.get('/dashboard/instructor/stats', { params: { tz_offset: tzOffset } })
    stats.value = res.data
  } catch (e) {
    console.error('Failed to fetch stats:', e)
  }
}

const _scopeParams = () => {
  const p = {}
  if (selectedCourse.value) p.course_id = selectedCourse.value
  if (selectedUser.value) p.user_id = selectedUser.value
  return p
}

const fetchPulse = async () => {
  try {
    const params = { ..._scopeParams() }
    const range = filterRange.value
    if (range.start) params.start = range.start
    if (range.end) params.end = range.end
    const res = await axios.get('/dashboard/instructor/pulse', { params })
    pulseRaw.value = res.data.data || []
    pulseGranularity.value = res.data.granularity || 'hour'
  } catch (e) {
    console.error('Failed to fetch pulse:', e)
  }
}

// Cheap change-detection so a background refresh that returns identical data
// does not reassign feed.value (which would re-render the whole table = flicker).
// The feed is chronological-desc, so new activity changes the count or top id.
const _feedSignature = (events) => {
  if (!events || !events.length) return '0'
  return `${events.length}:${events[0].id}:${events[events.length - 1].id}`
}

const fetchFeed = async (mode = 'reset', { silent = false } = {}) => {
  // mode: 'reset' = fresh load (first page), 'append' = load next page, 'refresh' = reload all loaded pages
  // silent = background auto-refresh: no spinner, and skip the update when unchanged.
  if (mode === 'append') {
    feedLoadingMore.value = true
  } else if (!silent) {
    feedLoading.value = true
  }
  if (mode === 'reset') {
    feedOffset.value = 0
    feedHasMore.value = true
  }
  try {
    const range = filterRange.value
    const scope = _scopeParams()

    if (mode === 'refresh' && feedOffset.value > feedPageSize) {
      // Re-fetch everything up to current offset to preserve expanded state
      const params = { limit: feedOffset.value, offset: 0, ...scope }
      if (range.start) params.start = range.start
      if (range.end) params.end = range.end
      const res = await axios.get('/dashboard/instructor/feed', { params })
      const events = res.data.events || []
      if (_feedSignature(events) !== _feedSignature(feed.value)) {
        feed.value = events
      }
      feedHasMore.value = events.length >= feedOffset.value
    } else {
      const offset = mode === 'append' ? feedOffset.value : 0
      const params = { limit: feedPageSize, offset, ...scope }
      if (range.start) params.start = range.start
      if (range.end) params.end = range.end
      const res = await axios.get('/dashboard/instructor/feed', { params })
      const events = res.data.events || []
      if (mode === 'append') {
        feed.value = [...feed.value, ...events]
      } else if (_feedSignature(events) !== _feedSignature(feed.value)) {
        feed.value = events
      }
      feedHasMore.value = events.length >= feedPageSize
      feedOffset.value = (mode === 'append' ? feedOffset.value : 0) + events.length
    }
  } catch (e) {
    console.error('Failed to fetch feed:', e)
  } finally {
    feedLoading.value = false
    feedLoadingMore.value = false
  }
}

const loadMoreFeed = () => {
  fetchFeed('append')
}

const fetchFilterOptions = async (courseId) => {
  try {
    const params = {}
    if (courseId) params.course_id = courseId
    const res = await axios.get('/dashboard/instructor/filter-options', { params })
    filterCourses.value = res.data.courses || []
    filterStudents.value = res.data.students || []
  } catch (e) {
    console.error('Failed to fetch filter options:', e)
  }
}

const onCourseChange = () => {
  selectedUser.value = null
  fetchFilterOptions(selectedCourse.value)
  fetchPulse()
  fetchFeed()
}

const onUserChange = () => {
  fetchPulse()
  fetchFeed()
}

const selectPreset = (preset) => {
  activePreset.value = preset
  fetchPulse()
  fetchFeed()
}

watch([customStart, customEnd], () => {
  if (activePreset.value === 'custom' && customStart.value) {
    fetchPulse()
    fetchFeed()
  }
})

const isDiagnosticEvent = (event) => {
  if (event.actor_role === 'admin') return true
  if (event.detail) {
    try {
      const obj = typeof event.detail === 'string' ? JSON.parse(event.detail) : event.detail
      if (obj.source === 'diagnostic') return true
    } catch {}
  }
  return false
}

const rangeLabelText = () => {
  switch (activePreset.value) {
    case '1h': return 'Last 1 hour'
    case '6h': return 'Last 6 hours'
    case '24h': return 'Last 24 hours'
    case '7d': return 'Last 7 days'
    case 'custom': {
      const s = customStart.value ? new Date(customStart.value).toLocaleString() : '...'
      const e = customEnd.value ? new Date(customEnd.value).toLocaleString() : 'now'
      return `${s} to ${e}`
    }
    default: return 'Last 24 hours'
  }
}

const downloadReport = async () => {
  if (exportLoading.value) return
  exportLoading.value = true
  try {
    const range = filterRange.value
    const params = {
      format: exportFormat.value,
      range_label: rangeLabelText(),
      ..._scopeParams(),
    }
    if (range.start) params.start = range.start
    if (range.end) params.end = range.end

    const res = await axios.get('/dashboard/instructor/report', {
      params,
      responseType: 'blob',
    })

    const mime = exportFormat.value === 'pdf' ? 'application/pdf' : 'text/csv'
    const blob = new Blob([res.data], { type: mime })
    const url = window.URL.createObjectURL(blob)

    // Try to read filename from Content-Disposition
    let filename = `ops_report.${exportFormat.value}`
    const disp = res.headers['content-disposition'] || res.headers['Content-Disposition']
    if (disp) {
      const m = /filename="?([^"]+)"?/.exec(disp)
      if (m) filename = m[1]
    }

    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  } catch (e) {
    console.error('Failed to download report:', e)
    alert('Failed to generate report. Please try again.')
  } finally {
    exportLoading.value = false
  }
}

const formatTime = (isoStr) => {
  if (!isoStr) return '-'
  const d = new Date(isoStr)
  const now = new Date()
  const diffMs = now - d
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return 'just now'
  if (diffMin < 60) return `${diffMin}m ago`
  const diffHr = Math.floor(diffMin / 60)
  if (diffHr < 24) return `${diffHr}h ago`
  return d.toLocaleDateString()
}

// Refresh the dashboard every 15 seconds; paused while the tab is hidden,
// with an immediate refresh when it becomes visible again.
usePoll(() => {
  if (showHealthCard) fetchDashboardHealth()
  fetchStats()
  fetchPulse()
  fetchFeed('refresh', { silent: true })
}, 15000)

onMounted(() => {
  if (showHealthCard) fetchDashboardHealth()
  fetchFilterOptions()
  fetchStats()
  fetchPulse()
  fetchFeed()
})
</script>

<style scoped>
.instructor-dashboard {
  max-width: 1200px;
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

/* Health Bar (compact, admin only) */
.health-bar {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 0.5rem 1rem;
  margin-bottom: 1rem;
  cursor: pointer;
  transition: border-color 0.3s ease;
}

.health-bar:hover { border-color: var(--accent); }
.health-bar--healthy { border-color: rgba(22, 101, 52, 0.4); }
.health-bar--warning { border-color: #854d0e; }
.health-bar--error { border-color: #991b1b; }

.health-bar__label {
  font-size: 0.75rem;
  color: var(--text-secondary);
  font-weight: 500;
  margin-right: 0.5rem;
}

/* Stats Grid - 3 wide cards */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  margin-bottom: 1.5rem;
}

/* Rich Cards */
.rich-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 14px;
  padding: 1.25rem 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
  min-height: 140px;
}

.rich-card__header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.rich-card__icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.rich-card__icon--flags { color: #4ade80; }
.rich-card__icon--active { color: #60a5fa; }
.rich-card__icon--time { color: #a78bfa; }

.rich-card__label {
  font-size: 0.6875rem;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.rich-card__body {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex: 1;
}

.rich-card__value {
  font-size: 2.25rem;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1;
}

.rich-card__value.avg--fast { color: #4ade80; }
.rich-card__value.avg--slow { color: #fbbf24; }

.rich-card__sparkline {
  flex: 1;
  height: 32px;
  opacity: 0.7;
}

.rich-card__sparkline svg {
  width: 100%;
  height: 100%;
}

.rich-card__footer {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-height: 1.25rem;
}

.rich-card__trend {
  font-size: 0.75rem;
  font-weight: 600;
}

.trend--up { color: #4ade80; }
.trend--down { color: #f87171; }
.trend--flat { color: var(--text-muted); }

.rich-card__detail {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.rich-card__detail--muted {
  color: var(--text-muted);
  font-style: italic;
}

/* Active user avatars */
.active-avatars {
  display: flex;
  gap: 0.375rem;
  flex-wrap: wrap;
}

.active-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  font-size: 0.625rem;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.active-avatar--more {
  background: rgba(100, 116, 139, 0.15);
  color: #94a3b8;
}

/* Health dots */
.health-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
  flex-shrink: 0;
}

.health-dot--green {
  background: #4ade80;
  box-shadow: 0 0 4px rgba(74, 222, 128, 0.4);
}

.health-dot--amber {
  background: #fbbf24;
  box-shadow: 0 0 4px rgba(251, 191, 36, 0.4);
  animation: pulse-amber 2s ease-in-out infinite;
}

.health-dot--red {
  background: #f87171;
  box-shadow: 0 0 6px rgba(248, 113, 113, 0.5);
  animation: pulse-red 1.5s ease-in-out infinite;
}

@keyframes pulse-amber {
  0%, 100% { box-shadow: 0 0 4px rgba(251, 191, 36, 0.4); }
  50% { box-shadow: 0 0 8px rgba(251, 191, 36, 0.7); }
}

@keyframes pulse-red {
  0%, 100% { box-shadow: 0 0 6px rgba(248, 113, 113, 0.5); }
  50% { box-shadow: 0 0 12px rgba(248, 113, 113, 0.8); }
}

.stat-card__content {
  display: flex;
  flex-direction: column;
}

.stat-card__value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
}

.stat-card__label {
  font-size: 0.75rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Panels */
.panel {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}

.panel--disabled {
  opacity: 0.5;
  position: relative;
}

.panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.panel__title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.panel__subtitle {
  font-size: 0.8125rem;
  color: var(--text-muted);
}

.panel__description {
  color: var(--text-muted);
  font-size: 0.875rem;
  margin: 0.5rem 0 0 0;
}

.badge--coming-soon {
  display: inline-block;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  font-size: 0.6875rem;
  font-weight: 600;
  padding: 0.25rem 0.625rem;
  border-radius: 9999px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-top: 0.5rem;
}

.refresh-btn {
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  padding: 0.375rem;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.refresh-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.refresh-btn svg {
  width: 16px;
  height: 16px;
  display: block;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  100% { transform: rotate(360deg); }
}

/* Chart */
.chart-container {
  height: 280px;
  position: relative;
}

.chart-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--nav-label);
  font-size: 0.9375rem;
}

/* Feed Table */
.feed-table-wrapper {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th {
  padding: 0.75rem 1rem;
  text-align: left;
  font-size: 0.6875rem;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid var(--border-color);
}

.data-table td {
  padding: 0.625rem 1rem;
  font-size: 0.8125rem;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--hover-bg);
}

.empty-row {
  text-align: center;
  color: var(--nav-label);
  padding: 2rem 1rem !important;
}

.feed-count {
  margin-left: auto;
  margin-right: 0.5rem;
}

.feed-load-more {
  display: flex;
  justify-content: center;
  padding: 0.75rem 0 0.25rem;
}

.load-more-btn {
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  padding: 0.4rem 1.5rem;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.load-more-btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}

.load-more-btn:disabled {
  opacity: 0.5;
  cursor: wait;
}

.user-cell {
  font-weight: 500;
  color: var(--text-primary);
}

.target-cell {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.time-cell {
  color: var(--text-muted);
  white-space: nowrap;
}

/* Event Badges */
.event-badge {
  display: inline-block;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.event-badge--lab_started { background: rgba(59, 130, 246, 0.15); color: #60a5fa; }
.event-badge--lab_stopped { background: rgba(100, 116, 139, 0.2); color: #94a3b8; }
.event-badge--lab_completed { background: rgba(34, 197, 94, 0.15); color: #4ade80; }
.event-badge--flag_correct { background: rgba(34, 197, 94, 0.15); color: #4ade80; }
.event-badge--flag_incorrect { background: rgba(239, 68, 68, 0.15); color: #f87171; }
.event-badge--hint_used { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }
.event-badge--user_registered { background: rgba(168, 85, 247, 0.15); color: #c084fc; }
.event-badge--user_approved { background: rgba(168, 85, 247, 0.15); color: #c084fc; }
.event-badge--vpn_downloaded { background: rgba(6, 182, 212, 0.15); color: #22d3ee; }
.event-badge--course_enrolled { background: rgba(236, 72, 153, 0.15); color: #f472b6; }
.event-badge--achievement_awarded { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }
.event-badge--diagnostic { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }

.diagnostic-tag {
  display: inline-block;
  margin-left: 0.375rem;
  padding: 0.125rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.625rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  background: rgba(245, 158, 11, 0.1);
  color: #fbbf24;
  border: 1px solid rgba(245, 158, 11, 0.25);
}

.activity-row--diagnostic { background: rgba(245, 158, 11, 0.03); }
.activity-row--diagnostic td { opacity: 0.75; }
.activity-row--diagnostic td:nth-child(2) { opacity: 1; }

.panel--diagnostic { border-color: rgba(245, 158, 11, 0.2); }
.panel--diagnostic .panel__title { font-size: 0.95rem; }
.diagnostic-chevron {
  display: inline-block;
  font-size: 0.7rem;
  margin-left: 0.35rem;
  transition: transform 0.2s ease;
}
.diagnostic-chevron--open { transform: rotate(180deg); }

/* Filter Bar */
.filter-bar {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}

.filter-bar__presets {
  display: flex;
  gap: 0.375rem;
}

.filter-pill {
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  padding: 0.3125rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.filter-pill:hover {
  border-color: var(--nav-label);
  color: var(--text-secondary);
}

.filter-pill--active {
  background: var(--accent);
  border-color: var(--accent);
  color: #ffffff;
}

.filter-pill--active:hover {
  background: #2563eb;
  border-color: #2563eb;
}

.filter-bar__dropdowns {
  display: flex;
  gap: 0.5rem;
  margin-left: 0.25rem;
}

.filter-select {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  padding: 0.3125rem 0.625rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-family: inherit;
  outline: none;
  cursor: pointer;
  transition: border-color 0.15s ease;
  max-width: 160px;
  -webkit-appearance: none;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%23888'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 0.5rem center;
  padding-right: 1.5rem;
}

.filter-select:hover {
  border-color: var(--nav-label);
}

.filter-select:focus {
  border-color: var(--accent);
}

.filter-select option {
  background: var(--bg-primary);
  color: var(--text-primary);
}

.filter-bar__custom {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.filter-datetime {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  padding: 0.3125rem 0.625rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-family: inherit;
  outline: none;
  transition: border-color 0.15s ease;
}

.filter-datetime:focus {
  border-color: var(--accent);
}

.filter-datetime::-webkit-calendar-picker-indicator {
  filter: invert(0.85) brightness(1.2);
  cursor: pointer;
}

.filter-separator {
  color: var(--text-muted);
  font-size: 0.75rem;
}

.filter-bar__export {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-left: auto;
}

.filter-select--compact {
  max-width: 90px;
}

.export-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  background: var(--accent);
  border: 1px solid var(--accent);
  color: #ffffff;
  padding: 0.3125rem 0.75rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease;
  white-space: nowrap;
}

.export-btn:hover:not(:disabled) {
  background: #2563eb;
  border-color: #2563eb;
}

.export-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Responsive */
@media (max-width: 900px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .rich-card { min-height: auto; }
}

@media (max-width: 768px) {
  .instructor-dashboard {
    padding: 1rem;
  }
}
</style>

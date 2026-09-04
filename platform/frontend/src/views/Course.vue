<template>
  <div class="course-page">
    <div class="course-container" v-if="course">
      <!-- Course Header -->
      <div class="course-header">
        <router-link :to="isInstructor ? '/instructor?tab=courses' : '/courses'" class="back-link">
          &larr; {{ isInstructor ? 'My Courses' : 'All Courses' }}
        </router-link>
        <div class="header-row">
          <div>
            <h1>{{ course.name }}</h1>
            <div class="header-meta">
              <span class="course-code">{{ course.code }}</span>
              <span class="meta-sep">|</span>
              <span>{{ course.semester }}</span>
              <span class="meta-sep">|</span>
              <span>{{ formatDate(course.start_date) }} - {{ formatDate(course.end_date) }}</span>
              <span :class="['course-status', statusClass]">{{ statusText }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Tabs -->
      <div class="tabs">
        <button
          @click="setTab('assignments')"
          :class="['tab', { active: activeTab === 'assignments' }]"
        >
          Exercises ({{ courseAssignments.length }})
        </button>
        <button
          @click="setTab('scoreboard')"
          :class="['tab', { active: activeTab === 'scoreboard' }]"
        >
          Scoreboard
        </button>
        <button
          @click="setTab('achievements')"
          :class="['tab', { active: activeTab === 'achievements' }]"
        >
          Achievements
        </button>
      </div>

      <!-- Labs Tab -->
      <div v-if="activeTab === 'labs'" class="tab-content">
        <div v-if="labs.length === 0" class="empty-tab">No exercises assigned to this course yet.</div>
        <div v-else class="labs-list">
          <div v-for="lab in labs" :key="lab.id"
            :class="['lab-row', lab.locked ? 'lab-row--locked' : 'lab-row--clickable']"
            @click="lab.locked ? null : openLab(lab)">
            <div class="lab-status-icon">
              <svg v-if="lab.locked" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16" style="opacity:0.5"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
              <span v-else-if="lab.is_completed" class="status-bar status-bar--completed"></span>
              <span v-else class="status-circle"></span>
            </div>
            <div class="lab-info">
              <div :class="['lab-name', { 'lab-name--locked': lab.locked }]">{{ lab.name }}</div>
              <div class="lab-meta">
                <span v-if="lab.slug && lab.slug.match(/^pentest-D\d/)" class="drill-badge">Drill</span>
                <span :class="['difficulty-badge', `difficulty-${lab.difficulty}`]">
                  {{ lab.difficulty }}
                </span>
                <span class="lab-duration">{{ lab.duration_minutes }} min</span>
                <span v-if="lab.locked" class="locked-badge">Locked</span>
                <span v-else-if="lab.is_course_exclusive" class="exclusive-badge">Course Only</span>
              </div>
            </div>
            <svg v-if="!lab.locked" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="lab-row-arrow">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
          </div>
        </div>
      </div>

      <!-- Assignments Tab -->
      <div v-if="activeTab === 'assignments'" class="tab-content">
        <div v-if="courseAssignments.length === 0" class="empty-tab">No assignments for this course yet.</div>
        <div v-else class="assignment-grid">
          <template v-for="asn in courseAssignments" :key="asn.id">
            <div
              class="asn-card"
              :class="{ 'asn-card--active': expandedAsn === asn.id, 'asn-card--locked': asn.locked || asn.not_yet_open }"
              @click="toggleAsn(asn)"
            >
              <div class="asn-card__header">
                <span class="asn-card__name">{{ asn.name }}</span>
                <span v-if="asn.not_yet_open" class="asn-due asn-due--locked">{{ asnStartText(asn.start_date) }}</span>
                <span v-else-if="asn.locked" class="asn-due asn-due--locked">Locked</span>
                <span v-else :class="['asn-due', asnDueClass(asn.due_date)]">{{ asnDueText(asn.due_date) }}</span>
              </div>
              <p v-if="asn.description" class="asn-card__desc">{{ asn.description }}</p>
              <div class="asn-card__stats">
                <span class="asn-stat">{{ asn.lab_count }} exercises</span>
              </div>
              <template v-if="asn.locked || asn.not_yet_open">
                <div class="asn-card__locked-msg">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                  <span v-if="asn.not_yet_open">Available {{ asnStartText(asn.start_date).toLowerCase() }}</span>
                  <span v-else>This assignment is locked by your instructor</span>
                </div>
              </template>
              <template v-else>
                <div class="asn-card__stats">
                  <span class="asn-stat">{{ asn.completed_count }}/{{ asn.lab_count }} completed</span>
                  <span class="asn-stat">{{ asn.lab_count }} exercises</span>
                </div>
                <div class="asn-card__progress">
                  <div class="asn-progress-bar">
                    <div class="asn-progress-fill" :style="{ width: asn.lab_count ? (asn.completed_count / asn.lab_count * 100) + '%' : '0%' }"></div>
                  </div>
                </div>
              </template>
            </div>

            <!-- Inline expanded detail (spans full grid row, directly below this card) -->
            <div
              v-if="expandedAsn === asn.id"
              :id="'asn-detail-' + asn.id"
              class="asn-detail asn-detail--inline"
            >
              <h3 class="asn-detail__title">{{ asn.name }}</h3>
              <div class="labs-list">
                <div v-for="lab in asn.labs" :key="lab.id" class="lab-row lab-row--clickable" @click.stop="openLab(lab)">
                  <div class="lab-status-icon">
                    <span v-if="lab.is_completed" class="status-bar status-bar--completed"></span>
                    <span v-else class="status-circle"></span>
                  </div>
                  <div class="lab-info">
                    <div class="lab-name">{{ lab.name }}</div>
                    <div class="lab-meta">
                      <span v-if="lab.slug && lab.slug.match(/^pentest-D\d/)" class="drill-badge">Drill</span>
                      <span :class="['difficulty-badge', `difficulty-${lab.difficulty}`]">{{ lab.difficulty }}</span>
                      <span class="lab-duration">{{ lab.duration_minutes }} min</span>
                    </div>
                  </div>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="lab-row-arrow">
                    <polyline points="9 18 15 12 9 6"/>
                  </svg>
                </div>
              </div>
            </div>
          </template>
        </div>
      </div>

      <!-- Scoring Guide (visible on Scoreboard or Achievements tab) -->
      <div v-if="activeTab === 'scoreboard' || activeTab === 'achievements'" class="scoring-guide-toggle">
        <button @click="showScoringGuide = !showScoringGuide" class="guide-toggle-btn">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
            <circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          {{ showScoringGuide ? 'Hide' : 'Show' }} Scoring Guide
        </button>
        <transition name="slide">
          <div v-if="showScoringGuide" class="scoring-guide">
            <div class="guide-section">
              <h4>Scoring Breakdown</h4>
              <div class="guide-grid">
                <div class="guide-item"><span class="guide-pts">100</span> Base score for completing an exercise</div>
                <div class="guide-item"><span class="guide-pts">+25</span> No hints used</div>
                <div class="guide-item"><span class="guide-pts">+25</span> Completed on first attempt</div>
                <div class="guide-item"><span class="guide-pts">+50</span> First student to complete (First Blood)</div>
                <div class="guide-item"><span class="guide-pts">+10</span> Completed under 75% of estimated time</div>
                <div class="guide-item"><span class="guide-pts">+30</span> Completed under 50% of estimated time</div>
                <div class="guide-item"><span class="guide-pts">+50</span> Completed under 25% of estimated time</div>
              </div>
              <div class="guide-note">Max possible per exercise: 250 points</div>
            </div>
            <div class="guide-section">
              <h4>Achievements</h4>
              <div class="guide-grid guide-grid--achievements">
                <div class="guide-ach"><span class="guide-ach-icon">&#x1F3AF;</span><strong>First Blood</strong><br>First to complete an exercise in this course</div>
                <div class="guide-ach"><span class="guide-ach-icon">&#x1F9E0;</span><strong>Self-Reliant</strong><br>Completed an exercise without using any hints</div>
                <div class="guide-ach"><span class="guide-ach-icon">&#x2B50;</span><strong>Perfectionist</strong><br>Completed an exercise on the first flag attempt</div>
                <div class="guide-ach"><span class="guide-ach-icon">&#x26A1;</span><strong>Speed Demon</strong><br>Completed in under half the estimated time</div>
                <div class="guide-ach"><span class="guide-ach-icon">&#x1F3C6;</span><strong>Clean Sweep</strong><br>Completed all assigned exercises in the course</div>
                <div class="guide-ach"><span class="guide-ach-icon">&#x1F525;</span><strong>On a Roll</strong><br>3+ exercises in a row with no hints &amp; first attempt</div>
              </div>
            </div>
          </div>
        </transition>
      </div>

      <!-- Scoreboard Tab (compact expandable rows) -->
      <div v-if="activeTab === 'scoreboard'" class="tab-content">
        <div v-if="loadingScoreboard" class="empty-tab">Loading scoreboard...</div>
        <div v-else-if="scoreboard.length === 0" class="empty-tab">
          No completions yet. Be the first!
        </div>
        <div v-else class="scoreboard-compact">
          <table class="scoreboard-table">
            <thead>
              <tr>
                <th class="col-rank">#</th>
                <th class="col-student">Student</th>
                <th class="col-progress">Progress</th>
                <th class="col-total">Score</th>
                <th class="col-badges">Badges</th>
              </tr>
            </thead>
            <tbody>
              <template v-for="entry in scoreboard" :key="entry.user_id">
                <tr
                  :class="{ 'my-row': entry.user_id === currentUserId }"
                  class="sb-main-row"
                  @click="toggleScoreboardExpand(entry.user_id)"
                >
                  <td class="col-rank">
                    <span v-if="entry.rank === 1" class="rank-badge gold">1</span>
                    <span v-else-if="entry.rank === 2" class="rank-badge silver">2</span>
                    <span v-else-if="entry.rank === 3" class="rank-badge bronze">3</span>
                    <span v-else class="rank-num">{{ entry.rank }}</span>
                  </td>
                  <td class="col-student">
                    <div class="student-name">{{ maskUsername(entry.username) }}</div>
                    <div v-if="entry.student_id" class="student-id">{{ entry.student_id }}</div>
                  </td>
                  <td class="col-progress">
                    <div class="progress-bar">
                      <div
                        class="progress-fill"
                        :style="{ width: (scoreboardLabs.length ? (entry.labs_completed / scoreboardLabs.length * 100) : 0) + '%' }"
                      ></div>
                    </div>
                    <span class="progress-text">{{ entry.labs_completed }} of {{ scoreboardLabs.length }}</span>
                  </td>
                  <td class="col-total">
                    <strong>{{ entry.total_score }}</strong>
                  </td>
                  <td class="col-badges">
                    <span v-if="entry.achievements.length > 0" class="badge-count-text">
                      {{ uniqueAchievements(entry.achievements).length }}
                    </span>
                    <span v-else class="badge-none">—</span>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"
                      class="sb-chevron"
                      :class="{ 'chevron-open': expandedScoreboardRow === entry.user_id }">
                      <polyline points="6 9 12 15 18 9"/>
                    </svg>
                  </td>
                </tr>
                <!-- Expanded per-lab breakdown -->
                <tr v-if="expandedScoreboardRow === entry.user_id" class="sb-detail-row">
                  <td colspan="5">
                    <div class="sb-detail-panel">
                      <div
                        v-for="lab in scoreboardLabs"
                        :key="lab.id"
                        class="sb-lab-item"
                      >
                        <span v-if="entry.lab_scores[String(lab.id)]?.completed" class="sb-lab-status sb-lab-done">✓</span>
                        <span v-else class="sb-lab-status sb-lab-pending">○</span>
                        <span class="sb-lab-name">{{ lab.name }}</span>
                        <span v-if="entry.lab_scores[String(lab.id)]?.completed" class="sb-lab-score">
                          {{ entry.lab_scores[String(lab.id)].score }}
                        </span>
                        <span v-else class="sb-lab-score-empty">—</span>
                        <div
                          v-if="entry.lab_scores[String(lab.id)]?.achievements?.length"
                          class="sb-lab-ach-icons"
                        >
                          <span
                            v-for="a in entry.lab_scores[String(lab.id)].achievements"
                            :key="a"
                            :title="achievementLabel(a)"
                            class="lab-ach-icon"
                          >{{ achievementIcon(a) }}</span>
                        </div>
                      </div>
                    </div>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Achievements Tab -->
      <div v-if="activeTab === 'achievements'" class="tab-content">
        <div v-if="loadingAchievements" class="empty-tab">Loading achievements...</div>
        <div v-else-if="achievements.length === 0" class="empty-tab">
          No achievements earned yet in this course.
        </div>
        <div v-else class="achievements-list">
          <div v-for="ach in achievements" :key="ach.id" class="achievement-row">
            <span class="ach-icon">{{ achievementIcon(ach.achievement_type) }}</span>
            <div class="ach-info">
              <span class="ach-label">{{ ach.label }}</span>
              <span class="ach-detail">
                {{ maskUsername(ach.username) }}
                <span v-if="ach.lab_name"> &mdash; {{ ach.lab_name }}</span>
              </span>
            </div>
            <span class="ach-date">{{ formatDate(ach.awarded_at) }}</span>
          </div>
        </div>
      </div>

    </div>

    <!-- Loading -->
    <div v-else-if="loading" class="course-page">
      <div class="course-container loading-text">Loading course...</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from '../api/axios'
import { usePrivacy } from '../composables/usePrivacy'

const route = useRoute()
const { maskUsername, maskEmail } = usePrivacy()
const router = useRouter()
const courseId = computed(() => route.params.id)

const course = ref(null)
const labs = ref([])
const isInstructor = ref(false)
const loading = ref(true)
const showScoringGuide = ref(false)
const expandedScoreboardRow = ref(null)

const tabFromRoute = () => (route.query.tab && ['assignments', 'scoreboard', 'achievements', 'manage-labs', 'students', 'settings'].includes(route.query.tab)) ? route.query.tab : 'assignments'
const activeTab = ref(tabFromRoute())

// Assignments tab
const courseAssignments = ref([])
const expandedAsn = ref(null)

function toggleAsn(asn) {
  if (asn.locked || asn.not_yet_open) return
  const wasOpen = expandedAsn.value === asn.id
  expandedAsn.value = wasOpen ? null : asn.id
  if (!wasOpen) {
    nextTick(() => {
      const el = document.getElementById('asn-detail-' + asn.id)
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    })
  }
}

// Manage Labs tab
const availableLabs = ref([])
const loadingAvailableLabs = ref(false)
const selectedLabIds = ref([])
const expandedAssignCategories = ref({})
const expandedAssignedCategories = ref({})
const addLabsSearch = ref('')
const removingLabId = ref(null)
const savingOrder = ref(false)
const labOrderDirty = ref(false)
const renamingLabId = ref(null)
const renameLabValue = ref('')

// Students tab
const courseStudents = ref([])
const enrollableUsers = ref([])
const loadingStudents = ref(false)
const enrolling = ref(false)
const enrollSearch = ref('')
const selectedEnrollIds = ref(new Set())

const filteredEnrollableUsers = computed(() => {
  if (!enrollSearch.value) return enrollableUsers.value
  const q = enrollSearch.value.toLowerCase()
  return enrollableUsers.value.filter(u =>
    u.username.toLowerCase().includes(q) ||
    (u.email && u.email.toLowerCase().includes(q)) ||
    (u.student_id && u.student_id.toLowerCase().includes(q))
  )
})
const studentLabDetails = ref({})
const resettingCourseLab = ref(null)
const downloadingReportUserId = ref(null)

// Settings tab
const settingsForm = ref({ name: '', code: '', semester: '', description: '', start_date: '', end_date: '' })
const savingSettings = ref(false)
const regeneratingInvite = ref(false)

// Scoreboard
const scoreboard = ref([])
const scoreboardLabs = ref([])
const loadingScoreboard = ref(false)

// Achievements
const achievements = ref([])
const loadingAchievements = ref(false)

// Report
const downloadingReport = ref(false)

const currentUserId = computed(() => {
  try {
    return JSON.parse(localStorage.getItem('user') || '{}').id
  } catch {
    return null
  }
})

const isAdmin = computed(() => {
  try {
    return JSON.parse(localStorage.getItem('user') || '{}').role === 'admin'
  } catch {
    return false
  }
})

const statusClass = computed(() => {
  if (!course.value) return ''
  const now = new Date()
  const end = new Date(course.value.end_date)
  const start = new Date(course.value.start_date)
  if (now > end) return 'status-ended'
  if (now < start) return 'status-upcoming'
  return 'status-active'
})

const statusText = computed(() => {
  if (!course.value) return ''
  const now = new Date()
  const end = new Date(course.value.end_date)
  const start = new Date(course.value.start_date)
  if (now > end) return 'Ended'
  if (now < start) return 'Upcoming'
  return 'Active'
})

function formatDate(dt) {
  if (!dt) return ''
  const d = new Date(dt)
  return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
}

function truncate(str, len) {
  if (!str) return ''
  return str.length > len ? str.slice(0, len - 2) + '..' : str
}

const ACHIEVEMENT_MAP = {
  first_blood: { label: 'First Blood', icon: '\u{1F3AF}' },
  no_hints: { label: 'Self-Reliant', icon: '\u{1F9E0}' },
  perfectionist: { label: 'Perfectionist', icon: '\u{2B50}' },
  speed_demon: { label: 'Speed Demon', icon: '\u{26A1}' },
  clean_sweep: { label: 'Clean Sweep', icon: '\u{1F3C6}' },
  streak: { label: 'On a Roll', icon: '\u{1F525}' },
}

function achievementLabel(type) {
  return ACHIEVEMENT_MAP[type]?.label || type
}

function achievementIcon(type) {
  return ACHIEVEMENT_MAP[type]?.icon || '\u{1F3C5}'
}

function uniqueAchievements(list) {
  return [...new Set(list)]
}

function setTab(tab) {
  activeTab.value = tab
  router.replace({ query: { ...route.query, tab } })
}

const assignedLabIds = computed(() => new Set(labs.value.map(l => l.id)))

const assignedLabsByCategory = computed(() => {
  const grouped = {}
  labs.value.forEach((lab, index) => {
    const track = lab.track_name || 'Uncategorized'
    const level = lab.level_name || 'General'
    const key = `${track} \u203A ${level}`
    if (!grouped[key]) grouped[key] = []
    grouped[key].push({ ...lab, _index: index })
  })
  return grouped
})

const assignedCategoryKeys = computed(() => Object.keys(assignedLabsByCategory.value).sort())

const allAssignedExpanded = computed(() => {
  const keys = assignedCategoryKeys.value
  return keys.length > 0 && keys.every(k => expandedAssignedCategories.value[k])
})

function toggleAssignedCategory(key) {
  expandedAssignedCategories.value = {
    ...expandedAssignedCategories.value,
    [key]: !expandedAssignedCategories.value[key],
  }
}

function toggleAllAssignedCategories() {
  const keys = assignedCategoryKeys.value
  const next = !allAssignedExpanded.value
  const state = {}
  keys.forEach(k => { state[k] = next })
  expandedAssignedCategories.value = state
}

const assignLabsByTrackLevel = computed(() => {
  const assigned = assignedLabIds.value
  const q = addLabsSearch.value.trim().toLowerCase()
  const grouped = {}
  for (const lab of availableLabs.value) {
    if (assigned.has(lab.id)) continue
    if (q && !(lab.name || '').toLowerCase().includes(q) && !(lab.description || '').toLowerCase().includes(q)) continue
    const trackName = lab.track_name || 'Uncategorized'
    const levelName = lab.level_name || 'Uncategorized'
    const levelKey = `${trackName}::${levelName}`
    if (!grouped[levelKey]) grouped[levelKey] = { track_name: trackName, level_name: levelName, labs: [] }
    grouped[levelKey].labs.push(lab)
  }
  return grouped
})

const assignLevelKeys = computed(() => Object.keys(assignLabsByTrackLevel.value).sort())

const allAssignExpanded = computed(() => {
  const keys = assignLevelKeys.value
  if (!keys.length) return false
  return keys.every(k => expandedAssignCategories.value[k])
})

function toggleAssignCategory(levelKey) {
  expandedAssignCategories.value = {
    ...expandedAssignCategories.value,
    [levelKey]: !expandedAssignCategories.value[levelKey],
  }
}

function toggleAllAssignCategories() {
  const keys = assignLevelKeys.value
  const next = !keys.every(k => expandedAssignCategories.value[k])
  const nextState = {}
  keys.forEach(k => { nextState[k] = next })
  expandedAssignCategories.value = { ...expandedAssignCategories.value, ...nextState }
}

function selectAllInGroup(levelKey) {
  const group = assignLabsByTrackLevel.value[levelKey]
  if (!group) return
  const ids = group.labs.map(l => l.id)
  const current = new Set(selectedLabIds.value)
  ids.forEach(id => current.add(id))
  selectedLabIds.value = [...current]
}

async function fetchAvailableLabs() {
  loadingAvailableLabs.value = true
  try {
    const res = await axios.get('/instructor/labs')
    availableLabs.value = res.data.labs || []
    const keys = assignLevelKeys.value
    const expanded = {}
    keys.forEach(k => { expanded[k] = true })
    expandedAssignCategories.value = { ...expandedAssignCategories.value, ...expanded }
  } catch (e) {
    console.error('Failed to fetch available labs', e)
  } finally {
    loadingAvailableLabs.value = false
  }
}

async function assignSelectedLabs() {
  if (selectedLabIds.value.length === 0) return
  try {
    await axios.post(`/courses/${courseId.value}/labs`, { lab_ids: selectedLabIds.value })
    selectedLabIds.value = []
    await fetchCourse()
    await fetchAvailableLabs()
  } catch (e) {
    console.error('Failed to assign labs', e.response?.data?.detail || e.message)
  }
}

async function removeLabFromCourse(lab) {
  removingLabId.value = lab.id
  try {
    await axios.delete(`/courses/${courseId.value}/labs/${lab.id}`)
    await fetchCourse()
    await fetchAvailableLabs()
  } catch (e) {
    console.error('Failed to remove lab', e)
  } finally {
    removingLabId.value = null
  }
}

function startRenameLab(lab) {
  renamingLabId.value = lab.id
  renameLabValue.value = lab.name
}

function cancelRenameLab() {
  renamingLabId.value = null
  renameLabValue.value = ''
}

async function saveRenameLab(lab) {
  const newName = renameLabValue.value.trim()
  try {
    await axios.put(`/courses/${courseId.value}/labs/${lab.id}`, {
      display_name: newName
    })
    renamingLabId.value = null
    renameLabValue.value = ''
    await fetchCourse()
    await fetchAssignments()
  } catch (e) {
    console.error('Failed to rename exercise', e)
  }
}

function moveLab(index, delta) {
  const arr = [...labs.value]
  const ni = index + delta
  if (ni < 0 || ni >= arr.length) return
  ;[arr[index], arr[ni]] = [arr[ni], arr[index]]
  labs.value = arr
  labOrderDirty.value = true
}

async function saveLabOrder() {
  savingOrder.value = true
  try {
    const lab_order = labs.value.map((lab, i) => ({ lab_id: lab.id, sort_order: i + 1 }))
    await axios.put(`/courses/${courseId.value}/labs/reorder`, { lab_order })
    labOrderDirty.value = false
  } catch (e) {
    console.error('Failed to save order', e)
  } finally {
    savingOrder.value = false
  }
}

function formatDateShort(dt) {
  if (!dt) return '—'
  const d = new Date(dt.endsWith('Z') || dt.includes('+') ? dt : dt + 'Z')
  return d.toLocaleDateString('en-US', { timeZone: 'America/Chicago', month: 'short', day: 'numeric', year: 'numeric' })
}

function copyInviteCode() {
  if (course.value?.invite_code) navigator.clipboard.writeText(course.value.invite_code)
}

async function fetchCourseStudents() {
  loadingStudents.value = true
  try {
    const res = await axios.get(`/courses/${courseId.value}/students`)
    courseStudents.value = res.data.students || []
  } catch (e) {
    console.error('Failed to fetch students', e)
  } finally {
    loadingStudents.value = false
  }
}

async function fetchEnrollableUsers() {
  try {
    const res = await axios.get(`/instructor/courses/${courseId.value}/enrollable-users`)
    enrollableUsers.value = res.data || []
  } catch (e) {
    console.error('Failed to fetch enrollable users', e)
    enrollableUsers.value = []
  }
}

function toggleEnrollUser(id) {
  const next = new Set(selectedEnrollIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selectedEnrollIds.value = next
}

function selectAllFiltered() {
  const next = new Set(selectedEnrollIds.value)
  for (const u of filteredEnrollableUsers.value) next.add(u.id)
  selectedEnrollIds.value = next
}

function clearSelection() {
  selectedEnrollIds.value = new Set()
}

async function enrollSelectedStudents() {
  if (selectedEnrollIds.value.size === 0) return
  enrolling.value = true
  try {
    const ids = Array.from(selectedEnrollIds.value)
    await axios.post(`/courses/${courseId.value}/enroll-bulk`, { user_ids: ids })
    selectedEnrollIds.value = new Set()
    enrollSearch.value = ''
    await fetchCourseStudents()
    await fetchEnrollableUsers()
    await fetchCourse()
  } catch (e) {
    console.error('Failed to enroll', e.response?.data?.detail || e)
  } finally {
    enrolling.value = false
  }
}

async function removeStudent(student) {
  if (!confirm(`Remove ${student.username} from this course?`)) return
  try {
    await axios.delete(`/courses/${courseId.value}/enroll/${student.id}`)
    await fetchCourseStudents()
    await fetchEnrollableUsers()
    await fetchCourse()
    const next = { ...studentLabDetails.value }
    delete next[student.id]
    studentLabDetails.value = next
  } catch (e) {
    console.error('Failed to remove student', e)
  }
}

async function toggleStudentLabs(student) {
  if (studentLabDetails.value[student.id]) {
    const next = { ...studentLabDetails.value }
    delete next[student.id]
    studentLabDetails.value = next
    return
  }
  studentLabDetails.value = { ...studentLabDetails.value, [student.id]: 'loading' }
  try {
    const res = await axios.get(`/courses/${courseId.value}/scoreboard`)
    const entry = res.data.scoreboard.find(e => e.user_id === student.id)
    const labList = res.data.labs || []
    const labs = labList.map(lab => {
      const scores = entry?.lab_scores?.[String(lab.id)] || {}
      return {
        lab_id: lab.id,
        lab_name: lab.name,
        completed: scores.completed || false,
        score: scores.score || 0,
        attempts: scores.attempts ?? 0,
        hints_used: scores.hints_used ?? 0,
      }
    })
    studentLabDetails.value = { ...studentLabDetails.value, [student.id]: labs }
  } catch (e) {
    console.error('Failed to load lab details', e)
    const next = { ...studentLabDetails.value }
    delete next[student.id]
    studentLabDetails.value = next
  }
}

async function resetStudentLab(student, lab) {
  if (!confirm(`Reset "${lab.lab_name}" for ${student.username}? They will need to resubmit.`)) return
  resettingCourseLab.value = `${student.id}-${lab.lab_id}`
  try {
    await axios.post(`/courses/${courseId.value}/labs/${lab.lab_id}/reset/${student.id}`)
    await toggleStudentLabs(student)
  } catch (e) {
    console.error('Failed to reset lab', e)
  } finally {
    resettingCourseLab.value = null
  }
}

async function downloadStudentReport(student) {
  downloadingReportUserId.value = student.id
  try {
    const res = await axios.get(`/courses/${courseId.value}/report/${student.id}`, { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `report_${course.value?.code || 'course'}_${student.username}.pdf`
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (e) {
    console.error('Failed to download report', e)
  } finally {
    downloadingReportUserId.value = null
  }
}

function syncSettingsForm() {
  const c = course.value
  if (!c) return
  settingsForm.value = {
    name: c.name || '',
    code: c.code || '',
    semester: c.semester || '',
    description: c.description || '',
    start_date: c.start_date ? String(c.start_date).slice(0, 10) : '',
    end_date: c.end_date ? String(c.end_date).slice(0, 10) : '',
  }
}

async function saveCourseSettings() {
  savingSettings.value = true
  try {
    const payload = {
      name: settingsForm.value.name,
      code: settingsForm.value.code,
      semester: settingsForm.value.semester,
      description: settingsForm.value.description || null,
      start_date: new Date(settingsForm.value.start_date).toISOString(),
      end_date: new Date(settingsForm.value.end_date).toISOString(),
    }
    await axios.put(`/courses/${courseId.value}`, payload)
    await fetchCourse()
    syncSettingsForm()
  } catch (e) {
    console.error('Failed to save settings', e.response?.data?.detail || e)
  } finally {
    savingSettings.value = false
  }
}

async function regenerateInviteCode() {
  regeneratingInvite.value = true
  try {
    const res = await axios.post(`/courses/${courseId.value}/regenerate-invite`)
    if (course.value) course.value.invite_code = res.data.invite_code
  } catch (e) {
    console.error('Failed to regenerate invite', e)
  } finally {
    regeneratingInvite.value = false
  }
}

async function toggleCourseActive() {
  try {
    const res = await axios.post(`/courses/${courseId.value}/toggle-active`)
    if (course.value) course.value.is_active = res.data.is_active
  } catch (e) {
    console.error('Failed to toggle active', e)
  }
}

async function archiveCourse() {
  if (!confirm(`Archive "${course.value?.name}"? It will be deactivated and hidden from students.`)) return
  try {
    await axios.post(`/courses/${courseId.value}/archive`)
    await fetchCourse()
  } catch (e) {
    console.error('Failed to archive', e)
  }
}

async function unarchiveCourse() {
  try {
    await axios.post(`/courses/${courseId.value}/unarchive`)
    await fetchCourse()
  } catch (e) {
    console.error('Failed to unarchive', e)
  }
}

async function deleteCourse() {
  if (!confirm(`Delete course "${course.value?.name}"? This cannot be undone.`)) return
  try {
    await axios.delete(`/courses/${courseId.value}`)
    router.push('/courses')
  } catch (e) {
    console.error('Failed to delete course', e)
  }
}

function toggleScoreboardExpand(userId) {
  expandedScoreboardRow.value = expandedScoreboardRow.value === userId ? null : userId
}

function openLab(lab) {
  router.push({ path: '/exercises', query: { labId: lab.id, courseId: courseId.value, wikiSlug: course.value?.wiki_slug || '' } })
}

async function fetchCourse() {
  loading.value = true
  try {
    const res = await axios.get(`/courses/${courseId.value}`)
    course.value = res.data.course
    labs.value = res.data.labs
    // Instructor management is handled in InstructorPanel.vue, not here
    isInstructor.value = false
    syncSettingsForm()
    fetchAssignments()
  } catch (e) {
    console.error('Failed to fetch course', e)
  } finally {
    loading.value = false
  }
}

async function fetchAssignments() {
  try {
    const res = await axios.get(`/courses/${courseId.value}/assignments`)
    courseAssignments.value = res.data.assignments || []
  } catch (e) {
    console.error('Failed to fetch assignments', e)
  }
}

function asnDueClass(dueDate) {
  if (!dueDate) return 'asn-due--none'
  const now = new Date()
  const due = new Date(dueDate)
  const diffDays = (due - now) / (1000 * 60 * 60 * 24)
  if (diffDays < 0) return 'asn-due--ended'
  if (diffDays <= 3) return 'asn-due--soon'
  return 'asn-due--ok'
}

function asnDueText(dueDate) {
  if (!dueDate) return 'No due date'
  const due = new Date(dueDate)
  const now = new Date()
  const dueDay = new Date(due.getFullYear(), due.getMonth(), due.getDate())
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const diffDays = Math.round((dueDay - today) / (1000 * 60 * 60 * 24))
  if (diffDays < 0) return `Ended`
  if (diffDays === 0) return 'Due today'
  if (diffDays === 1) return 'Due tomorrow'
  if (diffDays <= 7) return `Due in ${diffDays} days`
  return `Due ${due.toLocaleDateString()}`
}

function asnStartText(startDate) {
  if (!startDate) return ''
  const start = new Date(startDate)
  const now = new Date()
  const startDay = new Date(start.getFullYear(), start.getMonth(), start.getDate())
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const diffDays = Math.round((startDay - today) / (1000 * 60 * 60 * 24))
  if (diffDays <= 0) return 'Available now'
  if (diffDays === 1) return 'Opens tomorrow'
  if (diffDays <= 7) return `Opens in ${diffDays} days`
  return `Opens ${start.toLocaleDateString()}`
}

async function fetchScoreboard() {
  loadingScoreboard.value = true
  try {
    const res = await axios.get(`/courses/${courseId.value}/scoreboard`)
    scoreboard.value = res.data.scoreboard
    scoreboardLabs.value = res.data.labs
  } catch (e) {
    console.error('Failed to fetch scoreboard', e)
  } finally {
    loadingScoreboard.value = false
  }
}

async function fetchAchievements() {
  loadingAchievements.value = true
  try {
    const res = await axios.get(`/courses/${courseId.value}/achievements`)
    achievements.value = res.data.achievements
  } catch (e) {
    console.error('Failed to fetch achievements', e)
  } finally {
    loadingAchievements.value = false
  }
}

async function downloadClassReport() {
  downloadingReport.value = true
  try {
    const res = await axios.get(`/courses/${courseId.value}/report`, {
      responseType: 'blob',
    })
    const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `report_${course.value.code}_class.pdf`
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (e) {
    console.error('Failed to download report', e)
  } finally {
    downloadingReport.value = false
  }
}

// Sync tab from route (e.g. deep link)
watch(() => route.query.tab, (tab) => {
  if (tab && ['assignments', 'scoreboard', 'achievements', 'manage-labs', 'students', 'settings'].includes(tab)) {
    activeTab.value = tab
  }
})

// Fetch tab data on tab switch
watch(activeTab, (tab) => {
  if (tab === 'scoreboard' && scoreboard.value.length === 0) fetchScoreboard()
  if (tab === 'achievements' && achievements.value.length === 0) fetchAchievements()
  if (tab === 'assignments' && courseAssignments.value.length === 0) fetchAssignments()
  if (tab === 'manage-labs' && isInstructor.value && availableLabs.value.length === 0) fetchAvailableLabs()
  if (tab === 'students' && isInstructor.value) {
    fetchCourseStudents()
    if (isAdmin.value) fetchEnrollableUsers()
  }
  if (tab === 'settings' && isInstructor.value) syncSettingsForm()
})

onMounted(() => {
  fetchCourse().then(() => {
    const tab = tabFromRoute()
    if (tab === 'assignments') fetchAssignments()
    if (tab === 'manage-labs' && isInstructor.value) fetchAvailableLabs()
    if (tab === 'students' && isInstructor.value) {
      fetchCourseStudents()
      if (isAdmin.value) fetchEnrollableUsers()
    }
  })
})
</script>

<style scoped>
.course-page {
  min-height: calc(100vh - 64px);
  background: var(--bg-primary);
  padding: 2rem 1.5rem;
}

.course-container {
  max-width: 1100px;
  margin: 0 auto;
}

.loading-text {
  color: var(--text-secondary);
  text-align: center;
  padding: 3rem;
}

/* Header */
.back-link {
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 0.85rem;
  display: inline-block;
  margin-bottom: 0.75rem;
  transition: color 0.2s;
}

.back-link:hover {
  color: var(--accent);
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.course-header h1 {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 0.35rem;
}

.header-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  color: var(--text-secondary);
  flex-wrap: wrap;
}

.meta-sep {
  color: var(--nav-label);
}

.course-code {
  font-weight: 600;
  color: var(--accent);
}

.course-status {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
}

.status-active {
  color: var(--success);
  background: rgba(34, 197, 94, 0.1);
}

.status-ended {
  color: var(--text-secondary);
  background: rgba(148, 163, 184, 0.1);
}

.status-upcoming {
  color: var(--warning);
  background: rgba(245, 158, 11, 0.1);
}

.report-btn {
  background: var(--nav-label);
  color: var(--text-primary);
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
  white-space: nowrap;
}

.report-btn:hover:not(:disabled) {
  background: var(--text-muted);
}

.report-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Tabs */
.tabs {
  display: flex;
  gap: 0.25rem;
  margin-top: 1.5rem;
  margin-bottom: 1.5rem;
  border-bottom: 1px solid var(--border-color);
}

.tab {
  background: none;
  border: none;
  color: var(--text-secondary);
  padding: 0.75rem 1.25rem;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}

.tab:hover {
  color: var(--text-primary);
}

.tab.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
}

.empty-tab {
  color: var(--text-muted);
  text-align: center;
  padding: 3rem;
}

/* Labs List */
.labs-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.lab-row {
  display: flex;
  align-items: center;
  gap: 1rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 0.85rem 1.25rem;
  transition: border-color 0.2s;
}

.lab-row--clickable {
  cursor: pointer;
}

.lab-row--clickable:hover {
  border-color: var(--accent);
  background: rgba(59, 130, 246, 0.04);
}

.lab-row--locked {
  opacity: 0.55;
  cursor: not-allowed;
}

.lab-name--locked {
  color: var(--nav-label);
}

.locked-badge {
  font-size: 0.7rem;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(100, 116, 139, 0.15);
  color: var(--nav-label);
}

.lab-row-arrow {
  width: 18px;
  height: 18px;
  color: var(--nav-label);
  flex-shrink: 0;
  transition: color 0.2s, transform 0.2s;
}

.lab-row--clickable:hover .lab-row-arrow {
  color: var(--accent);
  transform: translateX(2px);
}

.lab-status-icon {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.status-bar {
  display: inline-block;
  width: 4px;
  height: 20px;
  border-radius: 2px;
}

.status-bar--completed {
  background: var(--success);
}

.lab-row:has(.status-bar--completed) {
  border-left: 3px solid var(--success);
  background: rgba(34, 197, 94, 0.05);
}

.lab-row:has(.status-bar--completed) .lab-name {
  text-decoration: line-through;
  text-decoration-color: rgba(34, 197, 94, 0.4);
  color: var(--text-secondary);
}

.status-circle {
  width: 14px;
  height: 14px;
  border: 2px solid var(--nav-label);
  border-radius: 50%;
}

.lab-info {
  flex: 1;
}

.lab-name {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-primary);
}

.lab-meta {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-top: 0.25rem;
}

.drill-badge {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 0.1rem 0.4rem;
  border-radius: 3px;
  background: #1e3a5f;
  color: #93c5fd;
}

.difficulty-badge {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  padding: 0.1rem 0.4rem;
  border-radius: 3px;
}

.difficulty-beginner {
  color: var(--success);
  background: rgba(34, 197, 94, 0.1);
}

.difficulty-intermediate {
  color: var(--warning);
  background: rgba(245, 158, 11, 0.1);
}

.difficulty-advanced {
  color: var(--danger);
  background: var(--danger-bg);
}

.lab-duration {
  font-size: 0.8rem;
  color: var(--text-muted);
}

.exclusive-badge {
  font-size: 0.7rem;
  font-weight: 600;
  color: #a78bfa;
  background: rgba(167, 139, 250, 0.1);
  padding: 0.1rem 0.45rem;
  border-radius: 3px;
}

/* Scoring Guide */
.scoring-guide-toggle {
  margin-bottom: 0.75rem;
}

.guide-toggle-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  padding: 0.35rem 0.75rem;
  border-radius: 6px;
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s;
}

.guide-toggle-btn:hover {
  color: #e2e8f0;
  border-color: var(--nav-label);
}

.scoring-guide {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 1rem 1.25rem;
  margin-top: 0.5rem;
}

.guide-section {
  margin-bottom: 1rem;
}

.guide-section:last-child {
  margin-bottom: 0;
}

.guide-section h4 {
  color: #e2e8f0;
  font-size: 0.85rem;
  margin: 0 0 0.5rem;
  padding-bottom: 0.35rem;
  border-bottom: 1px solid var(--border-color);
}

.guide-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 0.35rem 1.5rem;
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.guide-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.guide-pts {
  display: inline-block;
  min-width: 36px;
  text-align: right;
  font-weight: 700;
  color: var(--success);
  font-family: monospace;
  font-size: 0.85rem;
}

.guide-note {
  margin-top: 0.4rem;
  font-size: 0.75rem;
  color: var(--text-muted);
  font-style: italic;
}

.guide-grid--achievements {
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 0.5rem;
}

.guide-ach {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  font-size: 0.8rem;
  color: var(--text-secondary);
  line-height: 1.4;
}

.guide-ach strong {
  color: #e2e8f0;
}

.guide-ach-icon {
  font-size: 1.2rem;
  flex-shrink: 0;
}

.slide-enter-active,
.slide-leave-active {
  transition: all 0.2s ease;
}

.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  transform: translateY(-5px);
}

/* Scoreboard (compact expandable rows) */
.scoreboard-compact {
  max-width: 100%;
}

.scoreboard-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}

.scoreboard-table thead {
  background: var(--bg-secondary);
}

.scoreboard-table th {
  padding: 0.65rem 0.75rem;
  text-align: left;
  color: var(--text-secondary);
  font-weight: 600;
  font-size: 0.8rem;
  border-bottom: 1px solid var(--border-color);
  white-space: nowrap;
}

.scoreboard-table td {
  padding: 0.6rem 0.75rem;
  border-bottom: 1px solid var(--bg-secondary);
  color: var(--text-secondary);
}

.sb-main-row {
  cursor: pointer;
  transition: background 0.15s;
}

.scoreboard-table tbody .sb-main-row:hover {
  background: rgba(59, 130, 246, 0.08);
}

.my-row {
  background: rgba(59, 130, 246, 0.08) !important;
}

.my-row td {
  color: var(--text-primary);
}

.col-rank {
  width: 50px;
  text-align: center;
}

.col-student {
  width: 20%;
}

.col-progress {
  width: 30%;
  min-width: 140px;
}

.col-total {
  text-align: center;
  min-width: 60px;
}

.col-badges {
  min-width: 70px;
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.rank-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  font-weight: 700;
  font-size: 0.8rem;
}

.rank-badge.gold {
  background: linear-gradient(135deg, #f59e0b, #d97706);
  color: #1e293b;
}

.rank-badge.silver {
  background: linear-gradient(135deg, #94a3b8, #64748b);
  color: #1e293b;
}

.rank-badge.bronze {
  background: linear-gradient(135deg, #d97706, #92400e);
  color: #1e293b;
}

.rank-num {
  color: var(--text-muted);
}

.student-name {
  font-weight: 600;
  color: var(--text-primary);
}

.student-id {
  font-size: 0.75rem;
  color: var(--text-muted);
}

/* Progress bar */
.progress-bar {
  height: 8px;
  background: var(--bg-secondary);
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 0.25rem;
}

.progress-fill {
  height: 100%;
  background: var(--success);
  border-radius: 4px;
  transition: width 0.2s ease;
}

.progress-text {
  font-size: 0.8rem;
  color: var(--text-muted);
}

.badge-count-text {
  font-weight: 600;
  color: var(--accent);
}

.sb-chevron {
  color: var(--text-muted);
  flex-shrink: 0;
  transition: transform 0.2s;
}

.sb-chevron.chevron-open {
  transform: rotate(180deg);
}

.badge-none {
  color: var(--nav-label);
}

/* Expanded detail row */
.sb-detail-row td {
  padding: 0 !important;
  border-bottom: 1px solid var(--border-color);
  vertical-align: top;
}

.sb-detail-panel {
  padding: 0.75rem 1rem 1rem;
  background: rgba(59, 130, 246, 0.04);
  border-left: 3px solid var(--accent);
  margin: 0 0.75rem 0.6rem;
}

.sb-lab-item {
  display: flex;
  align-items: center;
  gap: 0.5rem 1rem;
  padding: 0.35rem 0;
  font-size: 0.85rem;
  flex-wrap: wrap;
}

.sb-lab-status {
  flex-shrink: 0;
  width: 1.2em;
  text-align: center;
  font-size: 0.9rem;
}

.sb-lab-done {
  color: var(--success);
}

.sb-lab-pending {
  color: var(--nav-label);
}

.sb-lab-name {
  flex: 1;
  min-width: 0;
  color: var(--text-secondary);
}

.sb-lab-score {
  font-weight: 600;
  color: var(--success);
  min-width: 2.5rem;
  text-align: right;
}

.sb-lab-score-empty {
  color: var(--nav-label);
  min-width: 2.5rem;
  text-align: right;
}

.sb-lab-ach-icons {
  display: inline-flex;
  gap: 0.15rem;
  flex-shrink: 0;
}

.lab-ach-icon {
  font-size: 0.75rem;
  cursor: default;
  line-height: 1;
}

/* Achievements List */
.achievements-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.achievement-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 0.75rem 1rem;
}

.ach-icon {
  font-size: 1.3rem;
  flex-shrink: 0;
}

.ach-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.ach-label {
  font-weight: 600;
  color: var(--text-primary);
  font-size: 0.9rem;
}

.ach-detail {
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.ach-date {
  font-size: 0.78rem;
  color: var(--text-muted);
  white-space: nowrap;
}

/* Manage Labs tab */
.manage-labs-tab {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.manage-labs-section {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 1rem 1.25rem;
}

.manage-section-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 0.75rem;
}

.assigned-labs-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.assigned-category-group {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
}

.assigned-category-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.6rem 0.75rem;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-secondary);
  background: var(--bg-primary);
  border: none;
  border-bottom: 1px solid var(--border-color);
  text-align: left;
  cursor: pointer;
  transition: color 0.15s;
}

.assigned-category-header:hover {
  color: var(--accent);
}

.assigned-category-count {
  font-weight: 400;
  color: var(--text-muted);
  font-size: 0.75rem;
}

.assigned-lab-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid var(--border-color);
}

.assigned-lab-row:last-child {
  border-bottom: none;
}

.assigned-lab-order {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.order-btn {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  padding: 0.15rem 0.4rem;
  font-size: 0.7rem;
  cursor: pointer;
  border-radius: 4px;
  line-height: 1;
}

.order-btn:hover:not(:disabled) {
  color: var(--accent);
  border-color: var(--accent);
}

.order-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.assigned-lab-info {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.assigned-lab-name {
  font-weight: 500;
  color: var(--text-primary);
}

.btn-remove-lab {
  background: transparent;
  border: 1px solid var(--danger);
  color: var(--danger);
  padding: 0.35rem 0.75rem;
  border-radius: 6px;
  font-size: 0.8rem;
  cursor: pointer;
}

.btn-remove-lab:hover:not(:disabled) {
  background: rgba(239, 68, 68, 0.1);
}

.btn-remove-lab:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-save-order {
  margin-top: 0.75rem;
  background: var(--accent);
  color: #fff;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
}

.btn-save-order:hover:not(:disabled) {
  background: #2563eb;
}

.btn-save-order:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.assign-labs-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.btn-expand-all {
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  padding: 0.35rem 0.75rem;
  border-radius: 6px;
  font-size: 0.8rem;
  cursor: pointer;
}

.btn-expand-all:hover {
  color: var(--accent);
  border-color: var(--accent);
}

.add-labs-search {
  width: 100%;
  max-width: 320px;
  padding: 0.5rem 0.75rem;
  margin-bottom: 0.75rem;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 0.875rem;
}

.add-labs-search::placeholder {
  color: var(--text-muted);
}

.assign-accordion {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-bottom: 0.75rem;
}

.assign-group-header-row {
  display: flex;
  align-items: center;
  gap: 0;
}

.assign-group-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 1;
  padding: 0.5rem 0.75rem;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px 0 0 6px;
  color: var(--text-secondary);
  font-size: 0.875rem;
  text-align: left;
  cursor: pointer;
}

.assign-group-header:hover {
  border-color: var(--accent);
  color: var(--text-primary);
}

.btn-add-all {
  padding: 0.5rem 0.625rem;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-left: none;
  border-radius: 0 6px 6px 0;
  color: var(--accent);
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.15s, color 0.15s;
}

.btn-add-all:hover {
  background: var(--accent);
  color: #fff;
}

.assign-chevron {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  transition: transform 0.2s;
}

.assign-chevron--open {
  transform: rotate(90deg);
}

.assign-group-track {
  font-weight: 500;
  color: var(--text-primary);
}

.assign-group-sep {
  color: var(--nav-label);
}

.assign-group-level {
  color: var(--text-secondary);
}

.assign-group-count {
  font-size: 0.8rem;
  color: var(--text-muted);
}

.assign-group-body {
  padding: 0.5rem 0.75rem 0.5rem 2rem;
  border-left: 2px solid var(--border-color);
  margin-left: 0.5rem;
}

.lab-checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 0;
  cursor: pointer;
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.lab-checkbox-label input {
  flex-shrink: 0;
}

.lab-checkbox-name {
  flex: 1;
  color: var(--text-primary);
}

.lab-checkbox-diff {
  font-size: 0.75rem;
  text-transform: capitalize;
  color: var(--text-muted);
}

.btn-assign-selected {
  background: var(--success);
  color: #fff;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
}

.btn-assign-selected:hover:not(:disabled) {
  background: #16a34a;
}

.btn-assign-selected:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Students tab */
.students-tab {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.students-invite {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.students-invite-label {
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.students-invite-code {
  font-family: monospace;
  font-size: 0.9rem;
  padding: 0.35rem 0.6rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--accent);
  cursor: pointer;
}

.students-invite-code:hover {
  border-color: var(--accent);
}

.btn-copy-invite {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  padding: 0.35rem 0.75rem;
  border-radius: 6px;
  font-size: 0.8rem;
  cursor: pointer;
}

.btn-copy-invite:hover {
  color: var(--accent);
  border-color: var(--accent);
}

.students-enroll-note {
  font-size: 0.85rem;
  color: var(--text-muted);
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 0.75rem 1rem;
}

.students-enroll-section,
.students-list-section {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 1rem 1.25rem;
}

.enroll-form {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  flex-wrap: wrap;
}

.enroll-select {
  min-width: 220px;
  padding: 0.5rem 0.75rem;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 0.875rem;
}

.btn-enroll {
  background: var(--success);
  color: #fff;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
}

.btn-enroll:hover:not(:disabled) {
  background: #16a34a;
}

.btn-enroll:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.students-table-wrap {
  overflow-x: auto;
}

.students-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}

.students-table th {
  padding: 0.5rem 0.75rem;
  text-align: left;
  color: var(--text-muted);
  font-weight: 600;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-primary);
}

.students-table td {
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid var(--border-color);
  color: var(--text-secondary);
}

.cell-primary {
  font-weight: 500;
  color: var(--text-primary);
}

.cell-muted {
  color: var(--text-muted);
  font-size: 0.8rem;
}

.cell-actions {
  display: flex;
  gap: 0.35rem;
  flex-wrap: wrap;
}

.action-btn-sm {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  cursor: pointer;
}

.action-btn-sm:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.action-btn-danger:hover {
  border-color: var(--danger);
  color: var(--danger);
}

.student-detail-row td {
  padding: 0;
  border-bottom: 1px solid var(--border-color);
  vertical-align: top;
}

.student-labs-detail {
  padding: 0.75rem 1rem;
  background: rgba(59, 130, 246, 0.04);
  border-left: 3px solid var(--accent);
  margin: 0 0.75rem 0.5rem;
}

.loading-text,
.empty-state {
  font-size: 0.85rem;
  color: var(--text-muted);
  padding: 0.5rem 0;
}

.data-table-nested {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8rem;
}

.data-table-nested th {
  padding: 0.35rem 0.5rem;
  text-align: left;
  color: var(--text-muted);
  font-weight: 600;
  border-bottom: 1px solid var(--border-color);
}

.data-table-nested td {
  padding: 0.35rem 0.5rem;
  border-bottom: 1px solid var(--border-color);
  color: var(--text-secondary);
}

.status-badge-sm {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
}

.status-done {
  background: rgba(34, 197, 94, 0.15);
  color: var(--success);
}

.status-pending {
  background: rgba(148, 163, 184, 0.15);
  color: var(--text-muted);
}

.btn-reset-lab {
  background: transparent;
  border: 1px solid var(--danger);
  color: var(--danger);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  cursor: pointer;
}

.btn-reset-lab:hover:not(:disabled) {
  background: rgba(239, 68, 68, 0.1);
}

.btn-reset-lab:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Settings tab */
.settings-tab {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.settings-section {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 1rem 1.25rem;
}

.settings-form {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.form-row {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.form-row label {
  font-size: 0.8rem;
  color: var(--text-secondary);
  font-weight: 500;
}

.settings-input {
  padding: 0.5rem 0.75rem;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 0.875rem;
  max-width: 400px;
}

.form-row--half {
  max-width: 200px;
}

.btn-save-settings {
  margin-top: 0.25rem;
  background: var(--accent);
  color: #fff;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  align-self: flex-start;
}

.btn-save-settings:hover:not(:disabled) {
  background: #2563eb;
}

.btn-save-settings:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.invite-code-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.settings-invite-code {
  font-family: monospace;
  font-size: 0.95rem;
  padding: 0.4rem 0.75rem;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--accent);
}

.btn-regenerate-invite {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  padding: 0.35rem 0.75rem;
  border-radius: 6px;
  font-size: 0.8rem;
  cursor: pointer;
}

.btn-regenerate-invite:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}

.btn-regenerate-invite:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.status-actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.btn-toggle-active,
.btn-archive,
.btn-unarchive {
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid var(--border-color);
  background: var(--bg-primary);
  color: var(--text-primary);
}

.btn-toggle-active:hover,
.btn-archive:hover,
.btn-unarchive:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.btn-archive {
  border-color: var(--warning);
  color: var(--warning);
}

.btn-archive:hover {
  background: rgba(245, 158, 11, 0.1);
}

.settings-danger {
  border-color: rgba(239, 68, 68, 0.3);
}

.danger-note {
  font-size: 0.85rem;
  color: var(--text-muted);
  margin: 0 0 0.75rem;
}

.btn-delete-course {
  background: transparent;
  border: 1px solid var(--danger);
  color: var(--danger);
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
}

.btn-delete-course:hover {
  background: rgba(239, 68, 68, 0.1);
}

/* Assignment Cards */
.assignment-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1.25rem;
}
.asn-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 1.25rem;
  cursor: pointer;
  transition: all 0.2s ease;
}
.asn-card:hover {
  border-color: var(--accent);
  transform: translateY(-2px);
}
.asn-card--active {
  border-color: var(--accent);
  box-shadow: 0 0 0 1px var(--accent);
}
.asn-card--locked {
  opacity: 0.7;
  cursor: default;
}
.asn-card--locked:hover {
  transform: none;
  border-color: var(--border-color);
}
.asn-card__locked-msg {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  background: var(--bg-primary);
  border-radius: 8px;
  font-size: 0.85rem;
  color: var(--text-muted);
  margin-top: 0.5rem;
}
.asn-due--locked {
  background: var(--bg-primary);
  color: var(--text-muted);
  border: 1px solid var(--border-color);
  padding: 0.2rem 0.6rem;
  border-radius: 12px;
  font-size: 0.75rem;
  white-space: nowrap;
}
.asn-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}
.asn-card__name {
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--text-primary);
}
.asn-card__desc {
  font-size: 0.83rem;
  color: var(--text-muted);
  margin-bottom: 0.75rem;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.asn-card__stats {
  display: flex;
  gap: 1rem;
  margin-bottom: 0.5rem;
}
.asn-stat {
  font-size: 0.8rem;
  color: var(--text-secondary);
}
.asn-card__progress {
  margin-top: 0.25rem;
}
.asn-progress-bar {
  height: 4px;
  background: var(--bg-tertiary, rgba(148, 163, 184, 0.15));
  border-radius: 2px;
  overflow: hidden;
}
.asn-progress-fill {
  height: 100%;
  background: var(--success);
  border-radius: 2px;
  transition: width 0.3s ease;
}
.asn-due {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.2rem 0.6rem;
  border-radius: 4px;
  white-space: nowrap;
}
.asn-due--ok { color: var(--success); background: rgba(34, 197, 94, 0.1); }
.asn-due--soon { color: var(--warning); background: rgba(245, 158, 11, 0.1); }
.asn-due--overdue, .asn-due--ended { color: var(--text-muted); background: rgba(100, 116, 139, 0.1); }
.asn-due--none { color: var(--text-muted); background: rgba(148, 163, 184, 0.1); }

.asn-detail {
  background: var(--bg-secondary);
  border: 1px solid var(--accent);
  border-radius: 12px;
  padding: 1.25rem;
}
.asn-detail--inline {
  grid-column: 1 / -1;
  margin-top: -0.25rem;
  margin-bottom: 0.5rem;
}
.asn-detail__title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 1rem;
}

/* Lab rename controls */
.rename-input {
  flex: 1;
  max-width: 260px;
  font-size: 0.8rem;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  border: 1px solid var(--border-color);
  background: var(--bg-primary);
  color: var(--text-primary);
}
.btn-rename-lab {
  background: none;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  padding: 0.15rem 0.4rem;
  cursor: pointer;
  font-size: 0.75rem;
  color: var(--text-secondary);
  transition: color 0.2s, border-color 0.2s;
}
.btn-rename-lab:hover { color: var(--accent); border-color: var(--accent); }
.btn-save-rename, .btn-cancel-rename {
  font-size: 0.75rem;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  cursor: pointer;
  border: 1px solid var(--border-color);
  background: none;
  color: var(--text-primary);
}
.btn-save-rename { color: var(--success); border-color: var(--success); }
.btn-save-rename:hover { background: var(--success); color: #fff; }
.btn-cancel-rename:hover { background: var(--bg-tertiary); }
.lab-name--custom {
  color: var(--accent);
  font-style: italic;
}

@media (max-width: 768px) {
  .header-row {
    flex-direction: column;
  }
  .assignment-grid {
    grid-template-columns: 1fr;
  }
}
</style>

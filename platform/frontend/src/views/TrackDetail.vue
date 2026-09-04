<template>
  <div class="track-page" :class="{ 'track-page--panel-open': activeLab }">
    <!-- Breadcrumb / Back nav -->
    <div class="track-breadcrumb">
      <router-link :to="backLink.to" class="breadcrumb-link">
        <ArrowLeftIcon />
        <span>{{ backLink.label }}</span>
      </router-link>
    </div>

    <!-- Track Header -->
    <div v-if="track" class="track-header" :style="{ '--track-color': track.color }">
      <div class="track-header__left">
        <div class="track-header__icon">
          <component :is="getTrackIcon(track.icon)" />
        </div>
        <div>
          <h1 class="track-header__title">{{ track.name }}</h1>
          <p class="track-header__description">{{ track.description }}</p>
        </div>
      </div>
      <div class="track-header__stats">
        <div class="stat-item">
          <span class="stat-value">{{ track.completed_labs }}</span>
          <span class="stat-label">Completed</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">{{ track.total_labs - track.completed_labs }}</span>
          <span class="stat-label">Remaining</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">{{ track.progress_percent }}%</span>
          <span class="stat-label">Progress</span>
        </div>
      </div>
    </div>

    <!-- Levels Accordion -->
    <div v-if="track" class="levels-container">
      <div
        v-for="level in track.levels"
        :key="level.id"
        class="level-section"
        :class="{ 'level-section--expanded': expandedLevels.includes(level.id) }"
      >
        <div
          class="level-header"
          role="button"
          tabindex="0"
          :aria-expanded="expandedLevels.includes(level.id)"
          @click="toggleLevel(level.id)"
          @keydown.enter.prevent="toggleLevel(level.id)"
          @keydown.space.prevent="toggleLevel(level.id)"
        >
          <div class="level-header__left">
            <span class="level-number">{{ level.level_number }}</span>
            <div class="level-info">
              <h3 class="level-title">{{ level.name }}</h3>
              <p class="level-description">{{ level.description }}</p>
            </div>
          </div>
          <div class="level-header__right">
            <span class="level-progress">{{ level.completed_labs }}/{{ level.total_labs }}</span>
            <div class="level-progress-ring" :class="{ 'level-progress-ring--complete': level.is_complete }">
              <svg viewBox="0 0 36 36">
                <path
                  class="ring-bg"
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                />
                <path
                  class="ring-fill"
                  :stroke-dasharray="`${level.total_labs > 0 ? (level.completed_labs / level.total_labs * 100) : 0}, 100`"
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                />
              </svg>
            </div>
            <ChevronIcon class="level-chevron" />
          </div>
        </div>

        <!-- Labs List -->
        <transition name="slide">
          <div v-if="expandedLevels.includes(level.id)" class="labs-list">
            <div
              v-for="lab in level.labs"
              :key="lab.id"
              class="lab-row"
              :class="{
                'lab-row--completed': lab.is_completed,
                'lab-row--current': lab.is_current,
                'lab-row--locked': !lab.is_unlocked,
                'lab-row--active': lab.is_active
              }"
              :role="(lab.is_unlocked || lab.is_completed) ? 'button' : undefined"
              :tabindex="(lab.is_unlocked || lab.is_completed) ? 0 : undefined"
              :aria-label="(lab.is_unlocked || lab.is_completed) ? `Open details for ${lab.name}` : undefined"
              @click="(lab.is_unlocked || lab.is_completed) && openActiveLab(lab)"
              @keydown.enter.self.prevent="(lab.is_unlocked || lab.is_completed) && openActiveLab(lab)"
              @keydown.space.self.prevent="(lab.is_unlocked || lab.is_completed) && openActiveLab(lab)"
              :style="{ cursor: (lab.is_unlocked || lab.is_completed) ? 'pointer' : 'default' }"
            >
              <div class="lab-row__status">
                <span v-if="lab.is_completed" class="status-bar status-bar--completed"></span>
                <PlayCircleIcon v-else-if="lab.is_active" class="status-icon status-icon--active" />
                <TargetIcon v-else-if="lab.is_current" class="status-icon status-icon--current" />
                <LockIcon v-else-if="!lab.is_unlocked" class="status-icon status-icon--locked" />
                <CircleIcon v-else class="status-icon status-icon--available" />
              </div>

              <div class="lab-row__content">
                <h4 class="lab-row__title">
                  {{ lab.name }}
                  <span v-if="isDrill(lab)" class="drill-badge">Drill</span>
                  <span
                    v-if="lab.requires_kvm && !kvmAvailable"
                    class="kvm-badge"
                    title="Uses a shared Windows VM; this server has no KVM hardware virtualization"
                  >Needs KVM host</span>
                </h4>
                <p v-if="lab.scenario_brief" class="lab-row__scenario-brief">{{ lab.scenario_brief }}</p>
                <div class="lab-row__meta">
                  <span class="lab-difficulty" :class="`lab-difficulty--${lab.difficulty}`">
                    {{ lab.difficulty }}
                  </span>
                  <span class="lab-duration">
                    <ClockIcon />
                    {{ lab.duration_minutes }} min
                  </span>
                  <span v-for="tool in lab.tools?.slice(0, 3)" :key="tool" class="lab-tool">
                    {{ tool }}
                  </span>
                </div>
              </div>

              <div class="lab-row__actions">
                <button
                  v-if="lab.workbook && workbookOpenable(lab.workbook)"
                  @click.stop="openWorkbookForLab(lab)"
                  class="btn btn--workbook-sm btn--sm workbook-btn-row"
                  title="Open walkthrough in new tab"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-icon">
                    <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>
                    <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
                  </svg>
                  Workbook
                </button>
                <button
                  v-if="lab.is_active"
                  @click.stop="openActiveLab(lab)"
                  class="btn btn--primary btn--sm"
                >
                  Continue
                </button>
                <button
                  v-if="lab.is_active"
                  @click.stop="stopLab"
                  class="btn btn--danger btn--sm"
                >
                  Stop
                </button>
                <button
                  v-else-if="lab.is_completed"
                  @click.stop="viewLab(lab)"
                  class="btn btn--secondary btn--sm"
                >
                  Review
                </button>
                <span
                  v-else-if="lab.requires_kvm && !kvmAvailable"
                  class="locked-text"
                  title="Uses a shared Windows VM; this server has no KVM hardware virtualization"
                >
                  Unavailable on this server
                </span>
                <button
                  v-else-if="lab.is_unlocked"
                  @click.stop="launchLab(lab)"
                  class="btn btn--primary btn--sm"
                  :disabled="hasActiveLab && !lab.is_active"
                >
                  Launch
                </button>
                <span v-else class="locked-text">
                  Complete previous exercise
                </span>
              </div>
            </div>
          </div>
        </transition>
      </div>
    </div>

    <!-- Active Lab Panel -->
    <transition name="slide-up">
      <div v-if="activeLab" class="active-lab-panel">
        <div class="active-lab-panel__header" :style="{ '--track-color': track?.color }">
          <div class="active-lab-panel__title-group">
            <h2>{{ activeLab.lab.name }}</h2>
            <span v-if="activeLab.session" class="active-badge">Active</span>
            <span v-else-if="activeLab.lab.is_completed" class="completed-badge">Completed</span>
            <button v-if="activeLab.session" @click="stopLab" class="btn btn--danger btn--sm">Stop Exercise</button>
            <template v-else>
              <div class="launch-buttons">
                <button @click="launchWithImage(null)" class="btn btn--primary btn--sm" :disabled="launchingLab">
                  {{ launchingLab && !launchingImage ? 'Starting...' : 'Start Exercise' }}
                </button>
              </div>
            </template>
          </div>
          <div v-if="activeLab.session" class="active-lab-panel__timer-section">
            <div class="active-lab-panel__timer" :class="{ 'timer--warning': isExpiringSoon }">
              <ClockIcon />
              {{ timeRemaining }}
            </div>
            <button
              @click="extendSession"
              class="btn btn--secondary btn--sm extend-btn"
              :disabled="extendingSession"
              title="Add 1 hour to your session"
            >
              {{ extendingSession ? 'Extending...' : '+1 Hour' }}
            </button>
          </div>
          <button @click="closeActiveLab" class="close-btn" aria-label="Close exercise panel">
            <XIcon />
          </button>
        </div>

        <!-- Session expiry notice: shown instead of silently closing the panel -->
        <div v-if="sessionExpired" class="panel-banner panel-banner--expired" role="alert">
          <div class="panel-banner__text">
            <strong>Your session expired.</strong>
            The lab environment was shut down when the timer reached zero. Completed flags are saved,
            but anything left inside the lab machines is gone. Relaunch to keep working.
          </div>
          <div class="panel-banner__actions">
            <button
              class="btn btn--primary btn--sm"
              :disabled="launchingLab"
              @click="relaunchExpiredSession"
            >
              {{ launchingLab ? 'Relaunching...' : 'Relaunch Exercise' }}
            </button>
            <button class="btn btn--secondary btn--sm" @click="sessionExpired = false">Dismiss</button>
          </div>
        </div>

        <!-- Errored session recovery: shown when a launch fails or the session errored -->
        <div
          v-if="spawnError || activeLab.session?.status === 'error'"
          class="panel-banner panel-banner--error"
          role="alert"
        >
          <div class="panel-banner__text">
            <strong>The lab environment hit an error.</strong>
            {{ spawnError || 'The last launch attempt failed.' }}
            Clear and Relaunch stops any active session, then starts a fresh environment.
            If it fails again, contact your instructor.
          </div>
          <div class="panel-banner__actions">
            <button
              class="btn btn--primary btn--sm"
              :disabled="launchingLab"
              @click="retryLaunch"
            >
              {{ launchingLab ? 'Starting...' : 'Clear and Relaunch' }}
            </button>
            <button class="btn btn--secondary btn--sm" @click="spawnError = ''">Dismiss</button>
          </div>
        </div>

        <div class="active-lab-panel__body">
          <div class="active-lab-grid">
            <!-- Scenario (spans full width of grid) -->
            <div v-if="activeLab.lab.scenario" class="panel-section panel-section--full panel-section--scenario">
              <h3 class="section-title">
                <TargetIcon />
                Scenario
              </h3>
              <div class="scenario-content" v-html="renderScenario(activeLab.lab.scenario)"></div>
            </div>
            <!-- Objectives -->
            <div class="panel-section">
              <h3 class="section-title">
                <TargetIcon />
                Objectives
              </h3>
              <ul class="objectives-list">
                <li v-for="(obj, idx) in activeLab.lab.objectives" :key="idx">
                  {{ obj }}
                </li>
              </ul>
            </div>

            <!-- ICS Techniques (ATT&CK for ICS) -->
            <div v-if="activeLab.lab.ics_techniques && activeLab.lab.ics_techniques.length" class="panel-section">
              <h3 class="section-title">
                <TargetIcon />
                ATT&amp;CK for ICS
              </h3>
              <div class="ics-tech-list">
                <span
                  v-for="(tech, idx) in activeLab.lab.ics_techniques"
                  :key="tech.technique_id ? `${tech.technique_id}-${idx}` : idx"
                  class="ics-tech-chip"
                  :class="`ics-tech-chip--${tech.tactic || 'other'}`"
                  :title="tech.note || ''"
                >
                  <span v-if="tech.tactic" class="ics-tech-chip__tactic">{{ tech.tactic }}</span>
                  <span class="ics-tech-chip__label">
                    <span class="ics-tech-chip__id">{{ tech.technique_id }}</span>
                    <span v-if="tech.technique_name" class="ics-tech-chip__name">- {{ tech.technique_name }}</span>
                  </span>
                </span>
              </div>
            </div>

            <!-- Lab Network (only shown when exercise is running) -->
            <div v-if="activeLab.session" class="panel-section">
              <h3 class="section-title">
                <ServerIcon />
                Exercise Network
              </h3>
              <div class="network-info network-info--prominent">
                <span class="network-label">Subnet:</span>
                <span class="network-value">{{ activeLab.session.network_subnet }}</span>
              </div>
              <div v-if="activeLab.target_ips && activeLab.target_ips.length > 0" class="target-ips">
                <div class="target-ips-heading">Your targets:</div>
                <ul class="target-ip-list">
                  <li v-for="t in activeLab.target_ips" :key="t.id" class="target-ip-row">
                    <span class="target-ip-label">{{ t.label || t.id }}</span>
                    <span class="target-ip-value">{{ t.ip }}</span>
                  </li>
                </ul>
              </div>
              <p v-else class="network-hint">Scan the network to discover target machines.</p>
            </div>

            <!-- Hostnames -->
            <div v-if="activeLab.hostnames && activeLab.hostnames.length > 0" class="panel-section">
              <h3 class="section-title">
                <ServerIcon />
                Target Hostnames
              </h3>
              <div class="hostnames-list">
                <div v-for="(hostname, idx) in activeLab.hostnames" :key="idx" class="hostname-item">
                  <div class="hostname-name">{{ hostname.hostname }}</div>
                  <div v-if="hostname.description" class="hostname-desc">{{ hostname.description }}</div>
                </div>
              </div>
              <div class="hosts-file-section">
                <p class="hosts-file-hint">
                  <template v-if="activeLab.hostnames.some(h => h.ip)">Add these lines to <code>/etc/hosts</code>:</template>
                  <template v-else>After scanning, add discovered IPs to <code>/etc/hosts</code>:</template>
                </p>
                <pre class="hosts-file-content">{{ activeLab.hostnames.map(h => (h.ip || '<target_ip>') + '    ' + h.hostname).join('\n') }}</pre>
              </div>
            </div>

            <!-- Workbook -->
            <div v-if="activeLab.lab.workbook" class="panel-section">
              <h3 class="section-title">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="section-icon">
                  <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>
                  <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
                </svg>
                Workbook
              </h3>
              <p class="workbook-hint">Step-by-step walkthrough for this exercise.</p>
              <p v-if="!workbookOpenable(activeLab?.lab?.workbook)" class="workbook-hint workbook-hint--unavailable">
                This exercise's walkthrough lives in a course workbook. Open the
                exercise from the course to read it.
              </p>
              <button
                @click="openWorkbook"
                :disabled="!workbookOpenable(activeLab?.lab?.workbook)"
                class="btn btn--workbook"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-icon">
                  <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>
                  <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
                </svg>
                Open Workbook
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-icon btn-icon--external">
                  <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                  <polyline points="15 3 21 3 21 9"/>
                  <line x1="10" y1="14" x2="21" y2="3"/>
                </svg>
              </button>
            </div>

            <!-- Flag Submission (hidden for in-app triage exercises, which are scored, not flag-based) -->
            <div class="panel-section panel-section--full">
              <h3 class="section-title">
                <FlagIcon />
                Submit Flag
              </h3>
              <div class="flag-form">
                <input
                  v-model="flagInput"
                  type="text"
                  placeholder="OCR{your_flag_here}"
                  class="flag-input"
                  :class="{ 'flag-input--error': flagError, 'flag-input--success': flagSuccess }"
                  @keyup.enter="submitFlag"
                />
                <button
                  @click="submitFlag"
                  class="btn btn--primary"
                  :disabled="submittingFlag || !flagInput"
                >
                  {{ submittingFlag ? 'Checking...' : 'Submit' }}
                </button>
              </div>
              <p class="flag-guidance">
                Flags follow the exact format <code>OCR{example_text}</code> and are case sensitive.
                Submit the whole value, including <code>OCR{</code> and <code>}</code>.
              </p>
              <p v-if="activeLab.session" class="flag-autostop-warning">
                A correct flag completes the exercise and automatically shuts down your lab
                environment a few seconds later. Save any notes or command output from the lab
                machines before you submit.
              </p>
              <p v-if="flagMessage" :class="['flag-message', flagSuccess ? 'flag-message--success' : 'flag-message--error']">
                {{ flagMessage }}
              </p>
              <p v-if="flagSuccess && flagStoppedSession" class="flag-message flag-message--success">
                Your lab environment is shutting down and this panel will close in a moment.
              </p>
            </div>

            <!-- Hints -->
            <div class="panel-section panel-section--full">
              <h3 class="section-title">
                <LightbulbIcon />
                Hints
                <span class="hint-count">({{ activeLab.lab.hints_used }}/{{ activeLab.lab.hints_total || activeLab.lab.hints_available }} used)</span>
              </h3>
              <div v-for="(hint, index) in receivedHints" :key="index" class="hint-box">
                <div class="hint-number">Hint {{ hint.number }}</div>
                <div v-html="renderMarkdown(hint.text)"></div>
              </div>
              <div v-if="hintMessage" class="hint-message">{{ hintMessage }}</div>
              <button
                v-if="(activeLab.lab.hints_total || activeLab.lab.hints_available) > activeLab.lab.hints_used || hintMessage"
                @click="requestHint"
                class="btn btn--secondary btn--sm"
                :disabled="requestingHint || hintUnlockSeconds > 0"
              >
                {{ requestingHint ? 'Loading...' : (hintUnlockSeconds > 0 ? 'Waiting...' : 'Request Hint') }}
              </button>
              <p v-else-if="receivedHints.length === 0 && !hintMessage" class="no-hints">No hints available for this exercise</p>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <!-- Loading Overlay -->
    <div v-if="loading || spawning" class="loading-overlay" role="status" aria-live="polite">
      <div class="loading-box">
        <div class="spinner"></div>
        <template v-if="spawning">
          <p class="loading-box__status">Starting lab environment... {{ spawnElapsedText }}</p>
          <p class="loading-box__note">
            First launch builds the lab image and can take several minutes.
            Keep this page open; it will refresh on its own when the lab is ready.
          </p>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import { hasRole } from '../utils/roles'
import { usePoll } from '../composables/usePoll'
import { useClipboard } from '../composables/useClipboard'
import { setWikiAuthCookie } from '../utils/wikiAuth'
import axios from '../api/axios'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

marked.setOptions({ breaks: true, gfm: true })

// Icons
import { getTrackIcon } from '../components/icons/trackIcons.js'
import WindowsIcon from '../components/icons/WindowsIcon.vue'
import ChevronIcon from '../components/icons/ChevronIcon.vue'
import ClockIcon from '../components/icons/ClockIcon.vue'
import LockIcon from '../components/icons/LockIcon.vue'
import TargetIcon from '../components/icons/TargetIcon.vue'
import PlayCircleIcon from '../components/icons/PlayCircleIcon.vue'
import CircleIcon from '../components/icons/CircleIcon.vue'
import XIcon from '../components/icons/XIcon.vue'
import ServerIcon from '../components/icons/ServerIcon.vue'
import FlagIcon from '../components/icons/FlagIcon.vue'
import LightbulbIcon from '../components/icons/LightbulbIcon.vue'
import ArrowLeftIcon from '../components/icons/ArrowLeftIcon.vue'
// RangeBox opens in a dedicated /rangebox tab (not embedded)

const route = useRoute()
const router = useRouter()

// State
const track = ref(null)
const expandedLevels = ref([])
const activeLab = ref(null)
const { copied, copyText } = useClipboard()

const loading = ref(false)
const launchingImage = ref(null)  // which image button was clicked: null, 'kali', or 'ubuntu'
const activeRangeboxImage = ref('kali')  // persists which image is running after launch

// Flag submission
const flagInput = ref('')
const flagMessage = ref('')
const flagError = ref(false)
const flagSuccess = ref(false)
const submittingFlag = ref(false)
// True when a correct flag is tearing down a live environment, so the panel
// can say so instead of silently vanishing
const flagStoppedSession = ref(false)

// Hints
const receivedHints = ref([])
const requestingHint = ref(false)
const hintMessage = ref('')
const hintUnlockSeconds = ref(0)
let hintTimerInterval = null

// Drill detection — drill slugs contain an uppercase D followed by a digit (e.g. pentest-D5-02-*)
function isDrill(lab) {
  return lab.slug && /-D\d+-/.test(lab.slug)
}

// Session
const extendingSession = ref(false)
const launchingLab = ref(false)
const activeCourseId = ref(null)

// Session expiry + spawn feedback state
const sessionExpired = ref(false)
const spawnError = ref('')
const spawning = ref(false)
const spawnElapsed = ref(0)
let spawnTimerInterval = null

const spawnElapsedText = computed(() => {
  const m = Math.floor(spawnElapsed.value / 60)
  const s = spawnElapsed.value % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
})

// Elapsed timer shown in the launch overlay. The spawn endpoint is ASYNC: it
// returns { session_id, status: "starting" } at once and brings the environment
// up in the background, so the launch flow must poll spawn-status until the
// session is actually running before opening the panel (see pollSpawnStatus).
const startSpawnTimer = () => {
  stopSpawnTimer()
  spawnElapsed.value = 0
  spawning.value = true
  spawnTimerInterval = setInterval(() => { spawnElapsed.value++ }, 1000)
}

const stopSpawnTimer = () => {
  if (spawnTimerInterval) {
    clearInterval(spawnTimerInterval)
    spawnTimerInterval = null
  }
  spawning.value = false
}

// The spawn endpoint returns immediately with status "starting" and finishes the
// bring-up in a background task; poll spawn-status until the session leaves
// "starting". Without this the panel opens against a not-yet-running session and
// never updates, so a launch looks like it did nothing until a manual refresh.
const pollSpawnStatus = async (sessionId, { timeoutMs = 8 * 60 * 1000, intervalMs = 2000 } = {}) => {
  const deadline = Date.now() + timeoutMs
  while (true) {
    let data
    try {
      ({ data } = await axios.get(`/labs/spawn-status/${sessionId}`))
    } catch (e) {
      if (Date.now() > deadline) throw new Error('Timed out waiting for the lab to start.')
      await new Promise(r => setTimeout(r, intervalMs))
      continue
    }
    if (data.status === 'running') return data
    if (data.status === 'error') {
      throw new Error(data.error || data.detail || 'The lab environment failed to start.')
    }
    if (Date.now() > deadline) {
      throw new Error('The lab is taking longer than expected to start; give it a moment and refresh.')
    }
    await new Promise(r => setTimeout(r, intervalMs))
  }
}

const relaunchExpiredSession = () => {
  sessionExpired.value = false
  launchWithImage(null)
}

const retryLaunch = async () => {
  spawnError.value = ''
  // Actually clear the blocking session before relaunching. This used to just
  // re-call launch, so when the spawn was refused *because* a session was
  // already active ("You already have an active lab session"), every click
  // repeated the identical request and got the identical 400 -- the button
  // looped forever while promising it had cleared the session.
  // 404 here is fine and expected: it means there was nothing to stop, which is
  // the case for a genuinely broken spawn that left no session row.
  try {
    await axios.post('/labs/stop')
  } catch (e) {
    if (e?.response?.status !== 404) {
      spawnError.value = 'Could not stop the active lab session. Try Stop on the running exercise first.'
      return
    }
  }
  await launchWithImage(null)
}

// Breadcrumb target: when this track was opened from a course (course_id in the
// route), "back" returns to that course's exercise list -- NOT the global
// Exercises dashboard. Mirrors the course-aware navigation in the close/submit
// handlers below.
const backLink = computed(() =>
  activeCourseId.value
    ? { to: `/courses/${activeCourseId.value}`, label: 'Back to course' }
    : { to: '/exercises', label: 'Exercises' }
)
const activeWikiSlug = ref(null)

// KVM availability (true unless the track has KVM labs and the backend
// reports the host has no /dev/kvm)
const kvmAvailable = computed(() => track.value?.kvm_available !== false)

const extendingVmSession = ref(false)
const isAdminUser = computed(() => hasRole('instructor'))  // true for instructors AND admins
const canManageVms = isAdminUser

// Timer
const localTimeRemaining = ref(0)
let timerInterval = null

// Computed
const hasActiveLab = computed(() => {
  if (!track.value) return false
  return track.value.levels.some(level =>
    level.labs.some(lab => lab.is_active)
  )
})

const timeRemaining = computed(() => {
  const secs = localTimeRemaining.value
  if (secs <= 0) return '00:00:00'
  const hours = Math.floor(secs / 3600)
  const mins = Math.floor((secs % 3600) / 60)
  const s = secs % 60
  return `${String(hours).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(s).padStart(2, '0')}`
})

const hintUnlockTime = computed(() => {
  const secs = hintUnlockSeconds.value
  if (secs <= 0) return null
  const mins = Math.floor(secs / 60)
  const s = secs % 60
  return `${String(mins).padStart(2, '0')}:${String(s).padStart(2, '0')}`
})

const scenarioParagraphs = computed(() => {
  if (!activeLab.value?.lab?.scenario) return []
  return activeLab.value.lab.scenario
    .split(/\n\s*\n/)
    .map(p => p.trim())
    .filter(p => p.length > 0)
})

const isExpiringSoon = computed(() => {
  return localTimeRemaining.value > 0 && localTimeRemaining.value < 600
})

const rangeboxSessionId = computed(() => {
  return activeLab.value?.session?.id || null
})

const isRangeBoxActive = computed(() => {
  return activeLab.value?.session?.rangebox_enabled && rangeboxSessionId.value
})

// Icon mapping

// Methods
const fetchTrack = async (slug) => {
  loading.value = true
  try {
    const token = localStorage.getItem('token')
    if (!token) {
      router.push('/login')
      return
    }
    const { data } = await axios.get(`/exercises/tracks/${slug}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    track.value = data.track

    // Only set default expanded level on initial load (no levels expanded yet).
    // On refresh, preserve whatever the user had open.
    if (expandedLevels.value.length === 0) {
      const firstIncomplete = data.track.levels.find(l => !l.is_complete)
      if (firstIncomplete) {
        expandedLevels.value = [firstIncomplete.id]
      } else if (data.track.levels.length > 0) {
        expandedLevels.value = [data.track.levels[0].id]
      }
    }

    // Check for active lab
    const activeLabInTrack = data.track.levels
      .flatMap(l => l.labs)
      .find(l => l.is_active)
    if (activeLabInTrack) {
      await openActiveLab(activeLabInTrack)
    }

  } catch (error) {
    console.error('Failed to fetch track:', error)
    if (error.response?.status === 404) {
      router.push('/exercises')
    }
  } finally {
    loading.value = false
  }
}

// Visibility-gated 10s poll: pauses while the tab is hidden, refreshes
// immediately on return, and cleans itself up on unmount

const toggleLevel = (levelId) => {
  const idx = expandedLevels.value.indexOf(levelId)
  if (idx > -1) {
    expandedLevels.value.splice(idx, 1)
  } else {
    expandedLevels.value.push(levelId)
  }
}

// Resolve a lab.yaml workbook field to a wiki URL.
//   Track labs carry a fully-qualified path: "wiki/range/<slug>/CH.../page/".
//   Course-shared chapters stay bare ("CH_COURSE.../") and resolve to the
//   active course wiki. There is no fallback: an unresolvable field is a
//   misconfiguration and is surfaced, not silently routed to a stale wiki.
const workbookUrl = (wb, quiet = false) => {
  if (!wb) return null
  if (wb.startsWith('wiki/range/') || wb.startsWith('wiki/course/')) {
    return '/' + wb
  }
  if (activeWikiSlug.value) {
    return '/wiki/course/' + activeWikiSlug.value + '/' + wb
  }
  if (!quiet) {
    console.error('workbookUrl: cannot resolve workbook field (no namespace, no course context):', wb)
  }
  return null
}

// Can this workbook actually be opened from where the user is standing?
// A course-shared chapter carries a bare path and only resolves inside a
// course, so the same lab viewed from its track has no workbook to open. The
// button used to render anyway and silently do nothing on click, which is
// indistinguishable from a broken deployment: it cost a support round trip.
// Quiet, because the template calls this on every render.
const workbookOpenable = (wb) => !!workbookUrl(wb, true)

const openWorkbook = () => {
  const url = activeLab.value?.lab?.workbook && workbookUrl(activeLab.value.lab.workbook)
  if (url) {
    setWikiAuthCookie()
    window.open(url, '_blank')
  }
}

const openWorkbookForLab = (lab) => {
  const url = lab.workbook && workbookUrl(lab.workbook)
  if (url) {
    setWikiAuthCookie()
    window.open(url, '_blank')
  }
}

const openActiveLab = async (lab) => {
  try {
    const token = localStorage.getItem('token')
    const { data } = await axios.get(`/exercises/labs/${lab.id}`, {
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    })
    activeLab.value = data

    if (data.session) {
      if (data.session.time_remaining_seconds !== undefined) {
        localTimeRemaining.value = data.session.time_remaining_seconds
      } else if (data.session.duration_minutes) {
        localTimeRemaining.value = data.session.duration_minutes * 60
      } else {
        localTimeRemaining.value = 2 * 60 * 60
      }
    } else {
      localTimeRemaining.value = 0
    }

    flagInput.value = ''
    flagMessage.value = ''
    flagError.value = false
    flagSuccess.value = false
    flagStoppedSession.value = false

    if (data.lab?.requested_hints && Array.isArray(data.lab.requested_hints)) {
      receivedHints.value = data.lab.requested_hints
    } else {
      receivedHints.value = []
    }

    hintMessage.value = ''
    stopHintTimer()
    hintUnlockSeconds.value = 0

    // A live session with time left means the last launch worked and the
    // panel is showing a fresh state, so drop any stale expiry/error notices.
    // A session already at zero (backend cleanup pending) keeps the notice.
    if (data.session && (data.session.time_remaining_seconds === undefined || data.session.time_remaining_seconds > 0)) {
      sessionExpired.value = false
      spawnError.value = ''
    }

  } catch (error) {
    console.error('Failed to fetch lab details:', error)
  }
}

const closeActiveLab = () => {
  activeLab.value = null
  sessionExpired.value = false
  spawnError.value = ''
}

const viewLab = async (lab) => {
  await openActiveLab(lab)
}

const launchLab = async (lab) => {
  const trackSlug = track.value?.slug || route.params.trackSlug
  loading.value = true
  spawnError.value = ''
  sessionExpired.value = false
  startSpawnTimer()
  try {
    const { data: sp } = await axios.post(`/labs/spawn/${lab.slug}`, { rangebox: false })
    // Async spawn: wait for the session to actually reach running before opening
    // the panel, otherwise it shows a not-ready lab and never updates.
    if (sp?.session_id && sp.status !== 'running') {
      await pollSpawnStatus(sp.session_id)
    }
    await fetchTrack(route.params.trackSlug)

    const activeLabInTrack = track.value.levels
      .flatMap(l => l.labs)
      .find(l => l.slug === lab.slug)
    if (activeLabInTrack) {
      await openActiveLab(activeLabInTrack)
    }
  } catch (error) {
    console.error('Failed to launch lab:', error)
    stopSpawnTimer()
    spawnError.value = error.response?.data?.detail || error.message || 'Failed to start the lab environment.'
    // Surface the error in the panel banner; open the panel if it was not
    // already showing so the recovery actions are visible
    if (!activeLab.value) {
      await openActiveLab(lab)
    }
    if (!activeLab.value) {
      alert(spawnError.value)
    }
  } finally {
    stopSpawnTimer()
    loading.value = false
  }
}

const launchWithImage = async (image) => {
  if (!activeLab.value?.lab?.slug) return
  launchingLab.value = true
  launchingImage.value = image
  spawnError.value = ''
  sessionExpired.value = false
  startSpawnTimer()
  try {
    const body = image
      ? { rangebox: true, rangebox_image: image }
      : { rangebox: false }
    const { data: sp } = await axios.post(`/labs/spawn/${activeLab.value.lab.slug}`, body)
    if (sp?.session_id && sp.status !== 'running') {
      await pollSpawnStatus(sp.session_id)
    }
    if (image) activeRangeboxImage.value = image
    await openActiveLab({ id: activeLab.value.lab.id })
    if (track.value) {
      fetchTrack(route.params.trackSlug).catch(() => {})
    }
  } catch (error) {
    console.error('Failed to launch lab:', error)
    spawnError.value = error.response?.data?.detail || error.message || 'Failed to start the lab environment.'
  } finally {
    stopSpawnTimer()
    launchingLab.value = false
    launchingImage.value = null
  }
}

const stopLab = async () => {
  if (!confirm('Are you sure you want to stop this exercise?')) return
  loading.value = true
  try {
    await axios.post('/labs/stop')
    activeLab.value = null
    // If launched from a course, navigate back to the course page
    if (activeCourseId.value) {
      router.push(`/courses/${activeCourseId.value}`)
      return
    }
    fetchTrack(route.params.trackSlug).catch(err => console.error('Failed to refresh track:', err))
  } catch (error) {
    console.error('Failed to stop lab:', error)
  } finally {
    loading.value = false
  }
}

const extendSession = async () => {
  if (extendingSession.value) return
  extendingSession.value = true
  try {
    const { data } = await axios.post('/labs/extend')
    if (activeLab.value?.session) {
      activeLab.value.session.expires_at = data.expires_at
    }
    localTimeRemaining.value += 3600
  } catch (error) {
    console.error('Failed to extend session:', error)
    alert(error.response?.data?.detail || 'Failed to extend session')
  } finally {
    extendingSession.value = false
  }
}

const submitFlag = async () => {
  if (!flagInput.value || submittingFlag.value) return

  submittingFlag.value = true
  flagMessage.value = ''
  flagError.value = false
  flagSuccess.value = false
  flagStoppedSession.value = !!activeLab.value?.session

  try {
    const flagUrl = activeCourseId.value
      ? `/exercises/labs/${activeLab.value.lab.id}/submit-flag?course_id=${activeCourseId.value}`
      : `/exercises/labs/${activeLab.value.lab.id}/submit-flag`
    const { data } = await axios.post(flagUrl, { flag: flagInput.value })

    flagMessage.value = data.message

    if (data.correct) {
      flagSuccess.value = true
      stopHintTimer()
      // Backend auto-stops the lab on correct flag — refresh after brief delay
      setTimeout(async () => {
        if (activeCourseId.value) {
          router.push(`/courses/${activeCourseId.value}`)
        } else {
          await fetchTrack(route.params.trackSlug)
          activeLab.value = null
        }
      }, 2500)
    } else {
      flagError.value = true
    }
  } catch (error) {
    flagMessage.value = error.response?.data?.detail || 'Submission failed'
    flagError.value = true
  } finally {
    submittingFlag.value = false
  }
}

const requestHint = async () => {
  if (requestingHint.value) return
  requestingHint.value = true
  hintMessage.value = ''

  try {
    const { data } = await axios.get(`/exercises/labs/${activeLab.value.lab.id}/hint`)

    if (data.hint) {
      receivedHints.value.push({
        text: data.hint,
        number: data.hint_number || receivedHints.value.length + 1
      })
      if (data.hint_number !== undefined) activeLab.value.lab.hints_used = data.hint_number
      if (data.hints_total !== undefined) activeLab.value.lab.hints_total = data.hints_total
      if (data.hints_available !== undefined) activeLab.value.lab.hints_available = data.hints_available

      if (data.hints_remaining !== undefined && data.hints_remaining > 0) {
        hintMessage.value = ''
        stopHintTimer()
      } else if (data.next_unlock_in_seconds !== undefined) {
        hintUnlockSeconds.value = data.next_unlock_in_seconds
        hintMessage.value = `Next hint unlocks in ${hintUnlockTime.value}`
        startHintTimer()
      } else if (data.next_unlock_in_minutes) {
        hintUnlockSeconds.value = data.next_unlock_in_minutes * 60
        hintMessage.value = `Next hint unlocks in ${hintUnlockTime.value}`
        startHintTimer()
      } else {
        hintMessage.value = ''
        stopHintTimer()
      }
    } else if (data.message) {
      if (data.next_unlock_in_seconds !== undefined) {
        hintUnlockSeconds.value = data.next_unlock_in_seconds
        hintMessage.value = data.message || `Next hint unlocks in ${hintUnlockTime.value}`
        startHintTimer()
      } else if (data.next_unlock_in_minutes) {
        hintUnlockSeconds.value = data.next_unlock_in_minutes * 60
        hintMessage.value = data.message || `Next hint unlocks in ${hintUnlockTime.value}`
        startHintTimer()
      } else {
        hintMessage.value = data.message
        stopHintTimer()
        hintUnlockSeconds.value = 0
      }
      if (data.hints_available !== undefined) activeLab.value.lab.hints_available = data.hints_available
      if (data.hints_total !== undefined) activeLab.value.lab.hints_total = data.hints_total
      if (data.hints_revealed !== undefined) activeLab.value.lab.hints_used = data.hints_revealed
    } else {
      stopHintTimer()
      hintUnlockSeconds.value = 0
    }
  } catch (error) {
    console.error('Failed to get hint:', error)
    hintMessage.value = 'Failed to retrieve hint'
  } finally {
    requestingHint.value = false
  }
}

const startHintTimer = () => {
  stopHintTimer()
  if (hintUnlockSeconds.value > 0) {
    hintTimerInterval = setInterval(() => {
      if (hintUnlockSeconds.value > 0) {
        hintUnlockSeconds.value--
        if (hintUnlockTime.value) {
          hintMessage.value = `Next hint unlocks in ${hintUnlockTime.value}`
        }
      } else {
        stopHintTimer()
        hintMessage.value = ''
      }
    }, 1000)
  }
}

const stopHintTimer = () => {
  if (hintTimerInterval) {
    clearInterval(hintTimerInterval)
    hintTimerInterval = null
  }
}

// Two visibility-gated usePoll instances cover the two speeds: a 3s
// boot-progress poll that hands off to the normal 10s poll once every
// container reports ready. Both pause while the tab is hidden and clean
// themselves up on unmount.

const vmSessionExpiringSoon = (sc) => {
  if (!sc.your_session?.expires_at) return false
  const remaining = (new Date(sc.your_session.expires_at) - Date.now()) / 1000
  return remaining > 0 && remaining < 900 // 15 minutes
}

const vmSessionTimeRemaining = (sc) => {
  if (!sc.your_session?.expires_at) return ''
  const secs = Math.max(0, Math.floor((new Date(sc.your_session.expires_at) - Date.now()) / 1000))
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  const s = secs % 60
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

// Hints/scenarios use angle-bracket placeholders -- flag formats like
// OCR{...reg_<register>_val_<value>} and command templates like `nmap <target>`.
// Two markdown hazards corrupt them: (1) <register>/<target> are parsed as HTML
// tags and stripped, and (2) underscores flanking a placeholder are parsed as
// emphasis (>_val_< -> italic "val"), dropping the underscores the exact-match
// flag needs. Escape the placeholder brackets, then convert the flanking
// underscores to a numeric entity so markdown leaves them literal. The URL-safe
// char class skips autolinks (<http://...> has :// ), and the transform is
// idempotent (entities are not re-matched).
const escapePlaceholders = (text) =>
  text
    .replace(/<([A-Za-z0-9_ -]+)>/g, '&lt;$1&gt;')
    .replace(/&gt;_/g, '&gt;&#95;')
    .replace(/_&lt;/g, '&#95;&lt;')

const renderMarkdown = (text) => {
  if (!text) return ''
  return DOMPurify.sanitize(marked.parse(escapePlaceholders(text)))
}

// Render scenario text: unwrap hard-wrapped lines so they flow naturally,
// while preserving intentional paragraph breaks (double newlines)
const renderScenario = (text) => {
  if (!text) return ''
  // Split into paragraphs (double newline), unwrap single newlines within each,
  // then rejoin as paragraphs
  const unwrapped = text
    .split(/\n\s*\n/)
    .map(para => para.replace(/\n/g, ' '))
    .join('\n\n')
  return marked.parse(escapePlaceholders(unwrapped))
}

// Lifecycle
onMounted(async () => {
  const slug = route.params.trackSlug
  if (!slug) {
    router.push('/exercises')
    return
  }

  // Support deep-link to specific lab
  const labId = route.query.labId
  const courseIdParam = route.query.courseId
  if (courseIdParam) {
    activeCourseId.value = Number(courseIdParam)
  }
  const wikiSlugParam = route.query.wikiSlug
  if (wikiSlugParam) {
    activeWikiSlug.value = wikiSlugParam
  } else if (activeCourseId.value && !activeWikiSlug.value) {
    // Fetch course wiki_slug if we have a courseId but no wikiSlug param
    try {
      const token = localStorage.getItem('token')
      const { data } = await axios.get(`/courses/${activeCourseId.value}`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      })
      if (data.wiki_slug) {
        activeWikiSlug.value = data.wiki_slug
      }
    } catch (e) { /* ignore */ }
  }

  await fetchTrack(slug)

  if (labId) {
    await openActiveLab({ id: Number(labId) })
    router.replace({ path: `/exercises/${slug}` })
  }

  timerInterval = setInterval(() => {
    if (localTimeRemaining.value > 0) {
      localTimeRemaining.value--
    }
  }, 1000)
})

onUnmounted(() => {
  if (timerInterval) clearInterval(timerInterval)
  stopHintTimer()
  stopSpawnTimer()
})

// When the countdown hits zero, keep the panel open and show an explicit
// expiry notice with a relaunch action instead of silently closing it.
// Guard on an actual session so opening a session-less lab (which resets the
// countdown to zero) cannot trigger the notice.
watch(timeRemaining, (val) => {
  if (val === '00:00:00' && activeLab.value?.session) {
    activeLab.value.session = null
    sessionExpired.value = true
    fetchTrack(route.params.trackSlug)
  }
})
</script>

<style scoped>
.track-page {
  min-height: 100vh;
  padding: 2rem;
  background: var(--bg-primary);
}

.track-page--panel-open {
  padding-bottom: 75vh;
}

/* Breadcrumb */
.track-breadcrumb {
  margin-bottom: 1.5rem;
}

.breadcrumb-link {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 0.875rem;
  transition: color 0.2s ease;
}

.breadcrumb-link:hover {
  color: var(--text-primary);
}

.breadcrumb-link svg {
  width: 18px;
  height: 18px;
}

/* Track Header */
.track-header {
  padding: 1.5rem 2rem;
  background: var(--bg-secondary);
  border-radius: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.track-header__left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.track-header__icon {
  width: 48px;
  height: 48px;
  background: var(--bg-tertiary);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--track-color);
}

.track-header__icon svg {
  width: 28px;
  height: 28px;
}

.track-header__title {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 0.25rem;
}

.track-header__description {
  color: var(--text-secondary);
  font-size: 0.875rem;
}

.track-header__stats {
  display: flex;
  gap: 2rem;
}

.stat-item {
  text-align: center;
}

.stat-value {
  display: block;
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
}

.stat-label {
  font-size: 0.75rem;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Track-level VM panel */
/* Per-level compact VM status strip */
.level-vm-strip {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  margin: 0 0.5rem;
  background: rgba(30, 41, 59, 0.4);
  border: 1px solid rgba(71, 85, 105, 0.25);
  border-radius: 8px;
  flex-wrap: wrap;
}
.level-vm-strip__icon {
  width: 18px;
  height: 18px;
  color: var(--accent);
  flex-shrink: 0;
}
.level-vm-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  font-size: 0.75rem;
  background: rgba(51, 65, 85, 0.5);
  border: 1px solid rgba(71, 85, 105, 0.3);
}
.level-vm-chip__dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}
.level-vm-chip--clickable { cursor: pointer; transition: border-color 0.2s, background 0.2s; }
.level-vm-chip--clickable:hover { border-color: rgba(148, 163, 184, 0.5); background: rgba(51, 65, 85, 0.7); }
.level-vm-chip--clickable.level-vm-chip--offline:hover { border-color: rgba(34, 197, 94, 0.4); }
.level-vm-chip--clickable.level-vm-chip--ready:hover { border-color: rgba(239, 68, 68, 0.4); }
.level-vm-chip--ready .level-vm-chip__dot { background: #22c55e; }
.level-vm-chip--booting .level-vm-chip__dot { background: #f59e0b; animation: pulse 1.5s infinite; }
.level-vm-chip--offline .level-vm-chip__dot { background: #64748b; }
.level-vm-chip__name {
  font-weight: 600;
  color: var(--text-primary);
}
.level-vm-chip__state {
  color: var(--text-muted);
}
.level-vm-chip--ready .level-vm-chip__state { color: #22c55e; }
.level-vm-chip--booting .level-vm-chip__state { color: #f59e0b; }
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

/* Levels */
.levels-container {
  background: var(--bg-secondary);
  border-radius: 16px;
  padding: 1rem;
}

.level-section {
  margin-bottom: 0.5rem;
  border-radius: 8px;
  overflow: hidden;
  background: var(--bg-primary);
}

.level-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  cursor: pointer;
  transition: background 0.2s ease;
}

.level-header:hover {
  background: var(--bg-tertiary);
}

.level-header__left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.level-number {
  width: 36px;
  height: 36px;
  background: var(--bg-tertiary);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  color: var(--text-primary);
}

.level-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.125rem;
}

.level-description {
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.level-header__right {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.level-progress {
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.level-progress-ring {
  width: 36px;
  height: 36px;
}

.level-progress-ring svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.ring-bg {
  fill: none;
  stroke: var(--bg-tertiary);
  stroke-width: 3;
}

.ring-fill {
  fill: none;
  stroke: var(--track-color, #22c55e);
  stroke-width: 3;
  stroke-linecap: round;
  transition: stroke-dasharray 0.3s ease;
}

.level-progress-ring--complete .ring-fill {
  stroke: var(--success);
}

.level-progress-ring--complete .ring-bg {
  fill: rgba(34, 197, 94, 0.1);
}

.level-chevron {
  width: 20px;
  height: 20px;
  color: var(--text-secondary);
  transition: transform 0.2s ease;
}

.level-section--expanded .level-chevron {
  transform: rotate(180deg);
}

/* Labs List */
.labs-list {
  border-top: 1px solid var(--border-color);
}

.lab-row {
  display: flex;
  align-items: center;
  padding: 1rem 1.5rem;
  gap: 1rem;
  border-bottom: 1px solid var(--border-color);
  transition: background 0.2s ease;
}

.lab-row:last-child {
  border-bottom: none;
}

.lab-row:hover {
  background: rgba(255, 255, 255, 0.02);
}

.lab-row--current {
  background: rgba(34, 197, 94, 0.05);
  border-left: 3px solid var(--success);
}

.lab-row--active {
  background: var(--accent-bg);
  border-left: 3px solid var(--accent);
}

.lab-row--locked {
  opacity: 0.5;
}

.lab-row__status {
  flex-shrink: 0;
}

.status-icon {
  width: 24px;
  height: 24px;
}

.status-icon--active { color: var(--accent); }
.status-icon--current { color: var(--warning); }
.status-icon--locked { color: var(--text-muted); }
.status-icon--available { color: var(--text-secondary); }

.status-bar {
  display: inline-block;
  width: 4px;
  height: 20px;
  border-radius: 2px;
}

.status-bar--completed {
  background: var(--success);
}

.lab-row--completed {
  border-left: 3px solid var(--success);
  background: rgba(34, 197, 94, 0.05);
  opacity: 1;
}

.lab-row--completed .lab-row__title {
  text-decoration: line-through;
  text-decoration-color: rgba(34, 197, 94, 0.4);
  color: var(--text-secondary);
}
.kvm-badge {
  display: inline-block;
  font-size: 0.6rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
  margin-left: 0.5rem;
}

.drill-badge {
  display: inline-block;
  font-size: 0.6rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  margin-left: 0.5rem;
  vertical-align: middle;
  position: relative;
  top: -1px;
}

.lab-row__content {
  flex: 1;
}

.lab-row__title {
  font-size: 0.9375rem;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 0.25rem;
}

.lab-row__scenario-brief {
  color: var(--text-secondary);
  font-size: 0.875rem;
  margin-top: 0.25rem;
  margin-bottom: 0.5rem;
  line-height: 1.4;
}

.lab-row__meta {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.lab-difficulty {
  font-size: 0.75rem;
  padding: 0.125rem 0.5rem;
  border-radius: 4px;
  font-weight: 500;
}

.lab-difficulty--beginner { background: #166534; color: #bbf7d0; }
.lab-difficulty--intermediate { background: #854d0e; color: #fef08a; }
.lab-difficulty--advanced { background: #991b1b; color: #fecaca; }

.lab-duration {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.lab-duration svg {
  width: 14px;
  height: 14px;
}

.lab-tool {
  font-size: 0.75rem;
  color: var(--text-muted);
  background: var(--bg-tertiary);
  padding: 0.125rem 0.5rem;
  border-radius: 4px;
}

.lab-row__actions {
  display: flex;
  gap: 0.75rem;
  flex-shrink: 0;
}

.locked-text {
  font-size: 0.75rem;
  color: var(--text-muted);
}

/* Buttons */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-weight: 500;
  font-size: 0.875rem;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn--sm {
  padding: 0.375rem 0.75rem;
  font-size: 0.8125rem;
}

.btn--primary {
  background: var(--accent);
  color: white;
}

.btn--primary:hover:not(:disabled) {
  background: #2563eb;
}

.btn--secondary {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.btn--secondary:hover:not(:disabled) {
  background: var(--nav-label);
}

.btn--danger {
  background: var(--danger);
  color: white;
}

.btn--danger:hover:not(:disabled) {
  background: #dc2626;
}

.btn--workbook {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: #e67e22;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s, transform 0.1s;
  width: 100%;
  justify-content: center;
}

.btn--workbook:disabled,
.btn--workbook:disabled:hover {
  background: var(--bg-tertiary, #2a3142);
  color: var(--text-muted, #8892a4);
  cursor: not-allowed;
}

.workbook-hint--unavailable {
  color: #fbbf24;
}

.btn--workbook:hover {
  background: #d35400;
  transform: translateY(-1px);
}

.btn--workbook:active {
  transform: translateY(0);
}

.btn--workbook .btn-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.btn--workbook .btn-icon--external {
  width: 14px;
  height: 14px;
  opacity: 0.7;
}

.workbook-hint {
  color: var(--text-secondary);
  font-size: 0.85rem;
  margin-bottom: 12px;
}

.workbook-btn-row {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.workbook-btn-row .btn-icon {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.btn--workbook-sm {
  background: #e67e22 !important;
  color: white !important;
  border: none;
}

.btn--workbook-sm:hover {
  background: #d35400 !important;
}

/* Active Lab Panel */
.active-lab-panel {
  position: fixed;
  bottom: 0;
  left: 250px;
  right: 0;
  max-height: 70vh;
  background: var(--bg-secondary);
  border-top: 1px solid var(--border-color);
  border-radius: 16px 16px 0 0;
  box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.3);
  z-index: 100;
  overflow-y: auto;
}

.active-lab-panel__header {
  position: sticky;
  top: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.5rem;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  z-index: 10;
}

.active-lab-panel__title-group {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.active-lab-panel__title-group h2 {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
}

.active-badge {
  background: var(--accent);
  color: white;
  font-size: 0.75rem;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-weight: 500;
}

.completed-badge {
  background: var(--success);
  color: white;
  font-size: 0.75rem;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-weight: 500;
}

.active-lab-panel__timer-section {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.active-lab-panel__timer {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.25rem;
  font-weight: 700;
  font-family: monospace;
  color: var(--success);
}

.active-lab-panel__timer svg {
  width: 20px;
  height: 20px;
}

.timer--warning {
  color: var(--danger);
  animation: pulse 1s infinite;
}

.extend-btn {
  font-size: 0.875rem;
  padding: 0.25rem 0.75rem;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.close-btn {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 0.5rem;
}

.close-btn svg {
  width: 24px;
  height: 24px;
}

.active-lab-panel__body {
  padding: 1.5rem;
}

.active-lab-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.5rem;
}

.panel-section {
  background: var(--bg-primary);
  border-radius: 8px;
  padding: 1rem;
}

.panel-section--full {
  grid-column: 1 / span 2;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 1rem;
}

.section-title svg {
  width: 18px;
  height: 18px;
}

.objectives-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.objectives-list li {
  position: relative;
  padding-left: 1.5rem;
  margin-bottom: 0.5rem;
  color: var(--text-primary);
  font-size: 0.9375rem;
}

.objectives-list li::before {
  content: '\25CB';
  position: absolute;
  left: 0;
  color: var(--text-secondary);
}

.panel-section--scenario {
  grid-column: 1 / -1;
  background: var(--bg-primary);
  border-left: 4px solid var(--accent);
}








.scenario-content {
  color: var(--text-primary);
  line-height: 1.6;
  font-size: 0.9375rem;
}

.scenario-content :deep(p) { margin: 0 0 1rem 0; }
.scenario-content :deep(p:last-child) { margin-bottom: 0; }

.scenario-content :deep(pre) {
  background: #1e1e1e;
  padding: 12px;
  border-radius: 4px;
  overflow-x: auto;
  margin: 12px 0;
}

.scenario-content :deep(code) {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  background: #1e1e1e;
  padding: 2px 6px;
  border-radius: 3px;
  color: #d4d4d4;
}

.scenario-content :deep(pre code) { background: transparent; padding: 0; }
.scenario-content :deep(strong) { color: #93c5fd; font-weight: 600; }
.scenario-content :deep(ul), .scenario-content :deep(ol) { margin: 0.75rem 0; padding-left: 1.5rem; }
.scenario-content :deep(li) { margin-bottom: 0.5rem; }
.scenario-content :deep(li:last-child) { margin-bottom: 0; }
.scenario-content :deep(h1), .scenario-content :deep(h2), .scenario-content :deep(h3) {
  color: var(--text-primary);
  margin: 1rem 0 0.5rem 0;
}
.scenario-content :deep(table) { border-collapse: collapse; width: 100%; margin: 0.75rem 0; }
.scenario-content :deep(th), .scenario-content :deep(td) { border: 1px solid var(--border-color); padding: 0.5rem 0.75rem; text-align: left; }
.scenario-content :deep(th) { background: var(--bg-tertiary); font-weight: 600; }

.network-info {
  font-size: 0.875rem;
}

.network-info--prominent {
  background: var(--bg-secondary);
  padding: 0.75rem 1rem;
  border-radius: 6px;
  margin-bottom: 0.5rem;
}

.network-label {
  color: var(--text-secondary);
}

.network-value {
  color: var(--success);
  font-family: monospace;
  font-weight: 600;
  font-size: 1rem;
}

.network-hint {
  font-size: 0.8rem;
  color: var(--text-secondary);
  margin: 0;
  font-style: italic;
}

.target-ips {
  margin-top: 0.5rem;
}
.target-ips-heading {
  font-size: 0.8rem;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 0.375rem;
}
.target-ip-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.target-ip-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: 0.4rem 0.75rem;
  background: var(--bg-secondary);
  border-radius: 4px;
  font-size: 0.875rem;
}
.target-ip-label {
  color: var(--text-secondary);
  margin-right: 0.75rem;
}
.target-ip-value {
  color: var(--success);
  font-family: monospace;
  font-weight: 600;
}

/* ICS Techniques (ATT&CK for ICS) */
.ics-tech-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.ics-tech-chip {
  display: inline-flex;
  flex-direction: column;
  gap: 0.15rem;
  padding: 0.35rem 0.65rem;
  border-radius: 8px;
  font-size: 0.8125rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-left: 3px solid var(--accent);
  cursor: default;
}
.ics-tech-chip__tactic {
  font-size: 0.625rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
}
.ics-tech-chip__label {
  display: inline-flex;
  align-items: baseline;
  gap: 0.35rem;
}
.ics-tech-chip__id {
  font-family: monospace;
  font-weight: 700;
  color: var(--accent);
}
.ics-tech-chip__name {
  color: var(--text-primary);
}
/* Tactic accent colors (left border + tactic label tint) */
.ics-tech-chip--initial-access { border-left-color: #60a5fa; }
.ics-tech-chip--initial-access .ics-tech-chip__tactic { color: #60a5fa; }
.ics-tech-chip--execution { border-left-color: #a78bfa; }
.ics-tech-chip--execution .ics-tech-chip__tactic { color: #a78bfa; }
.ics-tech-chip--persistence { border-left-color: #34d399; }
.ics-tech-chip--persistence .ics-tech-chip__tactic { color: #34d399; }
.ics-tech-chip--privilege-escalation { border-left-color: #fbbf24; }
.ics-tech-chip--privilege-escalation .ics-tech-chip__tactic { color: #fbbf24; }
.ics-tech-chip--evasion { border-left-color: #94a3b8; }
.ics-tech-chip--evasion .ics-tech-chip__tactic { color: #94a3b8; }
.ics-tech-chip--discovery { border-left-color: #22d3ee; }
.ics-tech-chip--discovery .ics-tech-chip__tactic { color: #22d3ee; }
.ics-tech-chip--lateral-movement { border-left-color: #818cf8; }
.ics-tech-chip--lateral-movement .ics-tech-chip__tactic { color: #818cf8; }
.ics-tech-chip--collection { border-left-color: #2dd4bf; }
.ics-tech-chip--collection .ics-tech-chip__tactic { color: #2dd4bf; }
.ics-tech-chip--command-and-control { border-left-color: #f472b6; }
.ics-tech-chip--command-and-control .ics-tech-chip__tactic { color: #f472b6; }
.ics-tech-chip--inhibit-response-function { border-left-color: #fb923c; }
.ics-tech-chip--inhibit-response-function .ics-tech-chip__tactic { color: #fb923c; }
.ics-tech-chip--impair-process-control { border-left-color: #f87171; }
.ics-tech-chip--impair-process-control .ics-tech-chip__tactic { color: #f87171; }
.ics-tech-chip--impact { border-left-color: #ef4444; }
.ics-tech-chip--impact .ics-tech-chip__tactic { color: #ef4444; }

.hosts-file-hint {
  font-size: 0.8rem;
  color: var(--text-secondary);
  margin: 0 0 0.5rem 0;
}

/* Flag Form */
.flag-form {
  display: flex;
  gap: 0.5rem;
}

.flag-input {
  flex: 1;
  background: var(--bg-secondary);
  border: 2px solid var(--border-color);
  border-radius: 6px;
  padding: 0.75rem 1rem;
  color: var(--text-primary);
  font-family: monospace;
  font-size: 1rem;
}

.flag-input:focus {
  outline: none;
  border-color: var(--accent);
}

.flag-input--error { border-color: var(--danger); }
.flag-input--success { border-color: var(--success); }

.flag-message {
  margin-top: 0.75rem;
  font-size: 0.875rem;
}

.flag-message--success { color: var(--success); }
.flag-message--error { color: var(--danger); }

/* Hints */
.hint-count {
  font-weight: 400;
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-left: 0.5rem;
}

.hint-box {
  background: var(--bg-secondary);
  border-left: 3px solid var(--warning);
  padding: 1rem;
  margin-bottom: 1rem;
  border-radius: 0 6px 6px 0;
  line-height: 1.6;
  color: var(--text-primary);
}

.hint-number {
  font-weight: 600;
  color: var(--warning);
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.hint-box p { color: var(--text-primary); margin: 0 0 0.75rem 0; }
.hint-box p:last-child { margin-bottom: 0; }

.hint-box pre {
  background: #1e1e1e;
  padding: 12px;
  border-radius: 4px;
  overflow-x: auto;
  margin: 12px 0;
}

.hint-box code {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  background: #1e1e1e;
  padding: 2px 6px;
  border-radius: 3px;
  color: #d4d4d4;
}

.hint-box pre code { background: transparent; padding: 0; }
.hint-box strong { color: var(--warning); font-weight: 600; }
.hint-box ul, .hint-box ol { margin: 0.75rem 0; padding-left: 1.5rem; }
.hint-box li { margin-bottom: 0.5rem; color: var(--text-primary); }
.hint-box li:last-child { margin-bottom: 0; }

.hint-message {
  background: rgba(245, 158, 11, 0.1);
  border-left: 3px solid var(--warning);
  padding: 0.75rem 1rem;
  margin-bottom: 1rem;
  border-radius: 0 4px 4px 0;
  color: var(--warning);
  font-size: 0.875rem;
}

.no-hints {
  color: var(--text-muted);
  font-style: italic;
  font-size: 0.875rem;
}

/* VM Card — Student Target Machine */
.vm-card {
  padding: 0.875rem 1rem;
  background: var(--bg-secondary);
  border-radius: 8px;
  margin-bottom: 0.5rem;
}
.vm-card:last-child { margin-bottom: 0; }

.vm-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.25rem;
}

.vm-card__name {
  font-weight: 600;
  font-size: 0.9375rem;
  color: var(--text-primary);
}

.vm-card__status-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.vm-card__status {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.8125rem;
  font-weight: 600;
}

.vm-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-muted);
}

.vm-card__status--ready .vm-status-dot {
  background: var(--success);
  box-shadow: 0 0 6px rgba(34, 197, 94, 0.5);
}
.vm-card__status--ready { color: var(--success); }

.vm-card__status--booting .vm-status-dot {
  background: var(--warning);
  animation: pulse 1.5s infinite;
}
.vm-card__status--booting { color: var(--warning); }

.vm-card__status--stopped .vm-status-dot { background: var(--text-muted); }
.vm-card__status--stopped { color: var(--text-muted); }

.vm-online-badge {
  font-size: 0.7rem;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
}

.vm-card__boot-msg {
  margin: 0.375rem 0 0.25rem;
  font-size: 0.8rem;
  color: var(--text-secondary);
  font-style: italic;
}

.vm-card__timer {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.375rem;
  font-size: 0.8rem;
  color: var(--text-secondary);
  font-family: monospace;
}
.vm-card__timer--warning { color: var(--warning, #f59e0b); }

.vm-card__actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

/* Legacy (keep for admin view compatibility) */
.vm-users-toggle {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 0.75rem;
  cursor: pointer;
  padding: 0;
  text-decoration: underline;
}

.vm-users-list {
  list-style: none;
  padding: 0;
  margin: 0.25rem 0 0;
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.vm-users-list li {
  padding: 0.15rem 0;
}

.reboot-banner {
  background: var(--bg-tertiary);
  border: 1px solid var(--warning, #f59e0b);
  border-radius: 0.5rem;
  padding: 0.75rem 1rem;
  margin-top: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.reboot-banner__text {
  font-size: 0.85rem;
  color: var(--text-primary);
}

.reboot-banner__actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.reboot-status {
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.btn--xs {
  padding: 0.15rem 0.4rem;
  font-size: 0.7rem;
}

/* Keyboard focus for the clickable rows and chips */
.level-header:focus-visible,
.lab-row:focus-visible,
.level-vm-chip--clickable:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: -2px;
}

/* Panel banners: session expiry + errored session recovery */
.panel-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
  padding: 0.75rem 1.5rem;
  border-bottom: 1px solid var(--border-color);
  font-size: 0.875rem;
}

.panel-banner__text {
  color: var(--text-primary);
  line-height: 1.5;
}

.panel-banner__text strong {
  margin-right: 0.35rem;
}

.panel-banner__actions {
  display: flex;
  gap: 0.5rem;
  flex-shrink: 0;
}

.panel-banner--expired {
  background: rgba(245, 158, 11, 0.1);
  border-left: 4px solid var(--warning, #f59e0b);
}

.panel-banner--expired strong {
  color: var(--warning, #f59e0b);
}

.panel-banner--error {
  background: rgba(239, 68, 68, 0.1);
  border-left: 4px solid var(--danger, #ef4444);
}

.panel-banner--error strong {
  color: var(--danger, #ef4444);
}

/* Flag guidance + auto-stop warning */
.flag-guidance {
  margin-top: 0.75rem;
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.flag-guidance code {
  font-family: monospace;
  background: var(--bg-secondary);
  padding: 0.1rem 0.35rem;
  border-radius: 4px;
  color: var(--text-primary);
}

.flag-autostop-warning {
  margin-top: 0.5rem;
  padding: 0.6rem 0.85rem;
  font-size: 0.8125rem;
  color: var(--warning, #f59e0b);
  background: rgba(245, 158, 11, 0.08);
  border-left: 3px solid var(--warning, #f59e0b);
  border-radius: 0 4px 4px 0;
}

/* Loading */
.loading-overlay {
  position: fixed;
  inset: 0;
  background: rgba(3, 7, 18, 0.82);
  backdrop-filter: blur(3px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
}

/* Solid card so the page text underneath can never bleed through and overlap the
   status text -- the box was fully transparent, which made this unreadable. */
.loading-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  max-width: 360px;
  padding: 1.75rem 2rem;
  text-align: center;
  background: var(--bg-secondary, #111827);
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.12));
  border-radius: 14px;
  box-shadow: 0 24px 60px -20px rgba(0, 0, 0, 0.7);
}

.loading-box__status {
  margin: 0;
  font-size: 0.9375rem;
  font-weight: 600;
  font-family: monospace;
  color: #ffffff;
}

.loading-box__note {
  margin: 0;
  font-size: 0.8125rem;
  line-height: 1.5;
  color: rgba(255, 255, 255, 0.75);
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--bg-tertiary);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Transitions */
.slide-enter-active,
.slide-leave-active {
  transition: all 0.3s ease;
}

.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  max-height: 0;
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.3s ease;
}

.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(100%);
}

/* Responsive */
@media (max-width: 768px) {
  .track-page {
    padding: 1rem;
  }

  .track-header {
    flex-direction: column;
    text-align: center;
  }

  .track-header__left {
    flex-direction: column;
    align-items: center;
  }

  .track-header__stats {
    justify-content: center;
  }

  .active-lab-panel {
    left: 0;
  }

  .active-lab-grid {
    grid-template-columns: 1fr;
  }

  .lab-row {
    flex-wrap: wrap;
  }

  .lab-row__actions {
    display: flex;
    gap: 0.75rem;
    width: 100%;
    margin-top: 0.5rem;
  }
}

/* Launch buttons row in header */
.launch-buttons {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

/* RangeBox launch bar (moved to VPN connection page) */
.rangebox-launch-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.65rem 1rem;
  background: rgba(92, 184, 92, 0.08);
  border: 1px solid rgba(92, 184, 92, 0.25);
  border-radius: 8px;
  margin-bottom: 1rem;
}

.rangebox-launch-bar__label {
  font-size: 0.85rem;
  color: #5cb85c;
  font-weight: 500;
}
</style>

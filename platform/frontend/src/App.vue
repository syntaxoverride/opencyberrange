<template>
  <div id="app" class="app-root" :class="{ 'app-root--impersonating': isImpersonating }">
    <!-- Impersonation Banner -->
    <ImpersonationBanner />

    <!-- Theme Toggle (global) -->
    <button @click="toggleTheme" class="theme-toggle" :title="isDark ? 'Switch to light mode' : 'Switch to dark mode'">
      <svg v-if="isDark" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
      </svg>
      <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
      </svg>
    </button>

    <!-- Sidebar Layout (authenticated) -->
    <template v-if="isAuthenticated">
      <AppSidebar
        :collapsed="sidebarCollapsed"
        :user-role="userRole"
        :username="username"
        @toggle="sidebarCollapsed = !sidebarCollapsed"
        @logout="logout"
      />
      <main class="main-content">
        <router-view :key="authState.token || 'guest'" />
      </main>
      <GuidedTour v-model="showTour" :steps="tourSteps" @finish="onTourFinish" />
    </template>

    <!-- Guest (no sidebar) -->
    <main v-else class="main-content main-content--guest">
      <router-view :key="'guest'" />
    </main>
  </div>
</template>

<script setup>
import { computed, ref, watch, onMounted, onUnmounted, provide } from 'vue'
import { useRouter } from 'vue-router'
import AppSidebar from './components/AppSidebar.vue'
import GuidedTour from './components/GuidedTour.vue'
import ImpersonationBanner from './components/ImpersonationBanner.vue'
import { useTheme } from './composables/useTheme'
import { useModules } from './composables/useModules'
import { setWikiAuthCookie } from './utils/wikiAuth'
import { useImpersonation } from './composables/useImpersonation'

const router = useRouter()
const { isDark, toggleTheme } = useTheme()
const { fetchModules, isModuleEnabled, resetModules } = useModules()
const { isImpersonating } = useImpersonation()

const sidebarCollapsed = ref(false)

// Reactive state to track auth changes - this ensures Vue reactivity works
const authState = ref({
  token: localStorage.getItem('token'),
  user: localStorage.getItem('user')
})

// Update auth state from localStorage - this function is exposed for external updates
const updateAuthState = () => {
  authState.value = {
    token: localStorage.getItem('token'),
    user: localStorage.getItem('user')
  }
}

// Provide updateAuthState and module helpers to child components
provide('updateAuthState', updateAuthState)
provide('isModuleEnabled', isModuleEnabled)
provide('isImpersonating', isImpersonating)

// Listen for storage events (cross-tab sync)
let storageListener = null
// Keep the wiki_auth cookie in sync with the current JWT so nginx auth_request
// gates (wikis and the SO console) always have a valid token. Scope logic is in
// the shared helper.
const refreshWikiAuthCookie = () => setWikiAuthCookie()

onMounted(() => {
  storageListener = () => { updateAuthState(); refreshWikiAuthCookie() }
  window.addEventListener('storage', storageListener)
  // Initial update
  updateAuthState()
  refreshWikiAuthCookie()
  // Fetch module status if authenticated
  if (authState.value.token) {
    fetchModules()
    maybeStartTour()
  }
})

onUnmounted(() => {
  if (storageListener) {
    window.removeEventListener('storage', storageListener)
  }
})

const isAuthenticated = computed(() => {
  return !!authState.value.token
})

const userRole = computed(() => {
  try {
    const user = JSON.parse(authState.value.user || '{}')
    return user.role || (user.is_admin ? 'admin' : 'student')
  } catch {
    return 'student'
  }
})

const username = computed(() => {
  try {
    const user = JSON.parse(authState.value.user || '{}')
    return user.username || 'User'
  } catch {
    return 'User'
  }
})

// ---- First-time-use orientation tour ----
const showTour = ref(false)
const currentUserId = computed(() => {
  try { const u = JSON.parse(authState.value.user || '{}'); return u.id ?? null } catch { return null }
})
const tourKey = computed(() => 'ocr_orientation_seen_v1_' + (currentUserId.value ?? 'anon'))
const tourSteps = [
  { title: 'Welcome to the range', body: 'Here is a quick tour to get you from zero to your first running lab. It takes under a minute.', placement: 'center' },
  { title: '1. Connect over the VPN', body: 'Most labs run on an isolated network you reach over a VPN. Open VPN Setup to download your config and connect. You only do this once.', selector: '[data-tour="nav-vpn"]' },
  { title: '2. Or skip the VPN with RangeBox', body: 'No local setup? When you start a lab you can launch it with RangeBox instead, a full Kali attack box right in your browser, with nothing to install.', placement: 'center' },
  { title: '3. Find your exercises', body: 'Your labs live under Exercises, grouped into tracks by skill. Courses holds any work an instructor has assigned you.', selector: '[data-tour="nav-exercises"]' },
  { title: '4. Start your first lab', body: 'Open a track, pick an exercise, and click Launch or Start Exercise. Choose the VPN or a RangeBox when it starts, and your step-by-step workbook opens right alongside.', route: '/exercises', selector: '.track-grid .track-card' },
  { title: 'You are set', body: 'That is the whole loop: connect, launch, follow the workbook. You can replay this tour anytime from the sidebar menu. Have fun.', placement: 'center', route: '/exercises' },
]
function maybeStartTour() {
  if (!authState.value.token || userRole.value === 'admin') return
  if (localStorage.getItem(tourKey.value)) return
  setTimeout(() => { if (isAuthenticated.value && userRole.value !== 'admin') showTour.value = true }, 900)
}
function onTourFinish() {
  try { localStorage.setItem(tourKey.value, '1') } catch (e) { /* private mode */ }
  showTour.value = false
}
function startTour() { showTour.value = true }
provide('startTour', startTour)
watch(() => authState.value.token, (t, old) => { if (t && !old) maybeStartTour() })

const logout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  updateAuthState() // Update reactive state immediately
  resetModules()
  router.push('/login')
}

// Expose updateAuthState globally for Login.vue to call
// This ensures immediate reactivity when login happens
if (typeof window !== 'undefined') {
  window.__updateAuthState = updateAuthState
}
</script>

<style>
/* Global CSS Variables - Dark (default) */
:root {
  --bg-primary: #0f172a;
  --bg-secondary: #1e293b;
  --bg-tertiary: #334155;
  --text-primary: #f8fafc;
  --text-secondary: #94a3b8;
  --text-muted: #64748b;
  --border-color: #334155;
  --accent: #3b82f6;
  --success: #22c55e;
  --warning: #f59e0b;
  --danger: #ef4444;
  --nav-label: #475569;
  --hover-bg: rgba(51, 65, 85, 0.5);
  --hover-text: #f1f5f9;
  --accent-bg: rgba(59, 130, 246, 0.1);
  --danger-bg: rgba(239, 68, 68, 0.1);
  --purple: #8b5cf6;
  --success-bg: rgba(34, 197, 94, 0.15);
  --warning-bg: rgba(245, 158, 11, 0.15);
  --panel-bg: #1e293b;
}

/* Light theme overrides */
[data-theme="light"] {
  --bg-primary: #ffffff;
  --bg-secondary: #f1f5f9;
  --bg-tertiary: #e2e8f0;
  --text-primary: #0f172a;
  --text-secondary: #475569;
  --text-muted: #94a3b8;
  --border-color: #cbd5e1;
  --accent: #2563eb;
  --success: #16a34a;
  --warning: #d97706;
  --danger: #dc2626;
  --nav-label: #94a3b8;
  --hover-bg: rgba(0, 0, 0, 0.05);
  --hover-text: #0f172a;
  --accent-bg: rgba(59, 130, 246, 0.1);
  --danger-bg: rgba(239, 68, 68, 0.1);
  --purple: #7c3aed;
  --success-bg: rgba(22, 163, 74, 0.12);
  --warning-bg: rgba(217, 119, 6, 0.12);
  --panel-bg: #ffffff;
}

/* Global Styles */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--bg-primary);
  color: var(--text-primary);
  line-height: 1.6;
}

/* Global button system. Views that define their own scoped .btn win by
   specificity; nested components that use .btn without a local definition fall
   back to this instead of rendering as raw browser buttons. */
.btn {
  display: inline-flex; align-items: center; justify-content: center; gap: 0.5rem;
  padding: 0.5rem 1rem; border: none; border-radius: 6px;
  font-family: inherit; font-size: 0.8125rem; font-weight: 500;
  cursor: pointer; text-decoration: none; transition: all 0.15s;
}
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn--primary { background: var(--accent); color: #fff; }
.btn--primary:hover:not(:disabled) { background: #2563eb; }
.btn--secondary { background: var(--bg-tertiary); color: var(--text-secondary); border: 1px solid var(--border-color); }
.btn--secondary:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
.btn--success { background: var(--success); color: #fff; }
.btn--success:hover:not(:disabled) { background: #16a34a; }
.btn--danger { background: transparent; border: 1px solid var(--danger); color: var(--danger); }
.btn--danger:hover:not(:disabled) { background: rgba(239, 68, 68, 0.1); }
.btn--outline { background: transparent; border: 1px solid var(--border-color); color: var(--text-secondary); }
.btn--outline:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
.btn--sm { padding: 0.375rem 0.75rem; font-size: 0.75rem; }
.btn--xs { padding: 0.25rem 0.5rem; font-size: 0.6875rem; }

/* App layout: sidebar + content */
.app-root {
  display: flex;
  min-height: 100vh;
}

/* Offset for impersonation banner */
.app-root--impersonating {
  padding-top: 44px;
}

.main-content {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  min-height: 100vh;
}

.main-content--guest {
  width: 100%;
}

/* Theme toggle */
.theme-toggle {
  position: fixed;
  top: 1rem;
  right: 1rem;
  z-index: 200;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}

.theme-toggle svg {
  width: 18px;
  height: 18px;
}

.theme-toggle:hover {
  color: var(--text-primary);
  border-color: var(--accent);
  background: var(--hover-bg);
}

/* Responsive */
@media (max-width: 768px) {
  .app-root {
    flex-direction: column;
  }
}
</style>

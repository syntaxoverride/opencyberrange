<template>
  <div class="profile-page">
    <div class="profile-container">
      <h1 class="page-title">My Profile</h1>

      <div v-if="loading" class="loading-message">Loading profile information...</div>

      <div v-else-if="user" class="profile-content">
        <!-- Account Information Section -->
        <div class="profile-section">
          <h2 class="section-title">Account Information</h2>
          
          <div class="info-grid">
            <div class="info-item">
              <label class="info-label">Username</label>
              <div class="info-value">{{ user.username }}</div>
            </div>

            <div class="info-item">
              <label class="info-label">Email</label>
              <div class="info-value">{{ user.email }}</div>
            </div>

            <div class="info-item">
              <label class="info-label">Account Status</label>
              <div class="info-value">
                <span v-if="user.is_approved" class="status-badge status-badge--approved">Approved</span>
                <span v-else class="status-badge status-badge--pending">Pending Approval</span>
              </div>
            </div>

            <div class="info-item">
              <label class="info-label">Account Active</label>
              <div class="info-value">
                <span v-if="user.is_active !== false" class="status-badge status-badge--active">Active</span>
                <span v-else class="status-badge status-badge--inactive">Inactive</span>
              </div>
            </div>

            <div class="info-item" v-if="user.created_at">
              <label class="info-label">Registration Date</label>
              <div class="info-value">{{ formatDate(user.created_at) }}</div>
            </div>

            <div class="info-item">
              <label class="info-label">VPN Registered</label>
              <div class="info-value">
                <!-- Use shared composable logic - same as Dashboard -->
                <span v-if="isVpnRegistered()" class="status-badge status-badge--vpn">Yes</span>
                <span v-else class="status-badge status-badge--no-vpn">No</span>
              </div>
            </div>

            <div class="info-item">
              <label class="info-label">Role</label>
              <div class="info-value">
                <span v-if="user.role === 'admin'" class="status-badge status-badge--admin">Admin</span>
                <span v-else-if="user.role === 'instructor'" class="status-badge status-badge--instructor">Instructor</span>
                <span v-else class="status-badge status-badge--user">Student</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Exercise Studio LLM connections (instructor/admin, editions that ship Studio) -->
        <div class="profile-section" v-if="isInstructor && exerciseAuthoring">
          <h2 class="section-title">Exercise Studio</h2>
          <label class="info-label">LLM provider connections</label>
          <p class="help-text" style="margin: 0.35rem 0 0.85rem;">
            Connect a model to generate exercises. Add more than one and pick a default; the one marked Default is used unless you choose another at generation time. Keys are stored encrypted and never shown again.
          </p>

          <!-- Saved profiles -->
          <div v-if="llm.profiles.length" class="llm-list">
            <div v-for="p in llm.profiles" :key="p.id" class="llm-row">
              <div class="llm-row__main">
                <span class="llm-row__label">{{ p.label }}</span>
                <span class="llm-row__meta">{{ providerLabel(p.provider) }} : {{ p.model || 'default model' }}</span>
                <span v-if="p.base_url" class="llm-row__meta llm-row__url">{{ p.base_url }}</span>
              </div>
              <div class="llm-row__actions">
                <span v-if="p.is_default" class="status-badge status-badge--approved">Default</span>
                <button v-else class="btn btn--secondary btn--sm" @click="makeDefault(p.id)">Make default</button>
                <button class="btn btn--ghost-danger btn--sm" @click="removeProfile(p.id)">Remove</button>
              </div>
            </div>
          </div>
          <p v-else class="help-text" style="margin: 0 0 0.85rem;">No connections yet. Add one below.</p>

          <!-- Add a connection -->
          <div class="llm-add">
            <div class="llm-field">
              <label class="info-label">Provider</label>
              <select aria-label="Provider" v-model="llm.form.provider" class="form-input" @change="onProviderChange">
                <option v-for="c in llm.catalog" :key="c.id" :value="c.id">{{ c.label }}</option>
              </select>
            </div>
            <div class="llm-field" v-if="currentSpec && currentSpec.fields.includes('base_url')">
              <label class="info-label">Endpoint URL</label>
              <input aria-label="Endpoint URL" v-model="llm.form.base_url" type="text" class="form-input" :placeholder="currentSpec.base_url_hint || 'https://...'" />
            </div>
            <div class="llm-field" v-if="currentSpec && currentSpec.fields.includes('api_key')">
              <label class="info-label">API key <span v-if="!currentSpec.needs_key" class="help-text">(optional)</span></label>
              <input v-model="llm.form.api_key" type="password" class="form-input" :placeholder="currentSpec.key_hint || ''" autocomplete="off" />
            </div>
            <div class="llm-field" v-if="currentSpec && currentSpec.fields.includes('model')">
              <label class="info-label">Model</label>
              <input aria-label="Model" v-if="!(currentSpec.models && currentSpec.models.length)" v-model="llm.form.model" type="text" class="form-input" :placeholder="currentSpec.model_hint || currentSpec.default_model || ''" />
              <select v-else v-model="llm.form.model" class="form-input">
                <option v-for="m in currentSpec.models" :key="m" :value="m">{{ m }}</option>
              </select>
            </div>
            <div class="llm-field">
              <label class="info-label">Label <span class="help-text">(optional)</span></label>
              <input v-model="llm.form.label" type="text" class="form-input" placeholder="e.g. My Provider, Lab Ollama" />
            </div>
            <div class="llm-actions">
              <button class="btn btn--secondary" :disabled="llm.testing || llm.saving" @click="testConnection">
                {{ llm.testing ? 'Testing...' : 'Test connection' }}
              </button>
              <button class="btn btn--primary" :disabled="llm.saving" @click="saveProfile">
                {{ llm.saving ? 'Saving...' : 'Save connection' }}
              </button>
            </div>
            <p v-if="llm.testMsg" :class="llm.testOk ? 'success-message' : 'error-message'" style="margin-top: 0.5rem;">{{ llm.testMsg }}</p>
            <p v-if="llm.msg" :class="llm.err ? 'error-message' : 'success-message'" style="margin-top: 0.5rem;">{{ llm.msg }}</p>
          </div>
        </div>

        <!-- Course Enrollment Section -->
        <div class="profile-section">
          <h2 class="section-title">Course Enrollment</h2>

          <div class="join-course-form">
            <label class="info-label">Join a Course</label>
            <div class="join-row">
              <input
                v-model="inviteCode"
                type="text"
                placeholder="Enter invite code"
                class="form-input"
                @keyup.enter="joinCourse"
              />
              <button @click="joinCourse" :disabled="!inviteCode.trim() || joiningCourse" class="btn btn--primary">
                {{ joiningCourse ? 'Joining...' : 'Join' }}
              </button>
            </div>
            <p v-if="joinMessage" :class="joinError ? 'error-message' : 'success-message'" style="margin-top: 0.75rem;">{{ joinMessage }}</p>
          </div>

          <div v-if="enrolledCourses.length > 0" class="enrolled-courses">
            <h4 class="enrolled-courses__title">My Courses</h4>
            <div class="enrolled-courses__list">
              <router-link
                v-for="c in enrolledCourses"
                :key="c.id"
                :to="'/courses/' + c.id"
                class="enrolled-course-card"
              >
                <div class="enrolled-course-card__info">
                  <span class="enrolled-course-card__name">{{ c.name }}</span>
                  <span class="enrolled-course-card__code">{{ c.code }} &mdash; {{ c.semester }}</span>
                </div>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="enrolled-course-card__arrow">
                  <polyline points="9 18 15 12 9 6"/>
                </svg>
              </router-link>
            </div>
          </div>
          <p v-else class="empty-courses">Not enrolled in any courses yet.</p>
        </div>

        <!-- Password Change Section -->
        <div class="profile-section">
          <h2 class="section-title">Change Password</h2>
          
          <form @submit.prevent="changePassword" class="password-form">
            <div class="form-group">
              <label for="currentPassword">Current Password</label>
              <div class="input-wrapper">
                <input
                  id="currentPassword"
                  v-model="passwordForm.currentPassword"
                  :type="showCurrentPassword ? 'text' : 'password'"
                  placeholder="Enter current password"
                  class="form-input"
                  :class="{ 'error': passwordErrors.currentPassword }"
                  required
                />
                <button
                  type="button"
                  @click="showCurrentPassword = !showCurrentPassword"
                  class="password-toggle"
                >
                  <svg v-if="showCurrentPassword" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                    <line x1="1" y1="1" x2="23" y2="23"/>
                  </svg>
                  <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                    <circle cx="12" cy="12" r="3"/>
                  </svg>
                </button>
              </div>
              <p v-if="passwordErrors.currentPassword" class="error-text">{{ passwordErrors.currentPassword }}</p>
            </div>

            <div class="form-group">
              <label for="newPassword">New Password</label>
              <div class="input-wrapper">
                <input
                  id="newPassword"
                  v-model="passwordForm.newPassword"
                  :type="showNewPassword ? 'text' : 'password'"
                  placeholder="Enter new password"
                  class="form-input"
                  :class="{ 'error': passwordErrors.newPassword }"
                  required
                  @blur="validateNewPassword"
                />
                <button
                  type="button"
                  @click="showNewPassword = !showNewPassword"
                  class="password-toggle"
                >
                  <svg v-if="showNewPassword" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                    <line x1="1" y1="1" x2="23" y2="23"/>
                  </svg>
                  <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                    <circle cx="12" cy="12" r="3"/>
                  </svg>
                </button>
              </div>
              <p v-if="passwordErrors.newPassword" class="error-text">{{ passwordErrors.newPassword }}</p>
              <p v-else-if="passwordForm.newPassword && !passwordErrors.newPassword" class="help-text">
                Password must be at least 8 characters and contain uppercase, lowercase, and a number.
              </p>
            </div>

            <div class="form-group">
              <label for="confirmPassword">Confirm New Password</label>
              <div class="input-wrapper">
                <input
                  id="confirmPassword"
                  v-model="passwordForm.confirmPassword"
                  :type="showConfirmPassword ? 'text' : 'password'"
                  placeholder="Confirm new password"
                  class="form-input"
                  :class="{ 'error': passwordErrors.confirmPassword }"
                  required
                  @blur="validateConfirmPassword"
                />
                <button
                  type="button"
                  @click="showConfirmPassword = !showConfirmPassword"
                  class="password-toggle"
                >
                  <svg v-if="showConfirmPassword" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                    <line x1="1" y1="1" x2="23" y2="23"/>
                  </svg>
                  <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                    <circle cx="12" cy="12" r="3"/>
                  </svg>
                </button>
              </div>
              <p v-if="passwordErrors.confirmPassword" class="error-text">{{ passwordErrors.confirmPassword }}</p>
            </div>

            <p v-if="passwordErrorMessage" class="error-message">{{ passwordErrorMessage }}</p>
            <p v-if="passwordSuccessMessage" class="success-message">{{ passwordSuccessMessage }}</p>

            <button type="submit" :disabled="passwordLoading" class="btn btn--primary">
              <span v-if="passwordLoading">Changing Password...</span>
              <span v-else>Change Password</span>
            </button>
          </form>
        </div>
      </div>

      <div v-else class="error-message">Failed to load profile information</div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import axios from '../api/axios'
import { useVpnStatus } from '../composables/useVpnStatus'
import { usePoll } from '../composables/usePoll'
import { useModules } from '../composables/useModules'

const route = useRoute()
const { exerciseAuthoring, fetchModules } = useModules()
const user = ref(null)
const { vpnStatus, fetchVpnStatus, isVpnRegistered } = useVpnStatus()
const loading = ref(true)

// Exercise Studio LLM connections (instructor/admin)
const isInstructor = computed(() => ['instructor', 'admin'].includes(user.value?.role))
const llm = reactive({
  profiles: [], catalog: [],
  form: { provider: 'custom', base_url: '', api_key: '', model: '', label: '' },
  saving: false, testing: false, msg: '', err: false, testMsg: '', testOk: false,
})
const currentSpec = computed(() => llm.catalog.find(c => c.id === llm.form.provider) || null)
function providerLabel(id) { const c = llm.catalog.find(x => x.id === id); return c ? c.label.split(' (')[0] : id }
function onProviderChange() {
  const s = currentSpec.value
  llm.form.base_url = s?.default_base_url || ''
  llm.form.api_key = ''
  llm.form.model = s?.default_model || (s?.models && s.models[0]) || ''
  llm.testMsg = ''; llm.msg = ''
}
async function loadStudioLlm() {
  // Exercise Studio is not in every edition; without it these routes 404 and
  // the LLM provider panel is dead controls.
  if (!exerciseAuthoring.value) { llm.profiles = []; llm.catalog = []; return }
  try {
    const r = await axios.get('/studio/providers')
    llm.profiles = r.data.profiles || []
    llm.catalog = r.data.catalog || []
    if (!currentSpec.value && llm.catalog.length) llm.form.provider = llm.catalog[0].id
    onProviderChange()
  } catch { llm.profiles = []; llm.catalog = [] }
}
function _formPayload() {
  return {
    provider: llm.form.provider,
    label: llm.form.label.trim() || null,
    base_url: llm.form.base_url.trim() || null,
    model: llm.form.model.trim() || null,
    api_key: llm.form.api_key.trim() || null,
  }
}
async function testConnection() {
  llm.testing = true; llm.testMsg = ''; llm.msg = ''
  try {
    const r = await axios.post('/studio/providers/test', _formPayload())
    llm.testOk = !!r.data.ok
    llm.testMsg = (r.data.ok ? 'OK: ' : 'Failed: ') + (r.data.detail || '')
      + (r.data.models && r.data.models.length ? ' (' + r.data.models.slice(0, 8).join(', ') + ')' : '')
  } catch (e) {
    llm.testOk = false; llm.testMsg = e.response?.data?.detail || 'Could not reach the test endpoint.'
  } finally { llm.testing = false }
}
async function saveProfile() {
  llm.saving = true; llm.msg = ''
  try {
    await axios.post('/studio/providers', { ..._formPayload(), make_default: llm.profiles.length === 0 })
    llm.form.api_key = ''; llm.form.label = ''
    llm.msg = 'Connection saved.'; llm.err = false; llm.testMsg = ''
    await loadStudioLlm()
  } catch (e) {
    llm.msg = e.response?.data?.detail || 'Could not save the connection.'; llm.err = true
  } finally { llm.saving = false }
}
async function makeDefault(id) {
  try { const r = await axios.post(`/studio/providers/${id}/default`); llm.profiles = r.data.profiles || llm.profiles }
  catch (e) { llm.msg = e.response?.data?.detail || 'Could not set default.'; llm.err = true }
}
async function removeProfile(id) {
  try { const r = await axios.delete(`/studio/providers/${id}`); llm.profiles = r.data.profiles || [] }
  catch (e) { llm.msg = e.response?.data?.detail || 'Could not remove the connection.'; llm.err = true }
}

const passwordForm = reactive({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const passwordErrors = reactive({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
})

// Course enrollment
const inviteCode = ref('')
const joiningCourse = ref(false)
const joinMessage = ref('')
const joinError = ref(false)
const enrolledCourses = ref([])

const fetchEnrolledCourses = async () => {
  try {
    const res = await axios.get('/courses/')
    enrolledCourses.value = res.data.courses || []
  } catch (e) {
    console.error('Failed to fetch courses:', e)
  }
}

const joinCourse = async () => {
  if (!inviteCode.value.trim() || joiningCourse.value) return
  joiningCourse.value = true
  joinMessage.value = ''
  joinError.value = false
  try {
    const res = await axios.post('/courses/join', { invite_code: inviteCode.value.trim() })
    joinMessage.value = res.data.message || 'Successfully enrolled!'
    joinError.value = false
    inviteCode.value = ''
    fetchEnrolledCourses()
  } catch (e) {
    joinMessage.value = e.response?.data?.detail || 'Failed to join course'
    joinError.value = true
  } finally {
    joiningCourse.value = false
  }
}

const showCurrentPassword = ref(false)
const showNewPassword = ref(false)
const showConfirmPassword = ref(false)
const passwordLoading = ref(false)
const passwordErrorMessage = ref('')
const passwordSuccessMessage = ref('')

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const d = new Date(dateStr.endsWith('Z') || dateStr.includes('+') ? dateStr : dateStr + 'Z')
  return d.toLocaleString('en-US', { timeZone: 'America/Chicago' })
}

const validateNewPassword = () => {
  passwordErrors.newPassword = ''
  if (!passwordForm.newPassword) return
  
  if (passwordForm.newPassword.length < 8) {
    passwordErrors.newPassword = 'Password must be at least 8 characters'
    return
  }
  if (!/[A-Z]/.test(passwordForm.newPassword)) {
    passwordErrors.newPassword = 'Password must contain at least one uppercase letter'
    return
  }
  if (!/[a-z]/.test(passwordForm.newPassword)) {
    passwordErrors.newPassword = 'Password must contain at least one lowercase letter'
    return
  }
  if (!/[0-9]/.test(passwordForm.newPassword)) {
    passwordErrors.newPassword = 'Password must contain at least one number'
    return
  }
}

const validateConfirmPassword = () => {
  passwordErrors.confirmPassword = ''
  if (!passwordForm.confirmPassword) return
  
  if (passwordForm.newPassword !== passwordForm.confirmPassword) {
    passwordErrors.confirmPassword = 'Passwords do not match'
  }
}

const changePassword = async () => {
  passwordErrorMessage.value = ''
  passwordSuccessMessage.value = ''
  
  // Validate
  validateNewPassword()
  validateConfirmPassword()
  
  if (passwordErrors.newPassword || passwordErrors.confirmPassword) {
    return
  }
  
  if (passwordForm.newPassword !== passwordForm.confirmPassword) {
    passwordErrorMessage.value = 'Passwords do not match'
    return
  }
  
  passwordLoading.value = true
  
  try {
    await axios.post('/auth/change-password', {
      current_password: passwordForm.currentPassword,
      new_password: passwordForm.newPassword,
      confirm_password: passwordForm.confirmPassword
    })
    
    passwordSuccessMessage.value = 'Password changed successfully!'
    
    // Clear form
    passwordForm.currentPassword = ''
    passwordForm.newPassword = ''
    passwordForm.confirmPassword = ''
    
    // Update localStorage user object to clear must_change_password flag if set
    const userObj = JSON.parse(localStorage.getItem('user') || '{}')
    userObj.must_change_password = false
    localStorage.setItem('user', JSON.stringify(userObj))
    
    // Trigger App.vue reactivity update
    if (window.__updateAuthState) {
      window.__updateAuthState()
    }
  } catch (error) {
    if (error.response?.data?.detail) {
      passwordErrorMessage.value = error.response.data.detail
    } else {
      passwordErrorMessage.value = 'Failed to change password. Please try again.'
    }
  } finally {
    passwordLoading.value = false
  }
}

// fetchVpnStatus is now provided by useVpnStatus composable

const fetchUserInfo = async () => {
  try {
    const [userResponse] = await Promise.all([
      axios.get('/auth/me'),
      fetchVpnStatus() // Fetch VPN status in parallel using shared composable
    ])
    user.value = userResponse.data
    if (['instructor', 'admin'].includes(user.value?.role)) {
      await fetchModules()
      loadStudioLlm()
    }
  } catch (error) {
    console.error('Failed to fetch user info:', error)
  } finally {
    loading.value = false
  }
}

// Refresh VPN status every 10 seconds to match Dashboard behavior. usePoll
// pauses while the tab is hidden and refreshes immediately on return, which
// replaces the old visibilitychange handler.
//
// Returning to a hidden tab fires visibilitychange (usePoll refreshes) and
// then focus, so the focus handler skips a fetch that just ran to avoid a
// duplicate request.
let lastVpnRefresh = 0
const refreshVpnStatus = () => {
  lastVpnRefresh = Date.now()
  fetchVpnStatus()
}
const onWindowFocus = () => {
  if (Date.now() - lastVpnRefresh < 1000) return
  refreshVpnStatus()
}
usePoll(refreshVpnStatus, 10000)

onMounted(() => {
  fetchUserInfo()
  fetchEnrolledCourses()

  // Window focus covers clicking back into the browser from another app,
  // which does not fire visibilitychange (the tab was never hidden).
  window.addEventListener('focus', onWindowFocus)
})

// Cleanup on unmount
onUnmounted(() => {
  window.removeEventListener('focus', onWindowFocus)
})

// Watch for route changes (when navigating to profile page)
watch(() => route.path, (newPath) => {
  if (newPath === '/profile') {
    // Refresh VPN status when navigating to profile page
    // Add small delay to ensure any pending VPN registrations complete
    setTimeout(() => {
      fetchVpnStatus()
    }, 500)
  }
}, { immediate: true })
</script>

<style scoped>
.profile-page {
  min-height: calc(100vh - 64px);
  padding: 2rem;
  background: var(--bg-primary);
}

.profile-container {
  max-width: 900px;
  margin: 0 auto;
}

.page-title {
  font-size: 2rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 2rem;
}

.loading-message {
  color: var(--text-secondary);
  text-align: center;
  padding: 2rem;
}

.profile-content {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.profile-section {
  background: var(--bg-secondary);
  border-radius: 12px;
  padding: 1.5rem;
  border: 1px solid var(--border-color);
}

.section-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 1.5rem 0;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--border-color);
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.info-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.info-value {
  font-size: 1rem;
  color: var(--text-primary);
}

.status-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 6px;
  font-size: 0.8125rem;
  font-weight: 500;
}

.status-badge--approved {
  background: rgba(34, 197, 94, 0.15);
  color: #10b981;
  border: 1px solid #10b981;
}

.status-badge--pending {
  background: rgba(245, 158, 11, 0.15);
  color: var(--warning);
  border: 1px solid var(--warning);
}

.status-badge--active {
  background: rgba(34, 197, 94, 0.15);
  color: #10b981;
  border: 1px solid #10b981;
}

.status-badge--inactive {
  background: rgba(239, 68, 68, 0.15);
  color: var(--danger);
  border: 1px solid var(--danger);
}

.status-badge--vpn {
  background: rgba(34, 197, 94, 0.15);
  color: #10b981;
  border: 1px solid #10b981;
}

.status-badge--no-vpn {
  background: rgba(100, 116, 139, 0.15);
  color: var(--text-muted);
  border: 1px solid var(--text-muted);
}

.status-badge--admin {
  background: rgba(139, 92, 246, 0.15);
  color: #a78bfa;
  border: 1px solid #8b5cf6;
}

.status-badge--instructor {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  border: 1px solid var(--accent);
}

.status-badge--user {
  background: rgba(148, 163, 184, 0.15);
  color: var(--text-secondary);
  border: 1px solid var(--text-secondary);
}

.password-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-size: 0.875rem;
  font-weight: 500;
  color: #e2e8f0;
}

.input-wrapper {
  position: relative;
}

.form-input {
  width: 100%;
  padding: 0.75rem 2.5rem 0.75rem 1rem;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 1rem;
  transition: all 0.2s ease;
}

.form-input:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-bg);
}

.form-input.error {
  border-color: #dc2626;
}

.form-input::placeholder {
  color: var(--text-muted);
}

.password-toggle {
  position: absolute;
  right: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 0.25rem;
  display: flex;
  align-items: center;
  transition: color 0.2s ease;
}

.password-toggle:hover {
  color: var(--text-primary);
}

.password-toggle svg {
  width: 20px;
  height: 20px;
}

.help-text {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-top: 0.25rem;
}

.error-text {
  font-size: 0.8125rem;
  color: #dc2626;
  margin-top: 0.25rem;
}

.error-message {
  font-size: 0.875rem;
  color: #dc2626;
  padding: 0.75rem;
  background: rgba(220, 38, 38, 0.1);
  border-radius: 6px;
  border: 1px solid #dc2626;
}

.success-message {
  font-size: 0.875rem;
  color: #10b981;
  padding: 0.75rem;
  background: rgba(16, 185, 129, 0.1);
  border-radius: 6px;
  border: 1px solid #10b981;
}

.btn {
  padding: 0.75rem 1.5rem;
  border-radius: 6px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  border: none;
  align-self: flex-start;
}

.btn--primary {
  background: var(--accent);
  color: white;
}

.btn--primary:hover:not(:disabled) {
  background: #2563eb;
}

.btn--primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.key-connected {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.key-connected .btn {
  align-self: auto;
}

.btn--secondary {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.btn--secondary:hover {
  background: var(--nav-label);
}

.btn--ghost-danger {
  background: transparent;
  color: var(--danger);
  border: 1px solid var(--danger);
}

.btn--ghost-danger:hover {
  background: var(--danger-bg);
}

.btn--sm {
  padding: 0.3rem 0.7rem;
  font-size: 0.82rem;
}

/* LLM provider connections */
.llm-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.llm-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  flex-wrap: wrap;
  padding: 0.6rem 0.8rem;
  background: var(--bg-tertiary);
  border-radius: 8px;
}

.llm-row__main {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  min-width: 0;
}

.llm-row__label {
  font-weight: 600;
  color: var(--text-primary);
}

.llm-row__meta {
  font-size: 0.82rem;
  color: var(--text-secondary);
}

.llm-row__url {
  font-family: monospace;
  word-break: break-all;
}

.llm-row__actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.llm-add {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--border-color, rgba(255, 255, 255, 0.08));
}

.llm-field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.llm-actions {
  display: flex;
  gap: 0.6rem;
  flex-wrap: wrap;
}

/* Course Enrollment */
.join-course-form {
  margin-bottom: 1.5rem;
}

.join-row {
  display: flex;
  gap: 0.75rem;
  margin-top: 0.5rem;
}

.join-row .form-input {
  flex: 1;
  max-width: 320px;
}

.join-row .btn {
  white-space: nowrap;
}

.enrolled-courses {
  margin-top: 1.5rem;
}

.enrolled-courses__title {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 0.75rem;
}

.enrolled-courses__list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.enrolled-course-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  text-decoration: none;
  transition: all 0.15s;
}

.enrolled-course-card:hover {
  border-color: var(--accent);
  background: rgba(59, 130, 246, 0.05);
}

.enrolled-course-card__info {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.enrolled-course-card__name {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--text-primary);
}

.enrolled-course-card__code {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.enrolled-course-card__arrow {
  width: 16px;
  height: 16px;
  color: var(--nav-label);
  flex-shrink: 0;
}

.empty-courses {
  color: var(--nav-label);
  font-size: 0.875rem;
  margin-top: 1rem;
}
</style>


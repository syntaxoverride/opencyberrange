<template>
  <div class="setup-page">
    <div class="setup-container">
      <!-- Header -->
      <div class="setup-header">
        <img src="/ocr-logo-dark.png" alt="OpenCyberRange" class="setup-logo" />
        <div class="brand-section">
          <h1 class="brand-title">OpenCyberRange</h1>
        </div>
        <p class="setup-subtitle">First-Run Setup</p>
      </div>

      <!-- Progress Steps -->
      <div class="steps-indicator">
        <div v-for="s in 4" :key="s" class="step" :class="{ 'step--active': step === s, 'step--done': step > s }">
          <div class="step-circle">{{ step > s ? '✓' : s }}</div>
          <span class="step-label">{{ stepLabels[s - 1] }}</span>
        </div>
      </div>

      <!-- Error -->
      <div v-if="errorMessage" class="error-message">{{ errorMessage }}</div>

      <!-- Step 1: Admin Account -->
      <div v-if="step === 1" class="setup-card">
        <h2 class="card-title">Admin Account</h2>
        <p class="card-desc">Create the initial administrator account.</p>
        <div class="form-group">
          <label class="form-label" for="setup-admin_username">Username</label>
          <input v-model="form.admin_username" type="text" id="setup-admin_username" class="form-input" placeholder="admin" autocomplete="username" />
        </div>
        <div class="form-group">
          <label class="form-label" for="setup-admin_email">Email</label>
          <input v-model="form.admin_email" type="email" id="setup-admin_email" class="form-input" placeholder="admin@example.com" autocomplete="email" />
        </div>
        <div class="form-group">
          <label class="form-label" for="setup-admin_password">Password</label>
          <input v-model="form.admin_password" type="password" id="setup-admin_password" class="form-input" placeholder="Min 8 characters" autocomplete="new-password" />
        </div>
        <div class="form-group">
          <label class="form-label" for="setup-confirm_password">Confirm Password</label>
          <input v-model="confirmPassword" type="password" id="setup-confirm_password" class="form-input" placeholder="Repeat password" autocomplete="new-password" />
        </div>
        <div class="form-group" v-if="tokenRequired">
          <label class="form-label" for="setup-setup_token">Setup token</label>
          <input v-model="form.setup_token" type="text" id="setup-setup_token" class="form-input" placeholder="From the server install output" autocomplete="off" />
          <p class="form-hint">This install requires the one-time setup token the installer generated (in the server's .env / install output).</p>
        </div>
        <div class="card-actions">
          <button @click="validateStep2" class="btn btn--primary">Next</button>
        </div>
      </div>

      <!-- Step 2: Security -->
      <div v-if="step === 2" class="setup-card">
        <h2 class="card-title">Security Settings</h2>
        <p class="card-desc">Configure initial security preferences.</p>
        <div class="toggle-row">
          <div class="toggle-info">
            <span class="toggle-label">Require Admin Approval</span>
            <span class="toggle-desc">New users must be approved by an admin before accessing the platform.</span>
          </div>
          <button
            class="toggle-btn"
            :class="form.require_approval ? 'toggle-btn--on' : 'toggle-btn--off'"
            @click="form.require_approval = !form.require_approval"
          >
            {{ form.require_approval ? 'ON' : 'OFF' }}
          </button>
        </div>
        <div class="card-actions">
          <button @click="step = 1" class="btn btn--secondary">Back</button>
          <button @click="step = 3" class="btn btn--primary">Next</button>
        </div>
      </div>

      <!-- Step 3: Modules -->
      <div v-if="step === 3" class="setup-card">
        <h2 class="card-title">Optional Modules</h2>
        <p v-if="availableModules.length" class="card-desc">Enable optional modules for your deployment. These can be changed later from Admin Settings.</p>
        <p v-else class="card-desc">This edition ships no optional modules, so there is nothing to configure here.</p>
        <div
          v-for="(m, i) in availableModules"
          :key="m.id"
          class="toggle-row"
          :style="i < availableModules.length - 1 ? 'margin-bottom: 0.75rem;' : ''"
        >
          <div class="toggle-info">
            <span class="toggle-label">{{ m.label }} Module</span>
            <span class="toggle-desc">{{ m.description }}</span>
          </div>
          <button
            class="toggle-btn"
            :class="form['module_' + m.id] ? 'toggle-btn--on' : 'toggle-btn--off'"
            @click="form['module_' + m.id] = !form['module_' + m.id]"
          >
            {{ form['module_' + m.id] ? 'ON' : 'OFF' }}
          </button>
        </div>
        <div class="card-actions">
          <button @click="step = 2" class="btn btn--secondary">Back</button>
          <button @click="step = 4" class="btn btn--primary">Next</button>
        </div>
      </div>

      <!-- Step 4: Review -->
      <div v-if="step === 4" class="setup-card">
        <h2 class="card-title">Review & Complete</h2>
        <p class="card-desc">Confirm your setup configuration.</p>
        <div class="review-grid">
          <div class="review-item">
            <span class="review-label">Admin Username</span>
            <span class="review-value">{{ form.admin_username }}</span>
          </div>
          <div class="review-item">
            <span class="review-label">Admin Email</span>
            <span class="review-value">{{ form.admin_email }}</span>
          </div>
          <div class="review-item">
            <span class="review-label">Require Approval</span>
            <span class="review-value">{{ form.require_approval ? 'Yes' : 'No' }}</span>
          </div>
          <div v-for="m in availableModules" :key="m.id" class="review-item">
            <span class="review-label">{{ m.label }} Module</span>
            <span class="review-value">{{ form['module_' + m.id] ? 'Enabled' : 'Disabled' }}</span>
          </div>
        </div>
        <div class="card-actions">
          <button @click="step = 3" class="btn btn--secondary">Back</button>
          <button @click="completeSetup" class="btn btn--primary" :disabled="loading">
            {{ loading ? 'Setting up...' : 'Complete Setup' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()

const step = ref(1)
const loading = ref(false)
const errorMessage = ref('')
const confirmPassword = ref('')
const stepLabels = ['Account', 'Security', 'Modules', 'Review']
const availableModules = ref([])
const tokenRequired = ref(false)

const form = reactive({
  admin_username: '',
  admin_email: '',
  admin_password: '',
  require_approval: true,
  setup_token: '',
})

const ShieldIcon = {
  template: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M12 2L3 7V12C3 16.97 7.02 21.45 12 22C16.98 21.45 21 16.97 21 12V7L12 2Z"/>
  </svg>`
}

onMounted(async () => {
  try {
    const { data } = await axios.get('/api/setup/status')
    if (data.setup_complete) {
      router.replace('/login')
    }
    tokenRequired.value = !!data.setup_token_required
  } catch {
    // If API not available, stay on setup page
  }
  // Only offer modules whose code actually ships in this edition.
  try {
    const { data: cfg } = await axios.get('/api/setup/config')
    availableModules.value = cfg.available_modules || []
    for (const m of availableModules.value) {
      if (form['module_' + m.id] === undefined) form['module_' + m.id] = false
    }
  } catch {
    availableModules.value = []
  }
})

const validateStep2 = () => {
  errorMessage.value = ''
  if (!form.admin_username || form.admin_username.length < 3) {
    errorMessage.value = 'Username must be at least 3 characters'
    return
  }
  // Mirror the backend's email rule (pydantic EmailStr) so a bad address is
  // caught here on step 1 rather than with a raw 422 on the final step. The
  // server rejects special-use / reserved domains (.local, .localhost,
  // .example, .invalid, .test) and anything without a real dotted domain.
  const email = (form.admin_email || '').trim()
  const emailShape = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/
  const reservedTld = /\.(local|localhost|example|invalid|test)$/i
  if (!email || !emailShape.test(email)) {
    errorMessage.value = 'Please enter a valid email address (name@domain.tld)'
    return
  }
  if (reservedTld.test(email)) {
    errorMessage.value = 'That email uses a reserved domain (.local, .example, .invalid, .test). Use a real, deliverable address.'
    return
  }
  // Password complexity validation
  const pw = form.admin_password || ''
  if (pw.length < 8) {
    errorMessage.value = 'Password must be at least 8 characters'
    return
  }
  if (!/[A-Z]/.test(pw)) {
    errorMessage.value = 'Password must contain at least one uppercase letter'
    return
  }
  if (!/[a-z]/.test(pw)) {
    errorMessage.value = 'Password must contain at least one lowercase letter'
    return
  }
  if (!/[0-9]/.test(pw)) {
    errorMessage.value = 'Password must contain at least one number'
    return
  }
  if (form.admin_password !== confirmPassword.value) {
    errorMessage.value = 'Passwords do not match'
    return
  }
  step.value = 3
}

/** Extract readable error from API response (handles Pydantic 422 array details) */
const parseSetupError = (error) => {
  const detail = error.response?.data?.detail
  if (!detail) return 'Setup failed. Please try again.'
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map(err => err.msg || JSON.stringify(err)).join('. ')
  }
  return 'Setup failed. Please try again.'
}

const completeSetup = async () => {
  loading.value = true
  errorMessage.value = ''
  try {
    const { data } = await axios.post('/api/setup/complete', form)

    // Store token and user for immediate login
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('user', JSON.stringify(data.user))

    // Update auth state if available
    if (window.__updateAuthState) {
      window.__updateAuthState()
    }

    // Full-page navigation, not router.push: the navigation guard checks
    // setup status once per load and caches it. At this point it still has the
    // stale "setup incomplete" flag from app start, so a soft route would bounce
    // back to /setup. A hard load re-runs the guard with fresh state.
    window.location.href = '/admin'
  } catch (error) {
    errorMessage.value = parseSetupError(error)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.setup-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-primary);
  padding: 2rem 1rem;
}

.setup-container {
  width: 100%;
  max-width: 540px;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.setup-header {
  text-align: center;
}
.setup-logo {
  height: 72px;
  width: auto;
  margin: 0 auto 0.75rem;
  display: block;
}

.brand-section {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}

.brand-icon {
  width: 32px;
  height: 32px;
  color: var(--accent);
}

.brand-title {
  font-size: 1.875rem;
  font-weight: 700;
  color: var(--text-primary);
}

.setup-subtitle {
  color: var(--text-secondary);
  font-size: 0.9375rem;
}

/* Steps indicator */
.steps-indicator {
  display: flex;
  justify-content: center;
  gap: 2rem;
}

.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.375rem;
}

.step-circle {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8125rem;
  font-weight: 600;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  border: 2px solid var(--nav-label);
  transition: all 0.2s;
}

.step--active .step-circle {
  background: var(--accent);
  color: white;
  border-color: var(--accent);
}

.step--done .step-circle {
  background: var(--success);
  color: white;
  border-color: var(--success);
}

.step-label {
  font-size: 0.6875rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.step--active .step-label {
  color: var(--accent);
}

/* Cards */
.setup-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 2rem;
}

.card-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.25rem;
}

.card-desc {
  color: var(--text-secondary);
  font-size: 0.875rem;
  margin-bottom: 1.5rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 0.375rem;
}

.form-input {
  width: 100%;
  padding: 0.75rem 1rem;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 0.9375rem;
  transition: border-color 0.2s;
}

.form-input:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-bg);
}

.form-input::placeholder {
  color: var(--text-muted);
}

/* Toggle */
.toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem;
  background: var(--bg-primary);
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.toggle-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.toggle-label {
  font-size: 0.9375rem;
  font-weight: 500;
  color: var(--text-primary);
}

.toggle-desc {
  font-size: 0.8125rem;
  color: var(--text-muted);
}

.toggle-btn {
  padding: 0.375rem 1rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  border: 1px solid;
  cursor: pointer;
  min-width: 50px;
  transition: all 0.2s;
}

.toggle-btn--on {
  background: rgba(34, 197, 94, 0.15);
  color: var(--success);
  border-color: var(--success);
}

.toggle-btn--off {
  background: rgba(100, 116, 139, 0.15);
  color: var(--text-secondary);
  border-color: var(--nav-label);
}

/* Review */
.review-grid {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.review-item {
  display: flex;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  background: var(--bg-primary);
  border-radius: 6px;
  border: 1px solid var(--border-color);
}

.review-label {
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.review-value {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-primary);
}

/* Actions */
.card-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 1.5rem;
}

.btn {
  padding: 0.625rem 1.5rem;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
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

.btn--secondary {
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--nav-label);
}

.btn--secondary:hover {
  background: var(--bg-tertiary);
  color: var(--hover-text);
}

.error-message {
  background: #7f1d1d;
  border: 1px solid #991b1b;
  color: #fecaca;
  padding: 0.75rem 1rem;
  border-radius: 6px;
  font-size: 0.875rem;
  text-align: center;
}

@media (max-width: 640px) {
  .setup-container {
    max-width: 100%;
  }
  .setup-card {
    padding: 1.5rem;
  }
  .steps-indicator {
    gap: 1rem;
  }
  .step-label {
    display: none;
  }
}
</style>

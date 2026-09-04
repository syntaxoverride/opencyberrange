<template>
  <div class="register-page">
    <div class="register-split">
      <!-- Left: Form Panel -->
      <div class="register-form-panel">
        <div class="form-panel-inner">
          <!-- Brand -->
          <div class="brand">
            <img src="/ocr-logo-dark.png" alt="OpenCyberRange" class="brand-icon" />
            <div class="brand-text">
              <h1 class="brand-title">OpenCyberRange</h1>
              <p class="brand-subtitle">Create Account</p>
            </div>
          </div>

          <p class="form-subtext">Join the cybersecurity training platform</p>

          <!-- Error Message -->
          <div v-if="errorMessage" class="error-message">
            {{ errorMessage }}
          </div>

          <!-- Success Message -->
          <div v-if="successMessage" class="success-message">
            {{ successMessage }}
          </div>

          <form @submit.prevent="handleRegister" class="register-form">
            <div class="form-group">
              <label for="username" class="form-label">Username</label>
              <input
                id="username"
                v-model="form.username"
                type="text"
                class="form-input"
                :class="{ 'form-input--error': errors.username }"
                placeholder="Enter your username"
                required
                autocomplete="username"
                @blur="validateUsername"
              />
              <p v-if="errors.username" class="error-text">{{ errors.username }}</p>
              <p v-else-if="form.username && !errors.username" class="help-text">
                Must start with a letter and contain only letters, numbers, underscores, and hyphens (3-50 characters)
              </p>
            </div>

            <div class="form-group">
              <label for="email" class="form-label">Email</label>
              <input
                id="email"
                v-model="form.email"
                type="email"
                class="form-input"
                :class="{ 'form-input--error': errors.email }"
                placeholder="Enter your email"
                required
                autocomplete="email"
                @blur="validateEmail"
              />
              <p v-if="errors.email" class="error-text">{{ errors.email }}</p>
            </div>

            <div class="form-group">
              <label for="password" class="form-label">Password</label>
              <div class="input-wrapper">
                <input
                  id="password"
                  v-model="form.password"
                  :type="showPassword ? 'text' : 'password'"
                  class="form-input"
                  :class="{ 'form-input--error': errors.password }"
                  placeholder="Enter your password"
                  required
                  autocomplete="new-password"
                  @blur="validatePassword"
                />
                <button
                  type="button"
                  @click="showPassword = !showPassword"
                  class="password-toggle"
                >
                  <svg v-if="showPassword" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                    <line x1="1" y1="1" x2="23" y2="23"/>
                  </svg>
                  <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                    <circle cx="12" cy="12" r="3"/>
                  </svg>
                </button>
              </div>
              <p v-if="errors.password" class="error-text">{{ errors.password }}</p>
              <p v-else-if="form.password && !errors.password" class="help-text">
                Must be at least 8 characters and contain uppercase, lowercase, and a number
              </p>
            </div>

            <div class="form-group">
              <label for="confirmPassword" class="form-label">Confirm Password</label>
              <div class="input-wrapper">
                <input
                  id="confirmPassword"
                  v-model="form.confirmPassword"
                  :type="showConfirmPassword ? 'text' : 'password'"
                  class="form-input"
                  :class="{ 'form-input--error': errors.confirmPassword }"
                  placeholder="Confirm your password"
                  required
                  autocomplete="new-password"
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
              <p v-if="errors.confirmPassword" class="error-text">{{ errors.confirmPassword }}</p>
            </div>

            <div v-if="inviteRequired" class="form-group">
              <label for="inviteCode" class="form-label">Invite Code</label>
              <input
                id="inviteCode"
                v-model="form.inviteCode"
                type="text"
                class="form-input"
                :class="{ 'form-input--error': errors.inviteCode }"
                placeholder="Enter the code you were given"
                autocomplete="one-time-code"
                @blur="validateInviteCode"
              />
              <p v-if="errors.inviteCode" class="error-text">{{ errors.inviteCode }}</p>
              <p v-else class="help-text">
                Registration on this site is limited to people who were given a code. Your instructor issues it.
              </p>
            </div>

            <button
              type="submit"
              class="register-button"
              :disabled="loading"
            >
              <span v-if="!loading">Create Account</span>
              <span v-else>Creating Account...</span>
            </button>
          </form>

          <div class="login-section">
            <p class="login-text">
              Already have an account?
              <router-link to="/login" class="login-link">Sign in here</router-link>
            </p>
          </div>
        </div>
      </div>

      <!-- Right: Illustration Panel -->
      <div class="register-hero-panel">
        <div class="hero-content">
          <!-- CSS Terminal Illustration -->
          <div class="terminal">
            <div class="terminal__titlebar">
              <span class="terminal__dot terminal__dot--red"></span>
              <span class="terminal__dot terminal__dot--yellow"></span>
              <span class="terminal__dot terminal__dot--green"></span>
              <span class="terminal__titlebar-text">ocr ~ setup</span>
            </div>
            <div class="terminal__body">
              <div class="terminal__line">
                <span class="terminal__prompt">$</span>
                <span class="terminal__cmd">ocr init --user new</span>
              </div>
              <div class="terminal__line terminal__line--output">
                Initializing training environment...
              </div>
              <div class="terminal__line terminal__line--success">
                VPN profile generated
              </div>
              <div class="terminal__line terminal__line--success">
                Lab networks configured
              </div>
              <div class="terminal__line terminal__line--success">
                Practice targets deployed
              </div>
              <div class="terminal__line terminal__line--output terminal__line--highlight">
                Ready. 4 learning paths available.
              </div>
              <div class="terminal__line">
                <span class="terminal__prompt">$</span>
                <span class="terminal__cursor"></span>
              </div>
            </div>
          </div>

          <div class="hero-text">
            <h2 class="hero-title">Start Your Journey</h2>
            <p class="hero-subtitle">
              Network security, pen testing, web exploitation, and more.
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios' // Use plain axios for registration (no token needed)

const router = useRouter()

const form = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  inviteCode: ''
})

const errors = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  inviteCode: ''
})

// Invite codes are off by default and a class can turn them on. Rather than
// asking every visitor for a code that is usually not needed, the field stays
// hidden until the server tells us one is required, which it does by rejecting
// the first submit. Costs one extra submit in the locked case, and keeps the
// form honest in the common one. Nothing here is a security control; the
// server decides.
const inviteRequired = ref(false)

const showPassword = ref(false)
const showConfirmPassword = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const loading = ref(false)


const validateUsername = () => {
  errors.username = ''
  if (!form.username) return

  if (form.username.length < 3 || form.username.length > 50) {
    errors.username = 'Username must be between 3 and 50 characters'
    return
  }
  if (/\s/.test(form.username)) {
    errors.username = 'Username cannot contain spaces'
    return
  }
  if (!/^[a-zA-Z][a-zA-Z0-9_-]*$/.test(form.username)) {
    errors.username = 'Username must start with a letter and contain only letters, numbers, underscores, and hyphens'
  }
}

const validateEmail = () => {
  errors.email = ''
  if (!form.email) return

  const emailRegex = /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/
  if (!emailRegex.test(form.email)) {
    errors.email = 'Invalid email format'
  }
}

const validatePassword = () => {
  errors.password = ''
  if (!form.password) return

  if (form.password.length < 8) {
    errors.password = 'Password must be at least 8 characters'
    return
  }
  if (!/[A-Z]/.test(form.password)) {
    errors.password = 'Password must contain at least one uppercase letter'
    return
  }
  if (!/[a-z]/.test(form.password)) {
    errors.password = 'Password must contain at least one lowercase letter'
    return
  }
  if (!/[0-9]/.test(form.password)) {
    errors.password = 'Password must contain at least one number'
  }
}

const validateConfirmPassword = () => {
  errors.confirmPassword = ''
  if (!form.confirmPassword) return

  if (form.password !== form.confirmPassword) {
    errors.confirmPassword = 'Passwords do not match'
  }
}

// The server accepts invite_code as optional and enforces whether one is
// actually required (the require_invite_code setting), so a blank value is
// valid here. A non-blank value still has to satisfy the server's length
// bounds, and catching that client-side beats a 422 with no useful text.
const validateInviteCode = () => {
  errors.inviteCode = ''
  const code = form.inviteCode.trim()
  if (!code) return
  if (code.length < 4 || code.length > 64) {
    errors.inviteCode = 'Invite code must be between 4 and 64 characters'
  }
}

const handleRegister = async () => {
  errorMessage.value = ''
  successMessage.value = ''

  // Validate all fields
  validateUsername()
  validateEmail()
  validatePassword()
  validateConfirmPassword()
  validateInviteCode()

  if (errors.username || errors.email || errors.password || errors.confirmPassword || errors.inviteCode) {
    errorMessage.value = 'Please fix the highlighted fields before creating your account.'
    return
  }

  if (form.password !== form.confirmPassword) {
    errors.confirmPassword = 'Passwords do not match'
    return
  }

  loading.value = true

  try {
    const payload = {
      username: form.username,
      email: form.email,
      password: form.password
    }
    const inviteCode = form.inviteCode.trim()
    if (inviteCode) {
      payload.invite_code = inviteCode
    }

    await axios.post('/api/auth/register', payload)

    successMessage.value = 'Account created successfully! Your account is pending administrator approval. You will be able to log in once approved.'

    // Clear form
    form.username = ''
    form.email = ''
    form.password = ''
    form.confirmPassword = ''
    form.inviteCode = ''

    // Redirect to login after 5 seconds
    setTimeout(() => {
      router.push('/login')
    }, 5000)
  } catch (error) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string' && /invite code is required/i.test(detail)) {
      inviteRequired.value = true
      errorMessage.value = 'Registration here needs an invite code. Enter the code you were given and submit again.'
      return
    }
    if (Array.isArray(detail)) {
      errorMessage.value = detail.map(err => err.msg || JSON.stringify(err)).join('. ')
    } else if (detail) {
      errorMessage.value = detail
    } else {
      errorMessage.value = 'Registration failed. Please check your information and try again.'
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.register-page {
  min-height: 100vh;
  background: var(--bg-primary);
}

.register-split {
  display: flex;
  min-height: 100vh;
}

/* ── Left: Form Panel ── */
.register-form-panel {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 3rem 2rem;
  background: var(--bg-primary);
}

.form-panel-inner {
  width: 100%;
  max-width: 420px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 2rem;
}

.brand-icon {
  width: 88px;
  height: 88px;
  flex-shrink: 0;
  background: var(--bg-primary);
  border-radius: 16px;
  padding: 6px;
}

.brand-text {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.brand-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.025em;
  line-height: 1.2;
}

.brand-subtitle {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-secondary);
  margin: 0;
}

.form-subtext {
  color: var(--text-secondary);
  font-size: 0.9375rem;
  margin-bottom: 1.75rem;
}

/* Messages */
.error-message {
  background: var(--danger-bg);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #fca5a5;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  margin-bottom: 1.25rem;
  font-size: 0.875rem;
}

.success-message {
  background: rgba(34, 197, 94, 0.1);
  border: 1px solid rgba(34, 197, 94, 0.3);
  color: #86efac;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  margin-bottom: 1.25rem;
  font-size: 0.875rem;
}

/* Form */
.register-form {
  display: flex;
  flex-direction: column;
  gap: 1.125rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.form-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.input-wrapper {
  position: relative;
}

.form-input {
  width: 100%;
  padding: 0.75rem 1rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 0.9375rem;
  transition: all 0.2s ease;
}

.input-wrapper .form-input {
  padding-right: 2.75rem;
}

.form-input:focus {
  outline: none;
  border-color: #f97316;
  box-shadow: 0 0 0 3px rgba(249, 115, 22, 0.15);
}

.form-input::placeholder {
  color: var(--text-muted);
}

.form-input--error {
  border-color: var(--danger);
}

.form-input--error:focus {
  border-color: var(--danger);
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.15);
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
}

.error-text {
  font-size: 0.8125rem;
  color: #f87171;
}

.register-button {
  width: 100%;
  padding: 0.875rem 1.5rem;
  background: linear-gradient(135deg, #f97316, #ea580c);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 0.9375rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  margin-top: 0.25rem;
}

.register-button:hover:not(:disabled) {
  background: linear-gradient(135deg, #fb923c, #f97316);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(249, 115, 22, 0.3);
}

.register-button:active:not(:disabled) {
  transform: translateY(0);
}

.register-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Login link */
.login-section {
  margin-top: 1.75rem;
  text-align: center;
}

.login-text {
  color: var(--text-secondary);
  font-size: 0.875rem;
}

.login-link {
  color: #f97316;
  text-decoration: none;
  font-weight: 500;
  margin-left: 0.25rem;
  transition: color 0.2s ease;
}

.login-link:hover {
  color: #fb923c;
  text-decoration: underline;
}

/* ── Right: Hero / Illustration Panel ── */
.register-hero-panel {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  background: linear-gradient(135deg, #f97316 0%, #ea580c 40%, #c2410c 100%);
  position: relative;
  overflow: hidden;
}

/* Subtle dot-grid overlay */
.register-hero-panel::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image: radial-gradient(rgba(255, 255, 255, 0.12) 1px, transparent 1px);
  background-size: 24px 24px;
  pointer-events: none;
}

.hero-content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2.5rem;
  max-width: 480px;
}

/* ── Terminal ── */
.terminal {
  width: 100%;
  background: #1e1e2e;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 25px 50px rgba(0, 0, 0, 0.35);
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 0.8125rem;
}

.terminal__titlebar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0.65rem 1rem;
  background: #181825;
}

.terminal__dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.terminal__dot--red { background: #f38ba8; }
.terminal__dot--yellow { background: #f9e2af; }
.terminal__dot--green { background: #a6e3a1; }

.terminal__titlebar-text {
  margin-left: 0.5rem;
  color: #6c7086;
  font-size: 0.75rem;
}

.terminal__body {
  padding: 1rem 1.25rem 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.terminal__line {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  line-height: 1.6;
  color: #cdd6f4;
}

.terminal__line--output {
  color: #a6adc8;
  padding-left: 1.25rem;
}

.terminal__line--highlight {
  color: #f9e2af;
  font-weight: 600;
}

.terminal__line--success {
  color: #a6e3a1;
  padding-left: 1.25rem;
}

.terminal__prompt {
  color: #a6e3a1;
  font-weight: 700;
}

.terminal__cmd {
  color: #89b4fa;
}

.terminal__cursor {
  display: inline-block;
  width: 8px;
  height: 15px;
  background: #cdd6f4;
  animation: cursor-blink 1s step-end infinite;
  vertical-align: middle;
}

@keyframes cursor-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* Hero text */
.hero-text {
  text-align: center;
}

.hero-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: white;
  margin-bottom: 0.5rem;
}

.hero-subtitle {
  color: rgba(255, 255, 255, 0.85);
  font-size: 1rem;
}

/* ── Responsive ── */
@media (max-width: 960px) {
  .register-split {
    flex-direction: column-reverse;
  }

  .register-hero-panel {
    padding: 2.5rem 2rem;
    min-height: auto;
  }

  .register-form-panel {
    padding: 2rem 1.5rem;
  }

  .terminal {
    max-width: 420px;
  }
}

@media (max-width: 640px) {
  .register-hero-panel {
    padding: 2rem 1rem;
  }

  .form-heading {
    font-size: 1.5rem;
  }

  .hero-title {
    font-size: 1.25rem;
  }

  .terminal {
    font-size: 0.75rem;
  }
}
</style>

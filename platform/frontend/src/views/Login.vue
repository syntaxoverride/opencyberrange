<template>
  <div class="login-page">
    <div class="login-split">
      <!-- Left: Form Panel -->
      <div class="login-form-panel">
        <div class="form-panel-inner">
          <!-- Brand -->
          <div class="brand">
            <img src="/ocr-logo-dark.png" alt="OpenCyberRange" class="brand-icon" />
            <div class="brand-text">
              <h1 class="brand-title">OpenCyberRange</h1>
              <p class="brand-subtitle">Welcome back</p>
            </div>
          </div>

          <p class="form-subtext">Sign in to continue your training</p>

          <!-- Error Message -->
          <div v-if="errorMessage" class="error-message">
            {{ errorMessage }}
          </div>

          <form @submit.prevent="handleLogin" class="login-form">
            <div class="form-group">
              <label for="username" class="form-label">Username</label>
              <input
                id="username"
                v-model="username"
                type="text"
                class="form-input"
                :class="{ 'form-input--error': errorMessage }"
                placeholder="Enter your username"
                required
                autocomplete="username"
              />
            </div>

            <div class="form-group">
              <label for="password" class="form-label">Password</label>
              <input
                id="password"
                v-model="password"
                type="password"
                class="form-input"
                :class="{ 'form-input--error': errorMessage }"
                placeholder="Enter your password"
                required
                autocomplete="current-password"
              />
            </div>

            <button
              type="submit"
              class="login-button"
              :disabled="loading"
            >
              <span v-if="!loading">Sign In</span>
              <span v-else>Signing In...</span>
            </button>
          </form>

          <div class="register-section">
            <p class="register-text">
              Don't have an account?
              <router-link to="/register" class="register-link">Register here</router-link>
            </p>
          </div>
        </div>
      </div>

      <!-- Right: Illustration Panel -->
      <div class="login-hero-panel">
        <div class="hero-content">
          <!-- CSS Terminal Illustration -->
          <div class="terminal">
            <div class="terminal__titlebar">
              <span class="terminal__dot terminal__dot--red"></span>
              <span class="terminal__dot terminal__dot--yellow"></span>
              <span class="terminal__dot terminal__dot--green"></span>
              <span class="terminal__titlebar-text">root@ocr ~</span>
            </div>
            <div class="terminal__body">
              <div class="terminal__line">
                <span class="terminal__prompt">$</span>
                <span class="terminal__cmd">nmap -sV 10.10.14.0/24</span>
              </div>
              <div class="terminal__line terminal__line--output">
                Starting Nmap scan...
              </div>
              <div class="terminal__line terminal__line--output">
                Discovered 3 hosts on network
              </div>
              <div class="terminal__line terminal__line--output terminal__line--highlight">
                PORT &nbsp;&nbsp;STATE &nbsp;SERVICE
              </div>
              <div class="terminal__line terminal__line--output">
                22 &nbsp;&nbsp;&nbsp;open &nbsp;&nbsp;ssh
              </div>
              <div class="terminal__line terminal__line--output">
                80 &nbsp;&nbsp;&nbsp;open &nbsp;&nbsp;http
              </div>
              <div class="terminal__line terminal__line--output">
                443 &nbsp;&nbsp;open &nbsp;&nbsp;https
              </div>
              <div class="terminal__line">
                <span class="terminal__prompt">$</span>
                <span class="terminal__cmd">ssh admin@10.10.14.12</span>
              </div>
              <div class="terminal__line terminal__line--success">
                Connection established.
              </div>
              <div class="terminal__line">
                <span class="terminal__prompt">$</span>
                <span class="terminal__cursor"></span>
              </div>
            </div>
          </div>

          <div class="hero-text">
            <h2 class="hero-title">Hands-on Cybersecurity Training</h2>
            <p class="hero-subtitle">
              Real labs. Real tools. Real skills.
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, inject } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios' // Use plain axios for login (no token needed)
import { setWikiAuthCookie } from '../utils/wikiAuth'

const router = useRouter()

const username = ref('')
const password = ref('')
const errorMessage = ref('')
const loading = ref(false)


const handleLogin = async () => {
  errorMessage.value = ''
  loading.value = true

  try {
    // Use URLSearchParams for OAuth2 password flow (application/x-www-form-urlencoded)
    const params = new URLSearchParams()
    params.append('username', username.value)
    params.append('password', password.value)

    const response = await axios.post('/api/auth/login', params, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    })

    // Store token and user info
    localStorage.setItem('token', response.data.access_token)
    localStorage.setItem('user', JSON.stringify(response.data.user))

    // Sync the wiki_auth cookie now, in THIS tab. App.vue only refreshes it on
    // mount (token was null then) and on cross-tab storage events (which do not
    // fire in the tab that logged in), so without this a fresh login cannot open
    // the gated course wikis until a full page reload.
    setWikiAuthCookie()

    // Trigger App.vue reactivity update immediately
    const updateAuthState = inject('updateAuthState', null)
    if (updateAuthState) {
      updateAuthState()
    } else if (window.__updateAuthState) {
      window.__updateAuthState()
    }

    // Wait for next tick to ensure Vue reactivity updates
    await nextTick()

    // Small delay to ensure navbar renders before navigation
    await new Promise(resolve => setTimeout(resolve, 100))

    // Redirect to dashboard
    router.push('/dashboard')
  } catch (error) {
    if (error.response?.data?.detail) {
      errorMessage.value = error.response.data.detail
    } else {
      errorMessage.value = 'Login failed. Please check your credentials and try again.'
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  background: var(--bg-primary);
}

.login-split {
  display: flex;
  min-height: 100vh;
}

/* ── Left: Form Panel ── */
.login-form-panel {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 3rem 2rem;
  background: var(--bg-primary);
}

.form-panel-inner {
  width: 100%;
  max-width: 400px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 2rem;
}

.brand-icon {
  width: 96px;
  height: 96px;
  flex-shrink: 0;
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
  margin-bottom: 2rem;
}

/* Error */
.error-message {
  background: var(--danger-bg);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #fca5a5;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  margin-bottom: 1.5rem;
  font-size: 0.875rem;
}

/* Form */
.login-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.form-input {
  width: 100%;
  padding: 0.8rem 1rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 0.9375rem;
  transition: all 0.2s ease;
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

.login-button {
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

.login-button:hover:not(:disabled) {
  background: linear-gradient(135deg, #fb923c, #f97316);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(249, 115, 22, 0.3);
}

.login-button:active:not(:disabled) {
  transform: translateY(0);
}

.login-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Register link */
.register-section {
  margin-top: 2rem;
  text-align: center;
}

.register-text {
  color: var(--text-secondary);
  font-size: 0.875rem;
}

.register-link {
  color: #f97316;
  text-decoration: none;
  font-weight: 500;
  margin-left: 0.25rem;
  transition: color 0.2s ease;
}

.register-link:hover {
  color: #fb923c;
  text-decoration: underline;
}

/* ── Right: Hero / Illustration Panel ── */
.login-hero-panel {
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
.login-hero-panel::before {
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
  .login-split {
    flex-direction: column-reverse;
  }

  .login-hero-panel {
    padding: 2.5rem 2rem;
    min-height: auto;
  }

  .login-form-panel {
    padding: 2rem 1.5rem;
  }

  .terminal {
    max-width: 420px;
  }
}

@media (max-width: 640px) {
  .login-hero-panel {
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

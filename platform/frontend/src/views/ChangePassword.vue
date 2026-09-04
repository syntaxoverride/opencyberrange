<template>
  <div class="change-password-page">
    <div class="change-password-container">
      <div class="header">
        <h1 class="title">OpenCyberRange</h1>
        <p class="subtitle">Change Your Password</p>
        <p class="message">Your password must be changed before you can continue.</p>
      </div>

      <form @submit.prevent="changePassword" class="form">
        <div class="form-group">
          <label for="currentPassword">Current Password</label>
          <div class="input-wrapper">
            <input
              id="currentPassword"
              v-model="form.currentPassword"
              :type="showCurrentPassword ? 'text' : 'password'"
              placeholder="Enter current password"
              class="form-input"
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
        </div>

        <div class="form-group">
          <label for="newPassword">New Password</label>
          <div class="input-wrapper">
            <input
              id="newPassword"
              v-model="form.newPassword"
              :type="showNewPassword ? 'text' : 'password'"
              placeholder="Enter new password"
              class="form-input"
              :class="{ 'error': errors.newPassword }"
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
          <p v-if="errors.newPassword" class="error-message">{{ errors.newPassword }}</p>
          <p v-else-if="form.newPassword && !errors.newPassword" class="help-text">
            Password must be at least 8 characters and contain uppercase, lowercase, and a number.
          </p>
        </div>

        <div class="form-group">
          <label for="confirmPassword">Confirm New Password</label>
          <div class="input-wrapper">
            <input
              id="confirmPassword"
              v-model="form.confirmPassword"
              :type="showConfirmPassword ? 'text' : 'password'"
              placeholder="Confirm new password"
              class="form-input"
              :class="{ 'error': errors.confirmPassword }"
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
          <p v-if="errors.confirmPassword" class="error-message">{{ errors.confirmPassword }}</p>
        </div>

        <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
        <p v-if="successMessage" class="success-message">{{ successMessage }}</p>

        <button type="submit" :disabled="loading" class="btn btn--primary">
          <span v-if="loading">Changing Password...</span>
          <span v-else>Change Password</span>
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import axios from '../api/axios'

const router = useRouter()

const form = reactive({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const errors = reactive({
  newPassword: '',
  confirmPassword: ''
})

const showCurrentPassword = ref(false)
const showNewPassword = ref(false)
const showConfirmPassword = ref(false)
const loading = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

const validateNewPassword = () => {
  errors.newPassword = ''
  if (!form.newPassword) return
  
  if (form.newPassword.length < 8) {
    errors.newPassword = 'Password must be at least 8 characters'
    return
  }
  if (!/[A-Z]/.test(form.newPassword)) {
    errors.newPassword = 'Password must contain at least one uppercase letter'
    return
  }
  if (!/[a-z]/.test(form.newPassword)) {
    errors.newPassword = 'Password must contain at least one lowercase letter'
    return
  }
  if (!/[0-9]/.test(form.newPassword)) {
    errors.newPassword = 'Password must contain at least one number'
    return
  }
}

const validateConfirmPassword = () => {
  errors.confirmPassword = ''
  if (!form.confirmPassword) return
  
  if (form.newPassword !== form.confirmPassword) {
    errors.confirmPassword = 'Passwords do not match'
  }
}

const changePassword = async () => {
  errorMessage.value = ''
  successMessage.value = ''
  
  // Validate
  validateNewPassword()
  validateConfirmPassword()
  
  if (errors.newPassword || errors.confirmPassword) {
    return
  }
  
  if (form.newPassword !== form.confirmPassword) {
    errorMessage.value = 'Passwords do not match'
    return
  }
  
  loading.value = true
  
  try {
    await axios.post('/auth/change-password', {
      current_password: form.currentPassword,
      new_password: form.newPassword,
      confirm_password: form.confirmPassword
    })
    
    successMessage.value = 'Password changed successfully! Redirecting...'
    
    // Update localStorage user object to clear must_change_password flag
    const user = JSON.parse(localStorage.getItem('user') || '{}')
    user.must_change_password = false
    localStorage.setItem('user', JSON.stringify(user))
    
    // Trigger App.vue reactivity update
    if (window.__updateAuthState) {
      window.__updateAuthState()
    }
    
    // Redirect after short delay
    setTimeout(() => {
      router.push('/dashboard')
    }, 1500)
  } catch (error) {
    const detail = error.response?.data?.detail
    if (Array.isArray(detail)) {
      errorMessage.value = detail.map(err => err.msg || JSON.stringify(err)).join('. ')
    } else if (detail) {
      errorMessage.value = detail
    } else {
      errorMessage.value = 'Failed to change password. Please try again.'
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.change-password-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-primary);
  padding: 2rem;
}

.change-password-container {
  background: var(--bg-secondary);
  border-radius: 12px;
  padding: 2.5rem;
  width: 100%;
  max-width: 450px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
}

.header {
  text-align: center;
  margin-bottom: 2rem;
}

.title {
  font-size: 2rem;
  font-weight: 700;
  color: var(--accent);
  margin-bottom: 0.5rem;
}

.subtitle {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.message {
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin-top: 0.5rem;
}

.form {
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

.error-message {
  font-size: 0.875rem;
  color: #dc2626;
  margin-top: 0.25rem;
}

.success-message {
  font-size: 0.875rem;
  color: #10b981;
  margin-top: 0.25rem;
}

.btn {
  padding: 0.75rem 1.5rem;
  border-radius: 6px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  border: none;
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
</style>


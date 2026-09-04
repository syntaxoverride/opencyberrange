<template>
  <transition name="toast-fade">
    <div
      v-if="state.message"
      class="toast"
      :class="`toast--${state.type}`"
      role="status"
      aria-live="polite"
    >
      {{ state.message }}
    </div>
  </transition>
</template>

<script>
import { reactive } from 'vue'

// Global toast channel, modeled on InstructorPanel's showAlert banner.
// Any view imports { showToast } to raise a message; the <Toast /> instance
// rendered by the current view displays it. State lives at module level so
// callers and the component stay in sync without a store.
const state = reactive({ message: '', type: 'success' })
let timer = null

// FastAPI 422 responses hand back Pydantic error arrays or detail objects.
// Normalizing here keeps every caller free to pass e.response?.data?.detail
// straight through.
function normalizeMessage(message) {
  if (Array.isArray(message)) {
    return message.map(err => {
      const field = err.loc?.[err.loc.length - 1] || 'field'
      const msg = err.msg?.replace(/^value is not /i, 'Not ').replace(/^Value error, /i, '') || 'Invalid value'
      return `${field.charAt(0).toUpperCase() + field.slice(1)}: ${msg}`
    }).join('. ')
  }
  if (typeof message === 'object' && message !== null) {
    return message.msg || message.detail || JSON.stringify(message)
  }
  return message
}

export function showToast(message, type = 'success', duration = 4000) {
  state.message = normalizeMessage(message)
  state.type = type
  if (timer) clearTimeout(timer)
  timer = setTimeout(() => { state.message = '' }, duration)
}

export default {
  name: 'Toast',
  setup() {
    return { state }
  }
}
</script>

<style scoped>
.toast {
  position: fixed;
  bottom: 2rem;
  left: 50%;
  transform: translateX(-50%);
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-primary);
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  z-index: 2000;
  max-width: min(90vw, 480px);
  text-align: center;
}

.toast--success {
  border-color: var(--success, #10b981);
}

.toast--error {
  border-color: var(--danger, #ef4444);
  color: var(--danger, #ef4444);
}

.toast--info {
  border-color: var(--accent, #3b82f6);
}

.toast-fade-enter-active,
.toast-fade-leave-active {
  transition: opacity 0.2s ease;
}

.toast-fade-enter-from,
.toast-fade-leave-to {
  opacity: 0;
}
</style>

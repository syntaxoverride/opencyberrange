import { ref } from 'vue'

const STORAGE_KEY = 'privacy-mode'

// Shared state across all components that call usePrivacy()
const privacyMode = ref(localStorage.getItem(STORAGE_KEY) === 'on')

function maskUsername(name) {
  if (!name) return ''
  if (!privacyMode.value) return name
  if (name.length <= 2) return name
  return name[0] + '\u2022'.repeat(name.length - 2) + name[name.length - 1]
}

function maskEmail(email) {
  if (!email) return ''
  if (!privacyMode.value) return email
  const [local, domain] = email.split('@')
  if (!domain) return email[0] + '\u2022\u2022\u2022'
  return local[0] + '\u2022\u2022\u2022@' + domain[0] + '\u2022\u2022\u2022.' + domain.split('.').pop()
}

function togglePrivacy() {
  privacyMode.value = !privacyMode.value
  localStorage.setItem(STORAGE_KEY, privacyMode.value ? 'on' : 'off')
}

export function usePrivacy() {
  return { privacyMode, maskUsername, maskEmail, togglePrivacy }
}

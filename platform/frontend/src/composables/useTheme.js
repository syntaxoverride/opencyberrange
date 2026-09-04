import { ref, watch } from 'vue'

const STORAGE_KEY = 'theme'
const DARK = 'dark'
const LIGHT = 'light'

// Shared state across all components that call useTheme()
const theme = ref(getInitialTheme())
const isDark = ref(theme.value === DARK)

function getInitialTheme() {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === DARK || stored === LIGHT) return stored
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? DARK : LIGHT
}

function applyTheme(value) {
  document.documentElement.setAttribute('data-theme', value)
  localStorage.setItem(STORAGE_KEY, value)
}

// Apply on module load
applyTheme(theme.value)

// Listen for system preference changes (only when no stored preference)
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
  if (!localStorage.getItem(STORAGE_KEY)) {
    theme.value = e.matches ? DARK : LIGHT
  }
})

watch(theme, (val) => {
  isDark.value = val === DARK
  applyTheme(val)
})

export function useTheme() {
  const toggleTheme = () => {
    theme.value = theme.value === DARK ? LIGHT : DARK
  }

  return { theme, isDark, toggleTheme }
}

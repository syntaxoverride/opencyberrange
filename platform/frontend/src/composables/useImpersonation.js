/**
 * Composable for managing "View As" impersonation sessions.
 *
 * Stores original session in sessionStorage so it survives page refreshes
 * but is cleared when the tab closes.
 */

import { ref, computed } from 'vue'

const ORIGINAL_SESSION_KEY = 'ocr_original_session'
const IMPERSONATION_KEY = 'ocr_impersonating'

// Reactive state (module-level singleton)
const impersonating = ref(
  sessionStorage.getItem(IMPERSONATION_KEY) === 'true'
)
const impersonationMeta = ref(
  JSON.parse(sessionStorage.getItem('ocr_imp_meta') || 'null')
)

export function useImpersonation() {
  const isImpersonating = computed(() => impersonating.value)

  /**
   * Start impersonation: save current session, swap in impersonation token.
   * @param {string} token - Impersonation JWT
   * @param {object} impUser - Impersonated user object
   * @param {object} originalUser - Original user object
   * @param {string} mode - "user" | "role_course" | "role_global"
   * @param {number|null} courseId
   * @param {string|null} courseName
   */
  function startImpersonation(token, impUser, originalUser, mode, courseId = null, courseName = null) {
    // Save current real session
    const original = {
      token: localStorage.getItem('token'),
      user: localStorage.getItem('user'),
      returnPath: window.location.pathname + window.location.search,
    }
    sessionStorage.setItem(ORIGINAL_SESSION_KEY, JSON.stringify(original))

    // Swap in impersonation session
    localStorage.setItem('token', token)
    localStorage.setItem('user', JSON.stringify(impUser))

    // Set impersonation flag and metadata
    sessionStorage.setItem(IMPERSONATION_KEY, 'true')
    const meta = {
      originalUser,
      impersonatedUser: impUser,
      mode,
      courseId,
      courseName,
    }
    sessionStorage.setItem('ocr_imp_meta', JSON.stringify(meta))

    // Update reactive state
    impersonating.value = true
    impersonationMeta.value = meta

    // Trigger App.vue reactivity
    if (window.__updateAuthState) window.__updateAuthState()
  }

  /**
   * Exit impersonation: restore the original session.
   * Optionally accepts a fresh token from the exit endpoint.
   */
  async function exitImpersonation(router) {
    const currentToken = localStorage.getItem('token')

    // Call exit endpoint to get a fresh token for original user
    try {
      const res = await fetch('/api/auth/impersonate/exit', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${currentToken}`,
          'Content-Type': 'application/json',
        },
      })

      if (res.ok) {
        const data = await res.json()
        localStorage.setItem('token', data.access_token)
        localStorage.setItem('user', JSON.stringify(data.user))
      } else {
        // Fallback: restore from saved session
        _restoreFromSaved()
      }
    } catch {
      // Fallback: restore from saved session
      _restoreFromSaved()
    }

    // Get the return path before clearing
    const saved = JSON.parse(sessionStorage.getItem(ORIGINAL_SESSION_KEY) || '{}')
    const returnPath = saved.returnPath || '/dashboard'

    // Clean up impersonation state
    sessionStorage.removeItem(ORIGINAL_SESSION_KEY)
    sessionStorage.removeItem(IMPERSONATION_KEY)
    sessionStorage.removeItem('ocr_imp_meta')

    impersonating.value = false
    impersonationMeta.value = null

    // Trigger App.vue reactivity
    if (window.__updateAuthState) window.__updateAuthState()

    // Navigate back
    if (router) {
      router.push(returnPath)
    }
  }

  function _restoreFromSaved() {
    const saved = JSON.parse(sessionStorage.getItem(ORIGINAL_SESSION_KEY) || '{}')
    if (saved.token) {
      localStorage.setItem('token', saved.token)
    }
    if (saved.user) {
      localStorage.setItem('user', saved.user)
    }
  }

  /**
   * Check if a 403 response is an impersonation block.
   * Useful in API call error handlers to show a toast.
   */
  function isImpersonationBlock(response) {
    return response?.status === 403 && response?.headers?.get('X-Impersonating') === 'true'
  }

  return {
    isImpersonating,
    impersonationMeta,
    startImpersonation,
    exitImpersonation,
    isImpersonationBlock,
  }
}

import axios from 'axios'

// Create axios instance with default config
const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor to handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // If impersonating and token expired, restore original session
      const imp = sessionStorage.getItem('ocr_impersonating') === 'true'
      if (imp) {
        const saved = JSON.parse(sessionStorage.getItem('ocr_original_session') || '{}')
        if (saved.token) {
          localStorage.setItem('token', saved.token)
          if (saved.user) localStorage.setItem('user', saved.user)
        }
        sessionStorage.removeItem('ocr_impersonating')
        sessionStorage.removeItem('ocr_original_session')
        sessionStorage.removeItem('ocr_imp_meta')
        window.location.href = '/dashboard'
      } else {
        // Token expired or invalid - redirect to login
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default api

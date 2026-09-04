import { createRouter, createWebHistory } from 'vue-router'
import { ensureModules, isModuleEnabled } from '../composables/useModules'

const ROLE_HIERARCHY = { student: 0, instructor: 1, admin: 2 }

function userHasRole(required) {
  try {
    const user = JSON.parse(localStorage.getItem('user') || '{}')
    const userLevel = ROLE_HIERARCHY[user.role] ?? 0
    const requiredLevel = ROLE_HIERARCHY[required] ?? 0
    return userLevel >= requiredLevel
  } catch {
    return false
  }
}

const routes = [
  {
    path: '/',
    redirect: '/dashboard'
  },
  {
    path: '/setup',
    name: 'Setup',
    component: () => import('../views/Setup.vue'),
    meta: { guest: true }
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { guest: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/Register.vue'),
    meta: { guest: true }
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../views/DashboardRouter.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/vpn-setup',
    name: 'VPNSetup',
    component: () => import('../views/Dashboard.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/exercises',
    name: 'Exercises',
    component: () => import('../views/Curriculum.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/workbooks',
    name: 'Workbooks',
    component: () => import('../views/WorkbooksLanding.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/exercises/:trackSlug',
    name: 'TrackDetail',
    component: () => import('../views/TrackDetail.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/labs',
    name: 'Labs',
    redirect: '/exercises'  // Redirect old labs route to exercises
  },
  {
    path: '/curriculum',
    name: 'Curriculum',
    redirect: '/exercises'  // Redirect old curriculum route to exercises
  },
  {
    path: '/courses',
    name: 'Courses',
    component: () => import('../views/CourseList.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/courses/:id',
    name: 'CourseDetail',
    component: () => import('../views/Course.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/instructor',
    name: 'Instructor',
    component: () => import('../views/InstructorPanel.vue'),
    meta: { requiresAuth: true, requiresInstructor: true }
  },
  
  {
    path: '/admin',
    name: 'Admin',
    component: () => import('../views/Admin.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/change-password',
    name: 'ChangePassword',
    component: () => import('../views/ChangePassword.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('../views/Profile.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/rangebox',
    name: 'RangeBox',
    component: () => import('../views/RangeBoxView.vue'),
    meta: { requiresAuth: true }
  },
  ]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation guard with setup check
let setupChecked = false
let setupComplete = true

router.beforeEach(async (to, from, next) => {
  // Check setup status once per session
  if (!setupChecked && to.path !== '/setup') {
    try {
      const res = await fetch('/api/setup/status')
      const data = await res.json()
      setupComplete = data.setup_complete
      setupChecked = true
    } catch {
      setupChecked = true
    }
  }

  // Redirect to setup if not complete
  if (!setupComplete && to.path !== '/setup') {
    return next('/setup')
  }

  const token = localStorage.getItem('token')

  if (to.meta.requiresAuth && !token) {
    next('/login')
  } else if (to.meta.guest && token) {
    next('/dashboard')
  } else if (to.meta.requiresAdmin && !userHasRole('admin')) {
    next('/dashboard')
  } else if (to.meta.requiresInstructor && !userHasRole('instructor')) {
    next('/dashboard')
  } else if (to.meta.module) {
    // Module route guard: fail closed. A module route is only reachable when
    // the modules API affirmatively reports the module enabled. Answers come
    // from the shared useModules cache, so this fetches once per session
    // instead of once per navigation; a failed load redirects to the dashboard.
    try {
      const loaded = await ensureModules()
      if (!loaded || !isModuleEnabled(to.meta.module)) {
        return next('/dashboard')
      }
    } catch {
      return next('/dashboard')
    }
    next()
  } else {
    // Check if user must change password (except when already on change-password page)
    // Skip during impersonation — impersonated users don't change passwords
    const user = JSON.parse(localStorage.getItem('user') || '{}')
    const imp = sessionStorage.getItem('ocr_impersonating') === 'true'
    if (token && user.must_change_password && !imp && to.path !== '/change-password') {
      next('/change-password')
    } else {
      next()
    }
  }
})

export default router

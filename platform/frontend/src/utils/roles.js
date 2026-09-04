/**
 * Role hierarchy helpers for the three-tier RBAC system.
 * Roles: student < instructor < admin
 */

const ROLE_HIERARCHY = { student: 0, instructor: 1, admin: 2 }

export function getUserRole() {
  try {
    const user = JSON.parse(localStorage.getItem('user') || '{}')
    return user.role || 'student'
  } catch {
    return 'student'
  }
}

/**
 * Check if current user has at least the required role level.
 * hasRole('instructor') returns true for instructors and admins.
 */
export function hasRole(required) {
  return (ROLE_HIERARCHY[getUserRole()] || 0) >= (ROLE_HIERARCHY[required] || 0)
}

export function isAdmin() {
  return getUserRole() === 'admin'
}

export function isInstructor() {
  return hasRole('instructor')
}

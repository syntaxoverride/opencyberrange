<template>
  <component :is="dashboard" />
</template>

<script setup>
import { computed, defineAsyncComponent } from 'vue'

// Role-split so a student never downloads the instructor dashboard (which pulls
// chart.js for its sparkline). Each dashboard is its own lazy chunk, fetched
// only for the role that lands here.
const InstructorDashboard = defineAsyncComponent(() => import('./InstructorDashboard.vue'))
const StudentDashboard = defineAsyncComponent(() => import('./StudentDashboard.vue'))

const showInstructorDashboard = computed(() => {
  try {
    const user = JSON.parse(localStorage.getItem('user') || '{}')
    return ['instructor', 'admin'].includes(user.role)
  } catch {
    return false
  }
})

const dashboard = computed(() => showInstructorDashboard.value ? InstructorDashboard : StudentDashboard)
</script>

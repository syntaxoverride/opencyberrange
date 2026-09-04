<template>
  <div v-if="isImpersonating" class="imp-banner">
    <div class="imp-banner__content">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="imp-banner__icon">
        <path d="M1 12S5 4 12 4S23 12 23 12S19 20 12 20S1 12 1 12Z"/>
        <circle cx="12" cy="12" r="3"/>
      </svg>
      <div class="imp-banner__text">
        <strong>VIEWING AS:</strong>
        <span class="imp-banner__target">{{ targetLabel }}</span>
        <span v-if="courseName" class="imp-banner__course">&mdash; {{ courseName }}</span>
        <span class="imp-banner__readonly">Read-only mode. Actions like launching labs are disabled.</span>
      </div>
      <button @click="handleExit" class="imp-banner__exit" :disabled="exiting">
        {{ exiting ? 'Exiting...' : 'Exit Preview' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useImpersonation } from '../composables/useImpersonation'

const router = useRouter()
const { isImpersonating, impersonationMeta, exitImpersonation } = useImpersonation()

const exiting = ref(false)

const targetLabel = computed(() => {
  const meta = impersonationMeta.value
  if (!meta) return 'Unknown'
  const user = meta.impersonatedUser
  if (!user) return 'Unknown'
  const role = (user.role || 'student').charAt(0).toUpperCase() + (user.role || 'student').slice(1)
  return `${user.username} (${role})`
})

const courseName = computed(() => {
  return impersonationMeta.value?.courseName || null
})

async function handleExit() {
  exiting.value = true
  try {
    await exitImpersonation(router)
  } finally {
    exiting.value = false
  }
}
</script>

<style scoped>
.imp-banner {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 9999;
  background: #f59e0b;
  color: #78350f;
  font-size: 0.8125rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.imp-banner__content {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 1.25rem;
  max-width: 100%;
}

.imp-banner__icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  stroke: #78350f;
}

.imp-banner__text {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  line-height: 1.4;
}

.imp-banner__target {
  font-weight: 600;
}

.imp-banner__course {
  font-weight: 500;
}

.imp-banner__readonly {
  opacity: 0.8;
  font-size: 0.75rem;
}

.imp-banner__exit {
  flex-shrink: 0;
  background: #78350f;
  color: #fef3c7;
  border: none;
  padding: 0.375rem 1rem;
  border-radius: 6px;
  font-size: 0.8125rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}

.imp-banner__exit:hover:not(:disabled) {
  background: #451a03;
  color: #fff;
}

.imp-banner__exit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 640px) {
  .imp-banner__readonly {
    display: none;
  }
}
</style>

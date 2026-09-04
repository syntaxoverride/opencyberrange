<template>
  <div class="rangebox-page">
    <RangeBox
      v-if="ready"
      :session-id="sessionId"
      :standalone="isStandalone"
      :image-name="imageName"
      :admin-target-user-id="adminTargetUserId"
    />
    <div v-else class="rangebox-page__error">
      <p>Missing session or standalone parameter.</p>
      <p class="rangebox-page__hint">This page is opened from an active exercise or the dashboard.</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import RangeBox from '../components/RangeBox.vue'

const route = useRoute()

const sessionId = computed(() => {
  const id = route.query.session
  return id ? Number(id) : null
})

const isStandalone = computed(() => route.query.standalone === 'true')

const imageName = computed(() => route.query.image || '')

// Admin mode: viewing a student's RangeBox
const adminTargetUserId = computed(() => {
  const id = route.query.userId
  return id ? Number(id) : null
})

const ready = computed(() => sessionId.value || isStandalone.value)
</script>

<style scoped>
.rangebox-page {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: #0a0a1a;
  z-index: 9999;
}

.rangebox-page :deep(.rangebox) {
  height: 100vh;
  border: none;
  border-radius: 0;
  margin: 0;
}

.rangebox-page :deep(.rangebox__viewport) {
  min-height: 0;
  flex: 1;
}

.rangebox-page__error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
  color: #a0a0c0;
  font-size: 1.1rem;
}

.rangebox-page__hint {
  font-size: 0.85rem;
  color: #606080;
  margin-top: 0.5rem;
}
</style>

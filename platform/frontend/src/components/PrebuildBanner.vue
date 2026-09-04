<template>
  <transition name="fade">
    <div v-if="prebuild.active && !dismissed" class="prebuild-banner">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex:none;"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
      <span>Lab environments are finishing setup<template v-if="prebuild.total"> ({{ prebuild.done }}/{{ prebuild.total }} ready)</template>. Exercises not yet built will show &ldquo;preparing&rdquo; for a few minutes.</span>
      <button @click="dismissed = true" class="prebuild-banner__x" aria-label="Dismiss">&times;</button>
    </div>
  </transition>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import axios from '../api/axios'

// Self-contained so any view can drop it in with <PrebuildBanner />. Polls the
// same endpoint the dashboard banner uses, and stops polling once the pre-build
// is no longer active so it quietly disappears on a settled install.
const prebuild = ref({ active: false, total: 0, done: 0 })
const dismissed = ref(false)
let timer = null

const fetchStatus = async () => {
  try {
    const { data } = await axios.get('/labs/prebuild-status')
    prebuild.value = data
    if (!data.active && timer) { clearInterval(timer); timer = null }
  } catch (e) { /* endpoint absent on older backends; leave the banner hidden */ }
}

onMounted(() => {
  fetchStatus()
  timer = setInterval(fetchStatus, 15000)
})
onUnmounted(() => { if (timer) clearInterval(timer) })
</script>

<style scoped>
.prebuild-banner {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin: 0 0 1.25rem;
  padding: 0.7rem 1rem;
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.28);
  border-radius: 10px;
  color: #cfe0ff;
  font-size: 0.85rem;
}
.prebuild-banner__x {
  margin-left: auto;
  background: transparent;
  border: none;
  color: inherit;
  font-size: 1.2rem;
  line-height: 1;
  cursor: pointer;
  opacity: 0.7;
  padding: 0 0.25rem;
}
.prebuild-banner__x:hover { opacity: 1; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.25s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>

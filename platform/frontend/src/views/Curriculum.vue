<template>
  <div class="exercises-page">
    <!-- Background lab pre-build banner (fresh installs) -->
    <PrebuildBanner />

    <!-- Hub Header -->
    <div class="hub-header">
      <h1 class="page-title">Exercises</h1>
      <p class="page-subtitle">Master cybersecurity through structured, hands-on exercises</p>
    </div>

    <!-- Overall Progress Summary -->
    <div v-if="tracks.length > 0" class="progress-summary">
      <div class="progress-summary__stat">
        <span class="progress-summary__value">{{ totalCompleted }}</span>
        <span class="progress-summary__label">Completed</span>
      </div>
      <div class="progress-summary__stat">
        <span class="progress-summary__value">{{ totalLabs }}</span>
        <span class="progress-summary__label">Total Exercises</span>
      </div>
      <div class="progress-summary__stat">
        <span class="progress-summary__value">{{ overallPercent }}%</span>
        <span class="progress-summary__label">Overall Progress</span>
      </div>
    </div>

    <!-- Track Cards Grid -->
    <div class="track-grid" ref="gridRef">
      <div
        v-for="track in tracks"
        :key="track.id"
        class="track-card-wrapper"
        :class="{ 'track-card-wrapper--reorderable': canReorder }"
        :data-id="track.id"
      >
        <!-- Drag handle (admin/instructor only) -->
        <div v-if="canReorder" class="track-card__drag-handle drag-handle" title="Drag to reorder">
          <svg viewBox="0 0 16 16" fill="currentColor"><circle cx="5" cy="3" r="1.25"/><circle cx="11" cy="3" r="1.25"/><circle cx="5" cy="8" r="1.25"/><circle cx="11" cy="8" r="1.25"/><circle cx="5" cy="13" r="1.25"/><circle cx="11" cy="13" r="1.25"/></svg>
        </div>
        <router-link
          :to="`/exercises/${track.slug}`"
          class="track-card"
          :style="{ '--track-color': track.color }"
        >
          <div class="track-card__icon">
            <component :is="getTrackIcon(track.icon)" />
          </div>
          <div class="track-card__body">
            <h3 class="track-card__title">{{ track.name }}</h3>
            <p class="track-card__description">{{ track.description }}</p>
            <div class="track-card__stats-row">
              <span class="track-card__stat">
                {{ track.completed_labs }}/{{ track.total_labs }} exercises
              </span>
              <span v-if="track.current_level" class="track-card__level">
                Level {{ track.current_level }}
              </span>
              <span v-if="track.is_complete" class="track-card__complete-badge">Complete</span>
            </div>
            <div class="track-card__progress">
              <div
                class="track-card__progress-bar"
                :style="{ width: track.progress_percent + '%' }"
              ></div>
            </div>
          </div>
          <div class="track-card__arrow">
            <ChevronRightIcon />
          </div>
        </router-link>
      </div>
    </div>

    <!-- Empty State -->
    <div v-if="!loading && tracks.length === 0" class="empty-state">
      <p>No learning paths available yet. Check back soon.</p>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-overlay">
      <div class="spinner"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from '../api/axios'
import { isAdmin, isInstructor } from '../utils/roles'
import Sortable from 'sortablejs'

import { getTrackIcon } from '../components/icons/trackIcons.js'
import ChevronRightIcon from '../components/icons/ChevronIcon.vue'
import PrebuildBanner from '../components/PrebuildBanner.vue'

const route = useRoute()
const router = useRouter()

const tracks = ref([])
const loading = ref(false)
const gridRef = ref(null)

const canReorder = computed(() => isAdmin() || isInstructor())

const totalCompleted = computed(() => tracks.value.reduce((sum, t) => sum + t.completed_labs, 0))
const totalLabs = computed(() => tracks.value.reduce((sum, t) => sum + t.total_labs, 0))
const overallPercent = computed(() => {
  if (totalLabs.value === 0) return 0
  return Math.round((totalCompleted.value / totalLabs.value) * 100)
})

// ── SortableJS drag-and-drop ─────────────────────────────────────────
let sortableInstance = null

const initSortable = () => {
  if (sortableInstance) { sortableInstance.destroy(); sortableInstance = null }
  if (!gridRef.value || !canReorder.value) return

  sortableInstance = Sortable.create(gridRef.value, {
    animation: 150,
    handle: '.drag-handle',
    ghostClass: 'track-card-wrapper--ghost',
    chosenClass: 'track-card-wrapper--chosen',
    dragClass: 'track-card-wrapper--drag',
    filter: 'a',              // don't start drag from links
    preventOnFilter: false,   // still allow link clicks
    onEnd: async (evt) => {
      if (evt.oldIndex === evt.newIndex) return
      // Undo SortableJS DOM mutation — put the node back so Vue stays in control
      const { from, item, oldIndex, newIndex } = evt
      from.removeChild(item)
      if (oldIndex < from.children.length) {
        from.insertBefore(item, from.children[oldIndex])
      } else {
        from.appendChild(item)
      }
      // Now update Vue state — Vue will re-render the correct order
      const moved = tracks.value.splice(oldIndex, 1)[0]
      tracks.value.splice(newIndex, 0, moved)
      // Persist
      try {
        await axios.put('/admin/curriculum/tracks/reorder', {
          ordered_ids: tracks.value.map(t => t.id)
        })
      } catch (err) {
        console.error('Failed to save track order:', err)
        await fetchTracks()
      }
    }
  })
}

onBeforeUnmount(() => {
  if (sortableInstance) { sortableInstance.destroy(); sortableInstance = null }
})

// ── Data fetching ────────────────────────────────────────────────────
const fetchTracks = async () => {
  loading.value = true
  try {
    const token = localStorage.getItem('token')
    if (!token) {
      router.push('/login')
      return
    }
    const { data } = await axios.get('/exercises/tracks', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    tracks.value = data.tracks || []
  } catch (error) {
    console.error('Failed to fetch tracks:', error)
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      router.push('/login')
    }
    tracks.value = []
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  // Handle deep-link from Course page: /exercises?labId=123&courseId=1
  const labId = route.query.labId
  const courseId = route.query.courseId
  const wikiSlug = route.query.wikiSlug
  if (labId) {
    try {
      const token = localStorage.getItem('token')
      const params = courseId ? { course_id: courseId } : {}
      const { data } = await axios.get(`/exercises/labs/${labId}`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
        params
      })
      const query = { labId }
      if (courseId) query.courseId = courseId
      if (wikiSlug) query.wikiSlug = wikiSlug
      if (data.track?.slug) {
        router.replace({ path: `/exercises/${data.track.slug}`, query })
        return
      }
      await fetchTracks()
      if (tracks.value.length > 0) {
        router.replace({ path: `/exercises/${tracks.value[0].slug}`, query })
        return
      }
    } catch (e) {
      console.error('Failed to resolve lab track for deep-link:', e)
    }
  }
  await fetchTracks()
  await nextTick()
  initSortable()
})
</script>

<style scoped>
.exercises-page {
  min-height: 100vh;
  padding: 2rem;
  background: var(--bg-primary);
}

/* Hub Header */
.hub-header {
  text-align: center;
  margin-bottom: 2rem;
}

.page-title {
  font-size: 2.5rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.page-subtitle {
  color: var(--text-secondary);
  font-size: 1.1rem;
}

/* Progress Summary */
.progress-summary {
  display: flex;
  justify-content: center;
  gap: 3rem;
  margin-bottom: 2.5rem;
  padding: 1.25rem 2rem;
  background: var(--bg-secondary);
  border-radius: 12px;
  max-width: 480px;
  margin-left: auto;
  margin-right: auto;
}

.progress-summary__stat {
  text-align: center;
}

.progress-summary__value {
  display: block;
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--text-primary);
}

.progress-summary__label {
  font-size: 0.75rem;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Track Grid */
.track-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 1rem;
  max-width: 1200px;
  margin: 0 auto;
}

/* Wrapper for drag-and-drop */
.track-card-wrapper {
  position: relative;
  border-radius: 12px;
  transition: transform 0.15s ease, opacity 0.15s ease;
}

/* SortableJS drag states */
.track-card-wrapper--ghost {
  opacity: 0.3;
}

.track-card-wrapper--chosen {
  outline: 2px solid var(--accent, #3b82f6);
  outline-offset: 2px;
  border-radius: 14px;
}

.track-card-wrapper--drag {
  opacity: 0.9;
  transform: scale(1.02);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
  border-radius: 12px;
}

/* Reorderable wrapper gets left padding for handle */
.track-card-wrapper--reorderable {
  padding-left: 28px;
}

/* Drag handle */
.track-card__drag-handle {
  position: absolute;
  top: 50%;
  left: 4px;
  transform: translateY(-50%);
  width: 22px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: grab;
  touch-action: none;
  color: var(--text-muted);
  opacity: 0.35;
  transition: opacity 0.15s ease, color 0.15s ease;
  z-index: 2;
  border-radius: 4px;
}

.track-card__drag-handle:active {
  cursor: grabbing;
}

.track-card__drag-handle svg {
  width: 14px;
  height: 14px;
}

.track-card-wrapper:hover .track-card__drag-handle {
  opacity: 0.7;
}

.track-card__drag-handle:hover {
  opacity: 1 !important;
  color: var(--text-primary);
  background: var(--bg-tertiary);
}

.track-card {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  background: var(--bg-secondary);
  border: 2px solid transparent;
  border-radius: 12px;
  padding: 1.5rem;
  cursor: pointer;
  transition: all 0.2s ease;
  text-decoration: none;
  color: inherit;
}

.track-card:hover {
  border-color: var(--track-color);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.track-card__icon {
  width: 56px;
  height: 56px;
  min-width: 56px;
  background: var(--bg-tertiary);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--track-color);
}

.track-card__icon svg {
  width: 32px;
  height: 32px;
}

.track-card__body {
  flex: 1;
  min-width: 0;
}

.track-card__title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.25rem;
}

.track-card__description {
  font-size: 0.8125rem;
  color: var(--text-secondary);
  margin-bottom: 0.75rem;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.track-card__stats-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}

.track-card__stat {
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.track-card__level {
  font-size: 0.75rem;
  color: var(--text-muted);
  background: var(--bg-tertiary);
  padding: 0.125rem 0.5rem;
  border-radius: 4px;
}

.track-card__complete-badge {
  font-size: 0.75rem;
  color: var(--success);
  background: rgba(34, 197, 94, 0.15);
  padding: 0.125rem 0.5rem;
  border-radius: 4px;
  font-weight: 500;
}

.track-card__progress {
  height: 4px;
  background: var(--bg-tertiary);
  border-radius: 2px;
  overflow: hidden;
}

.track-card__progress-bar {
  height: 100%;
  background: var(--track-color);
  transition: width 0.3s ease;
}

.track-card__arrow {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  color: var(--text-muted);
  transition: transform 0.2s ease;
  transform: rotate(-90deg);
}

.track-card:hover .track-card__arrow {
  color: var(--track-color);
  transform: rotate(-90deg) translateY(2px);
}

.track-card__arrow svg {
  width: 24px;
  height: 24px;
}

/* Empty State */
.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  color: var(--text-secondary);
  font-size: 1.1rem;
}

/* Loading */
.loading-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--bg-tertiary);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Responsive */
@media (max-width: 768px) {
  .exercises-page {
    padding: 1rem;
  }

  .track-grid {
    grid-template-columns: 1fr;
  }

  .progress-summary {
    gap: 1.5rem;
    padding: 1rem;
  }

  .track-card__drag-handle {
    display: none;
  }
}
</style>

<template>
  <div class="wb-page">
    <header class="wb-head">
      <h1 class="wb-title">Workbooks</h1>
      <p class="wb-sub">Step-by-step guides for every track on this range. Open one to read the full walkthrough, or reach an individual exercise's workbook from its page.</p>
    </header>

    <div v-if="loading" class="wb-state">Loading workbooks...</div>

    <div v-else-if="!workbooks.length" class="wb-state">
      No workbooks are available yet.
    </div>

    <div v-else ref="gridRef" class="wb-grid">
      <div
        v-for="wb in workbooks"
        :key="wb.id"
        class="wb-card"
        :data-id="wb.id"
        @click="open(wb)"
      >
        <div class="wb-card__top">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" class="wb-card__icon">
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
          </svg>
          <div class="wb-card__top-right">
            <span class="wb-card__badge" :class="'wb-card__badge--' + wb.type">{{ wb.type === 'course' ? 'Course' : 'Range' }}</span>
            <span v-if="canReorder" class="wb-card__drag" title="Drag to reorder" @click.stop>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="9" cy="6" r="1"/><circle cx="9" cy="12" r="1"/><circle cx="9" cy="18" r="1"/><circle cx="15" cy="6" r="1"/><circle cx="15" cy="12" r="1"/><circle cx="15" cy="18" r="1"/></svg>
            </span>
          </div>
        </div>
        <div class="wb-card__name">{{ wb.name }}</div>
        <div class="wb-card__meta">{{ wb.exercises }} {{ wb.exercises === 1 ? 'exercise' : 'exercises' }}</div>
        <div class="wb-card__open">
          Open workbook
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="wb-card__arrow">
            <line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>
          </svg>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, onUnmounted } from 'vue'
import api from '../api/axios'
import Sortable from 'sortablejs'
import { setWikiAuthCookie } from '../utils/wikiAuth'

const workbooks = ref([])
const loading = ref(true)
const gridRef = ref(null)
let sortable = null

// Reordering writes the shared track order, so it is admin-only (mirrors the
// Exercises track reorder).
const canReorder = (() => {
  try {
    const u = JSON.parse(localStorage.getItem('user') || '{}')
    return u.is_admin === true || u.role === 'admin'
  } catch { return false }
})()


function open(wb) {
  setWikiAuthCookie()
  window.open(wb.url, '_blank')
}

function initSortable() {
  if (!canReorder || !gridRef.value || sortable) return
  sortable = Sortable.create(gridRef.value, {
    handle: '.wb-card__drag',
    animation: 150,
    ghostClass: 'wb-card--ghost',
    onEnd: async (evt) => {
      if (evt.oldIndex === evt.newIndex) return
      // Undo SortableJS's DOM move so Vue stays authoritative, then reorder state.
      const { from, item, oldIndex, newIndex } = evt
      from.removeChild(item)
      if (oldIndex < from.children.length) from.insertBefore(item, from.children[oldIndex])
      else from.appendChild(item)
      const moved = workbooks.value.splice(oldIndex, 1)[0]
      workbooks.value.splice(newIndex, 0, moved)
      try {
        await api.put('/admin/curriculum/tracks/reorder', {
          ordered_ids: workbooks.value.map(w => w.id),
        })
      } catch {
        await load()
      }
    },
  })
}

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/exercises/workbooks')
    workbooks.value = data.workbooks || []
  } catch {
    workbooks.value = []
  } finally {
    loading.value = false
  }
  // Init AFTER loading clears so the v-else grid is actually in the DOM.
  await nextTick()
  initSortable()
}

onMounted(load)
onUnmounted(() => { if (sortable) { sortable.destroy(); sortable = null } })
</script>

<style scoped>
.wb-page {
  max-width: 1100px;
  margin: 0 auto;
  padding: 2rem 1.5rem 3rem;
}
.wb-head {
  margin-bottom: 1.75rem;
}
.wb-title {
  font-size: 1.75rem;
  font-weight: 700;
  margin: 0 0 0.4rem;
  color: var(--text-primary);
}
.wb-sub {
  color: var(--text-secondary);
  font-size: 0.95rem;
  line-height: 1.55;
  max-width: 640px;
  margin: 0;
}
.wb-state {
  color: var(--text-muted);
  padding: 3rem 0;
  text-align: center;
}
.wb-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 1rem;
}
.wb-card {
  text-align: left;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 1.15rem 1.2rem 1rem;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease;
}
.wb-card:hover {
  border-color: var(--accent);
  box-shadow: 0 10px 26px -18px rgba(0, 0, 0, 0.55);
  transform: translateY(-2px);
}
.wb-card__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.wb-card__icon {
  width: 26px;
  height: 26px;
  color: var(--accent);
}
.wb-card__badge {
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 0.2rem 0.5rem;
  border-radius: 999px;
  color: var(--text-secondary);
  background: var(--bg-tertiary);
}
.wb-card__badge--course {
  color: #a78bfa;
  background: rgba(139, 92, 246, 0.16);
}
.wb-card__top-right {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}
.wb-card__drag {
  display: inline-flex;
  cursor: grab;
  color: var(--text-muted);
  padding: 2px;
  border-radius: 4px;
}
.wb-card__drag:hover {
  color: var(--text-secondary);
  background: var(--bg-tertiary);
}
.wb-card__drag svg {
  width: 16px;
  height: 16px;
}
.wb-card__drag:active {
  cursor: grabbing;
}
.wb-card--ghost {
  opacity: 0.4;
}
.wb-card__name {
  font-size: 1.05rem;
  font-weight: 650;
  color: var(--text-primary);
  line-height: 1.3;
}
.wb-card__meta {
  font-size: 0.83rem;
  color: var(--text-muted);
}
.wb-card__open {
  margin-top: auto;
  padding-top: 0.6rem;
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--accent);
}
.wb-card__arrow {
  width: 15px;
  height: 15px;
  transition: transform 0.15s ease;
}
.wb-card:hover .wb-card__arrow {
  transform: translateX(3px);
}
</style>

<template>
  <div v-if="open" class="gt" role="dialog" aria-modal="true" :aria-label="'Orientation tour'">
    <!-- catches clicks over the spotlight hole so the page behind stays inert -->
    <div class="gt__blocker"></div>
    <!-- Dim + spotlight. Four panels around the target leave a clear hole; a full
         dim is used for centered (anchorless) steps. -->
    <template v-if="rect">
      <div class="gt__mask" :style="{ top: 0, left: 0, width: '100vw', height: rect.top + 'px' }"></div>
      <div class="gt__mask" :style="{ top: rect.top + 'px', left: 0, width: rect.left + 'px', height: rect.height + 'px' }"></div>
      <div class="gt__mask" :style="{ top: rect.top + 'px', left: rect.right + 'px', width: 'calc(100vw - ' + rect.right + 'px)', height: rect.height + 'px' }"></div>
      <div class="gt__mask" :style="{ top: rect.bottom + 'px', left: 0, width: '100vw', height: 'calc(100vh - ' + rect.bottom + 'px)' }"></div>
      <div class="gt__ring" :style="{ top: (rect.top - 4) + 'px', left: (rect.left - 4) + 'px', width: (rect.width + 8) + 'px', height: (rect.height + 8) + 'px' }"></div>
    </template>
    <div v-else class="gt__mask gt__mask--full"></div>

    <!-- Tooltip card -->
    <div class="gt__card" :class="'gt__card--' + placement" :style="cardStyle" ref="cardRef">
      <div class="gt__step">Step {{ idx + 1 }} of {{ steps.length }}</div>
      <h3 class="gt__title">{{ step.title }}</h3>
      <p class="gt__body">{{ step.body }}</p>
      <div class="gt__dots">
        <span v-for="(s, i) in steps" :key="i" class="gt__dot" :class="{ 'gt__dot--on': i === idx }"></span>
      </div>
      <div class="gt__actions">
        <button class="gt__skip" @click="finish(false)">Skip</button>
        <div class="gt__nav">
          <button v-if="idx > 0" class="gt__btn gt__btn--ghost" @click="prev">Back</button>
          <button class="gt__btn gt__btn--primary" @click="next">{{ idx === steps.length - 1 ? 'Finish' : 'Next' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  steps: { type: Array, required: true },
})
const emit = defineEmits(['update:modelValue', 'finish'])

const router = useRouter()
const route = useRoute()

const open = ref(false)
const idx = ref(0)
const rect = ref(null)         // target bounding rect in viewport coords, or null (centered)
const placement = ref('center')
const cardRef = ref(null)
const cardStyle = ref({})

const step = computed(() => props.steps[idx.value] || {})

watch(() => props.modelValue, (v) => {
  open.value = v
  if (v) { idx.value = 0; nextTick(() => applyStep()) }
  else teardownListeners()
})

function reduced() {
  return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

async function applyStep() {
  const s = step.value
  // navigate first if the step lives on another route
  if (s.route && route.path !== s.route) {
    try { await router.push(s.route) } catch (e) { /* redundant nav */ }
    await new Promise(r => setTimeout(r, reduced() ? 150 : 450))
  }
  await locate(s)
  addListeners()
}

// find the anchor (retrying briefly for async-rendered pages), else center
async function locate(s) {
  rect.value = null
  placement.value = s.placement || 'center'
  if (!s.selector) { positionCentered(); return }
  let el = null
  for (let i = 0; i < 12; i++) {
    el = document.querySelector(s.selector)
    if (el && el.getBoundingClientRect().width > 0) break
    await new Promise(r => setTimeout(r, 150))
  }
  if (!el) { rect.value = null; positionCentered(); return }
  el.scrollIntoView({ block: 'center', inline: 'nearest', behavior: reduced() ? 'auto' : 'smooth' })
  await new Promise(r => setTimeout(r, reduced() ? 60 : 320))
  measure(el)
}

function measure(el) {
  const b = el.getBoundingClientRect()
  rect.value = { top: b.top, left: b.left, right: b.right, bottom: b.bottom, width: b.width, height: b.height }
  positionByRect()
}

function positionByRect() {
  nextTick(() => {
    const r = rect.value
    if (!r) return positionCentered()
    const cw = 340, gap = 16
    const vw = window.innerWidth, vh = window.innerHeight
    let place, top, left
    if (r.right + gap + cw < vw) { place = 'right'; left = r.right + gap; top = clampV(r.top) }
    else if (r.left - gap - cw > 0) { place = 'left'; left = r.left - gap - cw; top = clampV(r.top) }
    else if (r.bottom + gap + 180 < vh) { place = 'bottom'; top = r.bottom + gap; left = clampH(r.left) }
    else { place = 'top'; top = Math.max(gap, r.top - gap - 200); left = clampH(r.left) }
    placement.value = place
    cardStyle.value = { top: top + 'px', left: left + 'px', transform: 'none' }
  })
}
function clampV(t) { return Math.min(Math.max(16, t), window.innerHeight - 240) }
function clampH(l) { return Math.min(Math.max(16, l), window.innerWidth - 356) }
function positionCentered() {
  placement.value = 'center'
  cardStyle.value = { top: '50%', left: '50%', transform: 'translate(-50%, -50%)' }
}

function reposition() {
  const s = step.value
  if (!s.selector) return
  const el = document.querySelector(s.selector)
  if (el) measure(el)
}
function addListeners() {
  window.addEventListener('resize', reposition)
  window.addEventListener('scroll', reposition, true)
  window.addEventListener('keydown', onKey)
}
function teardownListeners() {
  window.removeEventListener('resize', reposition)
  window.removeEventListener('scroll', reposition, true)
  window.removeEventListener('keydown', onKey)
}
function onKey(e) {
  if (e.key === 'Escape') finish(false)
  else if (e.key === 'ArrowRight' || e.key === 'Enter') next()
  else if (e.key === 'ArrowLeft') prev()
}

function next() {
  if (idx.value < props.steps.length - 1) { idx.value++; nextTick(applyStep) }
  else finish(true)
}
function prev() {
  if (idx.value > 0) { idx.value--; nextTick(applyStep) }
}
function finish(completed) {
  teardownListeners()
  open.value = false
  emit('update:modelValue', false)
  emit('finish', { completed })
}

onBeforeUnmount(teardownListeners)
</script>

<style scoped>
.gt { position: fixed; inset: 0; z-index: 10000; }
.gt__blocker { position: fixed; inset: 0; background: transparent; }
.gt__mask { position: fixed; background: rgba(8, 12, 22, 0.62); pointer-events: auto; }
.gt__mask--full { inset: 0; width: 100vw; height: 100vh; }
.gt__ring {
  position: fixed; border: 2px solid #3b82f6; border-radius: 10px;
  box-shadow: 0 0 0 3px rgba(59,130,246,0.35); pointer-events: none;
  transition: all 0.25s ease;
}
@media (prefers-reduced-motion: reduce) { .gt__ring { transition: none; } }

.gt__card {
  position: fixed; width: 340px; max-width: calc(100vw - 32px);
  background: #ffffff; color: #0f172a; border-radius: 14px; padding: 18px 18px 14px;
  box-shadow: 0 18px 50px rgba(0,0,0,0.4); z-index: 10001;
}
.gt__step { font-size: 0.68rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; color: #3b82f6; }
.gt__title { margin: 4px 0 6px; font-size: 1.08rem; font-weight: 800; color: #0f172a; text-wrap: balance; }
.gt__body { margin: 0 0 12px; font-size: 0.9rem; line-height: 1.5; color: #334155; }
.gt__dots { display: flex; gap: 6px; margin-bottom: 12px; }
.gt__dot { width: 7px; height: 7px; border-radius: 50%; background: #cbd5e1; }
.gt__dot--on { background: #3b82f6; }
.gt__actions { display: flex; align-items: center; justify-content: space-between; }
.gt__nav { display: flex; gap: 8px; }
.gt__skip { background: none; border: none; color: #64748b; font-size: 0.82rem; cursor: pointer; padding: 6px 4px; }
.gt__skip:hover { color: #334155; text-decoration: underline; }
.gt__btn { padding: 8px 16px; font-size: 0.85rem; font-weight: 700; border-radius: 8px; cursor: pointer; border: 1px solid transparent; }
.gt__btn--primary { background: #3b82f6; color: #fff; }
.gt__btn--primary:hover { background: #2563eb; }
.gt__btn--ghost { background: transparent; color: #334155; border-color: #cbd5e1; }
.gt__btn--ghost:hover { background: #f1f5f9; }

/* small arrow toward the target */
.gt__card--right::before,
.gt__card--left::before,
.gt__card--top::before,
.gt__card--bottom::before {
  content: ''; position: absolute; width: 12px; height: 12px; background: #fff; transform: rotate(45deg);
}
.gt__card--right::before { left: -6px; top: 22px; }
.gt__card--left::before { right: -6px; top: 22px; }
.gt__card--bottom::before { top: -6px; left: 24px; }
.gt__card--top::before { bottom: -6px; left: 24px; }
</style>

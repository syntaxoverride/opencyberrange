<template>
  <span ref="root" class="infotip" :class="{ 'infotip--below': below }" tabindex="0" role="note" :aria-label="text" @mouseenter="place" @focus="place">
    <span class="infotip__i" aria-hidden="true">i</span>
    <span class="infotip__bubble" :style="{ '--tip-shift': shift + 'px' }">{{ text }}</span>
  </span>
</template>

<script setup>
import { ref } from 'vue'

defineProps({ text: { type: String, required: true } })

// The bubble opens above the trigger by default; near the top of the viewport
// that clips off-screen, so flip it below when there is no headroom. It is also
// centered on the trigger, so a trigger near the right (or left) edge would push
// the bubble off-screen and force it to wrap into a narrow sliver -- clamp it
// back inside the viewport with a horizontal shift and slide the arrow the other
// way so it keeps pointing at the icon.
const root = ref(null)
const below = ref(false)
const shift = ref(0)
const HALF = 138 // half the max bubble width plus a little breathing room
function place() {
  if (!root.value) return
  const r = root.value.getBoundingClientRect()
  below.value = r.top < 220
  const center = r.left + r.width / 2
  const vw = window.innerWidth
  let s = 0
  if (center + HALF > vw - 8) s = (vw - 8) - (center + HALF)
  else if (center - HALF < 8) s = 8 - (center - HALF)
  shift.value = Math.round(s)
}
</script>

<style scoped>
.infotip {
  position: relative; display: inline-flex; align-items: center;
  margin-left: 0.3rem; cursor: help; vertical-align: middle;
}
.infotip__i {
  width: 15px; height: 15px; border-radius: 50%;
  border: 1px solid var(--border-color); color: var(--text-muted);
  font-size: 10px; font-weight: 700; font-style: italic;
  font-family: Georgia, 'Times New Roman', serif;
  display: grid; place-items: center; line-height: 1;
  transition: border-color .12s, color .12s;
}
.infotip:hover .infotip__i,
.infotip:focus-visible .infotip__i { border-color: var(--accent); color: var(--accent); }
.infotip:focus-visible { outline: none; }
.infotip__bubble {
  position: absolute; bottom: calc(100% + 8px); left: 50%;
  transform: translateX(calc(-50% + var(--tip-shift, 0px)));
  width: max-content; max-width: 260px;
  background: var(--bg-tertiary); color: var(--text-primary);
  border: 1px solid var(--border-color); border-radius: 8px;
  padding: 0.5rem 0.65rem; font-size: 0.75rem; font-weight: 400; line-height: 1.45;
  box-shadow: 0 8px 24px -10px rgba(0,0,0,.55);
  opacity: 0; visibility: hidden; transition: opacity .12s;
  z-index: 60; white-space: pre-line; text-align: left; text-transform: none; letter-spacing: normal;
}
.infotip:hover .infotip__bubble,
.infotip:focus-visible .infotip__bubble { opacity: 1; visibility: visible; }
.infotip__bubble::after {
  content: ''; position: absolute; top: 100%;
  left: calc(50% - var(--tip-shift, 0px)); transform: translateX(-50%);
  border: 5px solid transparent; border-top-color: var(--border-color);
}
.infotip--below .infotip__bubble { bottom: auto; top: calc(100% + 8px); }
.infotip--below .infotip__bubble::after {
  top: auto; bottom: 100%;
  left: calc(50% - var(--tip-shift, 0px)); transform: translateX(-50%);
  border-top-color: transparent; border-bottom-color: var(--border-color);
}
</style>

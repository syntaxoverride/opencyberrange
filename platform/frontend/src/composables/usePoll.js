import { onMounted, onUnmounted } from 'vue'

// Interval polling that pauses while the browser tab is hidden and fires an
// immediate refresh on return, so background tabs stop hammering the API but
// the view is never stale when the user comes back.
//
// Usage:
//   const poll = usePoll(load, 10000)                 // starts on mount
//   const poll = usePoll(load, 4000, { auto: false }) // caller drives start()
//   poll.start(); poll.stop()
//
// start/stop express the caller's intent; visibility changes pause and resume
// the timer underneath without losing that intent.
export function usePoll(fn, ms, { auto = true, immediate = false } = {}) {
  let timer = null
  let active = false

  const arm = (fireNow) => {
    if (timer || document.hidden) return
    if (fireNow) fn()
    timer = setInterval(fn, ms)
  }
  const disarm = () => {
    if (timer) { clearInterval(timer); timer = null }
  }
  const start = () => { active = true; arm(immediate) }
  const stop = () => { active = false; disarm() }
  const onVisibility = () => {
    if (document.hidden) disarm()
    else if (active) arm(true)
  }

  onMounted(() => {
    document.addEventListener('visibilitychange', onVisibility)
    if (auto) start()
  })
  onUnmounted(() => {
    stop()
    document.removeEventListener('visibilitychange', onVisibility)
  })

  return { start, stop }
}

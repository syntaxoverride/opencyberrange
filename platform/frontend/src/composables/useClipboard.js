import { ref } from 'vue'

// Clipboard copy with a per-key "copied" flash for button labels.
//
//   const { copied, copyText } = useClipboard()
//   copyText(value, 'lab-password')
//   {{ copied === 'lab-password' ? 'Copied' : 'Copy' }}
export function useClipboard(resetMs = 1500) {
  const copied = ref('')

  async function copyText(value, key = 'default') {
    try {
      await navigator.clipboard.writeText(value)
    } catch (e) {
      // Clipboard can be blocked (permissions, insecure context); the flash
      // still runs so the UI acknowledges the click.
    }
    copied.value = key
    setTimeout(() => { if (copied.value === key) copied.value = '' }, resetMs)
  }

  return { copied, copyText }
}

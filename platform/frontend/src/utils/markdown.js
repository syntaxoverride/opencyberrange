import { marked } from 'marked'
import DOMPurify from 'dompurify'

// The one sanctioned markdown-to-HTML path: parse with marked, sanitize with
// DOMPurify. Every v-html of user or content-authored markdown goes through
// here so the sanitization step can never be forgotten at a call site.
export function renderMarkdown(text) {
  return DOMPurify.sanitize(marked.parse(String(text || '')))
}

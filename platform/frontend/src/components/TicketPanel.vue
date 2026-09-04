<template>
  <div class="ticket-panel">
    <!-- Header -->
    <div class="ticket-header">
      <span class="ticket-number">{{ ticket.ticket_number || 'INC-PENDING' }}</span>
      <span class="ticket-status-badge" :class="'status--' + ticket.ticket_status">
        {{ ticket.ticket_status }}
      </span>
    </div>
    <div class="ticket-meta">
      Assigned to: <strong>{{ userName }}</strong>
    </div>

    <!-- Description (briefing) - collapsible -->
    <details class="ticket-description" open>
      <summary>Incident Description</summary>
      <div class="ticket-description-body" v-html="renderedDescription"></div>
    </details>

    <!-- Milestone Progress Bar -->
    <div class="milestone-bar">
      <div class="milestone-bar__label">
        {{ milestonesMetCount }}/{{ milestonesTotalCount }} milestones
        <span class="milestone-bar__score">{{ score.total }} pts</span>
      </div>
      <div class="milestone-bar__track">
        <div class="milestone-bar__fill" :style="{ width: milestonePercent + '%' }"></div>
      </div>
    </div>

    <!-- Updates -->
    <div class="ticket-updates">
      <h4 class="ticket-section-title">Ticket Updates</h4>
      <div class="ticket-updates-list">
        <div v-for="u in updates" :key="u.id" class="ticket-update">
          <div class="update-header">
            <span class="update-category" :class="'cat--' + u.category">{{ u.category }}</span>
            <span class="update-time">{{ formatTime(u.created_at) }}</span>
          </div>
          <div class="update-content">{{ u.content }}</div>
        </div>
        <p v-if="!updates.length" class="empty-text">No updates yet. Start your investigation and document your findings here.</p>
      </div>
    </div>

    <!-- Add Update Form -->
    <div v-if="exerciseStatus === 'running' || exerciseStatus === 'paused'" class="ticket-add-update">
      <select v-model="newCategory" class="update-category-select">
        <option value="triage">Triage</option>
        <option value="finding">Finding</option>
        <option value="analysis">Analysis</option>
        <option value="action">Action Taken</option>
        <option value="escalation">Escalation</option>
        <option value="status">Status Update</option>
      </select>
      <textarea v-model="newContent" class="update-textarea" placeholder="Document your investigation action. What did you do? What did you find? What is your next step?" rows="4" @keydown.ctrl.enter="submitUpdate"></textarea>
      <button class="btn btn--accent" @click="submitUpdate" :disabled="!newContent.trim()">Add Update</button>
    </div>

    <!-- Attachments -->
    <div v-if="showAttachments" class="ticket-attachments">
      <h4 class="ticket-section-title">Attachments</h4>
      <div class="attachment-tabs">
        <button v-for="tab in attachmentTabs" :key="tab.key"
          class="attachment-tab" :class="{ 'attachment-tab--active': activeAttachment === tab.key }"
          @click="activeAttachment = tab.key">
          {{ tab.label }}
          <span v-if="hasAttachment(tab.key)" class="attachment-check">ok</span>
        </button>
      </div>
      <textarea v-model="attachmentContent[activeAttachment]" class="attachment-textarea"
        :placeholder="attachmentPlaceholder" rows="6"></textarea>
      <button class="btn btn--accent btn--sm" @click="submitAttachment" :disabled="!attachmentContent[activeAttachment]?.trim()">
        Submit {{ activeAttachmentLabel }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const props = defineProps({
  ticket: { type: Object, required: true },
  updates: { type: Array, default: () => [] },
  milestones: { type: Array, default: () => [] },
  attachments: { type: Array, default: () => [] },
  score: { type: Object, default: () => ({ total: 0, max: 0, documentation_bonus: 0 }) },
  exerciseStatus: { type: String, default: 'running' },
  userName: { type: String, default: '' },
  phase: { type: Number, default: 1 },
})

const emit = defineEmits(['submit-update', 'submit-attachment'])

const newCategory = ref('triage')
const newContent = ref('')
const activeAttachment = ref('rules')
const attachmentContent = ref({
  rules: '',
  timeline: '',
  ioc_list: '',
  executive_summary: '',
})

const allAttachmentTabs = [
  { key: 'rules', label: 'Detection Rules' },
  { key: 'timeline', label: 'Attack Timeline' },
  { key: 'ioc_list', label: 'IOC List' },
  { key: 'executive_summary', label: 'Executive Summary' },
]

// Computed

const milestonesMetCount = computed(() => {
  return props.milestones.filter(m => m.status === 'met' || m.status === 'auto_answered').length
})

const milestonesTotalCount = computed(() => {
  return props.milestones.filter(m => !m.is_optional).length
})

const milestonePercent = computed(() => {
  if (milestonesTotalCount.value === 0) return 0
  return Math.round((milestonesMetCount.value / milestonesTotalCount.value) * 100)
})

const showAttachments = computed(() => props.phase >= 2)

const attachmentTabs = computed(() => {
  if (props.phase < 3) {
    return allAttachmentTabs.filter(t => t.key === 'rules')
  }
  return allAttachmentTabs
})

const attachmentPlaceholder = computed(() => {
  const placeholders = {
    rules: 'Paste your Suricata/Snort rules or YARA signatures here.',
    timeline: 'Describe the attack timeline: initial access, lateral movement, exfiltration, etc.',
    ioc_list: 'List indicators of compromise: IPs, domains, file hashes, URLs.',
    executive_summary: 'Write a brief executive summary of the incident and response.',
  }
  return placeholders[activeAttachment.value] || ''
})

const activeAttachmentLabel = computed(() => {
  const tab = allAttachmentTabs.find(t => t.key === activeAttachment.value)
  return tab ? tab.label : ''
})

const renderedDescription = computed(() => {
  if (!props.ticket.description) return ''
  const raw = marked.parse(props.ticket.description)
  return DOMPurify.sanitize(raw)
})

// Methods

function formatTime(isoString) {
  if (!isoString) return ''
  const date = new Date(isoString)
  const now = new Date()
  const diffMs = now - date
  const totalSeconds = Math.max(0, Math.floor(diffMs / 1000))
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `T+${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

function hasAttachment(key) {
  return props.attachments.some(a => a.type === key)
}

function submitUpdate() {
  if (!newContent.value.trim()) return
  emit('submit-update', { category: newCategory.value, content: newContent.value.trim() })
  newContent.value = ''
}

function submitAttachment() {
  const content = attachmentContent.value[activeAttachment.value]
  if (!content?.trim()) return
  emit('submit-attachment', { type: activeAttachment.value, content: content.trim() })
}
</script>

<style scoped>
.ticket-panel {
  display: flex;
  flex-direction: column;
  gap: 0;
  height: 100%;
  overflow-y: auto;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

/* Header */
.ticket-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px 6px;
  border-bottom: 1px solid var(--border-color);
}

.ticket-number {
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: 0.5px;
}

.ticket-status-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.6px;
}

.status--open { background: rgba(239, 68, 68, 0.18); color: #f87171; }
.status--triage { background: rgba(59, 130, 246, 0.18); color: #60a5fa; }
.status--investigating { background: rgba(20, 184, 166, 0.18); color: #2dd4bf; }
.status--containment { background: rgba(245, 158, 11, 0.18); color: #fbbf24; }
.status--closed { background: rgba(34, 197, 94, 0.18); color: #4ade80; }

.ticket-meta {
  padding: 4px 16px 12px;
  font-size: 0.82rem;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-color);
}

.ticket-meta strong {
  color: var(--text-secondary);
}

/* Description */
.ticket-description {
  border-bottom: 1px solid var(--border-color);
}

.ticket-description summary {
  padding: 10px 16px;
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--text-secondary);
  cursor: pointer;
  user-select: none;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.ticket-description summary:hover {
  color: var(--text-primary);
}

.ticket-description-body {
  padding: 0 16px 14px;
  font-size: 0.85rem;
  line-height: 1.6;
  color: var(--text-secondary);
}

.ticket-description-body :deep(p) {
  margin: 0 0 8px;
}

.ticket-description-body :deep(code) {
  background: var(--bg-tertiary);
  padding: 1px 5px;
  border-radius: 3px;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 0.82em;
}

.ticket-description-body :deep(pre) {
  background: var(--bg-tertiary);
  padding: 10px 12px;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 0.82em;
}

.ticket-description-body :deep(ul),
.ticket-description-body :deep(ol) {
  padding-left: 20px;
  margin: 0 0 8px;
}

.ticket-description-body :deep(strong) {
  color: var(--text-primary);
}

/* Milestone Bar */
.milestone-bar {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
}

.milestone-bar__label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.78rem;
  color: var(--text-muted);
  margin-bottom: 6px;
}

.milestone-bar__score {
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-weight: 600;
  color: var(--accent);
}

.milestone-bar__track {
  height: 6px;
  background: var(--bg-tertiary);
  border-radius: 3px;
  overflow: hidden;
}

.milestone-bar__fill {
  height: 100%;
  background: var(--accent);
  border-radius: 3px;
  transition: width 0.4s ease;
  min-width: 0;
}

/* Section Title */
.ticket-section-title {
  font-size: 0.78rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
  margin: 0 0 8px;
}

/* Updates */
.ticket-updates {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.ticket-updates-list {
  overflow-y: auto;
  flex: 1;
  min-height: 120px;
  max-height: 400px;
  padding: 4px 0;
}

.ticket-update {
  padding: 10px 12px;
  margin-bottom: 8px;
  background: var(--bg-primary);
  border-radius: 6px;
  border-left: 3px solid var(--border-color);
}

.update-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.update-category {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 1px 7px;
  border-radius: 3px;
}

.cat--triage { background: rgba(59, 130, 246, 0.15); color: #60a5fa; }
.cat--finding { background: rgba(20, 184, 166, 0.15); color: #2dd4bf; }
.cat--analysis { background: rgba(168, 85, 247, 0.15); color: #c084fc; }
.cat--action { background: rgba(34, 197, 94, 0.15); color: #4ade80; }
.cat--escalation { background: rgba(239, 68, 68, 0.15); color: #f87171; }
.cat--status { background: rgba(148, 163, 184, 0.15); color: #94a3b8; }

.update-time {
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 0.7rem;
  color: var(--text-muted);
}

.update-content {
  font-size: 0.85rem;
  line-height: 1.6;
  color: var(--text-primary);
  white-space: pre-wrap;
  word-break: break-word;
  padding-top: 4px;
}

.empty-text {
  font-size: 0.82rem;
  color: var(--text-muted);
  font-style: italic;
  padding: 8px 0;
}

/* Add Update Form */
.ticket-add-update {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.update-category-select {
  background: var(--bg-tertiary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  padding: 6px 10px;
  font-size: 0.82rem;
  outline: none;
  cursor: pointer;
  width: fit-content;
}

.update-category-select:focus {
  border-color: var(--accent);
}

.update-textarea {
  background: var(--bg-tertiary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  padding: 8px 10px;
  font-size: 0.83rem;
  line-height: 1.5;
  resize: vertical;
  font-family: inherit;
  outline: none;
}

.update-textarea:focus {
  border-color: var(--accent);
}

.update-textarea::placeholder {
  color: var(--text-muted);
}

/* Buttons */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 7px 16px;
  border: none;
  border-radius: 4px;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s, background 0.15s;
  align-self: flex-end;
}

.btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn--accent {
  background: var(--accent);
  color: #fff;
}

.btn--accent:hover:not(:disabled) {
  opacity: 0.85;
}

.btn--sm {
  padding: 5px 12px;
  font-size: 0.78rem;
}

/* Attachments */
.ticket-attachments {
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.attachment-tabs {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.attachment-tab {
  padding: 5px 12px;
  background: var(--bg-tertiary);
  color: var(--text-muted);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  font-size: 0.76rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.attachment-tab:hover {
  color: var(--text-secondary);
  border-color: var(--text-muted);
}

.attachment-tab--active {
  background: var(--bg-secondary);
  color: var(--text-primary);
  border-color: var(--accent);
}

.attachment-check {
  font-size: 0.65rem;
  font-weight: 700;
  color: #4ade80;
  text-transform: uppercase;
}

.attachment-textarea {
  background: var(--bg-tertiary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  padding: 8px 10px;
  font-size: 0.82rem;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  line-height: 1.5;
  resize: vertical;
  outline: none;
}

.attachment-textarea:focus {
  border-color: var(--accent);
}

.attachment-textarea::placeholder {
  color: var(--text-muted);
  font-family: inherit;
}

/* Scrollbar styling */
.ticket-panel::-webkit-scrollbar,
.ticket-updates-list::-webkit-scrollbar {
  width: 6px;
}

.ticket-panel::-webkit-scrollbar-track,
.ticket-updates-list::-webkit-scrollbar-track {
  background: transparent;
}

.ticket-panel::-webkit-scrollbar-thumb,
.ticket-updates-list::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: 3px;
}

.ticket-panel::-webkit-scrollbar-thumb:hover,
.ticket-updates-list::-webkit-scrollbar-thumb:hover {
  background: var(--text-muted);
}
</style>

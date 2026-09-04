<template>
  <div class="panel">
    <h2 class="panel-title">Pending Approvals</h2>
    <div v-if="users.length === 0" class="empty-state">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="empty-icon">
        <polyline points="20 6 9 17 4 12"/>
      </svg>
      <p>No pending users</p>
    </div>
    <div v-else class="pending-list">
      <div v-for="user in users" :key="user.id" class="pending-item">
        <div class="pending-info">
          <p class="pending-name">{{ maskUsername(user.username) }}</p>
          <p class="pending-details">{{ maskEmail(user.email) }}</p>
        </div>
        <div class="pending-actions">
          <button @click="$emit('approve', user.id)" class="btn btn--success btn--sm">Approve</button>
          <button @click="$emit('reject', user.id)" class="btn btn--danger btn--sm">Reject</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
// Pending Approvals tab, extracted from Admin.vue as the proof-of-approach
// for decomposing the admin panel into per-tab components. The pattern:
// the parent keeps ownership of data and mutations (users list, approve and
// reject handlers), the tab receives data via props and asks for actions via
// emits, and cross-cutting helpers (privacy masking) come from composables.
import { usePrivacy } from '../composables/usePrivacy'

defineProps({
  users: { type: Array, required: true }
})

defineEmits(['approve', 'reject'])

const { maskUsername, maskEmail } = usePrivacy()
</script>

<style scoped>
/* Copied from Admin.vue's scoped styles: parent scoped CSS does not reach a
   child component's inner elements. A shared admin stylesheet is the planned
   follow-up once more tabs are extracted. */
.panel {
  background: var(--bg-secondary);
  border-radius: 12px;
  padding: 1rem;
  border: 1px solid var(--border-color);
}

.panel-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 3rem;
  color: var(--text-muted);
}

.empty-icon {
  width: 48px;
  height: 48px;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.pending-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-top: 1rem;
}

.pending-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: var(--bg-tertiary);
  border-radius: 8px;
}

.pending-name {
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 0.25rem 0;
}

.pending-details {
  font-size: 0.8125rem;
  color: var(--text-muted);
  margin: 0;
}

.pending-actions {
  display: flex;
  gap: 0.5rem;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.625rem 1rem;
  font-size: 0.875rem;
  font-weight: 500;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn--success {
  background: var(--success);
  color: white;
}

.btn--success:hover {
  background: #16a34a;
}

.btn--danger {
  background: var(--danger);
  color: white;
}

.btn--danger:hover {
  background: #dc2626;
}

.btn--sm {
  padding: 0.375rem 0.75rem;
  font-size: 0.8125rem;
}

@media (max-width: 768px) {
  .pending-item {
    flex-direction: column;
    gap: 1rem;
    align-items: flex-start;
  }

  .pending-actions {
    width: 100%;
  }

  .pending-actions .btn {
    flex: 1;
  }
}
</style>

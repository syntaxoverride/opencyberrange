<template>
  <div class="courses-page">
    <div class="courses-container">
      <!-- Header -->
      <div class="courses-header">
        <div>
          <h1>Courses</h1>
          <p class="header-subtitle">Your enrolled courses and classrooms</p>
        </div>
      </div>

      <!-- Join Course -->
      <div class="join-section">
        <div class="join-card">
          <h3>Join a Course</h3>
          <p>Enter the invite code provided by your instructor</p>
          <div class="join-form">
            <input
              v-model="inviteCode"
              type="text"
              placeholder="Enter invite code"
              class="join-input"
              @keyup.enter="joinCourse"
            />
            <button @click="joinCourse" :disabled="!inviteCode || joining" class="join-btn">
              {{ joining ? 'Joining...' : 'Join' }}
            </button>
          </div>
          <p v-if="joinMessage" :class="['join-message', joinError ? 'error' : 'success']">
            {{ joinMessage }}
          </p>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="loading">Loading courses...</div>

      <!-- Empty state -->
      <div v-else-if="courses.length === 0" class="empty-state">
        <p>You are not enrolled in any courses. Enter an invite code above to join.</p>
      </div>

      <!-- Course Cards -->
      <div v-else class="course-grid">
        <div
          v-for="course in courses"
          :key="course.id"
          class="course-card"
          @click="$router.push(`/courses/${course.id}`)"
        >
          <div class="course-card__header">
            <span class="course-code">{{ course.code }}</span>
            <span :class="['course-status', courseStatus(course).class]">
              {{ courseStatus(course).text }}
            </span>
          </div>
          <h3 class="course-name">{{ course.name }}</h3>
          <p class="course-semester">{{ course.semester }}</p>
          <p v-if="course.description" class="course-description">{{ course.description }}</p>
          <div class="course-card__stats">
            <span class="stat">{{ course.student_count }} students</span>
            <span class="stat">{{ course.lab_count }} exercises</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from '../api/axios'

const courses = ref([])
const loading = ref(true)
const inviteCode = ref('')
const joining = ref(false)
const joinMessage = ref('')
const joinError = ref(false)

function courseStatus(course) {
  const now = new Date()
  const end = new Date(course.end_date)
  const start = new Date(course.start_date)

  if (!course.is_active) return { text: 'Inactive', class: 'status-inactive' }
  if (now > end) return { text: 'Ended', class: 'status-ended' }
  if (now < start) return { text: 'Upcoming', class: 'status-upcoming' }
  return { text: 'Active', class: 'status-active' }
}

async function fetchCourses() {
  loading.value = true
  try {
    const res = await axios.get('/courses/')
    courses.value = res.data.courses
  } catch (e) {
    console.error('Failed to fetch courses', e)
  } finally {
    loading.value = false
  }
}

async function joinCourse() {
  if (!inviteCode.value) return
  joining.value = true
  joinMessage.value = ''
  try {
    const res = await axios.post('/courses/join', { invite_code: inviteCode.value })
    joinMessage.value = res.data.message
    joinError.value = false
    inviteCode.value = ''
    fetchCourses()
  } catch (e) {
    joinMessage.value = e.response?.data?.detail || 'Failed to join course'
    joinError.value = true
  } finally {
    joining.value = false
  }
}


onMounted(fetchCourses)
</script>

<style scoped>
.courses-page {
  min-height: calc(100vh - 64px);
  background: var(--bg-primary);
  padding: 2rem 1.5rem;
}

.courses-container {
  max-width: 1100px;
  margin: 0 auto;
}

.courses-header {
  margin-bottom: 2rem;
}

.courses-header h1 {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--text-primary);
}

.header-subtitle {
  color: var(--text-secondary);
  margin-top: 0.25rem;
  font-size: 0.9rem;
}

/* Join Section */
.join-section {
  margin-bottom: 2rem;
}

.join-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 1.5rem;
}

.join-card h3 {
  font-size: 1rem;
  color: var(--text-primary);
  margin-bottom: 0.25rem;
}

.join-card > p {
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin-bottom: 1rem;
}

.join-form {
  display: flex;
  gap: 0.75rem;
  max-width: 400px;
}

.join-input {
  flex: 1;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  padding: 0.6rem 1rem;
  border-radius: 8px;
  font-size: 0.9rem;
  outline: none;
}

.join-input:focus {
  border-color: var(--accent);
}

.join-btn {
  background: var(--accent);
  color: white;
  border: none;
  padding: 0.6rem 1.5rem;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.join-btn:hover:not(:disabled) {
  background: #2563eb;
}

.join-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.join-message {
  margin-top: 0.75rem;
  font-size: 0.85rem;
}

.join-message.success {
  color: var(--success);
}

.join-message.error {
  color: var(--danger);
}


/* Loading & Empty */
.loading {
  color: var(--text-secondary);
  text-align: center;
  padding: 3rem;
}

.empty-state {
  color: var(--text-muted);
  text-align: center;
  padding: 3rem;
  font-size: 0.95rem;
}

/* Course Grid */
.course-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1.25rem;
}

.course-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 1.25rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.course-card:hover {
  border-color: var(--accent);
  transform: translateY(-2px);
}

.course-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.course-code {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--accent);
  background: var(--accent-bg);
  padding: 0.2rem 0.6rem;
  border-radius: 4px;
}

.course-status {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.2rem 0.6rem;
  border-radius: 4px;
}

.status-active {
  color: var(--success);
  background: rgba(34, 197, 94, 0.1);
}

.status-ended {
  color: var(--text-secondary);
  background: rgba(148, 163, 184, 0.1);
}

.status-upcoming {
  color: var(--warning);
  background: rgba(245, 158, 11, 0.1);
}

.status-inactive {
  color: var(--danger);
  background: var(--danger-bg);
}

.course-name {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.15rem;
}

.course-semester {
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin-bottom: 0.5rem;
}

.course-description {
  font-size: 0.83rem;
  color: var(--text-muted);
  margin-bottom: 0.75rem;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.course-card__stats {
  display: flex;
  gap: 1rem;
  margin-bottom: 0.5rem;
}

.stat {
  font-size: 0.8rem;
  color: var(--text-secondary);
}

@media (max-width: 768px) {
  .course-grid {
    grid-template-columns: 1fr;
  }
}
</style>

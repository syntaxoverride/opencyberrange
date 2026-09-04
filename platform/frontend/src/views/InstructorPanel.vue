<template>
  <div class="instructor-panel">
    <header class="panel-header">
      <h1>Instructor Panel</h1>
      <p class="panel-subtitle">Manage your courses and browse available exercises</p>
    </header>

    <!-- Tab Navigation -->
    <div class="tab-bar">
      <button
        class="tab-btn"
        :class="{ 'tab-btn--active': activeTab === 'courses' }"
        @click="switchTab('courses')"
      >My Courses</button>
      <button
        class="tab-btn"
        :class="{ 'tab-btn--active': activeTab === 'labs' }"
        @click="switchTab('labs')"
      >Exercises</button>
    </div>

    <!-- MY COURSES TAB -->
    <div v-if="activeTab === 'courses'" class="tab-content">
      <div class="panel">
        <div class="section-header">
          <h2>Course Management</h2>
        </div>

        <div v-if="coursesLoading" class="loading">Loading courses...</div>
        <div v-else-if="courses.length === 0" class="empty-state">
          <p>No courses assigned yet. Contact your administrator to create a course.</p>
        </div>
        <template v-else-if="courses.length > 0">
          <!-- Course Filter & Sort Controls -->
          <div class="course-controls" style="margin-top: 0.75rem">
          <div class="course-filters">
            <button @click="courseFilter = 'all'" :class="['filter-btn', { 'filter-btn--active': courseFilter === 'all' }]">All</button>
            <button @click="courseFilter = 'active'" :class="['filter-btn', { 'filter-btn--active': courseFilter === 'active' }]">Active</button>
            <button @click="courseFilter = 'archived'" :class="['filter-btn', { 'filter-btn--active': courseFilter === 'archived' }]">Archived</button>
          </div>
          <div class="course-sort">
            <select v-model="courseSortKey" class="form-input form-input--sm">
              <option value="created_at">Date Created</option>
              <option value="name">Name</option>
              <option value="code">Code</option>
              <option value="semester">Semester</option>
              <option value="status">Status</option>
            </select>
            <button @click="courseSortDir = courseSortDir === 'asc' ? 'desc' : 'asc'" class="sort-dir-btn" :title="courseSortDir === 'asc' ? 'Ascending' : 'Descending'">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
                <path v-if="courseSortDir === 'asc'" d="M12 5v14M5 12l7-7 7 7"/>
                <path v-else d="M12 19V5M5 12l7 7 7-7"/>
              </svg>
            </button>
          </div>
        </div>

        <!-- Course Cards -->
        <div class="course-grid" v-if="sortedFilteredCourses.length > 0">
          <div
            v-for="course in sortedFilteredCourses"
            :key="course.id"
            class="course-card"
            :class="{ 'course-card--active': managingCourse && managingCourse.id === course.id }"
            @click="openCourseManager(course)"
          >
            <div class="course-card__header">
              <span class="course-code">{{ course.code }}</span>
              <span :class="['course-status', courseStatusBadge(course).class]">
                {{ courseStatusBadge(course).text }}
              </span>
            </div>
            <h3 class="course-card__name">{{ course.name }}</h3>
            <p class="course-card__semester">{{ course.semester }}</p>
            <p v-if="course.description" class="course-card__desc">{{ course.description }}</p>
            <div class="course-card__stats">
              <span class="stat">{{ course.student_count }} students</span>
              <span class="stat">{{ course.lab_count }} exercises</span>
            </div>
            <div class="course-card__footer">
              <code class="invite-chip" @click.stop="copyToClipboard(course.invite_code)" title="Click to copy invite code">
                {{ course.invite_code }}
              </code>
              <div class="course-card__actions" @click.stop>
                <button @click="openCourseManagerTab(course, 'students')" class="action-btn action-btn--view" title="Students">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                  </svg>
                </button>
                <button @click="openCourseManagerTab(course, 'exercises')" class="action-btn action-btn--view" title="Exercises">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>
                  </svg>
                </button>
                <button @click="openCourseManagerTab(course, 'assignments')" class="action-btn action-btn--view" title="Assignments">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/><line x1="9" y1="12" x2="15" y2="12"/><line x1="9" y1="16" x2="15" y2="16"/>
                  </svg>
                </button>
                <button v-if="!course.is_archived" @click="archiveCourse(course)" class="action-btn action-btn--archive" title="Archive">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5"/><line x1="10" y1="12" x2="14" y2="12"/>
                  </svg>
                </button>
                <button v-if="course.is_archived" @click="unarchiveCourse(course)" class="action-btn action-btn--available" title="Unarchive">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5"/><polyline points="12 12 12 8 16 12 12 16 12 12"/>
                  </svg>
                </button>
                <button @click="deleteCourse(course)" class="action-btn action-btn--delete" title="Delete">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"/><path d="M19 6V20C19 21.1 18.1 22 17 22H7C5.9 22 5 21.1 5 20V6M8 6V4C8 2.9 8.9 2 10 2H14C15.1 2 16 2.9 16 4V6"/>
                  </svg>
                </button>
                <button @click="viewAsCourseStudent(course)" class="action-btn action-btn--impersonate" title="Student Preview">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M1 12S5 4 12 4S23 12 23 12S19 20 12 20S1 12 1 12Z"/>
                    <circle cx="12" cy="12" r="3"/>
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
        <div v-else-if="courses.length > 0 && sortedFilteredCourses.length === 0" class="empty-state">
          No courses match the current filter.
        </div>

        <!-- Inline Course Management Panel -->
        <div v-if="managingCourse" class="course-manage-section">
          <div class="manage-header">
            <h3 class="manage-title">Managing: {{ managingCourse.name }} ({{ managingCourse.code }})</h3>
            <button @click="managingCourse = null" class="btn btn--secondary btn--sm">Close</button>
          </div>

          <div class="sub-tabs">
            <button @click="courseManageTab = 'students'" :class="['sub-tab', { active: courseManageTab === 'students' }]">Students</button>
            <button @click="courseManageTab = 'exercises'" :class="['sub-tab', { active: courseManageTab === 'exercises' }]">Exercises</button>
            <button @click="switchToAssignments" :class="['sub-tab', { active: courseManageTab === 'assignments' }]">Assignments ({{ courseAssignments.length }})</button>
            <button @click="courseManageTab = 'reports'" :class="['sub-tab', { active: courseManageTab === 'reports' }]">Reports</button>
            <button @click="courseManageTab = 'settings'" :class="['sub-tab', { active: courseManageTab === 'settings' }]">Settings</button>
          </div>

          <!-- Students sub-tab -->
          <div v-if="courseManageTab === 'students'" class="sub-tab-content">
            <div v-if="isAdmin" class="enroll-section">
              <h4 class="settings-section-title">Enroll Students</h4>
              <div class="enroll-search-row">
                <input
                  v-model="enrollSearch"
                  type="text"
                  class="enroll-search-input"
                  placeholder="Search by username, email, or student ID..."
                />
                <span class="enroll-count-badge" v-if="selectedEnrollIds.size > 0">
                  {{ selectedEnrollIds.size }} selected
                </span>
              </div>
              <div class="enroll-actions-row">
                <button @click="selectAllFiltered" class="btn btn--outline btn--xs">Select All{{ enrollSearch ? ' Filtered' : '' }}</button>
                <button @click="clearSelection" class="btn btn--outline btn--xs" :disabled="selectedEnrollIds.size === 0">Clear</button>
                <button
                  @click="enrollSelectedStudents"
                  :disabled="selectedEnrollIds.size === 0 || enrolling"
                  class="btn btn--primary btn--sm enroll-submit-btn"
                >
                  {{ enrolling ? 'Enrolling...' : `Enroll (${selectedEnrollIds.size})` }}
                </button>
              </div>
              <div class="enroll-list" v-if="enrollableUsers.length > 0">
                <label
                  v-for="u in filteredEnrollableUsers"
                  :key="u.id"
                  class="enroll-list-item"
                  :class="{ 'enroll-list-item--selected': selectedEnrollIds.has(u.id) }"
                >
                  <input
                    type="checkbox"
                    :checked="selectedEnrollIds.has(u.id)"
                    @change="toggleEnrollUser(u.id)"
                    class="enroll-checkbox"
                  />
                  <span class="enroll-user-name">{{ u.username }}</span>
                  <span class="enroll-user-detail">{{ u.student_id || u.email || '' }}</span>
                </label>
                <div v-if="filteredEnrollableUsers.length === 0" class="empty-state">
                  No users match "{{ enrollSearch }}"
                </div>
              </div>
              <p v-else class="empty-state">All users are already enrolled.</p>
            </div>
            <div v-else class="students-note">
              Students are enrolled by an administrator. You can view progress, download reports, and remove students.
            </div>
            <div class="table-container" v-if="courseStudents.length > 0">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Username</th>
                    <th>Email</th>
                    <th>Enrolled</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  <template v-for="s in courseStudents" :key="s.id">
                    <tr>
                      <td class="cell-primary">{{ maskUsername(s.username) }}</td>
                      <td>{{ maskEmail(s.email) }}</td>
                      <td class="cell-muted">{{ formatDateShort(s.enrolled_at) }}</td>
                      <td class="cell-actions">
                        <button @click="toggleStudentLabs(s)" class="action-btn action-btn--view" title="View Exercises">
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>
                          </svg>
                        </button>
                        <button @click="downloadStudentReport(s)" :disabled="downloadingReportUserId === s.id" class="action-btn action-btn--archive" title="Download PDF">
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
                          </svg>
                        </button>
                        <button @click="removeStudent(s)" class="action-btn action-btn--delete" title="Remove">
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="3 6 5 6 21 6"/><path d="M19 6V20C19 21.1 18.1 22 17 22H7C5.9 22 5 21.1 5 20V6M8 6V4C8 2.9 8.9 2 10 2H14C15.1 2 16 2.9 16 4V6"/>
                          </svg>
                        </button>
                      </td>
                    </tr>
                    <tr v-if="studentLabDetails[s.id]" class="student-labs-row">
                      <td colspan="4">
                        <div class="student-labs-detail">
                          <div v-if="studentLabDetails[s.id] === 'loading'" class="loading-text">Loading exercise details...</div>
                          <div v-else-if="studentLabDetails[s.id].length === 0" class="empty-state">No exercises assigned.</div>
                          <table v-else class="data-table data-table--nested">
                            <thead>
                              <tr>
                                <th>Exercise</th>
                                <th>Status</th>
                                <th>Score</th>
                                <th>Attempts</th>
                                <th>Hints</th>
                                <th>Action</th>
                              </tr>
                            </thead>
                            <tbody>
                              <template v-for="lab in studentLabDetails[s.id]" :key="lab.lab_id">
                              <tr>
                                <td class="cell-primary">
                                  <button
                                    v-if="lab.attempts > 0"
                                    class="attempts-toggle"
                                    :title="attemptsKey(s.id, lab.lab_id) in studentAttempts ? 'Hide attempts' : 'Show every attempt'"
                                    @click.stop="toggleAttempts(s, lab)"
                                  >{{ attemptsKey(s.id, lab.lab_id) in studentAttempts ? '&#9662;' : '&#9656;' }}</button>
                                  {{ lab.lab_name }}
                                </td>
                                <td>
                                  <span :class="['status-badge', lab.completed ? 'status-badge--done' : 'status-badge--pending']">
                                    {{ lab.completed ? 'Completed' : 'Incomplete' }}
                                  </span>
                                </td>
                                <td>{{ lab.score }}</td>
                                <td>{{ lab.attempts }}</td>
                                <td>{{ lab.hints_used }}</td>
                                <td>
                                  <button
                                    v-if="lab.completed"
                                    @click="resetStudentLab(s, lab)"
                                    :disabled="resettingCourseLab === `${s.id}-${lab.lab_id}`"
                                    class="btn btn--danger btn--xs"
                                  >
                                    {{ resettingCourseLab === `${s.id}-${lab.lab_id}` ? 'Resetting...' : 'Reset' }}
                                  </button>
                                  <span v-else class="cell-muted">—</span>
                                </td>
                              </tr>
                              <tr v-if="attemptsKey(s.id, lab.lab_id) in studentAttempts" class="attempts-row">
                                <td colspan="6">
                                  <div v-if="studentAttempts[attemptsKey(s.id, lab.lab_id)] === 'loading'" class="loading-text">Loading attempts...</div>
                                  <div v-else-if="!studentAttempts[attemptsKey(s.id, lab.lab_id)].length" class="empty-state">No attempts recorded.</div>
                                  <table v-else class="data-table data-table--nested attempts-table">
                                    <thead>
                                      <tr><th>#</th><th>When</th><th>Gap</th><th>Submitted</th><th>Result</th></tr>
                                    </thead>
                                    <tbody>
                                      <tr v-for="(a, i) in studentAttempts[attemptsKey(s.id, lab.lab_id)]" :key="i">
                                        <td class="cell-muted">{{ i + 1 }}</td>
                                        <td>{{ new Date(a.attempted_at).toLocaleString() }}</td>
                                        <td class="cell-muted">{{ formatGap(a.seconds_since_previous) }}</td>
                                        <td><code class="attempt-value">{{ a.submitted || '(empty)' }}</code></td>
                                        <td>
                                          <span :class="['status-badge', a.is_correct ? 'status-badge--done' : 'status-badge--pending']">
                                            {{ a.is_correct ? 'Correct' : 'Incorrect' }}
                                          </span>
                                        </td>
                                      </tr>
                                    </tbody>
                                  </table>
                                </td>
                              </tr>
                              </template>
                            </tbody>
                          </table>
                        </div>
                      </td>
                    </tr>
                  </template>
                </tbody>
              </table>
            </div>
            <p v-else class="empty-state">No students enrolled yet.</p>
          </div>

          <!-- Exercises sub-tab -->
          <div v-if="courseManageTab === 'exercises'" class="sub-tab-content">
            <!-- Door A: Add exercises on-ramp (Exercise Studio) -->
            <div class="addex-bar">
              <button class="btn btn--primary btn--sm" @click="onAddExercisesClick">+ Add exercises</button>
              <span class="addex-hint">{{ exerciseAuthoring ? 'Pull a template, generate with AI, pick an existing lab, or fork.' : 'Pick an existing exercise to add it to this course.' }}</span>
            </div>

            <!-- Assigned Exercises (grouped accordion) -->
            <div class="assigned-exercises-section">
              <div class="assign-header-row">
                <h4>Assigned Exercises ({{ courseLabs.length }})</h4>
                <button v-if="assignedLevelKeys.length > 0" @click="toggleAllAssignedCategories" class="btn btn--outline btn--xs">
                  {{ allAssignedExpanded ? 'Collapse All' : 'Expand All' }}
                </button>
              </div>
              <div v-if="assignedLevelKeys.length > 0" class="assign-accordion">
                <div v-for="levelKey in assignedLevelKeys" :key="levelKey" class="assign-group">
                  <div class="assign-group__header-row">
                    <button class="assign-group__header" @click="toggleAssignedCategory(levelKey)">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="assign-group__chevron" :class="{ 'assign-group__chevron--open': expandedAssignedCategories[levelKey] }">
                        <polyline points="9 18 15 12 9 6"/>
                      </svg>
                      <span class="assign-group__track">{{ assignedLabsByTrackLevel[levelKey].track_name }}</span>
                      <span class="assign-group__sep">&rsaquo;</span>
                      <span class="assign-group__level">{{ assignedLabsByTrackLevel[levelKey].level_name }}</span>
                      <span class="assign-group__count">({{ assignedLabsByTrackLevel[levelKey].labs.length }})</span>
                    </button>
                    <button class="btn btn--outline btn--xs assign-group__remove-all" @click.stop="removeAllInGroup(levelKey)" title="Remove all exercises in this group">Remove All</button>
                  </div>
                  <div v-show="expandedAssignedCategories[levelKey]" class="assign-group__body">
                    <div v-for="lab in assignedLabsByTrackLevel[levelKey].labs" :key="lab.id" class="assigned-lab-row">
                      <template v-if="renamingLabId === lab.id">
                        <input v-model="renameLabValue" type="text" class="form-input form-input--inline" placeholder="Display name (blank = default)" @keyup.enter="saveRenameLab(lab)" @keyup.escape="cancelRenameLab" />
                        <button @click="saveRenameLab(lab)" class="btn btn--success btn--xs">Save</button>
                        <button @click="cancelRenameLab" class="btn btn--secondary btn--xs">Cancel</button>
                      </template>
                      <template v-else>
                        <span class="lab-checkbox-name" :class="{ 'lab-name--custom': lab.display_name }" :title="lab.display_name ? 'Custom name (click pencil to edit)' : ''">{{ lab.name }}</span>
                        <span class="lab-checkbox-diff">{{ lab.difficulty }}</span>
                        <button @click.stop="openLab(lab)" class="btn btn--outline btn--xs" title="Launch / Test">&#9654;</button>
                        <button @click.stop="startRenameLab(lab)" class="btn btn--outline btn--xs" title="Rename">&#9998;</button>
                        <!-- Answer key, masked until asked for so it is not on
                             screen while the panel is projected to the room. -->
                        <button
                          v-if="revealedFlags[lab.id] === undefined"
                          @click.stop="revealFlag(lab.id)"
                          class="btn btn--outline btn--xs"
                          :disabled="flagLoadingId === lab.id"
                          title="Show the flag students submit"
                        >{{ flagLoadingId === lab.id ? '...' : 'Flag' }}</button>
                        <template v-else>
                          <code class="lab-flag-value" :title="revealedFlags[lab.id].message">{{ revealedFlags[lab.id].flag || 'not set in lab.yaml' }}</code>
                          <button @click.stop="hideFlag(lab.id)" class="btn btn--outline btn--xs" title="Hide flag">Hide</button>
                        </template>
                        <button @click="unassignLab(lab)" class="btn btn--danger btn--xs">Remove</button>
                      </template>
                    </div>
                  </div>
                </div>
              </div>
              <p v-else class="empty-state" style="margin-top: 0.5rem;">No exercises assigned yet.</p>
            </div>

            <div class="section-divider"></div>

            <!-- Assign Exercises -->
            <div class="assign-exercises-form" id="assign-exercises" ref="assignExercisesRef">
              <div class="assign-header-row">
                <h4>Assign Exercises</h4>
                <button v-if="assignLevelKeys.length > 0" @click="toggleAllAssignCategories" class="btn btn--outline btn--xs">
                  {{ allAssignExpanded ? 'Collapse All' : 'Expand All' }}
                </button>
              </div>
              <div class="assign-accordion">
                <div v-for="levelKey in assignLevelKeys" :key="levelKey" class="assign-group">
                  <div class="assign-group__header-row">
                    <button class="assign-group__header" @click="toggleAssignCategory(levelKey)">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="assign-group__chevron" :class="{ 'assign-group__chevron--open': expandedAssignCategories[levelKey] }">
                        <polyline points="9 18 15 12 9 6"/>
                      </svg>
                      <span class="assign-group__track">{{ assignLabsByTrackLevel[levelKey].track_name }}</span>
                      <span class="assign-group__sep">&rsaquo;</span>
                      <span class="assign-group__level">{{ assignLabsByTrackLevel[levelKey].level_name }}</span>
                      <span class="assign-group__count">({{ assignLabsByTrackLevel[levelKey].labs.length }})</span>
                    </button>
                    <button class="btn btn--outline btn--xs assign-group__add-all" @click.stop="selectAllInGroup(levelKey)" title="Select all exercises in this group">Add All</button>
                  </div>
                  <div v-show="expandedAssignCategories[levelKey]" class="assign-group__body">
                    <label v-for="lab in assignLabsByTrackLevel[levelKey].labs" :key="lab.id" class="lab-checkbox-label">
                      <input type="checkbox" :value="lab.id" v-model="selectedLabIds" />
                      <span class="lab-checkbox-name">{{ lab.name }}</span>
                      <span class="lab-checkbox-diff">{{ lab.difficulty }}</span>
                    </label>
                  </div>
                </div>
              </div>
              <p v-if="assignLevelKeys.length === 0" class="empty-state" style="margin-top: 0.5rem;">All exercises have been assigned to this course.</p>
              <button v-else @click="assignSelectedLabs" :disabled="selectedLabIds.length === 0" class="btn btn--success assign-selected-btn">
                Assign Selected ({{ selectedLabIds.length }})
              </button>
            </div>

            <!-- Door A: Add exercises picker modal -->
            <div v-if="showAddPicker" class="addex-overlay" @click.self="showAddPicker = false">
              <div class="addex-modal">
                <div class="addex-modal__head">
                  <strong>Add exercises to {{ managingCourse.name }}</strong>
                  <button class="addex-close" @click="showAddPicker = false">&times;</button>
                </div>
                <button v-if="exerciseAuthoring" class="addex-door" @click="goStudio('templates')">
                  <span class="addex-door__title">From a template</span>
                  <span class="addex-door__desc">Browse vetted environments and reskin to this course.</span>
                </button>
                <button v-if="exerciseAuthoring" class="addex-door" @click="goStudio('generate')">
                  <span class="addex-door__title">Generate with AI</span>
                  <span class="addex-door__desc">Describe, paste, or upload requirements; the agent drafts exercises.</span>
                </button>
                <button class="addex-door" @click="showAddPicker = false; scrollToAssignExercises()">
                  <span class="addex-door__title">From an existing lab</span>
                  <span class="addex-door__desc">Pick from labs already in the platform, in the list below.</span>
                </button>
                <button v-if="exerciseAuthoring" class="addex-door" @click="goStudio('templates', true)">
                  <span class="addex-door__title">Fork a template</span>
                  <span class="addex-door__desc">Clone a template and edit its structure (advanced).</span>
                </button>
              </div>
            </div>
          </div>

          <!-- Assignments sub-tab -->
          <div v-if="courseManageTab === 'assignments'" class="sub-tab-content">
            <!-- Create assignment form -->
            <div class="assign-header-row" style="margin-bottom: 1rem;">
              <h4>Assignments</h4>
              <button @click="showCreateAssignment = !showCreateAssignment" class="btn btn--primary btn--sm">
                {{ showCreateAssignment ? 'Cancel' : '+ New Assignment' }}
              </button>
            </div>
            <div v-if="showCreateAssignment" class="create-assignment-form">
              <div class="form-row">
                <input v-model="newAssignment.name" type="text" placeholder="Assignment name" class="form-input" />
                <label class="form-label-inline">Start <input v-model="newAssignment.start_date" type="datetime-local" class="form-input" /></label>
                <label class="form-label-inline">Due <input v-model="newAssignment.due_date" type="datetime-local" class="form-input" /></label>
                <button @click="createAssignment" :disabled="!newAssignment.name.trim()" class="btn btn--success btn--sm">Create</button>
              </div>
              <input v-model="newAssignment.description" type="text" placeholder="Description (optional)" class="form-input" style="margin-top: 0.5rem;" />
            </div>

            <!-- Assignment cards -->
            <div v-if="courseAssignments.length === 0 && !showCreateAssignment" class="empty-state">
              <p>No assignments yet. Create one to group exercises with due dates.</p>
            </div>
            <div v-for="(asn, asnIdx) in courseAssignments" :key="asn.id"
                 class="assignment-card"
                 :class="{ 'assignment-card--expanded': expandedAssignment === asn.id, 'assignment-card--dragging': dragIndex === asnIdx, 'assignment-card--drag-over': dragOverIndex === asnIdx }"
                 draggable="true"
                 @dragstart="onAsnDragStart(asnIdx, $event)"
                 @dragover.prevent="onAsnDragOver(asnIdx)"
                 @dragleave="dragOverIndex = null"
                 @drop="onAsnDrop(asnIdx)"
                 @dragend="dragIndex = null; dragOverIndex = null">
              <div class="assignment-card__header" @click="toggleAssignmentExpand(asn.id)">
                <svg class="drag-grip" viewBox="0 0 24 24" fill="currentColor" @mousedown.stop><circle cx="9" cy="6" r="1.5"/><circle cx="15" cy="6" r="1.5"/><circle cx="9" cy="12" r="1.5"/><circle cx="15" cy="12" r="1.5"/><circle cx="9" cy="18" r="1.5"/><circle cx="15" cy="18" r="1.5"/></svg>
                <div class="assignment-card__info">
                  <span class="assignment-card__name">{{ asn.name }}</span>
                  <span v-if="asn.description" class="assignment-card__desc">{{ asn.description }}</span>
                </div>
                <div class="assignment-card__meta">
                  <span v-if="asn.start_date" :class="['due-badge', startBadgeClass(asn.start_date)]">{{ startBadgeText(asn.start_date) }}</span>
                  <span :class="['due-badge', dueBadgeClass(asn.due_date)]">{{ dueBadgeText(asn.due_date) }}</span>
                  <span class="assignment-card__count">{{ asn.lab_count }} exercises</span>
                </div>
                <div class="assignment-card__actions" @click.stop>
                  <button @click="toggleAssignmentAvailability(asn)"
                    :class="['action-btn', isAssignmentLocked(asn) ? 'action-btn--locked' : 'action-btn--available']"
                    :title="isAssignmentLocked(asn) ? 'Make Available Now' : 'Lock Assignment'">
                    <svg v-if="isAssignmentLocked(asn)" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                    <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 9.9-1"/></svg>
                  </button>
                  <button @click="startEditAssignment(asn)" class="action-btn action-btn--view" title="Edit">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                  </button>
                  <button @click="downloadAssignmentReport(asn)" class="action-btn action-btn--approve" title="Assignment Report (PDF)">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
                  </button>
                  <button @click="deleteAssignment(asn)" class="action-btn action-btn--delete" title="Delete">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6V20C19 21.1 18.1 22 17 22H7C5.9 22 5 21.1 5 20V6M8 6V4C8 2.9 8.9 2 10 2H14C15.1 2 16 2.9 16 4V6"/></svg>
                  </button>
                </div>
              </div>

              <!-- Expanded: labs in assignment + add labs -->
              <div v-if="expandedAssignment === asn.id" class="assignment-card__body">
                <!-- Edit form (inline) -->
                <div v-if="editingAssignment === asn.id" class="edit-assignment-form">
                  <div class="form-row">
                    <input v-model="editAssignmentData.name" type="text" class="form-input" placeholder="Name" />
                    <label class="form-label-inline">Start <input v-model="editAssignmentData.start_date" type="datetime-local" class="form-input" /></label>
                    <label class="form-label-inline">Due <input v-model="editAssignmentData.due_date" type="datetime-local" class="form-input" /></label>
                    <button @click="saveEditAssignment(asn.id)" class="btn btn--success btn--sm">Save</button>
                    <button @click="editingAssignment = null" class="btn btn--secondary btn--sm">Cancel</button>
                  </div>
                  <input v-model="editAssignmentData.description" type="text" placeholder="Description" class="form-input" style="margin-top: 0.5rem;" />
                </div>

                <!-- Current labs -->
                <div class="assignment-labs-list">
                  <div v-if="asn.labs.length === 0" class="empty-hint">No exercises in this assignment yet.</div>
                  <div v-for="lab in asn.labs" :key="lab.id" class="assignment-lab-row">
                    <span class="assignment-lab-name">{{ lab.name }}</span>
                    <span :class="['difficulty-badge', `difficulty-${lab.difficulty}`]">{{ lab.difficulty }}</span>
                    <button @click="openLab(lab)" class="action-btn action-btn--view action-btn--xs" title="Launch / Test">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                    </button>
                    <!-- Answer key for the week you are looking at. Masked until
                         asked for so it is not on screen while projecting. -->
                    <template v-if="revealedFlags[lab.id] === undefined">
                      <button
                        @click.stop="revealFlag(lab.id)"
                        class="btn btn--outline btn--xs"
                        :disabled="flagLoadingId === lab.id"
                        title="Show the flag students submit"
                      >{{ flagLoadingId === lab.id ? '...' : 'Flag' }}</button>
                    </template>
                    <template v-else>
                      <code class="lab-flag-value" :title="revealedFlags[lab.id].message">{{ revealedFlags[lab.id].flag || 'not set in lab.yaml' }}</code>
                      <button @click.stop="hideFlag(lab.id)" class="btn btn--outline btn--xs" title="Hide flag">Hide</button>
                    </template>
                    <button @click="removeLabFromAssignment(asn.id, lab.id)" class="action-btn action-btn--delete action-btn--xs" title="Remove">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                    </button>
                  </div>
                </div>

                <!-- Add exercises (browse all platform labs) -->
                <div class="assignment-add-labs">
                  <div class="assign-header-row">
                    <h5>Add Exercises</h5>
                    <button v-if="assignmentLabSelection.length > 0"
                            @click="addLabsToAssignment(asn.id)"
                            class="btn btn--primary btn--sm">
                      Add {{ assignmentLabSelection.length }} exercise(s)
                    </button>
                  </div>
                  <div v-if="allLabsForAssignment(asn).length === 0" class="empty-hint">
                    All course exercises are already in this assignment. Use the Exercises tab to add more exercises to the course.
                  </div>
                  <div v-else class="assign-accordion">
                    <div v-for="levelKey in Object.keys(asnLabsByTrackLevel(asn)).sort()" :key="levelKey" class="assign-group">
                      <button class="assign-group__header" @click="asnPickerExpanded[levelKey] = !asnPickerExpanded[levelKey]">
                        <svg class="assign-group__chevron" :class="{ 'assign-group__chevron--open': asnPickerExpanded[levelKey] }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                          <polyline points="9 18 15 12 9 6"/>
                        </svg>
                        <span class="assign-group__track">{{ asnLabsByTrackLevel(asn)[levelKey].track_name }}</span>
                        <span class="assign-group__sep">&rsaquo;</span>
                        <span class="assign-group__level">{{ asnLabsByTrackLevel(asn)[levelKey].level_name }}</span>
                        <span class="assign-group__count">({{ asnLabsByTrackLevel(asn)[levelKey].labs.length }})</span>
                      </button>
                      <div v-show="asnPickerExpanded[levelKey]" class="assign-group__body">
                        <label v-for="lab in asnLabsByTrackLevel(asn)[levelKey].labs" :key="lab.id" class="checkbox-row">
                          <input type="checkbox" :value="lab.id" v-model="assignmentLabSelection" />
                          <span>{{ lab.name }}</span>
                          <span :class="['difficulty-badge', `difficulty-${lab.difficulty}`]">{{ lab.difficulty }}</span>
                        </label>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Reports sub-tab -->
          <div v-if="courseManageTab === 'reports'" class="sub-tab-content">
            <div class="report-actions">
              <button @click="downloadClassReport" :disabled="downloadingReport" class="btn btn--primary">
                {{ downloadingReport ? 'Generating...' : 'Download Full Class Report (PDF)' }}
              </button>
            </div>
            <p class="report-description">
              Generates a PDF with one page per student, including scores, attempt counts, hints used, time spent, and achievements.
            </p>
          </div>

          <!-- Settings sub-tab -->
          <div v-if="courseManageTab === 'settings'" class="sub-tab-content">
            <div class="course-settings-form">
              <h4 class="settings-section-title">Course Details</h4>
              <div class="settings-grid">
                <div class="settings-field">
                  <label class="settings-label">Course Name</label>
                  <input aria-label="Course Name" v-model="settingsForm.name" type="text" class="settings-input" placeholder="Course name" />
                </div>
                <div class="settings-field">
                  <label class="settings-label">Course Code</label>
                  <input aria-label="Course Code" v-model="settingsForm.code" type="text" class="settings-input" placeholder="SEC-400" />
                </div>
                <div class="settings-field">
                  <label class="settings-label">Semester</label>
                  <input aria-label="Semester" v-model="settingsForm.semester" type="text" class="settings-input" placeholder="Spring 2026" />
                </div>
                <div class="settings-field settings-field--full">
                  <label class="settings-label">Description</label>
                  <textarea aria-label="Description" v-model="settingsForm.description" class="settings-input settings-textarea" rows="3" placeholder="Course description (visible to students)"></textarea>
                </div>
                <div class="settings-field">
                  <label class="settings-label">Start Date</label>
                  <input aria-label="Start Date" v-model="settingsForm.start_date" type="date" class="settings-input" />
                </div>
                <div class="settings-field">
                  <label class="settings-label">End Date</label>
                  <input aria-label="End Date" v-model="settingsForm.end_date" type="date" class="settings-input" />
                </div>
              </div>
              <div class="settings-actions">
                <button @click="saveCourseSettings" :disabled="savingSettings" class="btn btn--primary">
                  {{ savingSettings ? 'Saving...' : 'Save Changes' }}
                </button>
                <button @click="resetSettingsForm" class="btn btn--secondary">Reset</button>
              </div>
            </div>
          </div>
        </div>
      </template>
      </div>
    </div>

    <!-- MY EXERCISES TAB -->
    <div v-if="activeTab === 'labs'" class="tab-content">
      <div v-if="labsLoading" class="loading">Loading exercises...</div>
      <div v-else-if="labs.length === 0" class="empty-state">
        <p>No exercises available. Contact an administrator to add exercises to the platform.</p>
      </div>
      <div v-else class="catalog-layout">

        <!-- LEFT: Topic Sidebar -->
        <aside class="topic-sidebar">
          <div class="sidebar-title">Topics</div>
          <button
            class="topic-item"
            :class="{ 'topic-item--active': !selectedTrack }"
            @click="selectedTrack = null"
          >
            <span class="topic-item__name">All Exercises</span>
            <span class="topic-item__count">{{ labs.length }}</span>
          </button>
          <button
            v-for="track in trackSummaries"
            :key="track.slug"
            class="topic-item"
            :class="{ 'topic-item--active': selectedTrack === track.slug }"
            @click="selectedTrack = track.slug"
          >
            <span class="topic-item__dot" :style="{ background: track.color }"></span>
            <span class="topic-item__name">{{ track.name }}</span>
            <span class="topic-item__count">{{ track.lab_count }}</span>
          </button>

          <div class="sidebar-divider"></div>
          <div class="sidebar-title">Courses</div>
          <button
            class="topic-item"
            :class="{ 'topic-item--active': !selectedCourse }"
            @click="selectedCourse = null"
          >
            <span class="topic-item__name">All Courses</span>
          </button>
          <button
            v-for="cs in courseSummariesForSidebar"
            :key="cs.id"
            class="topic-item"
            :class="{ 'topic-item--active': selectedCourse === cs.id }"
            @click="selectedCourse = cs.id"
          >
            <span class="topic-item__name">{{ cs.code || cs.name }}</span>
            <span class="topic-item__count">{{ cs.lab_count }}</span>
          </button>

          <div class="sidebar-divider"></div>
          <div class="sidebar-title">Filter by assignment</div>
          <button
            class="topic-item"
            :class="{ 'topic-item--active': assignmentFilter === '' }"
            @click="assignmentFilter = ''"
          >
            <span class="topic-item__name">All</span>
          </button>
          <button
            class="topic-item"
            :class="{ 'topic-item--active': assignmentFilter === 'assigned' }"
            @click="assignmentFilter = 'assigned'"
          >
            <span class="topic-item__name">Assigned</span>
          </button>
          <button
            class="topic-item"
            :class="{ 'topic-item--active': assignmentFilter === 'unassigned' }"
            @click="assignmentFilter = 'unassigned'"
          >
            <span class="topic-item__name">Unassigned</span>
          </button>
        </aside>

        <!-- RIGHT: Exercises Table -->
        <div class="labs-panel">
          <div class="filter-bar">
            <input
              v-model="labSearch"
              type="text"
              placeholder="Search exercises..."
              class="search-input"
            />
            <select v-model="difficultyFilter" class="filter-select">
              <option value="">All difficulties</option>
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </select>
            <button v-if="exerciseAuthoring" class="btn btn--primary btn--sm" @click="router.push('/studio')" title="Browse templates, generate with AI, and review staged exercises">Exercise Studio</button>
            <button v-if="exerciseAuthoring" class="btn btn--success btn--sm" @click="showUploadModal = true">+ Upload Exercise</button>
          </div>

          <div class="results-count">
            {{ filteredLabs.length }} exercise{{ filteredLabs.length !== 1 ? 's' : '' }}
            <span v-if="selectedTrack"> in {{ trackSummaries.find(t => t.slug === selectedTrack)?.name }}</span>
            <span v-if="selectedCourse"> in {{ courseSummariesForSidebar.find(c => c.id === selectedCourse)?.name }}</span>
          </div>

          <div class="table-wrapper">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Exercise</th>
                  <th>Track</th>
                  <th>Difficulty</th>
                  <th>Status</th>
                  <th>Assigned To</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="filteredLabs.length === 0">
                  <td colspan="6" class="empty-row">No exercises match your filters</td>
                </tr>
                <tr v-for="lab in filteredLabs" :key="lab.id">
                  <td>
                    <div class="lab-name lab-name--link" @click="openLabDirect(lab)">
                      {{ lab.name }}
                      <span v-if="lab.created_by === currentUser.id" class="mine-badge">Mine</span>
                    </div>
                  </td>
                  <td>
                    <span
                      class="track-badge"
                      :style="{ background: lab.track_color + '1a', color: lab.track_color }"
                    >{{ lab.track_name }}</span>
                  </td>
                  <td>
                    <span :class="['difficulty-badge', `difficulty-${lab.difficulty}`]">{{ lab.difficulty }}</span>
                  </td>
                  <td>
                    <div class="status-cell">
                      <template v-if="lab.created_by === currentUser.id">
                        <select
                          class="visibility-select"
                          :class="`vis-${lab.visibility || 'public'}`"
                          :value="lab.visibility || 'public'"
                          @change="changeVisibility(lab, $event.target.value)"
                          :disabled="changingVisibility === lab.id"
                        >
                          <option value="draft">Draft</option>
                          <option value="course">Course</option>
                          <option value="pending_public">Pending Public</option>
                          <option value="public" disabled>Public</option>
                        </select>
                      </template>
                      <span v-else :class="['visibility-badge', `vis-${lab.visibility || 'public'}`]">
                        {{ (lab.visibility || 'public').replace('_', ' ') }}
                      </span>
                    </div>
                  </td>
                  <td>
                    <div class="assigned-courses-cell">
                      <template v-if="labAssignments[lab.id] && labAssignments[lab.id].length">
                        <span
                          v-for="c in labAssignments[lab.id]"
                          :key="c.id"
                          class="course-pill course-pill--removable"
                          :title="`Click to remove from ${c.name}`"
                          @click="quickUnassignLab(lab.id, c.id, c.name)"
                        >{{ c.code }} <span class="pill-x">&times;</span></span>
                      </template>
                      <span v-else class="unassigned-label">—</span>
                    </div>
                  </td>
                  <td>
                    <div class="action-group">
                      <select
                        class="assign-select"
                        :value="''"
                        @change="quickAssignLab(lab.id, $event.target.value); $event.target.value = ''"
                        :disabled="assigningLabId === lab.id"
                      >
                        <option value="" disabled>{{ assigningLabId === lab.id ? 'Assigning...' : 'Assign...' }}</option>
                        <option
                          v-for="c in unassignedCoursesForLab(lab.id)"
                          :key="c.id"
                          :value="c.id"
                        >{{ c.code }} — {{ c.name }}</option>
                      </select>
                      <button
                        class="action-btn action-btn--test"
                        @click="runTestForLab(lab)"
                        :disabled="testerRunning"
                        title="Run exercise tester"
                      >
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                          <path d="M9 3h6v5l4 9H5l4-9V3z"/>
                          <line x1="9" y1="3" x2="15" y2="3"/>
                        </svg>
                      </button>
                      <button
                        v-if="lab.created_by === currentUser.id || currentUser.role === 'admin'"
                        class="action-btn action-btn--view"
                        @click="openCategorizeModal(lab)"
                        title="Change track / level"
                      >
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                          <path d="M3 7h18M3 12h18M3 17h12"/>
                        </svg>
                      </button>
                      <button
                        v-if="lab.created_by === currentUser.id"
                        class="action-btn action-btn--delete"
                        @click="deleteExercise(lab)"
                        title="Delete exercise"
                      >
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                          <polyline points="3 6 5 6 21 6"/>
                          <path d="M19 6L18 20H6L5 6"/>
                          <line x1="10" y1="11" x2="10" y2="17"/>
                          <line x1="14" y1="11" x2="14" y2="17"/>
                        </svg>
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Categorize (track/level) modal -->
          <div v-if="categorizeLab" class="modal-overlay" @click.self="categorizeLab = null">
            <div class="modal modal--small">
              <h3 class="modal-title">Categorize Exercise</h3>
              <p class="modal-subtitle">{{ categorizeLab.name }}</p>
              <div class="form-stack">
                <div class="form-group">
                  <label class="form-label">Track</label>
                  <select aria-label="Track" v-model="categorizeTrackId" @change="categorizeLevelId = null" class="form-input">
                    <option :value="null">Course Assessments (no track)</option>
                    <option v-for="t in trackCatalog" :key="t.id" :value="t.id">{{ t.name }}</option>
                  </select>
                </div>
                <div v-if="categorizeTrackId" class="form-group">
                  <label class="form-label">Level</label>
                  <select aria-label="Level" v-model="categorizeLevelId" class="form-input">
                    <option :value="null">Select a level...</option>
                    <option v-for="lv in categorizeLevelOptions" :key="lv.id" :value="lv.id">
                      Level {{ lv.level_number }} - {{ lv.name }}
                    </option>
                  </select>
                </div>
              </div>
              <div class="modal-actions">
                <button class="btn btn--secondary" @click="categorizeLab = null">Cancel</button>
                <button class="btn btn--primary" @click="saveCategorize" :disabled="categorizeSaving">
                  {{ categorizeSaving ? 'Saving...' : 'Save' }}
                </button>
              </div>
            </div>
          </div>

          <!-- Tester Terminal Panel -->
          <div v-if="showTesterPanel" class="tester-panel">
            <div class="tester-header">
              <div class="tester-header__left">
                <span class="tester-dot" :class="{ 'tester-dot--active': testerRunning }"></span>
                <span class="tester-label">Exercise Tester</span>
                <template v-if="testerRunning && testerProgressTotal > 0">
                  <span class="tester-progress">{{ testerProgressCurrent }}/{{ testerProgressTotal }}</span>
                </template>
              </div>
              <div class="tester-header__right">
                <button v-if="testerRunning" class="btn btn--sm btn--danger" @click="cancelTest" :disabled="testerCancelling">
                  {{ testerCancelling ? 'Cancelling...' : 'Cancel' }}
                </button>
                <button v-else class="btn btn--sm btn--secondary" @click="showTesterPanel = false">Close</button>
              </div>
            </div>
            <div ref="testerTerminalRef" class="tester-terminal">
              <div v-if="!testerSections.length && !testerRunning" class="tester-empty">
                No test output yet. Click "Test" on one of your exercises to begin.
              </div>
              <template v-for="section in testerSections" :key="section.test_key">
                <div class="tester-section-header" :class="`tester-section--${section.status}`">
                  {{ section.name }}
                  <span class="tester-section-status">{{ section.status === 'running' ? '...' : section.status.toUpperCase() }}</span>
                </div>
                <div v-for="(line, li) in section.lines" :key="li" :class="['tester-line', `tester-line--${line.level}`]">
                  <span v-if="line.timestamp" class="tester-ts">{{ line.timestamp }}</span>
                  <span class="tester-msg">{{ line.message }}</span>
                </div>
              </template>
              <div v-if="testerRunning" class="tester-cursor">_</div>
            </div>
          </div>
        </div>

      </div>
    </div>

    <!-- Upload Modal -->
    <div v-if="showUploadModal" class="modal-overlay" @click.self="showUploadModal = false">
      <div class="modal-dialog modal-dialog--lg">
        <div class="modal-header">
          <h3>Upload Exercise</h3>
          <button class="modal-close" @click="showUploadModal = false; resetUploadForm()">&times;</button>
        </div>
        <div class="modal-body">
          <!-- Guide section -->
          <div class="guide-section">
            <button class="guide-toggle" @click="uploadGuideOpen = !uploadGuideOpen">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
                <path v-if="uploadGuideOpen" d="M19 9l-7 7-7-7"/>
                <path v-else d="M9 5l7 7-7 7"/>
              </svg>
              ZIP Structure Guide
            </button>
            <div v-if="uploadGuideOpen" class="guide-content">
              <pre class="guide-pre">Your ZIP should contain:

my-exercise/
  lab.yaml              (REQUIRED) Exercise metadata, flag, hints
  docker-compose.yml    (REQUIRED) Container definitions
  containers/
    target/             One folder per service
      Dockerfile        How to build the container
      (scripts, configs, flag files, etc.)

--- lab.yaml fields ---
name: "My Exercise Name"         # REQUIRED
description: "One-line summary"
difficulty: beginner             # beginner | intermediate | advanced
category: reconnaissance         # e.g. web, network, forensics
duration_minutes: 60
scenario: |
  Narrative backstory shown to students...
flag: "OCR{my_secret_flag}"      # Flag students submit
objectives:
  - "Learn to enumerate services"
hints:
  - text: "Try scanning common ports"
    unlock_after_minutes: 5
test:
  steps:
    - name: "Verify target is reachable"
      command: "ping -c 1 {target.target}"
      expect: "1 received"

--- docker-compose.yml ---
services:
  target:
    build:
      context: ./containers/target
      dockerfile: Dockerfile
    labels:
      ip_offset: "10"           # Assigns container IP
    restart: unless-stopped</pre>
            </div>
          </div>

          <!-- Upload form -->
          <div class="upload-form">
            <div class="form-group">
              <label>ZIP File</label>
              <input aria-label="ZIP File" type="file" accept=".zip" @change="handleFileSelect" class="form-input" />
            </div>
            <div v-if="uploadPreview" class="upload-preview">
              Selected: {{ uploadPreview.name }} ({{ uploadPreview.size }})
            </div>
            <div class="form-row-inline">
              <div class="form-group" style="flex:1">
                <label>Track</label>
                <select aria-label="Track" v-model="uploadTrack" class="form-input">
                  <option value="">Select track...</option>
                  <option v-for="t in trackSummaries" :key="t.slug" :value="t.slug">{{ t.name }}</option>
                </select>
              </div>
            </div>
            <div v-if="uploadError" class="upload-error">{{ uploadError }}</div>
            <div v-if="uploadWarnings.length" class="upload-warnings">
              <div v-for="(w, i) in uploadWarnings" :key="i" class="upload-warning-item">⚠ {{ w }}</div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn--secondary btn--sm" @click="showUploadModal = false; resetUploadForm()">Cancel</button>
          <button class="btn btn--success btn--sm" @click="submitUpload" :disabled="uploading || !uploadFile || !uploadTrack">
            {{ uploading ? 'Uploading...' : 'Upload' }}
          </button>
        </div>
      </div>
    </div>



    <!-- Alert -->
    <transition name="fade">
      <div v-if="alertMessage" :class="['alert-toast', `alert-toast--${alertType}`]">
        {{ alertMessage }}
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from '../api/axios'
import { usePrivacy } from '../composables/usePrivacy'
import { useImpersonation } from '../composables/useImpersonation'
import { useModules } from '../composables/useModules'

const { maskUsername, maskEmail } = usePrivacy()
const { startImpersonation } = useImpersonation()
const { exerciseAuthoring, exerciseTester, fetchModules } = useModules()

// Current user from localStorage
const currentUser = (() => { try { return JSON.parse(localStorage.getItem('user') || '{}') } catch { return {} } })()

const route = useRoute()
const router = useRouter()

const activeTab = ref(route.query.tab || 'courses')
const courses = ref([])
const coursesLoading = ref(false)
const labs = ref([])
const trackSummaries = ref([])
const labsLoading = ref(false)
const labSearch = ref('')
const difficultyFilter = ref('')
const selectedTrack = ref(null)
const selectedCourse = ref(null)
const assignmentFilter = ref('')
const labAssignments = ref({})
const assigningLabId = ref(null)

// Upload modal state
const showUploadModal = ref(false)
const uploadGuideOpen = ref(true)
const uploadFile = ref(null)
const uploadTrack = ref('')
const uploadLevelId = ref(null)
const uploading = ref(false)
const uploadPreview = ref(null)
const uploadError = ref('')
const uploadWarnings = ref([])

// Visibility management
const changingVisibility = ref(null)

// Exercise tester state
const testerRunning = ref(false)
const testerCancelling = ref(false)
const testerSections = ref([])
const testerComplete = ref(null)
const testerTerminalRef = ref(null)
const testerRunId = ref(null)
const testerResults = ref({})
const testerProgressCurrent = ref(0)
const testerProgressTotal = ref(0)
const testerLabDurations = ref([])
const testingLabSlug = ref(null)
const showTesterPanel = ref(false)
let _testerPollTimer = null

// Course filter state
const courseFilter = ref('all')
const courseSortKey = ref('created_at')
const courseSortDir = ref('desc')

// Course management state
const managingCourse = ref(null)
const showAddPicker = ref(false)
const assignExercisesRef = ref(null)
function scrollToAssignExercises() {
  nextTick(() => {
    (assignExercisesRef.value || document.getElementById('assign-exercises'))
      ?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  })
}
// Without authoring, the picker modal offers only "From an existing lab", which
// just points at the assign list below -- so skip the dead-end modal and take the
// instructor straight to that list. With authoring on, open the full picker.
function onAddExercisesClick() {
  if (exerciseAuthoring.value) showAddPicker.value = true
  else scrollToAssignExercises()
}
function goStudio(studioTab, fork) {
  const query = { tab: studioTab }
  if (managingCourse.value) query.course = managingCourse.value.id
  if (fork) query.fork = 1
  showAddPicker.value = false
  router.push({ path: '/studio', query })
}
const courseManageTab = ref('students')
const courseStudents = ref([])
const courseLabs = ref([])
const availableLabs = ref([])
const selectedLabIds = ref([])
const expandedAssignCategories = ref({})
const expandedAssignedCategories = ref({})
const studentLabDetails = ref({})
const resettingCourseLab = ref(null)
const downloadingReportUserId = ref(null)
const downloadingReport = ref(false)

// Lab rename state
const renamingLabId = ref(null)
const renameLabValue = ref('')

// Per-exercise attempt listings, keyed by "<studentId>:<labId>" so one
// student's expanded exercise does not collapse when another is opened.
const studentAttempts = ref({})

function attemptsKey(studentId, labId) {
  return `${studentId}:${labId}`
}

function formatGap(seconds) {
  if (seconds === null || seconds === undefined) return '—'
  if (seconds < 60) return `${seconds}s`
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`
  return `${(seconds / 3600).toFixed(1)}h`
}

async function toggleAttempts(student, lab) {
  const key = attemptsKey(student.id, lab.lab_id)
  if (key in studentAttempts.value) {
    const next = { ...studentAttempts.value }
    delete next[key]
    studentAttempts.value = next
    return
  }
  studentAttempts.value = { ...studentAttempts.value, [key]: 'loading' }
  try {
    const { data } = await axios.get(
      `/courses/${managingCourse.value.id}/students/${student.id}/labs/${lab.lab_id}/attempts`
    )
    studentAttempts.value = { ...studentAttempts.value, [key]: data.attempts || [] }
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Could not load attempts for this exercise.', 'error')
    const next = { ...studentAttempts.value }
    delete next[key]
    studentAttempts.value = next
  }
}

// Flag reveal state, keyed by lab id. Absent means masked; the backend audits
// every reveal, so this is fetched on demand rather than loaded with the list.
const revealedFlags = ref({})
const flagLoadingId = ref(null)

async function revealFlag(labId) {
  flagLoadingId.value = labId
  try {
    const { data } = await axios.get(`/instructor/labs/${labId}/flag`)
    revealedFlags.value = { ...revealedFlags.value, [labId]: data }
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Could not load the flag for this exercise.', 'error')
  } finally {
    flagLoadingId.value = null
  }
}

function hideFlag(labId) {
  const next = { ...revealedFlags.value }
  delete next[labId]
  revealedFlags.value = next
}

// Assignment management state
const courseAssignments = ref([])
const dragIndex = ref(null)
const dragOverIndex = ref(null)
const showCreateAssignment = ref(false)
const newAssignment = ref({ name: '', description: '', due_date: '', start_date: '' })
const expandedAssignment = ref(null)
const editingAssignment = ref(null)
const editAssignmentData = ref({ name: '', description: '', due_date: '', start_date: '' })
const assignmentLabSelection = ref([])
const asnPickerExpanded = ref({})

// Course settings state
const settingsForm = ref({ name: '', code: '', semester: '', description: '', start_date: '', end_date: '' })
const savingSettings = ref(false)

// Student enrollment state
const enrollableUsers = ref([])
const enrolling = ref(false)
const isAdmin = currentUser.role === 'admin'
const enrollSearch = ref('')
const selectedEnrollIds = ref(new Set())

const filteredEnrollableUsers = computed(() => {
  if (!enrollSearch.value) return enrollableUsers.value
  const q = enrollSearch.value.toLowerCase()
  return enrollableUsers.value.filter(u =>
    u.username.toLowerCase().includes(q) ||
    (u.email && u.email.toLowerCase().includes(q)) ||
    (u.student_id && u.student_id.toLowerCase().includes(q))
  )
})

// Alert
const alertMessage = ref('')
const alertType = ref('success')
let alertTimeout = null

watch(() => route.query.tab, (newTab) => {
  if (newTab && ['courses', 'labs'].includes(newTab)) {
    activeTab.value = newTab
  }
})

function switchTab(tab) {
  activeTab.value = tab
  router.replace({ query: { tab } })
}

function showAlert(msg, type = 'success') {
  alertMessage.value = msg
  alertType.value = type
  clearTimeout(alertTimeout)
  alertTimeout = setTimeout(() => { alertMessage.value = '' }, 3000)
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text)
  showAlert('Copied to clipboard')
}

function formatDateShort(dt) {
  if (!dt) return '—'
  const d = new Date(dt.endsWith('Z') || dt.includes('+') ? dt : dt + 'Z')
  return d.toLocaleDateString('en-US', { timeZone: 'America/Chicago', month: 'short', day: 'numeric', year: 'numeric' })
}

function courseStatusText(course) {
  if (course.is_archived) return 'Archived'
  if (!course.is_active) return 'Inactive'
  const now = new Date()
  const end = new Date(course.end_date)
  const start = new Date(course.start_date)
  if (now > end) return 'Ended'
  if (now < start) return 'Upcoming'
  return 'Active'
}

function courseStatusClass(course) {
  const text = courseStatusText(course)
  const map = { Active: 'status-badge--active', Ended: 'status-badge--ended', Upcoming: 'status-badge--upcoming', Inactive: 'status-badge--inactive', Archived: 'status-badge--archived' }
  return map[text] || ''
}

function courseStatusBadge(course) {
  if (course.is_archived) return { text: 'Archived', class: 'status-badge--archived' }
  const now = new Date()
  const end = new Date(course.end_date)
  const start = new Date(course.start_date)
  if (!course.is_active) return { text: 'Pending Review', class: 'status-badge--inactive' }
  if (now > end) return { text: 'Ended', class: 'status-badge--ended' }
  if (now < start) return { text: 'Upcoming', class: 'status-badge--upcoming' }
  return { text: 'Active', class: 'status-badge--active' }
}

const sortedFilteredCourses = computed(() => {
  let list = [...courses.value]
  if (courseFilter.value === 'active') {
    list = list.filter(c => c.is_active && !c.is_archived)
  } else if (courseFilter.value === 'archived') {
    list = list.filter(c => c.is_archived)
  }
  const key = courseSortKey.value
  const dir = courseSortDir.value === 'asc' ? 1 : -1
  list.sort((a, b) => {
    let va = a[key], vb = b[key]
    if (key === 'status') {
      va = courseStatusBadge(a).text
      vb = courseStatusBadge(b).text
    }
    if (va == null) va = ''
    if (vb == null) vb = ''
    if (typeof va === 'string') return dir * va.localeCompare(vb)
    return dir * ((va > vb ? 1 : va < vb ? -1 : 0))
  })
  return list
})

async function archiveCourse(course) {
  if (!confirm(`Archive "${course.name}"? Students will no longer see this course.`)) return
  try {
    await axios.put(`/courses/${course.id}`, { is_archived: true })
    showAlert('Course archived')
    fetchCourses()
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Failed to archive course', 'error')
  }
}

async function unarchiveCourse(course) {
  try {
    await axios.put(`/courses/${course.id}`, { is_archived: false })
    showAlert('Course unarchived')
    fetchCourses()
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Failed to unarchive course', 'error')
  }
}

async function deleteCourse(course) {
  if (!confirm(`Delete "${course.name}"? This cannot be undone.`)) return
  try {
    await axios.delete(`/courses/${course.id}`)
    showAlert('Course deleted')
    if (managingCourse.value && managingCourse.value.id === course.id) {
      managingCourse.value = null
    }
    fetchCourses()
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Failed to delete course', 'error')
  }
}

async function viewAsCourseStudent(course) {
  try {
    const { data } = await axios.post('/auth/impersonate', {
      target_role: 'student',
      course_id: course.id,
    })
    startImpersonation(
      data.token,
      data.impersonated_user,
      data.original_user,
      data.mode,
      course.id,
      course.name,
    )
    router.push('/dashboard')
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Failed to start student preview', 'error')
  }
}

// ---- Course Management ----

const assignedLabIds = computed(() => new Set(courseLabs.value.map(l => l.id)))

const assignLabsByTrackLevel = computed(() => {
  const assigned = assignedLabIds.value
  const grouped = {}
  for (const lab of availableLabs.value) {
    if (assigned.has(lab.id)) continue
    const trackName = lab.track_name || 'Uncategorized'
    const levelName = lab.level_name || 'Uncategorized'
    const key = `${trackName}::${levelName}`
    if (!grouped[key]) grouped[key] = {
      track_name: trackName, level_name: levelName,
      track_sort_order: lab.track_sort_order ?? 999,
      level_number: lab.level_number ?? 999,
      labs: [] }
    grouped[key].labs.push(lab)
  }
  // Order labs within each level by sort_order, then name.
  for (const k of Object.keys(grouped)) {
    grouped[k].labs.sort((a, b) =>
      ((a.sort_order ?? 0) - (b.sort_order ?? 0)) || a.name.localeCompare(b.name))
  }
  return grouped
})

// Order groups by track sort order, then by level number, so "Level 2"
// precedes "Level 10" instead of sorting lexically by descriptive name.
const assignLevelKeys = computed(() => {
  const g = assignLabsByTrackLevel.value
  return Object.keys(g).sort((a, b) => {
    const ga = g[a], gb = g[b]
    return (ga.track_sort_order - gb.track_sort_order)
      || (ga.level_number - gb.level_number)
      || ga.level_name.localeCompare(gb.level_name)
  })
})

const assignedLabsByTrackLevel = computed(() => {
  const grouped = {}
  for (const lab of courseLabs.value) {
    const trackName = lab.track_name || 'Uncategorized'
    const levelName = lab.level_name || 'Uncategorized'
    const key = `${trackName}::${levelName}`
    if (!grouped[key]) grouped[key] = { track_name: trackName, level_name: levelName, labs: [] }
    grouped[key].labs.push(lab)
  }
  return grouped
})

const assignedLevelKeys = computed(() => Object.keys(assignedLabsByTrackLevel.value).sort())

const allAssignedExpanded = computed(() => {
  const keys = assignedLevelKeys.value
  if (!keys.length) return false
  return keys.every(k => expandedAssignedCategories.value[k])
})

const allAssignExpanded = computed(() => {
  const keys = assignLevelKeys.value
  if (!keys.length) return false
  return keys.every(k => expandedAssignCategories.value[k])
})

function toggleAssignedCategory(levelKey) {
  expandedAssignedCategories.value = { ...expandedAssignedCategories.value, [levelKey]: !expandedAssignedCategories.value[levelKey] }
}

function toggleAllAssignedCategories() {
  const keys = assignedLevelKeys.value
  const next = !keys.every(k => expandedAssignedCategories.value[k])
  const nextState = {}
  keys.forEach(k => { nextState[k] = next })
  expandedAssignedCategories.value = nextState
}

function toggleAssignCategory(levelKey) {
  expandedAssignCategories.value = { ...expandedAssignCategories.value, [levelKey]: !expandedAssignCategories.value[levelKey] }
}

function toggleAllAssignCategories() {
  const keys = assignLevelKeys.value
  const next = !keys.every(k => expandedAssignCategories.value[k])
  const nextState = {}
  keys.forEach(k => { nextState[k] = next })
  expandedAssignCategories.value = nextState
}

function selectAllInGroup(levelKey) {
  const group = assignLabsByTrackLevel.value[levelKey]
  if (!group) return
  const ids = group.labs.map(l => l.id)
  const current = new Set(selectedLabIds.value)
  ids.forEach(id => current.add(id))
  selectedLabIds.value = [...current]
}

async function fetchEnrollableUsers() {
  if (!managingCourse.value) return
  try {
    const res = await axios.get(`/instructor/courses/${managingCourse.value.id}/enrollable-users`)
    enrollableUsers.value = res.data || []
  } catch (e) {
    console.error('Failed to fetch enrollable users', e)
    enrollableUsers.value = []
  }
}

function toggleEnrollUser(id) {
  const next = new Set(selectedEnrollIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selectedEnrollIds.value = next
}

function selectAllFiltered() {
  const next = new Set(selectedEnrollIds.value)
  for (const u of filteredEnrollableUsers.value) next.add(u.id)
  selectedEnrollIds.value = next
}

function clearSelection() {
  selectedEnrollIds.value = new Set()
}

async function enrollSelectedStudents() {
  if (selectedEnrollIds.value.size === 0 || !managingCourse.value) return
  enrolling.value = true
  try {
    const ids = Array.from(selectedEnrollIds.value)
    const res = await axios.post(`/courses/${managingCourse.value.id}/enroll-bulk`, { user_ids: ids })
    const count = res.data.enrolled_count || ids.length
    selectedEnrollIds.value = new Set()
    enrollSearch.value = ''
    showAlert(`${count} student${count !== 1 ? 's' : ''} enrolled`)
    await fetchCourseStudents()
    await fetchEnrollableUsers()
    fetchCourses()
  } catch (e) {
    showAlert('Failed to enroll: ' + (e.response?.data?.detail || e.message), 'error')
  } finally {
    enrolling.value = false
  }
}

function syncSettingsForm() {
  if (!managingCourse.value) return
  const c = managingCourse.value
  settingsForm.value = {
    name: c.name || '',
    code: c.code || '',
    semester: c.semester || '',
    description: c.description || '',
    start_date: c.start_date ? c.start_date.substring(0, 10) : '',
    end_date: c.end_date ? c.end_date.substring(0, 10) : '',
  }
}

function resetSettingsForm() {
  syncSettingsForm()
}

async function saveCourseSettings() {
  if (!managingCourse.value) return
  savingSettings.value = true
  try {
    const payload = {
      name: settingsForm.value.name,
      code: settingsForm.value.code,
      semester: settingsForm.value.semester,
      description: settingsForm.value.description || null,
    }
    if (settingsForm.value.start_date) payload.start_date = new Date(settingsForm.value.start_date).toISOString()
    if (settingsForm.value.end_date) payload.end_date = new Date(settingsForm.value.end_date).toISOString()
    const res = await axios.put(`/courses/${managingCourse.value.id}`, payload)
    // Update local course data
    Object.assign(managingCourse.value, res.data.course || res.data)
    syncSettingsForm()
    fetchCourses()
    showAlert('Course settings saved')
  } catch (e) {
    showAlert('Failed to save settings: ' + (e.response?.data?.detail || e.message), 'error')
  } finally {
    savingSettings.value = false
  }
}

async function openCourseManager(course) {
  if (managingCourse.value && managingCourse.value.id === course.id) {
    managingCourse.value = null
    return
  }
  managingCourse.value = course
  courseManageTab.value = 'students'
  courseStudents.value = []
  courseLabs.value = []
  courseAssignments.value = []
  studentLabDetails.value = {}
  selectedLabIds.value = []
  expandedAssignment.value = null
  selectedEnrollIds.value = new Set()
  enrollSearch.value = ''
  syncSettingsForm()
  await Promise.all([fetchCourseStudents(), fetchCourseLabs(), fetchAvailableLabs(), fetchAssignments(), isAdmin ? fetchEnrollableUsers() : Promise.resolve()])
}

async function openCourseManagerTab(course, tab) {
  managingCourse.value = course
  courseManageTab.value = tab
  syncSettingsForm()
  courseStudents.value = []
  courseLabs.value = []
  courseAssignments.value = []
  studentLabDetails.value = {}
  selectedLabIds.value = []
  expandedAssignment.value = null
  selectedEnrollIds.value = new Set()
  enrollSearch.value = ''
  await Promise.all([fetchCourseStudents(), fetchCourseLabs(), fetchAvailableLabs(), fetchAssignments(), isAdmin ? fetchEnrollableUsers() : Promise.resolve()])
}

async function fetchCourseStudents() {
  if (!managingCourse.value) return
  try {
    const res = await axios.get(`/courses/${managingCourse.value.id}/students`)
    courseStudents.value = res.data.students || []
  } catch (e) {
    console.error('Failed to fetch course students:', e)
  }
}

async function fetchCourseLabs() {
  if (!managingCourse.value) return
  try {
    const res = await axios.get(`/courses/${managingCourse.value.id}`)
    courseLabs.value = res.data.labs || []
    const keys = assignedLevelKeys.value
    const expanded = {}
    keys.forEach(k => { expanded[k] = true })
    expandedAssignedCategories.value = expanded
  } catch (e) {
    console.error('Failed to fetch course exercises:', e)
  }
}

async function fetchAvailableLabs() {
  try {
    const res = await axios.get('/instructor/labs')
    availableLabs.value = res.data.labs || []
    const keys = assignLevelKeys.value
    const expanded = {}
    keys.forEach(k => { expanded[k] = true })
    expandedAssignCategories.value = expanded
  } catch (e) {
    console.error('Failed to fetch available exercises:', e)
  }
}

async function assignSelectedLabs() {
  if (!selectedLabIds.value.length || !managingCourse.value) return
  try {
    await axios.post(`/courses/${managingCourse.value.id}/labs`, { lab_ids: selectedLabIds.value })
    showAlert(`${selectedLabIds.value.length} exercise(s) assigned`)
    selectedLabIds.value = []
    await fetchCourseLabs()
    await fetchCourses()
  } catch (e) {
    showAlert('Failed to assign exercises', 'error')
  }
}

async function removeAllInGroup(levelKey) {
  const group = assignedLabsByTrackLevel.value[levelKey]
  if (!group) return
  if (!confirm(`Remove all ${group.labs.length} exercise(s) from ${group.track_name} > ${group.level_name}?`)) return
  try {
    for (const lab of group.labs) {
      await axios.delete(`/courses/${managingCourse.value.id}/labs/${lab.id}`)
    }
    showAlert(`${group.labs.length} exercise(s) removed`)
    await fetchCourseLabs()
    await fetchCourses()
  } catch (e) {
    showAlert('Failed to remove exercises', 'error')
  }
}

async function unassignLab(lab) {
  if (!managingCourse.value) return
  if (!confirm(`Remove "${lab.name}" from this course?`)) return
  try {
    await axios.delete(`/courses/${managingCourse.value.id}/labs/${lab.id}`)
    showAlert('Exercise removed from course')
    await fetchCourseLabs()
    await fetchCourses()
  } catch (e) {
    showAlert('Failed to remove exercise', 'error')
  }
}

function startRenameLab(lab) {
  renamingLabId.value = lab.id
  renameLabValue.value = lab.name
}

function cancelRenameLab() {
  renamingLabId.value = null
  renameLabValue.value = ''
}

async function saveRenameLab(lab) {
  if (!managingCourse.value) return
  const newName = renameLabValue.value.trim()
  try {
    await axios.put(`/courses/${managingCourse.value.id}/labs/${lab.id}`, {
      display_name: newName
    })
    showAlert(newName ? `Renamed to "${newName}"` : 'Name reset to default')
    renamingLabId.value = null
    renameLabValue.value = ''
    await fetchCourseLabs()
    await fetchAssignments()
  } catch (e) {
    showAlert('Failed to rename exercise', 'error')
  }
}

async function toggleStudentLabs(student) {
  if (studentLabDetails.value[student.id]) {
    const next = { ...studentLabDetails.value }
    delete next[student.id]
    studentLabDetails.value = next
    return
  }
  studentLabDetails.value = { ...studentLabDetails.value, [student.id]: 'loading' }
  try {
    const res = await axios.get(`/courses/${managingCourse.value.id}/scoreboard`)
    const entry = res.data.scoreboard.find(e => e.user_id === student.id)
    const labList = res.data.labs || []
    const details = labList.map(lab => {
      const scores = entry?.lab_scores?.[String(lab.id)] || {}
      return {
        lab_id: lab.id,
        lab_name: lab.name,
        completed: scores.completed || false,
        score: scores.score || 0,
        attempts: scores.attempts ?? 0,
        hints_used: scores.hints_used ?? 0,
      }
    })
    studentLabDetails.value = { ...studentLabDetails.value, [student.id]: details }
  } catch (e) {
    console.error('Failed to load exercise details', e)
    const next = { ...studentLabDetails.value }
    delete next[student.id]
    studentLabDetails.value = next
  }
}

async function resetStudentLab(student, lab) {
  if (!confirm(`Reset "${lab.lab_name}" for ${student.username}?`)) return
  resettingCourseLab.value = `${student.id}-${lab.lab_id}`
  try {
    await axios.post(`/courses/${managingCourse.value.id}/labs/${lab.lab_id}/reset/${student.id}`)
    showAlert('Exercise reset successfully')
    const next = { ...studentLabDetails.value }
    delete next[student.id]
    studentLabDetails.value = next
    await toggleStudentLabs(student)
  } catch (e) {
    showAlert('Failed to reset exercise', 'error')
  } finally {
    resettingCourseLab.value = null
  }
}

async function removeStudent(student) {
  if (!confirm(`Remove ${student.username} from this course?`)) return
  try {
    await axios.delete(`/courses/${managingCourse.value.id}/enroll/${student.id}`)
    showAlert('Student removed')
    await fetchCourseStudents()
    if (isAdmin) fetchEnrollableUsers()
    await fetchCourses()
    const next = { ...studentLabDetails.value }
    delete next[student.id]
    studentLabDetails.value = next
  } catch (e) {
    showAlert('Failed to remove student', 'error')
  }
}

async function downloadStudentReport(student) {
  downloadingReportUserId.value = student.id
  try {
    const res = await axios.get(`/courses/${managingCourse.value.id}/report/${student.id}`, { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `report_${managingCourse.value.code}_${student.username}.pdf`
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (e) {
    showAlert('Failed to download report', 'error')
  } finally {
    downloadingReportUserId.value = null
  }
}

async function downloadClassReport() {
  downloadingReport.value = true
  try {
    const res = await axios.get(`/courses/${managingCourse.value.id}/report`, { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `report_${managingCourse.value.code}_class.pdf`
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (e) {
    showAlert('Failed to download report', 'error')
  } finally {
    downloadingReport.value = false
  }
}

// ---- Assignments ----

async function fetchAssignments() {
  if (!managingCourse.value) return
  try {
    const res = await axios.get(`/courses/${managingCourse.value.id}/assignments`)
    courseAssignments.value = res.data.assignments || []
  } catch (e) {
    console.error('Failed to fetch assignments:', e)
  }
}

function onAsnDragStart(index, event) {
  dragIndex.value = index
  event.dataTransfer.effectAllowed = 'move'
}
function onAsnDragOver(index) {
  dragOverIndex.value = index
}
async function onAsnDrop(targetIndex) {
  const fromIndex = dragIndex.value
  if (fromIndex === null || fromIndex === targetIndex) { dragIndex.value = null; dragOverIndex.value = null; return }
  const items = [...courseAssignments.value]
  const [moved] = items.splice(fromIndex, 1)
  items.splice(targetIndex, 0, moved)
  courseAssignments.value = items
  dragIndex.value = null
  dragOverIndex.value = null
  const order = items.map((a, i) => ({ id: a.id, sort_order: i }))
  try {
    await axios.put(`/courses/${managingCourse.value.id}/assignments/reorder`, { assignment_order: order })
  } catch (e) {
    showAlert('Failed to reorder assignments', 'error')
    await fetchAssignments()
  }
}

function switchToAssignments() {
  courseManageTab.value = 'assignments'
  if (courseAssignments.value.length === 0) fetchAssignments()
}

async function createAssignment() {
  if (!newAssignment.value.name.trim() || !managingCourse.value) return
  try {
    const payload = {
      name: newAssignment.value.name.trim(),
      description: newAssignment.value.description.trim() || null,
      start_date: newAssignment.value.start_date || null,
      due_date: newAssignment.value.due_date || null,
    }
    await axios.post(`/courses/${managingCourse.value.id}/assignments`, payload)
    showAlert('Assignment created')
    showCreateAssignment.value = false
    newAssignment.value = { name: '', description: '', due_date: '', start_date: '' }
    await fetchAssignments()
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Failed to create assignment', 'error')
  }
}

function toggleAssignmentExpand(id) {
  assignmentLabSelection.value = []
  asnPickerExpanded.value = {}
  expandedAssignment.value = expandedAssignment.value === id ? null : id
  editingAssignment.value = null
}

function startEditAssignment(asn) {
  editingAssignment.value = asn.id
  editAssignmentData.value = {
    name: asn.name,
    description: asn.description || '',
    start_date: asn.start_date ? asn.start_date.slice(0, 16) : '',
    due_date: asn.due_date ? asn.due_date.slice(0, 16) : '',
  }
  if (expandedAssignment.value !== asn.id) expandedAssignment.value = asn.id
}

async function saveEditAssignment(asnId) {
  try {
    const payload = {
      name: editAssignmentData.value.name.trim(),
      description: editAssignmentData.value.description.trim() || null,
      start_date: editAssignmentData.value.start_date || null,
      due_date: editAssignmentData.value.due_date || null,
    }
    await axios.put(`/courses/${managingCourse.value.id}/assignments/${asnId}`, payload)
    showAlert('Assignment updated')
    editingAssignment.value = null
    await fetchAssignments()
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Failed to update', 'error')
  }
}

async function deleteAssignment(asn) {
  if (!confirm(`Delete assignment "${asn.name}"? Exercises will remain in the course.`)) return
  try {
    await axios.delete(`/courses/${managingCourse.value.id}/assignments/${asn.id}`)
    showAlert('Assignment deleted')
    if (expandedAssignment.value === asn.id) expandedAssignment.value = null
    await fetchAssignments()
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Failed to delete', 'error')
  }
}

function isAssignmentLocked(asn) {
  return !!asn.locked
}

function isAssignmentUnavailable(asn) {
  // Unavailable = manually locked OR not yet open (future start_date)
  return !!asn.locked || !!asn.not_yet_open
}

async function toggleAssignmentAvailability(asn) {
  const locked = isAssignmentLocked(asn)
  const action = locked ? 'unlock' : 'lock'
  if (!confirm(`${locked ? 'Unlock' : 'Lock'} "${asn.name}"${locked ? ' (students can access exercises)' : ' (students cannot access exercises)'}?`)) return
  try {
    await axios.put(`/courses/${managingCourse.value.id}/assignments/${asn.id}`, { locked: !locked })
    showAlert(locked ? 'Assignment unlocked' : 'Assignment locked')
    await fetchAssignments()
  } catch (e) {
    showAlert(e.response?.data?.detail || `Failed to ${action}`, 'error')
  }
}

function allLabsForAssignment(asn) {
  const inAssignment = new Set(asn.labs.map(l => l.id))
  return courseLabs.value.filter(l => !inAssignment.has(l.id))
}

function asnLabsByTrackLevel(asn) {
  const labs = allLabsForAssignment(asn)
  const grouped = {}
  for (const lab of labs) {
    const trackName = lab.track_name || 'Uncategorized'
    const levelName = lab.level_name || 'Uncategorized'
    const key = `${trackName}::${levelName}`
    if (!grouped[key]) grouped[key] = { track_name: trackName, level_name: levelName, labs: [] }
    grouped[key].labs.push(lab)
  }
  return grouped
}

async function addLabsToAssignment(asnId) {
  if (!assignmentLabSelection.value.length) return
  try {
    await axios.post(`/courses/${managingCourse.value.id}/assignments/${asnId}/labs`, {
      lab_ids: assignmentLabSelection.value,
    })
    showAlert(`${assignmentLabSelection.value.length} exercise(s) added`)
    assignmentLabSelection.value = []
    await fetchAssignments()
    await fetchCourseLabs()
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Failed to add labs', 'error')
  }
}

async function removeLabFromAssignment(asnId, labId) {
  try {
    await axios.delete(`/courses/${managingCourse.value.id}/assignments/${asnId}/labs/${labId}`)
    showAlert('Exercise removed from assignment')
    await fetchAssignments()
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Failed to remove', 'error')
  }
}

async function downloadAssignmentReport(asn) {
  try {
    const res = await axios.get(
      `/courses/${managingCourse.value.id}/assignments/${asn.id}/report`,
      { responseType: 'blob' }
    )
    const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `report_${managingCourse.value.code}_${asn.name.replace(/\s+/g, '_')}.pdf`
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (e) {
    showAlert('Failed to generate report', 'error')
  }
}

function openLab(lab) {
  router.push({ path: '/exercises', query: { labId: lab.id, courseId: managingCourse.value.id } })
}

function openLabDirect(lab) {
  router.push({ path: '/exercises', query: { labId: lab.id } })
}

function dueBadgeClass(dueDate) {
  if (!dueDate) return 'due-badge--none'
  const now = new Date()
  const due = new Date(dueDate)
  const diffDays = (due - now) / (1000 * 60 * 60 * 24)
  if (diffDays < 0) return 'due-badge--ended'
  if (diffDays <= 3) return 'due-badge--soon'
  return 'due-badge--ok'
}

function dueBadgeText(dueDate) {
  if (!dueDate) return 'No due date'
  const due = new Date(dueDate)
  const now = new Date()
  const dueDay = new Date(due.getFullYear(), due.getMonth(), due.getDate())
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const diffDays = Math.round((dueDay - today) / (1000 * 60 * 60 * 24))
  if (diffDays < 0) return `Ended ${due.toLocaleDateString()}`
  if (diffDays === 0) return 'Due today'
  if (diffDays === 1) return 'Due tomorrow'
  if (diffDays <= 7) return `Due in ${diffDays} days`
  return `Due ${due.toLocaleDateString()}`
}

function startBadgeClass(startDate) {
  if (!startDate) return 'due-badge--none'
  const now = new Date()
  const start = new Date(startDate)
  if (start <= now) return 'due-badge--ok'
  return 'due-badge--soon'
}

function startBadgeText(startDate) {
  if (!startDate) return ''
  const start = new Date(startDate)
  const now = new Date()
  if (start <= now) return `Available since ${start.toLocaleDateString()}`
  // Compare calendar dates to avoid rounding issues
  const startDay = new Date(start.getFullYear(), start.getMonth(), start.getDate())
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const diffDays = Math.round((startDay - today) / (1000 * 60 * 60 * 24))
  if (diffDays === 0) return 'Opens today'
  if (diffDays === 1) return 'Opens tomorrow'
  if (diffDays <= 7) return `Opens in ${diffDays} days`
  return `Opens ${start.toLocaleDateString()}`
}

// ---- My Exercises tab ----

const courseSummariesForSidebar = computed(() => {
  const counts = {}
  for (const [labId, assignedCourses] of Object.entries(labAssignments.value)) {
    for (const c of assignedCourses) {
      counts[c.id] = (counts[c.id] || 0) + 1
    }
  }
  return courses.value
    .filter(c => !c.is_archived)
    .map(c => ({ id: c.id, name: c.name, code: c.code, lab_count: counts[c.id] || 0 }))
    .sort((a, b) => a.name.localeCompare(b.name))
})

const filteredLabs = computed(() => {
  let result = labs.value
  if (selectedCourse.value) {
    result = result.filter(lab => {
      const assigned = labAssignments.value[lab.id] || []
      return assigned.some(c => c.id === selectedCourse.value)
    })
  }
  if (selectedTrack.value) {
    result = result.filter(lab => lab.track_slug === selectedTrack.value)
  }
  if (difficultyFilter.value) {
    result = result.filter(lab => lab.difficulty === difficultyFilter.value)
  }
  if (assignmentFilter.value === 'assigned') {
    result = result.filter(lab => labAssignments.value[lab.id] && labAssignments.value[lab.id].length > 0)
  } else if (assignmentFilter.value === 'unassigned') {
    result = result.filter(lab => !labAssignments.value[lab.id] || labAssignments.value[lab.id].length === 0)
  }
  if (labSearch.value.trim()) {
    const q = labSearch.value.toLowerCase()
    result = result.filter(lab =>
      lab.name.toLowerCase().includes(q) ||
      (lab.description || '').toLowerCase().includes(q)
    )
  }
  result = [...result].sort((a, b) => {
    const trackA = a.track_sort_order ?? 999
    const trackB = b.track_sort_order ?? 999
    if (trackA !== trackB) return trackA - trackB
    const levelA = a.level_number ?? 999
    const levelB = b.level_number ?? 999
    if (levelA !== levelB) return levelA - levelB
    const sortA = a.sort_order ?? 0
    const sortB = b.sort_order ?? 0
    return sortA - sortB
  })
  return result
})

function unassignedCoursesForLab(labId) {
  const assigned = new Set((labAssignments.value[labId] || []).map(c => c.id))
  return courses.value.filter(c => !assigned.has(c.id) && !c.is_archived)
}

async function quickAssignLab(labId, courseId) {
  if (!courseId) return
  assigningLabId.value = labId
  try {
    await axios.post(`/courses/${courseId}/labs`, { lab_ids: [labId] })
    await fetchLabAssignments()
    showAlert('Exercise assigned to course')
  } catch (e) {
    showAlert('Failed to assign exercise', 'error')
  } finally {
    assigningLabId.value = null
  }
}

async function quickUnassignLab(labId, courseId, courseName) {
  if (!confirm(`Remove this exercise from ${courseName}?`)) return
  try {
    await axios.delete(`/courses/${courseId}/labs/${labId}`)
    await fetchLabAssignments()
    showAlert(`Removed from ${courseName}`)
  } catch (e) {
    showAlert('Failed to remove exercise', 'error')
  }
}

// ---- Upload functions ----

function handleFileSelect(event) {
  const file = event.target.files[0]
  if (!file) { uploadFile.value = null; uploadPreview.value = null; return }
  uploadFile.value = file
  uploadPreview.value = { name: file.name, size: (file.size / 1024).toFixed(1) + ' KB' }
  uploadError.value = ''
  uploadWarnings.value = []
}

async function submitUpload() {
  if (!uploadFile.value || !uploadTrack.value) {
    uploadError.value = 'Please select a ZIP file and a track'
    return
  }
  uploading.value = true
  uploadError.value = ''
  uploadWarnings.value = []
  try {
    const formData = new FormData()
    formData.append('file', uploadFile.value)
    formData.append('track', uploadTrack.value)
    if (uploadLevelId.value) formData.append('level_id', uploadLevelId.value)
    const { data } = await axios.post('/instructor/labs/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    uploadWarnings.value = data.warnings || []
    showAlert(`Exercise "${data.slug}" uploaded (${data.file_count} files). Status: Draft.`)
    if (!data.warnings.length) {
      showUploadModal.value = false
      resetUploadForm()
    }
    fetchLabs()
  } catch (e) {
    uploadError.value = e.response?.data?.detail || 'Upload failed'
  } finally {
    uploading.value = false
  }
}

function resetUploadForm() {
  uploadFile.value = null
  uploadTrack.value = ''
  uploadLevelId.value = null
  uploadPreview.value = null
  uploadError.value = ''
  uploadWarnings.value = []
}

async function changeVisibility(lab, newVis) {
  changingVisibility.value = lab.id
  try {
    await axios.put(`/instructor/labs/${lab.id}/visibility`, { visibility: newVis })
    showAlert(`Visibility changed to "${newVis}"`)
    fetchLabs()
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Failed to change visibility', 'error')
  } finally {
    changingVisibility.value = null
  }
}

async function deleteExercise(lab) {
  if (!confirm(`Delete "${lab.name}"? This removes the exercise from the database and disk permanently.`)) return
  try {
    await axios.delete(`/instructor/labs/${lab.id}`)
    showAlert(`Exercise "${lab.name}" deleted`)
    fetchLabs()
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Failed to delete exercise', 'error')
  }
}

// ---- Categorize (track/level) ----
const trackCatalog = ref([])
const categorizeLab = ref(null)
const categorizeTrackId = ref(null)
const categorizeLevelId = ref(null)
const categorizeSaving = ref(false)
const categorizeLevelOptions = computed(() => {
  if (!categorizeTrackId.value) return []
  const t = trackCatalog.value.find(t => t.id === categorizeTrackId.value)
  return t ? t.levels : []
})

async function ensureTrackCatalog() {
  if (trackCatalog.value.length) return
  const { data } = await axios.get('/instructor/tracks-and-levels')
  trackCatalog.value = data.tracks || []
}

async function openCategorizeModal(lab) {
  try {
    await ensureTrackCatalog()
    categorizeLab.value = lab
    categorizeLevelId.value = lab.level_id || null
    categorizeTrackId.value = null
    if (lab.level_id) {
      const owner = trackCatalog.value.find(t => t.levels.some(l => l.id === lab.level_id))
      if (owner) categorizeTrackId.value = owner.id
    }
  } catch (e) {
    showAlert('Failed to load tracks', 'error')
  }
}

async function saveCategorize() {
  if (!categorizeLab.value) return
  if (categorizeTrackId.value && !categorizeLevelId.value) {
    showAlert('Pick a level, or switch back to "Course Assessments"', 'error')
    return
  }
  categorizeSaving.value = true
  try {
    await axios.put(`/instructor/labs/${categorizeLab.value.id}`, {
      level_id: categorizeLevelId.value ?? null,
    })
    showAlert('Exercise re-categorized')
    categorizeLab.value = null
    fetchLabs()
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Failed to re-categorize', 'error')
  } finally {
    categorizeSaving.value = false
  }
}

// ---- Exercise tester functions ----

const _processTestEvents = (events, ctx) => {
  for (const event of events) {
    if (event.type === 'started' && event.run_id) {
      testerRunId.value = event.run_id
      testerProgressTotal.value = event.total_labs || 0
    } else if (event.type === 'lab_start') {
      ctx.currentLabSlug = event.lab_slug
      ctx.currentLabName = event.lab_name
      ctx.labSections[ctx.currentLabSlug] = []
      const sep = { name: `Testing: ${event.lab_name}`, test_key: `_lab_${event.lab_slug}`, status: 'running', lines: [] }
      ctx.sectionMap[sep.test_key] = sep
      testerSections.value.push(sep)
    } else if (event.type === 'section_start') {
      const section = { name: event.name, test_key: event.test_key, status: 'running', lines: [] }
      ctx.sectionMap[event.test_key] = section
      testerSections.value.push(section)
      if (ctx.currentLabSlug && ctx.labSections[ctx.currentLabSlug]) {
        ctx.labSections[ctx.currentLabSlug].push(section)
      }
    } else if (event.type === 'line') {
      const sec = ctx.sectionMap[event.test_key]
      if (sec) {
        sec.lines.push({ timestamp: event.timestamp, level: event.level, message: event.message })
        testerSections.value = [...testerSections.value]
      }
    } else if (event.type === 'section_end') {
      const sec = ctx.sectionMap[event.test_key]
      if (sec) sec.status = event.status
      testerSections.value = [...testerSections.value]
    } else if (event.type === 'lab_end') {
      testerProgressCurrent.value++
      testerLabDurations.value.push(event.duration_seconds || 0)
      const sep = ctx.sectionMap[`_lab_${event.lab_slug}`]
      if (sep) {
        sep.status = event.status
        sep.lines.push({ timestamp: '', level: event.status === 'ok' ? 'ok' : 'error', message: `Completed in ${event.duration_seconds}s -- ${event.status.toUpperCase()}` })
        testerSections.value = [...testerSections.value]
      }
      testerResults.value = {
        ...testerResults.value,
        [event.lab_slug]: {
          status: event.status,
          date: new Date().toLocaleString(),
          labName: ctx.currentLabName || event.lab_slug,
          duration: event.duration_seconds,
          sections: JSON.parse(JSON.stringify(ctx.labSections[event.lab_slug] || []))
        }
      }
    } else if (event.type === 'complete') {
      testerComplete.value = event
    }
  }
  nextTick(() => {
    if (testerTerminalRef.value) {
      testerTerminalRef.value.scrollTop = testerTerminalRef.value.scrollHeight
    }
  })
}

const _startPolling = (runId) => {
  if (_testerPollTimer) { clearTimeout(_testerPollTimer); _testerPollTimer = null }
  let afterIdx = 0
  const ctx = { sectionMap: {}, labSections: {}, currentLabSlug: null, currentLabName: null }
  const poll = async () => {
    try {
      const res = await axios.get(`/instructor/exercise-test/events/${runId}`, { params: { after: afterIdx } })
      const { events, status, labs_completed, event_count } = res.data
      testerProgressCurrent.value = labs_completed
      if (events && events.length) {
        _processTestEvents(events, ctx)
      }
      afterIdx = event_count
      if (status !== 'running') {
        testerRunning.value = false
        testerCancelling.value = false
        _testerPollTimer = null
        await fetchTesterResults()
        return
      }
    } catch (e) {
      console.error('Test poll error:', e)
    }
    _testerPollTimer = setTimeout(poll, 2000)
  }
  poll()
}

async function runTestForLab(lab) {
  testingLabSlug.value = lab.slug
  showTesterPanel.value = true
  testerRunning.value = true
  testerCancelling.value = false
  testerRunId.value = null
  testerSections.value = []
  testerComplete.value = null
  testerProgressCurrent.value = 0
  testerProgressTotal.value = 0
  testerLabDurations.value = []
  try {
    const res = await axios.post('/instructor/exercise-test', { lab_slugs: [lab.slug] })
    const { run_id, total_labs } = res.data
    testerRunId.value = run_id
    testerProgressTotal.value = total_labs
    _startPolling(run_id)
  } catch (e) {
    showAlert(`Exercise tester failed: ${e.response?.data?.detail || e.message}`, 'error')
    testerRunning.value = false
  }
}

async function cancelTest() {
  testerCancelling.value = true
  if (testerRunId.value) {
    try {
      await axios.post('/instructor/exercise-test/cancel', { run_id: testerRunId.value })
    } catch (e) {
      console.error('Cancel request failed', e)
    }
  }
  setTimeout(async () => { await fetchTesterResults() }, 3000)
}

async function fetchTesterResults() {
  // Not shipped in every edition; the backend reports availability.
  if (!exerciseTester.value) return
  try {
    const { data } = await axios.get('/instructor/exercise-test/results')
    testerResults.value = data
  } catch {}
}

async function checkActiveTestRun() {
  if (!exerciseTester.value) return
  try {
    const res = await axios.get('/instructor/exercise-test/active')
    if (res.data.run_id && res.data.status === 'running') {
      testerRunning.value = true
      testerRunId.value = res.data.run_id
      testerProgressTotal.value = res.data.total_labs
      testerProgressCurrent.value = res.data.labs_completed
      showTesterPanel.value = true
      testerSections.value = []
      testerComplete.value = null
      testerLabDurations.value = []
      _startPolling(res.data.run_id)
    }
  } catch {}
}

// ---- Data fetching ----

async function fetchCourses() {
  coursesLoading.value = true
  try {
    const { data } = await axios.get('/instructor/courses')
    courses.value = data
  } catch (e) {
    console.error('Failed to fetch courses:', e)
  } finally {
    coursesLoading.value = false
  }
}

async function fetchLabs() {
  labsLoading.value = true
  try {
    const { data } = await axios.get('/instructor/labs')
    labs.value = data.labs
    trackSummaries.value = data.tracks
  } catch (e) {
    console.error('Failed to fetch exercises:', e)
  } finally {
    labsLoading.value = false
  }
}

async function fetchLabAssignments() {
  try {
    const { data } = await axios.get('/instructor/labs/assignments')
    labAssignments.value = data
  } catch (e) {
    console.error('Failed to fetch exercise assignments:', e)
  }
}

onMounted(() => {
  fetchModules()
  fetchCourses()
  fetchLabs()
  fetchLabAssignments()
  fetchTesterResults()
  checkActiveTestRun()
})

onUnmounted(() => {
  if (_testerPollTimer) { clearTimeout(_testerPollTimer); _testerPollTimer = null }
})
</script>

<style scoped>
.instructor-panel {
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem;
  position: relative;
}

.panel-header {
  margin-bottom: 1.5rem;
}

.panel-header h1 {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
}

.panel-subtitle {
  color: var(--text-secondary);
  font-size: 0.875rem;
  margin-top: 0.25rem;
}

/* Tab Bar */
.tab-bar {
  display: flex;
  gap: 0.25rem;
  border-bottom: 1px solid var(--border-color);
  margin-bottom: 1.5rem;
}

.tab-btn {
  padding: 0.75rem 1.25rem;
  background: transparent;
  border: none;
  color: var(--text-secondary);
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.15s;
}

.tab-btn:hover { color: var(--hover-text); }

.tab-btn--active {
  color: var(--accent);
  border-bottom-color: var(--accent);
}

/* Panel */
.panel {
  background: var(--bg-secondary);
  border-radius: 12px;
  padding: 1.5rem;
  border: 1px solid var(--border-color);
}

/* Section Header */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.section-header h2 {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
}

/* Buttons */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 6px;
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  text-decoration: none;
  transition: all 0.15s;
}

.btn--primary { background: var(--accent); color: #fff; }
.btn--primary:hover { background: #2563eb; }
.btn--secondary { background: var(--bg-tertiary); color: var(--text-secondary); border: 1px solid var(--border-color); }
.btn--secondary:hover { border-color: var(--accent); color: var(--accent); }
.btn--success { background: var(--success); color: #fff; }
.btn--success:hover:not(:disabled) { background: #16a34a; }
.btn--success:disabled { opacity: 0.5; cursor: not-allowed; }
.btn--danger { background: transparent; border: 1px solid var(--danger); color: var(--danger); }
.btn--danger:hover { background: rgba(239, 68, 68, 0.1); }
.btn--outline { background: transparent; border: 1px solid var(--border-color); color: var(--text-secondary); }
.btn--outline:hover { border-color: var(--accent); color: var(--accent); }
.btn--sm { padding: 0.375rem 0.75rem; font-size: 0.75rem; }
.btn--xs { padding: 0.25rem 0.5rem; font-size: 0.6875rem; }

/* Table */
.table-container { overflow-x: auto; }

.data-table { width: 100%; border-collapse: collapse; }

.data-table th,
.data-table td {
  padding: 0.75rem 1rem;
  text-align: left;
  border-bottom: 1px solid var(--bg-secondary);
}

.data-table th {
  font-size: 0.6875rem;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  background: var(--bg-primary);
}

.data-table td {
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.data-table tr:hover td { background: var(--hover-bg); }

.row--selected td { background: rgba(59, 130, 246, 0.08) !important; }

.data-table--nested { font-size: 0.8rem; }
.data-table--nested th { font-size: 0.625rem; padding: 0.35rem 0.5rem; }
.data-table--nested td { padding: 0.35rem 0.5rem; }

.cell-primary { font-weight: 500; color: var(--text-primary); }
.cell-muted { color: var(--text-muted); font-size: 0.8rem; }
.cell-actions { display: flex; gap: 0.35rem; flex-wrap: wrap; }

/* Action buttons */
.action-btn {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s;
}

.action-btn svg { width: 14px; height: 14px; }

.action-btn--view { background: rgba(59, 130, 246, 0.15); color: var(--accent); }
.action-btn--view:hover { background: var(--accent); color: white; }

.action-btn--manage { background: rgba(59, 130, 246, 0.15); color: var(--accent); }
.action-btn--manage:hover { background: var(--accent); color: white; }

.action-btn--archive { background: rgba(148, 163, 184, 0.15); color: var(--text-secondary); }
.action-btn--archive:hover { background: var(--text-secondary); color: white; }

.action-btn--delete { background: rgba(239, 68, 68, 0.15); color: var(--danger); }
.action-btn--delete:hover { background: var(--danger); color: white; }
.action-btn--impersonate { background: rgba(245, 158, 11, 0.15); color: var(--warning); }
.action-btn--impersonate:hover { background: var(--warning); color: white; }
.action-btn--available { background: rgba(34, 197, 94, 0.15); color: #22c55e; }
.action-btn--available:hover { background: #22c55e; color: white; }
.action-btn--locked { background: rgba(234, 179, 8, 0.15); color: #eab308; }
.action-btn--locked:hover { background: #eab308; color: white; }
.action-btn--test { background: rgba(245, 158, 11, 0.15); color: #f59e0b; margin-left: 0.375rem; }
.action-btn--test:hover { background: #f59e0b; color: white; }
.action-btn--test:disabled { opacity: 0.4; cursor: not-allowed; }

/* Status badges */
.status-badge {
  font-size: 0.6875rem;
  font-weight: 600;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.status-badge--active { background: rgba(34, 197, 94, 0.15); color: #4ade80; }
.status-badge--ended { background: rgba(148, 163, 184, 0.15); color: var(--text-secondary); }
.status-badge--upcoming { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }
.status-badge--inactive { background: rgba(239, 68, 68, 0.15); color: #f87171; }
.status-badge--archived { background: rgba(148, 163, 184, 0.15); color: #94a3b8; }
.status-badge--done { background: rgba(34, 197, 94, 0.15); color: #4ade80; }
.status-badge--pending { background: rgba(148, 163, 184, 0.15); color: #94a3b8; }

/* Invite code */
.invite-code-display {
  font-family: monospace;
  font-size: 0.75rem;
  color: var(--warning);
  background: rgba(245, 158, 11, 0.1);
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  cursor: pointer;
}

.invite-code-display:hover { background: rgba(245, 158, 11, 0.2); }

/* Inline Course Management */
.course-manage-section {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 1.25rem;
  margin-top: 1rem;
}

.manage-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.manage-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
}

/* Sub-tabs */
.sub-tabs {
  display: flex;
  gap: 0.25rem;
  margin-bottom: 1rem;
  border-bottom: 1px solid var(--border-color);
}

.sub-tab {
  padding: 0.5rem 1rem;
  background: transparent;
  border: none;
  color: var(--text-secondary);
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.15s;
}

.sub-tab:hover { color: var(--hover-text); }

.sub-tab.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
}

.sub-tab-content {
  min-height: 100px;
}

.students-note {
  font-size: 0.85rem;
  color: var(--text-muted);
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 0.75rem 1rem;
  margin-bottom: 1rem;
}

/* Student lab detail */
.student-labs-row td {
  padding: 0 !important;
  border-bottom: 1px solid var(--border-color);
}

.student-labs-detail {
  padding: 0.75rem 1rem;
  background: rgba(59, 130, 246, 0.04);
  border-left: 3px solid var(--accent);
  margin: 0 0.75rem 0.5rem;
}

.loading-text { color: var(--text-muted); font-size: 0.85rem; padding: 0.5rem 0; }

/* Assign exercises */
.assign-exercises-form {
  margin-bottom: 1rem;
}

.assign-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.assign-header-row h4 {
  color: var(--text-primary);
  font-size: 0.9rem;
  font-weight: 600;
  margin: 0;
}

.assign-accordion {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-bottom: 0.75rem;
}

.assign-group__header-row {
  display: flex;
  align-items: center;
  gap: 0;
}

.assign-group__header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 1;
  padding: 0.5rem 0.75rem;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px 0 0 6px;
  color: var(--text-secondary);
  font-size: 0.8125rem;
  text-align: left;
  cursor: pointer;
}

.assign-group__header:hover { border-color: var(--accent); color: var(--text-primary); }

.assign-group__add-all {
  border-radius: 0 6px 6px 0 !important;
  border-left: none !important;
}

.assign-group__chevron {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  transition: transform 0.2s;
}

.assign-group__chevron--open { transform: rotate(90deg); }

.assign-group__track { font-weight: 500; color: var(--text-primary); }
.assign-group__sep { color: var(--nav-label); }
.assign-group__level { color: var(--text-secondary); }
.assign-group__count { font-size: 0.75rem; color: var(--text-muted); }

.assign-group__body {
  padding: 0.5rem 0.75rem 0.5rem 2rem;
  border-left: 2px solid var(--border-color);
  margin-left: 0.5rem;
}

.lab-checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 0;
  cursor: pointer;
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.lab-checkbox-label input { flex-shrink: 0; }
.lab-checkbox-name { flex: 1; color: var(--text-primary); }
.lab-checkbox-diff { font-size: 0.6875rem; text-transform: capitalize; color: var(--text-muted); }

.assign-selected-btn { margin-top: 0.5rem; }

.assigned-exercises-section { margin-bottom: 0; }

.section-divider {
  border: none;
  border-top: 1px solid var(--border-color, #1e293b);
  margin: 1.75rem 0;
  position: relative;
}

.section-divider::after {
  content: '';
  display: block;
  width: 48px;
  height: 3px;
  background: var(--accent, #38bdf8);
  border-radius: 2px;
  margin: -2px auto 0;
}

.assigned-lab-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 0;
  font-size: 0.8125rem;
}

.attempts-toggle {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 0 0.35rem 0 0;
  font-size: 0.7rem;
}
.attempts-toggle:hover { color: var(--text-primary); }

.attempts-row > td { background: rgba(0, 0, 0, 0.15); padding: 0.5rem 0.75rem; }
.attempts-table { font-size: 0.75rem; }

.attempt-value {
  font-family: 'Courier New', monospace;
  font-size: 0.72rem;
  color: var(--text-primary);
  word-break: break-all;
}

.assigned-lab-row .lab-checkbox-name { flex: 1; color: var(--text-primary); }
.assigned-lab-row .lab-checkbox-diff { font-size: 0.6875rem; text-transform: capitalize; color: var(--text-muted); }

.lab-flag-value {
  font-family: 'Courier New', monospace;
  font-size: 0.75rem;
  color: #4ade80;
  background: rgba(34, 197, 94, 0.12);
  border: 1px solid rgba(34, 197, 94, 0.3);
  border-radius: 4px;
  padding: 0.2rem 0.45rem;
  user-select: all;
  word-break: break-all;
}

.assign-group__remove-all {
  border-radius: 0 6px 6px 0 !important;
  border-left: none !important;
  color: var(--danger) !important;
  border-color: var(--danger) !important;
}
.assign-group__remove-all:hover { background: rgba(239, 68, 68, 0.1) !important; }

/* Report */
.report-actions { margin-bottom: 0.75rem; }

.report-description {
  font-size: 0.85rem;
  color: var(--text-muted);
}

/* Catalog Layout (My Exercises tab) */
.catalog-layout {
  display: flex;
  gap: 1.5rem;
}

.topic-sidebar {
  width: 240px;
  min-width: 240px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 1rem;
  height: fit-content;
  position: sticky;
  top: 1rem;
}

.sidebar-title {
  font-size: 0.625rem;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  padding: 0 0.5rem 0.75rem;
}

.topic-item {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  width: 100%;
  padding: 0.5rem 0.625rem;
  background: transparent;
  border: none;
  color: var(--text-secondary);
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.15s ease;
  text-align: left;
}

.topic-item:hover { background: var(--hover-bg); color: var(--hover-text); }
.topic-item--active { background: var(--accent-bg, rgba(59, 130, 246, 0.1)); color: var(--accent); }

.topic-item__dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.topic-item__name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.topic-item__count {
  font-size: 0.6875rem;
  color: var(--text-muted);
  background: var(--bg-tertiary);
  padding: 0.0625rem 0.4375rem;
  border-radius: 9999px;
  flex-shrink: 0;
}

.topic-item--active .topic-item__count { background: rgba(59, 130, 246, 0.2); color: var(--accent); }

.labs-panel { flex: 1; min-width: 0; }

.filter-bar {
  display: flex;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.search-input {
  flex: 1;
  padding: 0.5rem 0.75rem;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 0.8125rem;
}

.search-input::placeholder { color: var(--text-muted); }

.filter-select {
  padding: 0.5rem 0.75rem;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 0.8125rem;
}

.results-count {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-bottom: 0.75rem;
}

.table-wrapper {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
}

.lab-name { font-weight: 500; color: var(--text-primary); }
.lab-name--link { cursor: pointer; }
.lab-name--link:hover { color: var(--accent); text-decoration: underline; }
.lab-desc { font-size: 0.75rem; color: var(--text-muted); margin-top: 0.125rem; }

.difficulty-badge {
  font-size: 0.6875rem;
  font-weight: 600;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  text-transform: capitalize;
}

.difficulty-beginner { background: rgba(34, 197, 94, 0.15); color: #4ade80; }
.difficulty-intermediate { background: rgba(234, 179, 8, 0.15); color: #facc15; }
.difficulty-advanced { background: rgba(239, 68, 68, 0.15); color: #f87171; }

.track-badge {
  display: inline-block;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.6875rem;
  font-weight: 600;
  white-space: nowrap;
}

.empty-row { text-align: center; color: var(--text-muted); padding: 2rem 1rem !important; }

.sidebar-divider { border-top: 1px solid var(--border-color); margin: 0.75rem 0; }

.assigned-courses-cell { display: flex; flex-wrap: wrap; gap: 0.25rem; }

.course-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.15rem;
  font-size: 0.625rem;
  font-weight: 600;
  padding: 0.125rem 0.4rem;
  border-radius: 9999px;
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  white-space: nowrap;
}

.course-pill--removable {
  cursor: pointer;
  transition: all 0.15s;
}

.course-pill--removable:hover {
  background: rgba(239, 68, 68, 0.2);
  color: #f87171;
}

.pill-x {
  font-size: 0.75rem;
  line-height: 1;
  opacity: 0;
  transition: opacity 0.15s;
}

.course-pill--removable:hover .pill-x { opacity: 1; }

.unassigned-label { color: var(--text-muted); font-size: 0.8125rem; }

.assign-action { min-width: 130px; }

.assign-select {
  width: 100%;
  padding: 0.3rem 0.5rem;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 5px;
  color: var(--text-secondary);
  font-size: 0.75rem;
  cursor: pointer;
  transition: border-color 0.15s;
}

.assign-select:hover { border-color: var(--accent); }
.assign-select:disabled { opacity: 0.6; cursor: wait; }

/* Form inputs (dark-mode friendly) */
.form-input {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 0.625rem 0.875rem;
  color: var(--text-primary);
  font-size: 0.875rem;
  width: 100%;
}
.form-input:focus {
  outline: none;
  border-color: var(--accent);
}
.form-input::placeholder {
  color: var(--text-muted);
}
.form-input::-webkit-calendar-picker-indicator {
  filter: invert(0.85) brightness(1.2);
  cursor: pointer;
}

/* Assignment Cards */
.create-assignment-form {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1rem;
}
.create-assignment-form .form-row {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}
.form-label-inline {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.8rem;
  color: var(--text-secondary);
  white-space: nowrap;
}
.assignment-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  margin-bottom: 0.75rem;
  transition: border-color 0.2s;
}
.assignment-card:hover { border-color: var(--accent); }
.assignment-card--expanded { border-color: var(--accent); }
.assignment-card[draggable="true"] { cursor: grab; }
.assignment-card--dragging { opacity: 0.4; }
.assignment-card--drag-over { border-top: 2.5px solid var(--accent, #6366f1); }
.drag-grip { width: 16px; height: 16px; color: var(--text-muted); flex-shrink: 0; cursor: grab; }
.assignment-card__header {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.25rem;
  cursor: pointer;
}
.assignment-card__info { flex: 1; min-width: 0; }
.assignment-card__name {
  font-weight: 600;
  font-size: 0.95rem;
  color: var(--text-primary);
  display: block;
}
.assignment-card__desc {
  font-size: 0.8rem;
  color: var(--text-muted);
  display: block;
  margin-top: 0.15rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.assignment-card__meta {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  flex-shrink: 0;
}
.assignment-card__count {
  font-size: 0.8rem;
  color: var(--text-secondary);
  white-space: nowrap;
}
.assignment-card__actions {
  display: flex;
  gap: 0.35rem;
  flex-shrink: 0;
}
.assignment-card__body {
  padding: 0 1.25rem 1.25rem;
  border-top: 1px solid var(--border-color);
}
.edit-assignment-form {
  padding: 0.75rem 0;
}
.edit-assignment-form .form-row {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}
.assignment-labs-list {
  padding: 0.75rem 0;
}
.assignment-lab-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.4rem 0;
  border-bottom: 1px solid var(--border-color);
}
.assignment-lab-row:last-child { border-bottom: none; }
.assignment-lab-name {
  flex: 1;
  font-size: 0.85rem;
  color: var(--text-primary);
}
.assignment-add-labs {
  padding-top: 0.75rem;
  border-top: 1px solid var(--border-color);
}
.assignment-add-labs h5 {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 0.5rem;
}
.assignment-lab-checkboxes label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.3rem 0;
  font-size: 0.85rem;
  color: var(--text-primary);
  cursor: pointer;
}
.empty-hint {
  font-size: 0.8rem;
  color: var(--text-muted);
  padding: 0.5rem 0;
}
.action-btn--xs {
  width: 22px;
  height: 22px;
  padding: 2px;
}
.action-btn--xs svg {
  width: 12px;
  height: 12px;
}

/* Due date badges */
.due-badge {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.2rem 0.6rem;
  border-radius: 4px;
  white-space: nowrap;
}
.due-badge--ok { color: var(--success); background: rgba(34, 197, 94, 0.1); }
.due-badge--soon { color: var(--warning); background: rgba(245, 158, 11, 0.1); }
.due-badge--overdue, .due-badge--ended { color: var(--text-muted); background: rgba(100, 116, 139, 0.1); }
.due-badge--none { color: var(--text-muted); background: rgba(148, 163, 184, 0.1); }

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.form-group label {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--text-secondary);
}

/* Course Card Grid */
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
  display: flex;
  flex-direction: column;
}

.course-card:hover {
  border-color: var(--accent);
  transform: translateY(-2px);
}

.course-card--active {
  border-color: var(--accent);
  box-shadow: 0 0 0 1px var(--accent);
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
  background: var(--accent-bg, rgba(59, 130, 246, 0.1));
  padding: 0.2rem 0.6rem;
  border-radius: 4px;
}

.course-status {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.2rem 0.6rem;
  border-radius: 4px;
}

.course-card__name {
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.15rem;
}

.course-card__semester {
  font-size: 0.8rem;
  color: var(--text-secondary);
  margin-bottom: 0.5rem;
}

.course-card__desc {
  font-size: 0.8rem;
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
  margin-bottom: 0.75rem;
}

.course-card__stats .stat {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.course-card__footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: auto;
  padding-top: 0.75rem;
  border-top: 1px solid var(--border-color);
}

.invite-chip {
  font-size: 0.6875rem;
  font-weight: 600;
  color: var(--warning, #f59e0b);
  background: rgba(245, 158, 11, 0.1);
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.15s;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
}

.invite-chip:hover {
  background: rgba(245, 158, 11, 0.2);
}

.course-card__actions {
  display: flex;
  gap: 0.3rem;
}

@media (max-width: 768px) {
  .course-grid { grid-template-columns: 1fr; }
}

/* Course Filter & Sort Controls */
.course-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
  gap: 1rem;
  flex-wrap: wrap;
}

.course-filters {
  display: flex;
  gap: 0.5rem;
}

.filter-btn {
  padding: 0.375rem 0.875rem;
  border: 1px solid var(--border-color);
  background: transparent;
  color: var(--text-muted);
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.filter-btn:hover {
  color: var(--text-primary);
  border-color: var(--text-secondary);
}

.filter-btn--active {
  background: var(--accent);
  color: white;
  border-color: var(--accent);
}

.course-sort {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.course-sort .form-input--sm {
  max-width: 160px;
}

.form-input--sm {
  padding: 0.375rem 0.75rem;
  font-size: 0.75rem;
}

.sort-dir-btn {
  display: flex;
  align-items: center;
  padding: 0.375rem;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.15s;
}

.sort-dir-btn:hover {
  color: var(--text-primary);
  border-color: var(--text-secondary);
}

/* Alert Toast */
.alert-toast {
  position: fixed;
  bottom: 1.5rem;
  right: 1.5rem;
  padding: 0.75rem 1.25rem;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 500;
  z-index: 100;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.alert-toast--success { background: var(--success); color: #fff; }
.alert-toast--error { background: var(--danger); color: #fff; }

.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* States */
.loading { text-align: center; padding: 3rem; color: var(--text-muted); }
.empty-state { text-align: center; padding: 2rem; color: var(--text-muted); font-size: 0.85rem; }
.empty-state p { margin-bottom: 0.5rem; }

/* Inline rename */
.form-input--inline {
  flex: 1;
  max-width: 260px;
  font-size: 0.8rem;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  border: 1px solid var(--border-color);
  background: var(--bg-primary);
  color: var(--text-primary);
}
.lab-name--custom {
  color: var(--accent);
  font-style: italic;
}

/* Status cell */
.status-cell {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  white-space: nowrap;
}

/* Mine badge */
.mine-badge {
  display: inline-block;
  font-size: 0.5625rem;
  font-weight: 700;
  padding: 0.0625rem 0.375rem;
  border-radius: 9999px;
  background: rgba(139, 92, 246, 0.2);
  color: #a78bfa;
  margin-left: 0.375rem;
  vertical-align: middle;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Visibility badges & selects */
.visibility-badge {
  font-size: 0.6875rem;
  font-weight: 600;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  text-transform: capitalize;
  white-space: nowrap;
}
.vis-draft { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }
.vis-course { background: rgba(59, 130, 246, 0.15); color: #60a5fa; }
.vis-pending_public { background: rgba(236, 72, 153, 0.15); color: #f472b6; }
.vis-public { background: rgba(34, 197, 94, 0.15); color: #4ade80; }

.visibility-select {
  padding: 0.2rem 0.4rem;
  font-size: 0.6875rem;
  font-weight: 600;
  border-radius: 6px;
  border: 1px solid var(--border-color);
  background: var(--bg-primary);
  color: var(--text-primary);
  cursor: pointer;
  transition: border-color 0.15s;
}
.visibility-select:hover { border-color: var(--accent); }
.visibility-select.vis-draft { border-color: #fbbf24; color: #fbbf24; }
.visibility-select.vis-course { border-color: #60a5fa; color: #60a5fa; }
.visibility-select.vis-pending_public { border-color: #f472b6; color: #f472b6; }


/* Action group */
.action-group {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

/* Tester panel */
.tester-panel {
  margin-top: 1.25rem;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
}
.tester-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0.75rem;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}
.tester-header__left {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.tester-header__right {
  display: flex;
  gap: 0.375rem;
}
.tester-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #64748b;
}
.tester-dot--active {
  background: #22c55e;
  animation: tester-pulse 1.5s infinite;
}
@keyframes tester-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
.tester-label {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--text-primary);
}
.tester-progress {
  font-size: 0.75rem;
  color: var(--text-muted);
}
.tester-terminal {
  background: #0f172a;
  color: #94a3b8;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 0.6875rem;
  line-height: 1.6;
  padding: 0.75rem;
  max-height: 400px;
  overflow-y: auto;
}
.tester-empty {
  color: #475569;
  text-align: center;
  padding: 2rem;
}
.tester-section-header {
  color: #60a5fa;
  font-weight: 700;
  margin-top: 0.5rem;
  padding: 0.25rem 0;
  border-bottom: 1px solid #1e293b;
  display: flex;
  justify-content: space-between;
}
.tester-section--ok { color: #4ade80; }
.tester-section--warning { color: #fbbf24; }
.tester-section--error { color: #f87171; }
.tester-section-status {
  font-size: 0.625rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.tester-line { padding: 0.0625rem 0; }
.tester-line--ok .tester-msg { color: #4ade80; }
.tester-line--warning .tester-msg { color: #fbbf24; }
.tester-line--error .tester-msg { color: #f87171; }
.tester-line--info .tester-msg { color: #94a3b8; }
.tester-ts {
  color: #475569;
  margin-right: 0.5rem;
}
.tester-cursor {
  display: inline-block;
  animation: tester-blink 1s step-end infinite;
  color: #60a5fa;
}
@keyframes tester-blink {
  50% { opacity: 0; }
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
}
.modal-dialog {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  width: 90%;
  max-width: 600px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
}
.modal-dialog--lg { max-width: 700px; }
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--border-color);
}
.modal-header h3 {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
}
.modal-close {
  background: none; border: none;
  color: var(--text-muted);
  font-size: 1.5rem; cursor: pointer;
  line-height: 1;
}
.modal-close:hover { color: var(--text-primary); }
.modal-body {
  padding: 1.25rem;
  overflow-y: auto;
  flex: 1;
}
.modal-footer {
  padding: 0.75rem 1.25rem;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}

/* Guide */
.guide-section {
  margin-bottom: 1rem;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
}
.guide-toggle {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.625rem 0.875rem;
  background: var(--bg-primary);
  border: none;
  color: var(--text-secondary);
  font-size: 0.8125rem;
  font-weight: 600;
  cursor: pointer;
  text-align: left;
}
.guide-toggle:hover { color: var(--text-primary); }
.guide-content {
  padding: 0.75rem;
  background: var(--bg-primary);
  border-top: 1px solid var(--border-color);
}
.guide-pre {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 0.6875rem;
  line-height: 1.5;
  color: #94a3b8;
  white-space: pre;
  overflow-x: auto;
  margin: 0;
}

/* Upload form */
.upload-form { margin-top: 0.5rem; }
.form-row-inline { display: flex; gap: 0.75rem; margin-top: 0.5rem; }
.upload-preview {
  font-size: 0.75rem;
  color: var(--text-secondary);
  margin-top: 0.25rem;
  padding: 0.375rem 0.5rem;
  background: var(--bg-primary);
  border-radius: 4px;
}
.upload-error {
  color: #f87171;
  font-size: 0.8125rem;
  margin-top: 0.5rem;
  padding: 0.5rem 0.625rem;
  background: rgba(239, 68, 68, 0.1);
  border-radius: 6px;
}
.upload-warnings {
  margin-top: 0.5rem;
}
.upload-warning-item {
  font-size: 0.75rem;
  color: #fbbf24;
  padding: 0.25rem 0.5rem;
  background: rgba(245, 158, 11, 0.1);
  border-radius: 4px;
  margin-bottom: 0.25rem;
}

@media (max-width: 768px) {
  .catalog-layout { flex-direction: column; }
  .topic-sidebar { width: 100%; min-width: unset; position: static; display: flex; flex-wrap: wrap; gap: 0.5rem; padding: 0.75rem; }
  .sidebar-title { width: 100%; padding-bottom: 0.5rem; }
  .topic-item { width: auto; padding: 0.375rem 0.75rem; }
}

/* Tester status dots on exercise rows */
.tester-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
  margin-right: 0.35rem;
  flex-shrink: 0;
}
.tester-status-dot--ok {
  background: #22c55e;
  box-shadow: 0 0 4px rgba(34, 197, 94, 0.5);
}
.tester-status-dot--warning {
  background: #f59e0b;
  box-shadow: 0 0 4px rgba(245, 158, 11, 0.5);
}
.tester-status-dot--error {
  background: #ef4444;
  box-shadow: 0 0 4px rgba(239, 68, 68, 0.5);
}
.tester-status-dot--cancelled {
  background: #6b7280;
  box-shadow: 0 0 4px rgba(107, 114, 128, 0.3);
}

/* Course Settings Form */
.course-settings-form {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 1.25rem;
}
.settings-section-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 1rem 0;
}
.settings-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}
.settings-field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.settings-field--full {
  grid-column: 1 / -1;
}
.settings-label {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--text-secondary);
}
.settings-input {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  color: var(--text-primary);
  transition: border-color 0.2s;
}
.settings-input:focus {
  outline: none;
  border-color: var(--accent);
}
.settings-textarea {
  resize: vertical;
  min-height: 60px;
  font-family: inherit;
}
.settings-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 1.25rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border-color);
}

/* Student Enrollment */
.enroll-section {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 1rem 1.25rem;
  margin-bottom: 1rem;
}
.enroll-search-row {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  margin-bottom: 0.5rem;
}
.enroll-search-input {
  flex: 1;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  color: var(--text-primary);
}
.enroll-search-input:focus {
  outline: none;
  border-color: var(--accent);
}
.enroll-search-input::placeholder {
  color: var(--text-muted);
}
.enroll-count-badge {
  font-size: 0.8rem;
  color: var(--accent);
  font-weight: 600;
  white-space: nowrap;
}
.enroll-actions-row {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  margin-bottom: 0.5rem;
}
.enroll-submit-btn {
  margin-left: auto;
}
.enroll-list {
  max-height: 260px;
  overflow-y: auto;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-secondary);
}
.enroll-list-item {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.45rem 0.75rem;
  cursor: pointer;
  transition: background 0.15s;
  border-bottom: 1px solid var(--border-color);
  font-size: 0.875rem;
}
.enroll-list-item:last-child {
  border-bottom: none;
}
.enroll-list-item:hover {
  background: var(--bg-hover, rgba(255,255,255,0.04));
}
.enroll-list-item--selected {
  background: rgba(var(--accent-rgb, 99,102,241), 0.1);
}
.enroll-checkbox {
  accent-color: var(--accent);
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}
.enroll-user-name {
  color: var(--text-primary);
  font-weight: 500;
}
.enroll-user-detail {
  color: var(--text-muted);
  font-size: 0.8rem;
  margin-left: auto;
}
</style>

<style scoped>
/* Door A: Add exercises on-ramp (Exercise Studio) */
.addex-bar { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem; padding: 0.7rem 1rem; background: var(--accent-bg); border: 1px solid var(--border-color); border-radius: 8px; }
.addex-hint { font-size: 0.8rem; color: var(--text-secondary); }
.addex-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.55); display: flex; align-items: center; justify-content: center; z-index: 200; padding: 1.5rem; }
.addex-modal { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 12px; padding: 1.5rem; width: 100%; max-width: 460px; display: flex; flex-direction: column; gap: 0.7rem; }
.addex-modal__head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.4rem; }
.addex-modal__head strong { font-size: 1.05rem; color: var(--text-primary); }
.addex-close { background: none; border: none; color: var(--text-muted); font-size: 1.2rem; cursor: pointer; }
.addex-door { display: flex; flex-direction: column; align-items: flex-start; gap: 0.2rem; text-align: left; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 8px; padding: 0.8rem 1rem; cursor: pointer; transition: all 0.15s; }
.addex-door:hover { border-color: var(--accent); transform: translateY(-1px); }
.addex-door__title { font-weight: 600; color: var(--text-primary); font-size: 0.9rem; }
.addex-door__desc { font-size: 0.78rem; color: var(--text-muted); }
</style>

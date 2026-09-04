<template>
  <div class="admin-page">
    <div class="admin-container">
      <!-- Header -->
      <div class="admin-header">
        <h1 class="page-title">Admin Panel</h1>
        <p class="page-subtitle">Manage users, exercises, sessions, VPN peers, curriculum, and settings</p>
      </div>

      <!-- Alert messages render through the shared global toast -->
      <Toast />

      <!-- Stats Cards -->
      <div class="stats-grid">
        <div class="stat-card stat-card--health" :class="dashboardHealthClass ? `stat-card--health-${dashboardHealthClass}` : ''" @click="activeTab = 'system'; systemSubTab = 'health'" style="cursor: pointer;">
          <div class="stat-card__icon stat-card__icon--health" :class="`stat-card__icon--health-${dashboardHealthClass || 'loading'}`">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
            </svg>
          </div>
          <div class="stat-card__content" v-if="dashboardHealthLoaded">
            <div class="health-card-indicators">
              <div class="health-card-row">
                <span class="health-dot" :class="`health-dot--${dashboardHealthStatus === 'ok' ? 'green' : dashboardHealthStatus === 'warning' ? 'amber' : 'red'}`"></span>
                <span class="health-card-label">System<InfoTip :text="dashboardHealthTip" /></span>
              </div>
            </div>
          </div>
          <div class="stat-card__content" v-else>
            <span class="stat-card__label">Checking...</span>
          </div>
        </div>

        <div class="stat-card" :class="{ 'stat-card--alert': stats.pending_users > 0 }" @click="activeTab = 'pending'" style="cursor: pointer;" title="View pending approvals">
          <div class="stat-card__icon stat-card__icon--pending">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <polyline points="12 6 12 12 16 14"/>
            </svg>
          </div>
          <div class="stat-card__content">
            <span class="stat-card__value">{{ stats.pending_users }}</span>
            <span class="stat-card__label">Pending<InfoTip text="Users awaiting admin approval before they can sign in." /></span>
          </div>
          <span v-if="stats.pending_users > 0" class="stat-card__badge">{{ stats.pending_users }}</span>
        </div>

        <div class="stat-card">
          <div class="stat-card__icon stat-card__icon--locked">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
              <path d="M7 11V7C7 4.2 9.2 2 12 2C14.8 2 17 4.2 17 7V11"/>
            </svg>
          </div>
          <div class="stat-card__content">
            <span class="stat-card__value">{{ stats.locked_users }}</span>
            <span class="stat-card__label">Locked<InfoTip text="Accounts locked out from too many failed logins or a manual lock. Unlock them from the Users tab." /></span>
          </div>
        </div>

        <div class="stat-card">
          <div class="stat-card__icon stat-card__icon--active">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
          </div>
          <div class="stat-card__content">
            <span class="stat-card__value">{{ stats.active_labs }}</span>
            <span class="stat-card__label">Active Exercises<InfoTip text="Lab sessions currently running across all users right now." /></span>
          </div>
        </div>

        <div class="stat-card">
          <div class="stat-card__icon stat-card__icon--vpn">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2L3 7V12C3 16.97 7.02 21.45 12 22C16.98 21.45 21 16.97 21 12V7L12 2Z"/>
            </svg>
          </div>
          <div class="stat-card__content">
            <span class="stat-card__value">{{ stats.vpn_registered }}</span>
            <span class="stat-card__label">VPN Peers<InfoTip text="Configured WireGuard peers — students with VPN access to the lab network." /></span>
          </div>
        </div>
      </div>

      <!-- Tab Content -->
      <div class="tab-content">
        
        <!-- Users Tab -->
        <div v-if="activeTab === 'users'" class="panel">
          <!-- Create User Form -->
          <div class="panel-section">
            <button @click="showCreateForm = !showCreateForm" class="expand-btn">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" 
                   class="expand-icon" :class="{ 'expand-icon--open': showCreateForm }">
                <polyline points="9 18 15 12 9 6"/>
              </svg>
              Create New User
            </button>

            <transition name="slide">
              <div v-if="showCreateForm" class="create-form">
                <div class="form-grid">
                  <input v-model="newUser.username" placeholder="Username" class="form-input">
                  <input v-model="newUser.email" type="email" placeholder="Email" class="form-input">
                  <input v-model="newUser.password" type="password" placeholder="Password" class="form-input">
                </div>
                <div class="form-actions">
                  <label class="checkbox-label">
                    <input type="checkbox" v-model="newUser.is_approved">
                    <span>Pre-approved</span>
                  </label>
                  <label class="select-label">
                    <span>Role</span>
                    <select v-model="newUser.role" class="form-select form-select--inline">
                      <option value="student">Student</option>
                      <option value="instructor">Instructor</option>
                      <option value="admin">Admin</option>
                    </select>
                  </label>
                  <button @click="createUser" class="btn btn--success">Create User</button>
                </div>
              </div>
            </transition>
          </div>

          <!-- Users Search & Filter Bar -->
          <div class="filter-bar">
            <input v-model="userSearch" type="text" placeholder="Search by username or email..." class="search-input" style="flex: 2;" />
            <select v-model="userStatusFilter" class="filter-select">
              <option value="">All Statuses</option>
              <option value="active">Active</option>
              <option value="pending">Pending</option>
              <option value="locked">Locked</option>
              <option value="disabled">Disabled</option>
            </select>
            <select v-model="userRoleFilter" class="filter-select">
              <option value="">All Roles</option>
              <option value="admin">Admin</option>
              <option value="instructor">Instructor</option>
              <option value="student">Student</option>
            </select>
          </div>
          <div class="results-count" style="margin-bottom: 0.5rem;">
            {{ filteredUsers.length }} user{{ filteredUsers.length !== 1 ? 's' : '' }}
            <span v-if="userSearch || userStatusFilter || userRoleFilter"> (filtered)</span>
          </div>

          <!-- Users Table -->
          <div class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th style="width: 20%">Username</th>
                  <th style="width: 25%">Email</th>
                  <th style="width: 10%">Status</th>
                  <th style="width: 5%">VPN</th>
                  <th style="width: 40%">Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="user in paginatedUsers" :key="user.id" :class="{ 'row--inactive': !user.is_active }">
                  <td class="cell-primary">
                    <span class="exercise-status-dot" :class="user.is_active ? 'exercise-status-dot--active' : 'exercise-status-dot--inactive'" style="display: inline-block; margin-right: 0.4rem;"></span>
                    <span class="masked-email">{{ maskUsername(user.username) }}</span>
                    <span v-if="user.must_change_password" class="password-change-badge" title="Password change required">🔒</span>
                  </td>
                  <td class="masked-email" :title="'Click user profile to view full email'">{{ maskEmail(user.email) }}</td>
                  <td>
                    <span v-if="user.is_locked" class="status-badge status-badge--locked">Locked</span>
                    <span v-else-if="!user.is_approved" class="status-badge status-badge--pending">Pending</span>
                    <span v-else-if="user.role === 'admin'" class="status-badge status-badge--admin">Admin</span>
                    <span v-else-if="user.role === 'instructor'" class="status-badge status-badge--instructor">Instructor</span>
                    <span v-else class="status-badge status-badge--approved">Student</span>
                  </td>
                  <td>
                    <span v-if="user.vpn_registered" class="vpn-status vpn-status--yes">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="20 6 9 17 4 12"/>
                      </svg>
                    </span>
                    <span v-else class="vpn-status vpn-status--no">-</span>
                  </td>
                  <td class="cell-actions">
                    <button @click="openUserDetailsModal(user.id)" class="action-btn action-btn--view" title="View Details">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M1 12S5 4 12 4S23 12 23 12S19 20 12 20S1 12 1 12Z"/>
                        <circle cx="12" cy="12" r="3"/>
                      </svg>
                    </button>
                    <button v-if="user.is_locked" @click="unlockUser(user.id)" class="action-btn action-btn--unlock" title="Unlock">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                        <path d="M7 11V7C7 4.2 9.2 2 12 2C13.5 2 14.8 2.6 15.8 3.6"/>
                      </svg>
                    </button>
                    <button v-if="!user.is_approved" @click="approveUser(user.id)" class="action-btn action-btn--approve" title="Approve">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="20 6 9 17 4 12"/>
                      </svg>
                    </button>
                    <button @click="openEditUserModal(user)" class="action-btn action-btn--reset" title="Edit User">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 2L19 4M19 4L15.5 7.5L16.5 8.5L20 5L19 4Z"/>
                        <path d="M11 6C7.7 6 5 8.7 5 12S7.7 18 11 18C12.7 18 14.2 17.3 15.2 16.2"/>
                        <path d="M13.5 9.5L15 8"/>
                      </svg>
                    </button>
                    <button
                      @click="toggleUserActive(user)"
                      :class="['action-btn', user.is_active ? 'action-btn--archive' : 'action-btn--approve']"
                      :title="user.is_active ? 'Disable' : 'Enable'"
                    >
                      <svg v-if="!user.is_active" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="20 6 9 17 4 12"/>
                      </svg>
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/>
                      </svg>
                    </button>
                    <button @click="deleteUser(user.id)" class="action-btn action-btn--delete" title="Delete">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6"/>
                        <path d="M19 6V20C19 21.1 18.1 22 17 22H7C5.9 22 5 21.1 5 20V6M8 6V4C8 2.9 8.9 2 10 2H14C15.1 2 16 2.9 16 4V6"/>
                      </svg>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="userTotalPages > 1" class="pagination" style="display: flex; gap: 0.5rem; margin-top: 1rem; justify-content: center; align-items: center;">
            <button @click="userPage = userPage - 1" :disabled="userPage <= 1" class="btn btn--secondary btn--sm">Prev</button>
            <span style="padding: 0.4rem 0.75rem; color: #94a3b8;">Page {{ userPage }} of {{ userTotalPages }}</span>
            <button @click="userPage = userPage + 1" :disabled="userPage >= userTotalPages" class="btn btn--secondary btn--sm">Next</button>
          </div>
        </div>

        <!-- Pending Tab -->
        <AdminPendingTab
          v-if="activeTab === 'pending'"
          :users="pendingUsers"
          @approve="approveUser"
          @reject="deleteUser"
        />

        <!-- Exercises Tab (consolidated Labs + Curriculum) -->
        <div v-if="activeTab === 'exercises'" class="panel">
          <div class="panel-header">
            <h2 class="panel-title">Exercises</h2>
            <div style="display: flex; gap: 0.5rem;">
              <button @click="openDiskManagement" class="btn btn--secondary btn--sm" title="Manage Docker images and build cache">
                Disk Management
              </button>
              <button v-if="devTools" @click="scanLabs" :disabled="scanningLabs" class="btn btn--secondary btn--sm">
                {{ scanningLabs ? 'Scanning...' : 'Scan for Exercises' }}
              </button>
              <button @click="openCreateLabModal" class="btn btn--success btn--sm">+ Create Exercise</button>
            </div>
          </div>

          <!-- Scan Warnings -->
          <div v-if="scanWarnings.length" class="scan-warnings">
            <div class="scan-warnings__header" @click="scanWarnings = []">
              <span>Scan Warnings ({{ scanWarnings.length }})</span>
              <span class="scan-warnings__dismiss">&times;</span>
            </div>
            <ul class="scan-warnings__list">
              <li v-for="(w, i) in scanWarnings" :key="i">{{ w }}</li>
            </ul>
          </div>

          <div class="catalog-layout">
            <!-- LEFT: Topic Sidebar -->
            <aside class="topic-sidebar">
              <div class="sidebar-title">Topics</div>
              <button class="topic-item" :class="{ 'topic-item--active': !selectedTrack && exercisesView === 'manage' }" @click="selectedTrack = null; exercisesView = 'manage'">
                <span class="topic-item__name">All Exercises</span>
                <span class="topic-item__count">{{ labs.length }}</span>
              </button>
              <button
                v-for="track in adminTrackSummaries"
                :key="track.slug"
                class="topic-item"
                :class="{ 'topic-item--active': selectedTrack === track.slug && exercisesView === 'manage' }"
                @click="selectedTrack = track.slug; exercisesView = 'manage'"
              >
                <span class="topic-item__dot" :style="{ background: track.color }"></span>
                <span class="topic-item__name">{{ track.name }}</span>
                <span class="topic-item__count">{{ track.lab_count }}</span>
              </button>

              <div class="sidebar-divider"></div>
              <div class="sidebar-title">Status</div>
              <button class="topic-item" :class="{ 'topic-item--active': activeLabStatus === 'all' && exercisesView === 'manage' }" @click="activeLabStatus = 'all'; exercisesView = 'manage'">
                <span class="topic-item__name">All</span>
                <span class="topic-item__count">{{ labs.length }}</span>
              </button>
              <button class="topic-item" :class="{ 'topic-item--active': activeLabStatus === 'enabled' && exercisesView === 'manage' }" @click="activeLabStatus = 'enabled'; exercisesView = 'manage'">
                <span class="topic-item__dot" style="background: #22c55e;"></span>
                <span class="topic-item__name">Enabled</span>
                <span class="topic-item__count">{{ enabledLabsCount }}</span>
              </button>
              <button class="topic-item" :class="{ 'topic-item--active': activeLabStatus === 'disabled' && exercisesView === 'manage' }" @click="activeLabStatus = 'disabled'; exercisesView = 'manage'">
                <span class="topic-item__dot" style="background: #6b7280;"></span>
                <span class="topic-item__name">Disabled</span>
                <span class="topic-item__count">{{ disabledLabsCount }}</span>
              </button>

              <div class="sidebar-divider"></div>
              <div class="sidebar-title">Management</div>
              <button class="topic-item" :class="{ 'topic-item--active': exercisesView === 'tracks' }" @click="exercisesView = 'tracks'">
                <span class="topic-item__name">Tracks &amp; Levels</span>
              </button>
              <button class="topic-item" :class="{ 'topic-item--active': exercisesView === 'workbook' }" @click="exercisesView = 'workbook'; loadWorkbookChapters()">
                <span class="topic-item__name">Workbook</span>
              </button>
            </aside>

            <!-- RIGHT: Main Content -->
            <div class="labs-panel">

              <!-- Manage Exercises View -->
              <template v-if="exercisesView === 'manage'">
                <div class="filter-bar">
                  <input v-model="labSearch" type="text" placeholder="Search exercises..." class="search-input" />
                  <select v-model="difficultyFilter" class="filter-select">
                    <option value="">All difficulties</option>
                    <option value="beginner">Beginner</option>
                    <option value="intermediate">Intermediate</option>
                    <option value="advanced">Advanced</option>
                  </select>
                  <select v-model="labInstructorFilter" class="filter-select">
                    <option value="">All Instructors</option>
                    <option v-for="[id, name] in labCreators" :key="id" :value="id">{{ name }}</option>
                  </select>
                  <select v-model="labVisibilityFilter" class="filter-select">
                    <option value="">All Visibility</option>
                    <option value="public">Public</option>
                    <option value="course">Course</option>
                    <option value="draft">Draft</option>
                    <option value="pending_public">Pending Review</option>
                  </select>
                </div>

                <div class="results-count">
                  {{ adminFilteredLabs.length }} exercise{{ adminFilteredLabs.length !== 1 ? 's' : '' }}
                  <span v-if="selectedTrack"> in {{ adminTrackSummaries.find(t => t.slug === selectedTrack)?.name }}</span>
                  <span v-if="activeLabStatus !== 'all'"> &mdash; {{ activeLabStatus }}</span>
                </div>

                <div class="table-wrapper">
                  <table class="data-table">
                    <thead>
                      <tr>
                        <th>Exercise</th>
                        <th>Track / Level</th>
                        <th>Difficulty</th>
                        <th>Duration</th>
                        <th>Visibility</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-if="adminFilteredLabs.length === 0">
                        <td colspan="6" class="empty-row">No exercises match your filters</td>
                      </tr>
                      <template v-for="lab in paginatedAdminLabs" :key="lab.id">
                      <tr :class="{ 'row--inactive': !lab.is_active }">
                        <td>
                          <div class="lab-name">
                            {{ lab.name }}
                          </div>
                        </td>
                        <td>
                          <span class="track-badge" :style="{ background: (adminTrackColorMap[lab.track_name] || '#3b82f6') + '1a', color: adminTrackColorMap[lab.track_name] || '#3b82f6' }">
                            {{ lab.track_name || '—' }}
                          </span>
                          <div v-if="lab.level_name" class="lab-desc">{{ lab.level_name }}</div>
                        </td>
                        <td>
                          <span v-if="lab.difficulty" :class="['difficulty-badge', 'difficulty-' + lab.difficulty]">{{ lab.difficulty }}</span>
                          <span v-else class="lab-desc">&mdash;</span>
                        </td>
                        <td>{{ lab.duration_minutes ? lab.duration_minutes + ' min' : '—' }}</td>
                        <td>
                          <select
                            class="exercise-vis-select"
                            :class="'exercise-vis-select--' + (lab.visibility || 'public')"
                            :value="lab.visibility || 'public'"
                            @change="setLabVisibility(lab, $event.target.value)"
                            @click.stop
                          >
                            <option value="public">Public</option>
                            <option value="course">Course</option>
                            <option value="pending_public">Pending</option>
                            <option value="draft">Draft</option>
                          </select>
                        </td>
                        <td>
                          <div class="exercise-actions">
                            <button @click="openLabEditModal(lab)" class="action-btn action-btn--view" title="Edit exercise">
                              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                            </button>
                            <button
                              @click="runQuickTest(lab)"
                              class="action-btn action-btn--test"
                              :disabled="testerRunning"
                              title="Run exercise tester"
                            >
                              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 3h6v5l3 9H6l3-9V3z"/><path d="M8 3h8"/></svg>
                            </button>
                            <button
                              @click="deleteLabImages(lab)"
                              class="action-btn action-btn--cache"
                              :disabled="deletingLabImages[lab.id]"
                              title="Delete cached Docker images"
                            >
                              <svg v-if="deletingLabImages[lab.id]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
                              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                            </button>
                            <button
                              @click="toggleLab(lab.id)"
                              :class="['action-btn', lab.is_active ? 'action-btn--delete' : 'action-btn--available']"
                              :title="lab.is_active ? 'Disable' : 'Enable'"
                            >
                              <svg v-if="lab.is_active" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
                              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                            </button>
                          </div>
                        </td>
                      </tr>
                      <!-- Inline tester row -->
                      <tr v-if="quickTestSlug === lab.slug" class="quick-test-row">
                        <td colspan="6" style="padding: 0;">
                          <div class="diagnostics-terminal" style="margin: 0; border-radius: 0;">
                            <div class="diagnostics-terminal-header">
                              <span class="diagnostics-terminal-dot" :class="{ 'diagnostics-terminal-dot--active': testerRunning }"></span>
                              <span class="diagnostics-terminal-label">Testing: {{ lab.name }}</span>
                              <template v-if="testerRunning && testerProgress.total > 0">
                                <span class="tester-progress-text">{{ testerProgress.current }}/{{ testerProgress.total }}</span>
                              </template>
                              <span style="flex:1"></span>
                              <button v-if="testerRunning" class="btn btn--xs btn--danger" @click="cancelExerciseTest" :disabled="testerCancelling" style="font-size:0.625rem;padding:0.125rem 0.4rem;">
                                {{ testerCancelling ? 'Cancelling...' : 'Cancel' }}
                              </button>
                              <button v-else class="btn btn--xs btn--secondary" @click="quickTestSlug = null" style="font-size:0.625rem;padding:0.125rem 0.4rem;">Close</button>
                            </div>
                            <div ref="quickTestTerminalRef" class="diagnostics-terminal-body" style="max-height: 300px;">
                              <template v-for="(section, sIdx) in testerSections" :key="section.test_key">
                                <div class="diagnostics-section-header">-- {{ section.name }} --</div>
                                <div v-for="(line, lIdx) in section.lines" :key="sIdx + '-' + lIdx" class="diagnostics-line">
                                  <span class="diagnostics-line-time">{{ line.timestamp }}</span>
                                  <span class="diagnostics-line-level" :class="'diagnostics-level--' + line.level">
                                    [{{ line.level === 'ok' ? 'PASS' : line.level === 'error' ? 'FAIL' : line.level === 'warning' ? 'WARN' : 'INFO' }}]
                                  </span>
                                  <span class="diagnostics-line-msg">{{ line.message }}</span>
                                </div>
                              </template>
                              <div v-if="testerRunning" class="diagnostics-cursor">_</div>
                            </div>
                          </div>
                        </td>
                      </tr>
                      </template>
                    </tbody>
                  </table>
                  <div v-if="labTotalPages > 1" class="pagination" style="display: flex; gap: 0.5rem; margin-top: 1rem; justify-content: center; align-items: center;">
                    <button @click="labPage = labPage - 1" :disabled="labPage <= 1" class="btn btn--secondary btn--sm">Prev</button>
                    <span style="padding: 0.4rem 0.75rem; color: #94a3b8;">Page {{ labPage }} of {{ labTotalPages }}</span>
                    <button @click="labPage = labPage + 1" :disabled="labPage >= labTotalPages" class="btn btn--secondary btn--sm">Next</button>
                  </div>
                </div>
              </template>

              <!-- Tracks & Levels View -->
              <div v-else-if="exercisesView === 'tracks'" class="sub-tab-content">
                <div class="panel-header">
                  <h2 class="panel-title">Curriculum Management</h2>
                  <button @click="showCreateTrackModal = true" class="btn btn--success btn--sm">+ Create Track</button>
                </div>

                <div v-if="curriculumLoading" class="empty-state">Loading curriculum...</div>
                <div v-else-if="curriculumTracks.length === 0" class="empty-state">
                  No tracks yet. Click "+ Create Track" to get started.
                </div>
                <div v-else class="curriculum-list">
                  <div v-for="track in curriculumTracks" :key="track.id" class="lab-category-section">
                    <button @click="toggleCurriculumTrack(track.id)" class="lab-category-header">
                      <span class="lab-category-name">
                        <div class="exercise-status-dot" :class="track.is_active ? 'exercise-status-dot--active' : 'exercise-status-dot--inactive'"></div>
                        <span class="lab-track-name">{{ track.name }}</span>
                        <span v-if="!track.is_active" class="exercise-badge exercise-badge--creator">Inactive</span>
                      </span>
                      <span class="lab-category-count">({{ track.level_count }} levels, {{ track.lab_count }} exercises)</span>
                      <span class="lab-category-toggle">{{ expandedCurriculumTracks[track.id] ? '−' : '+' }}</span>
                    </button>

                    <div v-if="expandedCurriculumTracks[track.id]">
                      <div class="curriculum-track-actions" style="display: flex; gap: 0.5rem; padding: 0.5rem 0.75rem;">
                        <button @click="editTrack(track)" class="exercise-action-btn" title="Edit track">Edit Track</button>
                        <button @click="deleteTrack(track)" class="exercise-action-btn exercise-action-btn--danger" title="Delete track">Delete</button>
                        <button @click="openCreateLevelModal(track)" class="exercise-action-btn exercise-action-btn--success" title="Add level">+ Add Level</button>
                      </div>

                      <div v-if="track.levels && track.levels.length > 0" class="exercise-list" style="margin: 0 0.5rem 0.5rem;">
                        <div v-for="level in track.levels" :key="level.id" class="exercise-item">
                          <div class="exercise-status-dot exercise-status-dot--active"></div>
                          <span class="exercise-name">Level {{ level.level_number }}: {{ level.name }}</span>
                          <span class="exercise-badge exercise-badge--difficulty">{{ level.lab_count }} exercises</span>
                          <span v-if="level.description" class="exercise-badge exercise-badge--creator">{{ level.description }}</span>
                          <div class="exercise-actions">
                            <button @click="editLevel(level)" class="exercise-action-btn" title="Edit level">Edit</button>
                            <button @click="deleteLevel(level)" class="exercise-action-btn exercise-action-btn--danger" :disabled="level.lab_count > 0" title="Delete level">Delete</button>
                          </div>
                        </div>
                      </div>
                      <p v-else class="empty-state" style="padding: 0.5rem;">No levels in this track.</p>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Workbook View -->
              <div v-else-if="exercisesView === 'workbook'" class="sub-tab-content">
                <div class="panel-header">
                  <h2 class="panel-title">Workbook Management</h2>
                  <div style="display: flex; gap: 0.5rem;">
                    <button @click="triggerWorkbookBuild" :disabled="workbookBuilding" class="btn btn--secondary btn--sm">
                      {{ workbookBuilding ? 'Building...' : 'Rebuild Wiki' }}
                    </button>
                  </div>
                </div>

                <!-- Upload Section -->
                <div class="workbook-upload-section" style="margin-bottom: 1.5rem;">
                  <h3 style="margin-bottom: 0.75rem; font-size: 0.95rem; font-weight: 600;">Upload Chapter Files</h3>
                  <div class="workbook-upload-form" style="display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: flex-end;">
                    <div style="flex: 1; min-width: 200px;">
                      <label style="display: block; font-size: 0.8rem; margin-bottom: 0.25rem; opacity: 0.7;">Chapter Directory</label>
                      <input aria-label="Chapter Directory" v-model="workbookUploadDir" type="text" placeholder="e.g. CH_COURSE01_Weekly_Challenges" class="form-input" style="width: 100%;" />
                    </div>
                    <div style="flex: 1; min-width: 200px;">
                      <label style="display: block; font-size: 0.8rem; margin-bottom: 0.25rem; opacity: 0.7;">Nav Section</label>
                      <input aria-label="Nav Section" v-model="workbookUploadSection" type="text" placeholder="e.g. Course Weekly Challenges" class="form-input" style="width: 100%;" />
                    </div>
                    <div style="min-width: 180px;">
                      <label style="display: block; font-size: 0.8rem; margin-bottom: 0.25rem; opacity: 0.7;">ZIP of .md files</label>
                      <input aria-label="ZIP of .md files" ref="workbookFileInput" type="file" accept=".zip" @change="handleWorkbookFileSelect" style="font-size: 0.85rem;" />
                    </div>
                    <button @click="uploadWorkbook" :disabled="workbookUploading || !workbookFile || !workbookUploadDir" class="btn btn--success btn--sm">
                      {{ workbookUploading ? 'Uploading...' : 'Upload & Build' }}
                    </button>
                  </div>
                  <p style="font-size: 0.78rem; opacity: 0.6; margin-top: 0.5rem;">
                    Upload a ZIP containing numbered markdown files (e.g. 00_Introduction.md, 01_Network_Discovery.md).
                    The wiki will auto-rebuild after upload.
                  </p>
                </div>

                <!-- Upload Result -->
                <div v-if="workbookUploadResult" class="workbook-result" style="margin-bottom: 1rem; padding: 0.75rem; border-radius: 6px; font-size: 0.85rem;"
                     :style="{ background: workbookUploadResult.build?.success !== false ? 'var(--success-bg, rgba(46,160,67,0.1))' : 'var(--error-bg, rgba(248,81,73,0.1))' }">
                  <div v-if="workbookUploadResult.files_extracted">
                    <strong>Extracted {{ workbookUploadResult.files_extracted.length }} files</strong> to {{ workbookUploadResult.chapter_dir }}/
                  </div>
                  <div v-if="workbookUploadResult.nav_updated">
                    Nav updated: {{ workbookUploadResult.nav_updated.chapter_label }} ({{ workbookUploadResult.nav_updated.pages }} pages)
                  </div>
                  <div v-if="workbookUploadResult.build">
                    Build: {{ workbookUploadResult.build.success ? 'Success' : 'Failed' }}
                    ({{ workbookUploadResult.build.duration_seconds }}s)
                  </div>
                  <div v-if="workbookUploadResult.warnings?.length">
                    <span style="color: var(--warning-color, #d29922);">Warnings: {{ workbookUploadResult.warnings.join(', ') }}</span>
                  </div>
                </div>

                <!-- Build Result -->
                <div v-if="workbookBuildResult && !workbookUploadResult" class="workbook-result" style="margin-bottom: 1rem; padding: 0.75rem; border-radius: 6px; font-size: 0.85rem;"
                     :style="{ background: workbookBuildResult.success ? 'var(--success-bg, rgba(46,160,67,0.1))' : 'var(--error-bg, rgba(248,81,73,0.1))' }">
                  Wiki build {{ workbookBuildResult.success ? 'succeeded' : 'failed' }} ({{ workbookBuildResult.duration_seconds }}s)
                  <div v-if="!workbookBuildResult.success" style="margin-top: 0.25rem; white-space: pre-wrap; font-family: monospace; font-size: 0.8rem;">{{ workbookBuildResult.output }}</div>
                </div>

                <!-- Chapters List -->
                <div v-if="workbookChaptersLoading" class="empty-state">Loading chapters...</div>
                <div v-else-if="workbookChapters.length === 0" class="empty-state">
                  No workbook chapters found. Upload a ZIP to get started.
                </div>
                <div v-else>
                  <h3 style="margin-bottom: 0.5rem; font-size: 0.95rem; font-weight: 600;">Chapters ({{ workbookChapters.length }})</h3>
                  <div class="workbook-chapters-list">
                    <div v-for="ch in workbookChapters" :key="ch.directory" class="lab-row" style="display: flex; justify-content: space-between; align-items: center; padding: 0.5rem 0.75rem;">
                      <div>
                        <strong style="font-size: 0.9rem;">{{ ch.label }}</strong>
                        <span style="font-size: 0.8rem; opacity: 0.6; margin-left: 0.5rem;">{{ ch.directory }}/</span>
                        <span style="font-size: 0.8rem; opacity: 0.5; margin-left: 0.5rem;">{{ ch.page_count }} pages</span>
                      </div>
                      <div style="display: flex; gap: 0.25rem;">
                        <button @click="toggleChapterExpand(ch.directory)" class="btn btn--secondary btn--sm" style="font-size: 0.75rem; padding: 0.15rem 0.4rem;">
                          {{ expandedChapter === ch.directory ? 'Hide' : 'Files' }}
                        </button>
                        <button @click="deleteWorkbookChapter(ch.directory)" class="btn btn--sm" style="font-size: 0.75rem; padding: 0.15rem 0.4rem; background: var(--danger-color, #da3633); color: white;">
                          Delete
                        </button>
                      </div>
                    </div>
                    <!-- Expanded file list -->
                    <template v-if="expandedChapter">
                      <div v-for="ch in workbookChapters.filter(c => c.directory === expandedChapter)" :key="'files-' + ch.directory"
                           style="padding: 0.5rem 1rem; font-size: 0.8rem; opacity: 0.7; border-top: 1px solid rgba(128,128,128,0.15);">
                        <div v-for="f in ch.files" :key="f" style="padding: 0.15rem 0;">{{ f }}</div>
                      </div>
                    </template>
                  </div>
                </div>
              </div>

            </div><!-- end .labs-panel -->
          </div><!-- end .catalog-layout -->
        </div>

        <!-- Monitoring Tab (consolidated Sessions + VPN + Activity) -->
        <div v-if="activeTab === 'monitoring'" class="panel">
          <div class="panel-header">
            <h2 class="panel-title">Monitoring</h2>
          </div>
          <div class="sub-tabs">
            <button @click="monitoringSubTab = 'sessions'" :class="['sub-tab', { active: monitoringSubTab === 'sessions' }]">Sessions</button>
            <button @click="monitoringSubTab = 'vpn'" :class="['sub-tab', { active: monitoringSubTab === 'vpn' }]">VPN Peers</button>
            <button @click="monitoringSubTab = 'activity'" :class="['sub-tab', { active: monitoringSubTab === 'activity' }]">Activity Log</button>
          </div>

          <!-- Sessions sub-tab -->
          <div v-if="monitoringSubTab === 'sessions'" class="sub-tab-content">
            <div class="panel-header">
              <h2 class="panel-title">Active Sessions ({{ sessionsHealth.total_sessions || 0 }})</h2>
              <div class="panel-actions">
                <button @click="refreshSessionsHealth" class="btn btn--secondary" :disabled="loadingHealth">
                  <svg v-if="loadingHealth" class="spinner-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/>
                  </svg>
                  {{ loadingHealth ? 'Refreshing...' : 'Refresh' }}
                </button>
                <button @click="showLaunchAsModal = true" class="btn btn--outline impersonate-btn">
                  Launch As Student
                </button>
                <button @click="terminateAll" class="btn btn--danger" :disabled="!sessionsHealth.sessions?.length">
                  Terminate All
                </button>
              </div>
            </div>

            <div v-if="!sessionsHealth.sessions || sessionsHealth.sessions.length === 0" class="empty-state">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="empty-icon">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="8" x2="12" y2="12"/>
                <line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
              <p>No active sessions</p>
            </div>

            <div v-else class="sessions-health-grid">
              <div 
                v-for="session in sessionsHealth.sessions" 
                :key="session.session_id" 
                class="session-health-card"
                :class="{ 'session-health-card--warning': session.time_remaining_seconds < 900, 'session-health-card--stale': session.is_stale, 'session-health-card--diagnostic': session.is_diagnostic }"
              >
                <div class="session-health-header">
                  <div class="session-user-info">
                    <span class="session-username">{{ maskUsername(session.username) }}</span>
                    <span v-if="session.impersonated_by" class="admin-session-tag">Admin ({{ session.impersonated_by.admin_username }})</span>
                    <span v-if="session.is_diagnostic" class="diagnostic-tag">Diagnostics</span>
                    <span class="session-lab">{{ session.lab_name }}</span>
                  </div>
                  <div class="session-time" :class="{ 'session-time--warning': session.time_remaining_seconds < 900 }">
                    {{ formatTimeRemaining(session.time_remaining_seconds) }}
                  </div>
                </div>
                
                <div class="session-connectivity-status">
                  <div class="session-vpn-status">
                    <span class="vpn-status-label">VPN:</span>
                    <span v-if="!session.vpn?.has_config" class="vpn-badge vpn-badge--none">No Config</span>
                    <span v-else-if="session.vpn?.connected" class="vpn-badge vpn-badge--connected">
                      Connected
                      <span v-if="session.vpn.last_handshake" class="vpn-handshake">({{ session.vpn.last_handshake }})</span>
                    </span>
                    <span v-else-if="session.vpn?.registered" class="vpn-badge vpn-badge--disconnected">
                      Disconnected
                      <span v-if="session.vpn.last_handshake" class="vpn-handshake">({{ session.vpn.last_handshake }})</span>
                    </span>
                    <span v-else class="vpn-badge vpn-badge--unregistered">Not Registered</span>
                  </div>
                  <div class="session-rangebox-status">
                    <span class="vpn-status-label">RangeBox:</span>
                    <a
                      v-if="session.rangebox?.status === 'running'"
                      class="vpn-badge vpn-badge--connected rangebox-view-link"
                      :href="`/rangebox?session=${session.session_id}&userId=${session.user_id}`"
                      target="_blank"
                      title="View student's RangeBox screen in new tab"
                    >
                      Active ↗
                      <span v-if="session.rangebox?.mode === 'standalone'" class="vpn-handshake">(standalone)</span>
                    </a>
                    <span v-else-if="session.rangebox?.enabled" class="vpn-badge vpn-badge--disconnected">Stopped</span>
                    <span v-else class="vpn-badge vpn-badge--none">None</span>
                  </div>
                </div>

                <div class="session-network">
                  <span class="network-label">Network:</span>
                  <span class="network-value">{{ session.network_subnet }}</span>
                </div>

                <div v-if="session.is_stale" class="stale-warning">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="stale-warning-icon">
                    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                    <line x1="12" y1="9" x2="12" y2="13"/>
                    <line x1="12" y1="17" x2="12.01" y2="17"/>
                  </svg>
                  <span>Stale session — DB shows running but no containers exist</span>
                </div>

                <div class="containers-section">
                  <h4 class="containers-title">Containers</h4>
                  <div v-if="session.containers && session.containers.length > 0" class="containers-list">
                    <div v-for="container in session.containers" :key="container.name" class="container-row">
                      <span class="container-name">{{ container.name }}</span>
                      <span v-if="container.ip" class="container-ip">{{ container.ip }}</span>
                      <span class="container-status" :class="`container-status--${container.status}`">
                        {{ container.status }}
                      </span>
                      <span v-if="container.health !== 'none'" class="container-health" :class="`container-health--${container.health}`">
                        {{ container.health }}
                      </span>
                      <span v-if="container.ports && container.ports.length > 0" class="container-ports">
                        Port{{ container.ports.length > 1 ? 's' : '' }}: {{ container.ports.join(', ') }}
                      </span>
                      <span class="container-resources">
                        CPU: {{ container.cpu_percent }}% | RAM: {{ container.memory_mb }}MB
                      </span>
                    </div>
                  </div>
                  <div v-else class="no-containers">
                    No containers found
                  </div>
                </div>

                <div class="session-actions">
                  <button @click="viewSessionLogs(session.session_id)" class="btn btn--secondary btn--sm">Logs</button>
                  <button @click="impersonateSession(session.session_id, session.username)" class="btn btn--outline btn--sm impersonate-btn" title="Connect your RangeBox to this student's lab network">
                    {{ impersonatingSessionId === session.session_id ? 'Connected' : 'Impersonate' }}
                  </button>
                  <button v-if="session.is_stale" @click="resetStaleSession(session.session_id, session.username)" class="btn btn--warning btn--sm">
                    Reset Stale
                  </button>
                  <button v-if="session.vpn && !session.vpn.connected && session.vpn.has_config" @click="resyncSessionVpn(session.session_id, session.username)" class="btn btn--primary btn--sm">
                    Re-sync VPN
                  </button>
                  <button @click="terminateSession(session.session_id)" class="btn btn--danger btn--sm">
                    Force Stop
                  </button>
                </div>
              </div>
            </div>

            <!-- Container Logs Modal -->
            <div v-if="viewingLogsSessionId" class="modal-overlay" @click.self="closeSessionLogs">
              <div class="modal" style="max-width: 900px; max-height: 80vh; overflow: auto;">
                <div class="modal-header">
                  <h3 class="modal-title">Container Logs — Session #{{ viewingLogsSessionId }}</h3>
                  <button @click="closeSessionLogs" class="modal-close">&times;</button>
                </div>
                <div v-if="sessionLogsLoading" class="empty-state">Loading logs...</div>
                <div v-else>
                  <div v-for="(info, name) in sessionLogs" :key="name" style="margin-bottom: 1.5rem;">
                    <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                      <span style="font-weight: 600; color: #e2e8f0;">{{ name }}</span>
                      <span class="status-badge" :class="`status-badge--${info.status}`">{{ info.status }}</span>
                    </div>
                    <pre style="background: #020617; border: 1px solid #1e293b; border-radius: 6px; padding: 0.75rem; font-size: 0.75rem; color: #94a3b8; overflow-x: auto; max-height: 300px; white-space: pre-wrap; word-break: break-all;">{{ info.logs }}</pre>
                  </div>
                </div>
              </div>
            </div>

            <div class="session-history">
              <div class="history-header">
                <h3 class="section-title">Recent History</h3>
                <button @click="clearSessionHistory" class="btn btn--secondary btn--sm" :disabled="!sessionHistory.length">
                  Clear History
                </button>
              </div>
              <div class="vpn-filter-bar">
                <div class="vpn-filter-presets">
                  <button
                    v-for="preset in [
                      { key: '1h', label: '1h' },
                      { key: '6h', label: '6h' },
                      { key: '24h', label: '24h' },
                      { key: '7d', label: '7d' },
                      { key: '', label: 'All' },
                      { key: 'custom', label: 'Custom' },
                    ]"
                    :key="preset.key"
                    class="vpn-filter-pill"
                    :class="{ 'vpn-filter-pill--active': sessionsTimeRange === preset.key }"
                    @click="sessionsTimeRange = preset.key; fetchSessionHistory(1)"
                  >{{ preset.label }}</button>
                </div>
                <div v-if="sessionsTimeRange === 'custom'" class="vpn-filter-custom">
                  <input type="datetime-local" v-model="sessionsCustomStart" class="form-input form-input--sm" @change="fetchSessionHistory(1)" />
                  <span style="color: var(--text-muted); font-size: 0.75rem;">to</span>
                  <input type="datetime-local" v-model="sessionsCustomEnd" class="form-input form-input--sm" @change="fetchSessionHistory(1)" />
                </div>
              </div>
              <div v-if="sessionHistoryLoading" class="empty-state" style="padding: 1.5rem;">Loading sessions...</div>
              <div v-else>
                <div class="table-container">
                  <table class="data-table data-table--compact">
                    <thead>
                      <tr>
                        <th>User</th>
                        <th>Exercise</th>
                        <th>Status</th>
                        <th>Started</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-if="sessionHistory.length === 0">
                        <td colspan="4" class="empty-row">No sessions in selected time range</td>
                      </tr>
                      <tr v-for="session in sessionHistory" :key="session.id" :class="{ 'activity-row--diagnostic': session.is_diagnostic }">
                        <td>{{ maskUsername(session.username) }}</td>
                        <td>{{ session.lab_name }}</td>
                        <td>
                          <span class="event-badge" :class="session.is_diagnostic ? 'event-badge--diagnostic' : `event-badge--session-${session.status}`">
                            {{ session.status }}
                          </span>
                          <span v-if="session.is_diagnostic" class="diagnostic-tag">Diagnostics</span>
                        </td>
                        <td class="cell-muted">{{ formatDate(session.started_at) }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-if="sessionHistoryPages > 1" class="pagination" style="display: flex; gap: 0.5rem; margin-top: 1rem; justify-content: center; align-items: center;">
                  <button @click="fetchSessionHistory(sessionHistoryPage - 1)" :disabled="sessionHistoryPage <= 1" class="btn btn--secondary btn--sm">Prev</button>
                  <span style="padding: 0.4rem 0.75rem; color: #94a3b8;">Page {{ sessionHistoryPage }} of {{ sessionHistoryPages }} ({{ sessionHistoryTotal }} total)</span>
                  <button @click="fetchSessionHistory(sessionHistoryPage + 1)" :disabled="sessionHistoryPage >= sessionHistoryPages" class="btn btn--secondary btn--sm">Next</button>
                </div>
              </div>
            </div>
          </div>

          <!-- VPN Peers sub-tab -->
          <div v-if="monitoringSubTab === 'vpn'" class="sub-tab-content">
            <div class="panel-header">
              <h2 class="panel-title">VPN Peer Management</h2>
              <button @click="syncVpnPeers" :disabled="syncing" class="btn btn--primary">
                <svg v-if="syncing" class="spinner-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"/>
                </svg>
                {{ syncing ? 'Syncing...' : 'Sync All Peers' }}
              </button>
            </div>

            <!-- Time Range Filter -->
            <div class="vpn-filter-bar">
              <div class="vpn-filter-presets">
                <button
                  v-for="preset in [
                    { key: '1h', label: '1h' },
                    { key: '6h', label: '6h' },
                    { key: '24h', label: '24h' },
                    { key: '7d', label: '7d' },
                    { key: '', label: 'All' },
                    { key: 'custom', label: 'Custom' },
                  ]"
                  :key="preset.key"
                  class="vpn-filter-pill"
                  :class="{ 'vpn-filter-pill--active': vpnTimeRange === preset.key }"
                  @click="vpnTimeRange = preset.key"
                >{{ preset.label }}</button>
              </div>
              <div v-if="vpnTimeRange === 'custom'" class="vpn-filter-custom">
                <input type="datetime-local" v-model="vpnCustomStart" class="form-input form-input--sm" />
                <span style="color: var(--text-muted); font-size: 0.75rem;">to</span>
                <input type="datetime-local" v-model="vpnCustomEnd" class="form-input form-input--sm" />
              </div>
            </div>

            <!-- Sync Status -->
            <div class="vpn-stats">
              <div class="vpn-stat-card vpn-stat-card--registered">
                <span class="vpn-stat-value">{{ vpnStatus.registered_count || 0 }}</span>
                <span class="vpn-stat-label">Registered on VPN Server</span>
              </div>
              <div class="vpn-stat-card vpn-stat-card--unregistered">
                <span class="vpn-stat-value">{{ vpnStatus.unregistered_count || 0 }}</span>
                <span class="vpn-stat-label">Not Registered</span>
              </div>
            </div>

            <!-- Unregistered Users -->
            <div v-if="vpnStatus.unregistered && vpnStatus.unregistered.length > 0" class="unregistered-section">
              <h3 class="section-title section-title--warning">Unregistered Users</h3>
              <div class="unregistered-list">
                <div v-for="user in vpnStatus.unregistered" :key="user.user_id" class="unregistered-item">
                  <div class="unregistered-info">
                    <span class="unregistered-name">{{ maskUsername(user.username) }}</span>
                    <span class="unregistered-ip">{{ user.client_ip }}</span>
                  </div>
                  <button @click="registerPeer(user.user_id)" class="btn btn--success btn--sm">Register</button>
                </div>
              </div>
            </div>

            <!-- Active Peers Table -->
            <div class="peers-section">
              <h3 class="section-title">Active VPN Peers</h3>
              <div class="table-container">
                <table class="data-table">
                  <thead>
                    <tr>
                      <th>User</th>
                      <th>IP</th>
                      <th>Status</th>
                      <th>Last Handshake</th>
                      <th>Transfer</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="peer in paginatedVpnPeers" :key="peer.public_key">
                      <td class="cell-primary">
                        <span v-if="peer.is_labs_server" class="server-badge">Labs Server</span>
                        <span v-else-if="peer.user">{{ maskUsername(peer.user.username) }}</span>
                        <span v-else class="cell-muted">Unknown</span>
                      </td>
                      <td class="cell-mono">{{ peer.allowed_ips }}</td>
                      <td>
                        <span
                          v-if="peer.is_labs_server || !peer.health || peer.health === 'ok'"
                          class="health-badge health-badge--ok"
                        >OK</span>
                        <span
                          v-else-if="peer.health === 'no_allowed_ips'"
                          class="health-badge health-badge--bad"
                          :title="peer.health_detail || ''"
                        >No allowed_ips</span>
                        <span
                          v-else-if="peer.health === 'duplicate_for_ip'"
                          class="health-badge health-badge--bad"
                          :title="peer.health_detail || ''"
                        >Duplicate</span>
                        <span
                          v-else-if="peer.health === 'orphan_no_db'"
                          class="health-badge health-badge--warn"
                          :title="peer.health_detail || ''"
                        >Orphan</span>
                      </td>
                      <td>
                        <span v-if="peer.latest_handshake" class="handshake-active">{{ peer.latest_handshake }}</span>
                        <span v-else class="cell-muted">Never</span>
                      </td>
                      <td class="cell-muted cell-mono">
                        <template v-if="peer.transfer_rx || peer.transfer_tx">
                          <span class="transfer-down">↓ {{ peer.transfer_rx || '0 B' }}</span>
                          <span class="transfer-up">↑ {{ peer.transfer_tx || '0 B' }}</span>
                        </template>
                        <span v-else class="cell-muted">—</span>
                      </td>
                      <td>
                        <template v-if="!peer.is_labs_server">
                          <button
                            v-if="peer.repair_user_id"
                            @click="repairPeer(peer.repair_user_id)"
                            class="btn btn--primary btn--sm"
                            style="margin-right: 0.25rem;"
                            title="Remove conflicting peers and re-register from DB"
                          >Repair</button>
                          <button
                            @click="peer.user ? removePeer(peer.user.id) : removePeerByKey(peer.public_key)"
                            class="btn btn--danger btn--sm"
                          >Remove</button>
                        </template>
                      </td>
                    </tr>
                  </tbody>
                </table>
                <div v-if="vpnTotalPages > 1" class="pagination" style="display: flex; gap: 0.5rem; margin-top: 1rem; justify-content: center; align-items: center;">
                  <button @click="vpnPage = vpnPage - 1" :disabled="vpnPage <= 1" class="btn btn--secondary btn--sm">Prev</button>
                  <span style="padding: 0.4rem 0.75rem; color: #94a3b8;">Page {{ vpnPage }} of {{ vpnTotalPages }}</span>
                  <button @click="vpnPage = vpnPage + 1" :disabled="vpnPage >= vpnTotalPages" class="btn btn--secondary btn--sm">Next</button>
                </div>
              </div>
            </div>
          </div>

          <!-- Activity Log sub-tab -->
          <div v-if="monitoringSubTab === 'activity'" class="sub-tab-content">
            <div class="panel-header">
              <h2 class="panel-title">Activity Log</h2>
              <select v-model="activityFilter" @change="fetchActivity(1)" class="form-input form-input--sm" style="width: auto;">
                <option value="">All Events</option>
                <option v-for="et in activityEventTypes" :key="et" :value="et">{{ eventTypeLabel(et) }}</option>
              </select>
            </div>
            <div class="vpn-filter-bar">
              <div class="vpn-filter-presets">
                <button
                  v-for="preset in [
                    { key: '1h', label: '1h' },
                    { key: '6h', label: '6h' },
                    { key: '24h', label: '24h' },
                    { key: '7d', label: '7d' },
                    { key: '', label: 'All' },
                    { key: 'custom', label: 'Custom' },
                  ]"
                  :key="preset.key"
                  class="vpn-filter-pill"
                  :class="{ 'vpn-filter-pill--active': activityTimeRange === preset.key }"
                  @click="activityTimeRange = preset.key; fetchActivity(1)"
                >{{ preset.label }}</button>
              </div>
              <div v-if="activityTimeRange === 'custom'" class="vpn-filter-custom">
                <input type="datetime-local" v-model="activityCustomStart" class="form-input form-input--sm" @change="fetchActivity(1)" />
                <span style="color: var(--text-muted); font-size: 0.75rem;">to</span>
                <input type="datetime-local" v-model="activityCustomEnd" class="form-input form-input--sm" @change="fetchActivity(1)" />
              </div>
            </div>
            <div v-if="activityLoading" class="empty-state">Loading activity...</div>
            <div v-else-if="activityEvents.length === 0" class="empty-state">No activity events found.</div>
            <div v-else>
              <div class="table-container">
                <table class="data-table data-table--compact">
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Event</th>
                      <th>User</th>
                      <th>Target</th>
                      <th>Details</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="event in activityEvents" :key="event.id" :class="{ 'activity-row--diagnostic': isDiagnosticEvent(event) }">
                      <td class="cell-muted" style="white-space: nowrap;">{{ formatDate(event.created_at) }}</td>
                      <td>
                        <span class="event-badge" :class="isDiagnosticEvent(event) ? 'event-badge--diagnostic' : 'event-badge--' + event.event_type">{{ event.label }}</span>
                        <span v-if="isDiagnosticEvent(event)" class="diagnostic-tag">Diagnostics</span>
                      </td>
                      <td>{{ event.actor_name || '—' }}</td>
                      <td>{{ event.target_label || '—' }}</td>
                      <td class="cell-muted" style="max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{{ formatActivityDetail(event.detail) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div v-if="activityPages > 1" class="pagination" style="display: flex; gap: 0.5rem; margin-top: 1rem; justify-content: center;">
                <button @click="fetchActivity(activityPage - 1)" :disabled="activityPage <= 1" class="btn btn--secondary btn--sm">Prev</button>
                <span style="padding: 0.4rem 0.75rem; color: #94a3b8;">Page {{ activityPage }} of {{ activityPages }}</span>
                <button @click="fetchActivity(activityPage + 1)" :disabled="activityPage >= activityPages" class="btn btn--secondary btn--sm">Next</button>
              </div>
            </div>
          </div>

        </div>

        <!-- Courses Tab -->
        <div v-if="activeTab === 'courses'" class="panel">
          <div class="panel-header">
            <h2 class="panel-title">Course Management</h2>
            <button v-if="!showAdminCreateCourse" @click="showAdminCreateCourse = true" class="btn btn--success btn--sm">+ Create Course</button>
          </div>

          <!-- Create Course Form -->
          <div v-if="showAdminCreateCourse" class="create-course-form" style="margin-bottom: 1.5rem;">
            <h3 style="color: #f8fafc; margin-bottom: 1rem;">Create New Course</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
              <div class="form-group">
                <label>Course Name</label>
                <input aria-label="Course Name" v-model="newCourseForm.name" type="text" placeholder="e.g. Network Security Exercise" class="form-input" />
              </div>
              <div class="form-group">
                <label>Course Code</label>
                <input aria-label="Course Code" v-model="newCourseForm.code" type="text" placeholder="e.g. CYB301" class="form-input" />
              </div>
              <div class="form-group">
                <label>Semester</label>
                <input aria-label="Semester" v-model="newCourseForm.semester" type="text" placeholder="e.g. Spring 2026" class="form-input" />
              </div>
              <div class="form-group">
                <label>Description (optional)</label>
                <input aria-label="Description (optional)" v-model="newCourseForm.description" type="text" placeholder="Brief description" class="form-input" />
              </div>
              <div class="form-group">
                <label>Start Date</label>
                <input aria-label="Start Date" v-model="newCourseForm.start_date" type="date" class="form-input" />
              </div>
              <div class="form-group">
                <label>End Date</label>
                <input aria-label="End Date" v-model="newCourseForm.end_date" type="date" class="form-input" />
              </div>
              <div class="form-group" style="grid-column: 1 / -1;">
                <label>Assign Instructor</label>
                <select aria-label="Assign Instructor" v-model="newCourseForm.instructor_id" class="form-input">
                  <option value="">Me (current admin)</option>
                  <option v-for="u in instructorUsers" :key="u.id" :value="u.id">
                    {{ u.username }} ({{ u.role }})
                  </option>
                </select>
              </div>
            </div>
            <div style="margin-top: 1rem; display: flex; gap: 0.75rem;">
              <button @click="createAdminCourse" :disabled="creatingAdminCourse" class="btn btn--success btn--sm">
                {{ creatingAdminCourse ? 'Creating...' : 'Create Course' }}
              </button>
              <button @click="showAdminCreateCourse = false" class="btn btn--secondary btn--sm">Cancel</button>
            </div>
          </div>

          <!-- Course Filter & Sort Controls -->
          <div v-if="adminCourses.length > 0" class="course-controls">
            <div class="course-filters">
              <button @click="courseFilter = 'all'" :class="['filter-btn', { 'filter-btn--active': courseFilter === 'all' }]">All</button>
              <button @click="courseFilter = 'active'" :class="['filter-btn', { 'filter-btn--active': courseFilter === 'active' }]">Active</button>
              <button @click="courseFilter = 'pending'" :class="['filter-btn', { 'filter-btn--active': courseFilter === 'pending' }]">Pending Review</button>
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

          <!-- Course List -->
          <div v-if="adminCourses.length === 0 && !showAdminCreateCourse" class="empty-state">
            No courses yet. Click "+ Create Course" above to get started.
          </div>

          <div class="table-container" v-if="sortedFilteredCourses.length > 0">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Code</th>
                  <th>Semester</th>
                  <th>Instructor</th>
                  <th>Students</th>
                  <th>Exercises</th>
                  <th>Invite Code</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="course in sortedFilteredCourses" :key="course.id">
                  <td class="cell-primary">{{ course.name }}</td>
                  <td>{{ course.code }}</td>
                  <td>{{ course.semester }}</td>
                  <td>{{ course.instructor_name || '—' }}</td>
                  <td>{{ course.student_count }}</td>
                  <td>{{ course.lab_count }}</td>
                  <td>
                    <code class="invite-code-admin" @click="copyToClipboard(course.invite_code)">
                      {{ course.invite_code }}
                    </code>
                  </td>
                  <td>
                    <span :class="['status-badge', adminCourseStatus(course).class]">
                      {{ adminCourseStatus(course).text }}
                    </span>
                  </td>
                  <td class="cell-actions">
                    <button @click="openCourseManager(course)" class="action-btn action-btn--view" title="Manage">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
                      </svg>
                    </button>
                    <button v-if="!course.is_archived && !course.is_active" @click="toggleCourseActive(course)" class="action-btn action-btn--approve" title="Approve & Activate">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"/><polyline points="9 12 12 15 16 9"/>
                      </svg>
                    </button>
                    <button v-if="!course.is_archived && course.is_active" @click="toggleCourseActive(course)" class="action-btn action-btn--reset" title="Deactivate">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"/><line x1="10" y1="15" x2="10" y2="9"/><line x1="14" y1="15" x2="14" y2="9"/>
                      </svg>
                    </button>
                    <button v-if="!course.is_archived" @click="archiveCourse(course)" class="action-btn action-btn--archive" title="Archive">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5"/><line x1="10" y1="12" x2="14" y2="12"/>
                      </svg>
                    </button>
                    <button v-if="course.is_archived" @click="unarchiveCourse(course)" class="action-btn action-btn--unlock" title="Unarchive">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5"/><polyline points="12 12 12 8 16 12 12 16 12 12"/>
                      </svg>
                    </button>
                    <button @click="deleteCourse(course)" class="action-btn action-btn--delete" title="Delete">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6"/><path d="M19 6V20C19 21.1 18.1 22 17 22H7C5.9 22 5 21.1 5 20V6M8 6V4C8 2.9 8.9 2 10 2H14C15.1 2 16 2.9 16 4V6"/>
                      </svg>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else-if="adminCourses.length > 0 && sortedFilteredCourses.length === 0" class="empty-state">
            No courses match the current filter.
          </div>

          <!-- Manage Course Panel (slim - platform oversight only) -->
          <div v-if="managingCourse" class="course-manage-section">
            <div class="panel-header">
              <h3 class="panel-title">{{ managingCourse.name }} ({{ managingCourse.code }})</h3>
              <div style="display: flex; gap: 0.5rem;">
                <router-link :to="`/courses/${managingCourse.id}`" class="btn btn--primary btn--sm">
                  Open Course &rarr;
                </router-link>
                <button @click="managingCourse = null" class="btn btn--secondary btn--sm">Close</button>
              </div>
            </div>
            <div class="assign-instructor-row">
              <label class="assign-instructor-label">Assigned instructor:</label>
              <select aria-label="Assigned instructor:" class="form-input assign-instructor-select" :value="managingCourse.instructor_id" @change="updateCourseInstructor($event.target.value)">
                <option v-for="u in instructorUsers" :key="u.id" :value="u.id">
                  {{ u.username }} ({{ u.role }})
                </option>
              </select>
            </div>
            <div class="course-overview-stats" style="display: flex; gap: 1.5rem; padding: 0.75rem 0; color: #94a3b8; font-size: 0.875rem;">
              <span><strong style="color: #f8fafc;">{{ managingCourse.student_count }}</strong> students</span>
              <span><strong style="color: #f8fafc;">{{ managingCourse.lab_count }}</strong> exercises</span>
              <span>Invite: <code class="invite-code-admin" @click="copyToClipboard(managingCourse.invite_code)" style="cursor: pointer;">{{ managingCourse.invite_code }}</code></span>
            </div>
            <p style="color: #64748b; font-size: 0.8125rem; margin: 0;">
              Use <strong>Open Course</strong> to manage students, exercises, assignments, and reports.
            </p>
          </div>
        </div>

        <!-- Settings Tab -->
        <div v-if="activeTab === 'settings'" class="panel">
          <h2 class="panel-title">Platform Settings</h2>
          <div class="settings-categories">
            <button
              v-for="cat in settingsCategories"
              :key="cat"
              @click="activeSettingsCategory = cat"
              class="lab-tab"
              :class="{ 'lab-tab--active': activeSettingsCategory === cat }"
            >
              {{ categoryLabel(cat) }}
            </button>
          </div>
          <!-- Custom Modules panel with save buttons -->
          <div v-if="activeSettingsCategory === 'modules'" class="settings-form">
            <div v-if="settingsLoading" class="empty-state">Loading settings...</div>
            <template v-else>
              <div v-for="mod in moduleCards" :key="mod.key" class="module-card" :class="{ 'module-card--enabled': mod.staged }">
                <div class="module-card__header">
                  <div class="module-card__icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
                  </div>
                  <div class="module-card__info">
                    <span class="module-card__name">{{ mod.label }}</span>
                    <span class="module-card__desc">{{ mod.description }}</span>
                  </div>
                  <div class="module-card__actions">
                    <button
                      class="module-card__toggle"
                      :class="mod.staged ? 'module-card__toggle--on' : 'module-card__toggle--off'"
                      :disabled="moduleToggling === mod.key"
                      @click="stageModuleToggle(mod.key)"
                    >
                      {{ mod.staged ? 'Enabled' : 'Disabled' }}
                    </button>
                    <button
                      v-if="mod.dirty"
                      class="module-card__save"
                      :disabled="moduleToggling === mod.key"
                      @click="saveModule(mod.key)"
                    >
                      <span v-if="moduleToggling === mod.key" class="module-toggle-spinner"></span>
                      {{ moduleToggling === mod.key ? 'Saving...' : (mod.staged ? 'Enable Module' : 'Disable Module') }}
                    </button>
                  </div>
                </div>
                <!-- Live status log -->
                <div class="module-card__log" v-if="moduleLog[mod.key] && moduleLog[mod.key].length">
                  <div class="module-log-header">
                    <span class="module-log-dot" :class="{ 'module-log-dot--active': moduleToggling === mod.key }"></span>
                    <span class="module-log-label">module-status</span>
                  </div>
                  <div class="module-log-body">
                    <div v-for="(entry, i) in moduleLog[mod.key]" :key="i" class="module-log-line" :class="'module-log-line--' + entry.level">
                      <span class="module-log-time">{{ entry.time }}</span>
                      <span class="module-log-msg">{{ entry.message }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </template>
          </div>

          <!-- Generic settings form for other categories -->
          <div v-else class="settings-form">
            <div v-if="settingsLoading" class="empty-state">Loading settings...</div>
            <template v-else>
              <div v-for="(value, key) in filteredSettings" :key="key" class="setting-row">
                <div class="setting-info">
                  <span class="setting-key">
                    {{ friendlyLabel(key) }}
                    <span v-if="settingDescription(key)" class="setting-info-icon" tabindex="0">
                      i
                      <span class="setting-tooltip">{{ settingDescription(key) }}</span>
                    </span>
                  </span>
                </div>
                <div class="setting-control">
                  <template v-if="value === 'true' || value === 'false'">
                    <button
                      class="visibility-toggle"
                      :class="settingsEdits[key] === 'true' ? 'visibility-toggle--public' : 'visibility-toggle--exclusive'"
                      :disabled="togglesSaving[key]"
                      @click="toggleSetting(key)"
                    >
                      {{ togglesSaving[key] ? 'Saving...' : (settingsEdits[key] === 'true' ? 'Enabled' : 'Disabled') }}
                    </button>
                  </template>
                  <template v-else-if="key.includes('color')">
                    <input type="color" v-model="settingsEdits[key]" class="color-input" />
                  </template>
                  <template v-else>
                    <div class="setting-input-group">
                      <input
                        v-model="settingsEdits[key]"
                        :type="value === '••••••••' ? 'password' : 'text'"
                        :placeholder="settingPlaceholder(key)"
                        class="form-input form-input--sm"
                      />
                      <span v-if="settingUnit(key)" class="setting-unit">{{ settingUnit(key) }}</span>
                    </div>
                  </template>
                </div>
              </div>
              <div v-if="Object.keys(filteredSettings).length === 0" class="empty-state">
                No settings in this category.
              </div>
            </template>
            <div class="form-actions" style="margin-top: 1rem;">
              <button @click="saveSettings" class="btn btn--success" :disabled="savingSettings">
                {{ savingSettings ? 'Saving...' : 'Save Settings' }}
              </button>
            </div>
          </div>
        </div>

        <!-- System Tab -->
        <div v-if="activeTab === 'system'" class="panel">
          <h2 class="panel-title" style="margin-bottom: 1rem;">System</h2>
          <div class="sub-tabs">
            <button @click="systemSubTab = 'health'" :class="['sub-tab', { active: systemSubTab === 'health' }]">Health</button>
            <button @click="systemSubTab = 'backups'" :class="['sub-tab', { active: systemSubTab === 'backups' }]">Backups</button>
            <button v-if="exerciseTester" @click="systemSubTab = 'tester'" :class="['sub-tab', { active: systemSubTab === 'tester' }]">Exercise Tester</button>
            <button v-if="stressTester" @click="systemSubTab = 'stress'; checkActiveStressTest()" :class="['sub-tab', { active: systemSubTab === 'stress' }]">Stress Tester</button>
          </div>

          <!-- Health Sub-tab -->
          <div v-if="systemSubTab === 'health'">
            <!-- Minimal status (default; plain-language, install-aware, this-install only) -->
            <div class="panel-header">
              <h3 class="section-title">Status</h3>
              <button @click="fetchSystemStatus" :disabled="systemStatusLoading" class="btn btn--secondary btn--sm">
                {{ systemStatusLoading ? 'Checking...' : 'Refresh' }}
              </button>
            </div>
            <div v-if="systemStatusLoading && !systemStatus.items" class="empty-state">Checking status...</div>
            <div v-else-if="systemStatus.items">
              <div v-if="systemStatus.overall === 'ok'" class="health-inline">
                <span class="health-dot health-dot--green"></span>
                <span class="health-inline__text">All good</span>
              </div>
              <div v-else class="security-overall" :class="`security-overall--${systemStatus.overall}`">
                {{ systemStatus.overall === 'warning' ? 'Some items need attention' : 'Action needed' }}
              </div>
              <div class="security-checks-grid">
                <div v-for="item in systemStatus.items" :key="item.name" class="security-check-card" :class="`security-check-card--${item.status}`">
                  <div class="security-check-header">
                    <span class="security-check-icon">
                      <template v-if="item.status === 'ok'">&#10003;</template>
                      <template v-else-if="item.status === 'warning'">&#9888;</template>
                      <template v-else>&#10007;</template>
                    </span>
                    <span class="security-check-name">{{ item.name }}</span>
                  </div>
                  <div class="security-check-detail">{{ item.detail }}</div>
                </div>
              </div>
            </div>
          </div>

          <!-- Backups Sub-tab -->
          <div v-if="systemSubTab === 'backups'">
            <div class="panel-header">
              <h3 class="section-title">Database Snapshots</h3>
              <button @click="createBackup" :disabled="creatingBackup" class="btn btn--success btn--sm">
                {{ creatingBackup ? 'Creating...' : 'Create Snapshot' }}
              </button>
            </div>
            <p class="section-desc">Snapshots capture all users, courses, enrollments, exercise assignments, scores, achievements, and activity logs. Use restore to roll back to a previous point in time.</p>

            <!-- Backup Activity Heatmap -->
            <div class="backup-heatmap-card">
              <div class="backup-heatmap-header">
                <span class="backup-heatmap-title">{{ backupHeatmapData.totalBackups }} snapshot{{ backupHeatmapData.totalBackups === 1 ? '' : 's' }} in the last year</span>
                <div class="backup-heatmap-legend">
                  <span class="heatmap-swatch heatmap-swatch--green"></span>
                  <span class="cell-muted" style="margin-right:8px;">Backed up</span>
                  <span class="heatmap-swatch heatmap-swatch--split"></span>
                  <span class="cell-muted" style="margin-right:8px;">Changes after backup</span>
                  <span class="heatmap-swatch heatmap-swatch--yellow"></span>
                  <span class="cell-muted">Unbacked changes</span>
                </div>
              </div>
              <div class="backup-heatmap-scroll">
                <div class="backup-heatmap-grid">
                  <div class="heatmap-day-labels">
                    <span></span>
                    <span>Mon</span>
                    <span></span>
                    <span>Wed</span>
                    <span></span>
                    <span>Fri</span>
                    <span></span>
                  </div>
                  <div class="heatmap-columns">
                    <div class="heatmap-month-labels">
                      <span v-for="m in backupHeatmapData.monthLabels" :key="m.key" :style="{ gridColumn: m.col + ' / span ' + m.span }">{{ m.label }}</span>
                    </div>
                    <div class="heatmap-cells">
                      <div v-for="(week, wi) in backupHeatmapData.weeks" :key="wi" class="heatmap-week">
                        <template v-for="(day, di) in week" :key="di">
                          <span v-if="day === null" class="heatmap-cell heatmap-cell--empty"></span>
                          <span v-else class="heatmap-cell" :class="`heatmap-cell--${day.color}`" :title="day.tooltip"></span>
                        </template>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div v-if="restoringBackup" class="restore-overlay">
              <div class="restore-overlay-content">
                <div class="spinner"></div>
                <p>Restoring database from snapshot...</p>
                <p class="cell-muted">Do not close this page.</p>
              </div>
            </div>

            <div v-if="backupsLoading" class="empty-state">Loading snapshots...</div>
            <div v-else-if="backups.length === 0" class="empty-state">No snapshots available. Click "Create Snapshot" to create your first backup.</div>
            <div v-else class="table-container">
              <table class="data-table data-table--compact">
                <thead>
                  <tr>
                    <th>Filename</th>
                    <th>Size</th>
                    <th>Created</th>
                    <th style="text-align:right;">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="backup in backups" :key="backup.filename">
                    <td class="cell-mono">{{ backup.filename }}</td>
                    <td>{{ formatBackupSize(backup.size_bytes) }}</td>
                    <td class="cell-muted">{{ formatDate(backup.created) }}</td>
                    <td style="text-align:right;">
                      <div class="backup-actions">
                        <button @click="downloadBackup(backup.filename)" class="btn btn--secondary btn--xs" title="Download">
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                            <polyline points="7 10 12 15 17 10"/>
                            <line x1="12" y1="15" x2="12" y2="3"/>
                          </svg>
                          Download
                        </button>
                        <button @click="confirmRestore(backup)" class="btn btn--warning btn--xs" :disabled="restoringBackup" title="Restore">
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;">
                            <polyline points="1 4 1 10 7 10"/>
                            <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/>
                          </svg>
                          Restore
                        </button>
                        <button @click="confirmDeleteBackup(backup)" class="btn btn--danger btn--xs" :disabled="deletingBackup === backup.filename" title="Delete">
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;">
                            <polyline points="3 6 5 6 21 6"/>
                            <path d="M19 6l-2 14H7L5 6"/>
                            <path d="M10 11v6M14 11v6M9 6V4h6v2"/>
                          </svg>
                          {{ deletingBackup === backup.filename ? 'Deleting...' : 'Delete' }}
                        </button>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- ===================== TESTER SUB-TAB ===================== -->
          <div v-if="systemSubTab === 'tester'">
            <div class="panel-header">
              <h3 class="section-title">Exercise Tester</h3>
            </div>

          <!-- Controls row: filters + actions -->
          <div class="tester-controls">
            <div class="tester-filters">
              <div class="tester-filter-row">
                <select v-model="testerTrackFilter" class="form-select tester-track-select">
                  <option value="">All Tracks</option>
                  <option v-for="track in testerTracks" :key="track" :value="track">{{ track }}</option>
                </select>
                <select v-model="testerCategoryFilter" class="form-select tester-category-select">
                  <option value="">All Categories</option>
                  <option v-for="cat in testerCategories" :key="cat" :value="cat">{{ cat }}</option>
                </select>
                <select v-model="testerCourseFilter" class="form-select tester-course-select">
                  <option value="">All Courses</option>
                  <option v-for="course in testerCourses" :key="course.id" :value="course.id">{{ course.code }} - {{ course.name }}</option>
                </select>
                <select v-model="testerStatusFilter" class="form-select tester-status-select">
                  <option value="">All Results</option>
                  <option value="ok">Passed</option>
                  <option value="warning">Warning</option>
                  <option value="failed">Failed</option>
                  <option value="untested">Untested</option>
                </select>
                <input
                  v-model="testerSearchQuery"
                  type="text"
                  class="form-input tester-search"
                  placeholder="Search labs..."
                />
                <span class="tester-selection-count">{{ testerLabSelection.filter(s => searchedTesterLabs.some(l => l.slug === s)).length }} selected</span>
              </div>

              <!-- Results summary bar -->
              <div v-if="Object.keys(testerResults).length" class="tester-results-summary">
                <span class="tester-summary-item tester-summary-item--ok" :title="testerSummaryPassed + ' passed'">
                  <span class="tester-status-dot tester-status-dot--ok"></span> {{ testerSummaryPassed }} passed
                </span>
                <span v-if="testerSummaryWarned" class="tester-summary-item tester-summary-item--warning" :title="testerSummaryWarned + ' warnings'">
                  <span class="tester-status-dot tester-status-dot--warning"></span> {{ testerSummaryWarned }} warning{{ testerSummaryWarned !== 1 ? 's' : '' }}
                </span>
                <span v-if="testerSummaryFailed" class="tester-summary-item tester-summary-item--error" :title="testerSummaryFailed + ' failed'">
                  <span class="tester-status-dot tester-status-dot--error"></span> {{ testerSummaryFailed }} failed
                </span>
                <span class="tester-summary-item tester-summary-item--total">{{ Object.keys(testerResults).length }}/{{ testerLabList.length }} tested</span>
              </div>

              <!-- Checkbox lab picker -->
              <div class="tester-lab-picker">
                <template v-for="(lab, idx) in searchedTesterLabs" :key="lab.slug">
                  <div
                    v-if="testerCourseFilter && lab.week != null && (idx === 0 || searchedTesterLabs[idx - 1].week !== lab.week)"
                    class="tester-week-divider"
                  >Week {{ lab.week }}</div>
                  <label
                    class="tester-lab-item"
                    :class="[
                      testerLabSelection.includes(lab.slug) ? 'tester-lab-item--selected' : '',
                      testerResults[lab.slug] ? 'tester-lab-item--' + testerResults[lab.slug].status : ''
                    ]"
                  >
                    <input
                      type="checkbox"
                      :value="lab.slug"
                      v-model="testerLabSelection"
                      class="tester-lab-checkbox"
                    />
                    <span
                      v-if="testerResults[lab.slug]"
                      class="tester-status-dot"
                      :class="'tester-status-dot--' + testerResults[lab.slug].status"
                      :title="testerResults[lab.slug].status.toUpperCase() + ' - ' + (testerResults[lab.slug].date || '')"
                    ></span>
                    <span class="tester-lab-name">{{ lab.name }}</span>
                    <span
                      v-if="testerResults[lab.slug]"
                      class="tester-badge tester-badge--report"
                      :class="'tester-badge--report-' + testerResults[lab.slug].status"
                      :title="'View report (' + testerResults[lab.slug].status + ')'"
                      @click.prevent.stop="generateTestReport(lab.slug)"
                    >Report</span>
                    <span v-if="lab.has_test_steps" class="tester-badge tester-badge--test" title="Has test steps">T</span>
                    <span v-if="lab.has_flag" class="tester-badge tester-badge--flag" title="Has flag hash">F</span>
                    <span class="tester-lab-track">{{ lab.track }}</span>
                  </label>
                </template>
                <div v-if="!searchedTesterLabs.length" class="tester-lab-empty">
                  No labs match your filters
                </div>
              </div>
            </div>

            <div class="tester-actions">
              <button @click="runExerciseTest" class="btn btn--primary btn--sm" :disabled="testerRunning || testerLabSelection.length === 0">
                {{ testerRunning ? 'Testing...' : 'Run Selected' }}
              </button>
              <button v-if="testerRunning" @click="cancelExerciseTest" class="btn btn--danger btn--sm" :disabled="testerCancelling">
                {{ testerCancelling ? 'Cancelling...' : 'Cancel' }}
              </button>
              <button @click="testerLabSelection = searchedTesterLabs.map(l => l.slug)" class="btn btn--secondary btn--sm" :disabled="testerRunning">
                Select All
              </button>
              <button @click="testerLabSelection = []" class="btn btn--secondary btn--sm" :disabled="testerRunning">
                Deselect
              </button>
              <button @click="clearTesterResults" class="btn btn--secondary btn--sm" :disabled="testerRunning">
                Clear Output
              </button>
            </div>
          </div>

          <!-- Terminal -->
          <div class="diagnostics-terminal">
            <div class="diagnostics-terminal-header">
              <span class="diagnostics-terminal-dot" :class="{ 'diagnostics-terminal-dot--active': testerRunning }"></span>
              <span class="diagnostics-terminal-label">ocr-exercise-tester</span>
              <template v-if="testerRunning && testerProgress.total > 0">
                <span class="tester-progress-text">{{ testerProgress.current }}/{{ testerProgress.total }}</span>
                <div class="tester-progress-bar">
                  <div class="tester-progress-fill" :style="{ width: testerProgress.pct + '%' }"></div>
                </div>
                <span class="tester-progress-pct">{{ testerProgress.pct }}%</span>
              </template>
            </div>
            <div class="diagnostics-terminal-body" ref="testerTerminalRef" style="max-height: 600px;">
              <div v-if="!testerSections.length && !testerRunning" class="diagnostics-empty">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#475569" stroke-width="1.5">
                  <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
                </svg>
                <p>Select labs and click <strong>Run Tests</strong> to validate exercises end-to-end.</p>
              </div>

              <template v-for="(section, sIdx) in testerSections" :key="section.test_key">
                <div class="diagnostics-section-header">-- {{ section.name }} --</div>
                <div v-for="(line, lIdx) in section.lines" :key="sIdx + '-' + lIdx" class="diagnostics-line">
                  <span class="diagnostics-line-time">{{ line.timestamp }}</span>
                  <span class="diagnostics-line-level" :class="'diagnostics-level--' + line.level">
                    [{{ line.level === 'ok' ? 'PASS' : line.level === 'error' ? 'FAIL' : line.level === 'warning' ? 'WARN' : 'INFO' }}]
                  </span>
                  <span class="diagnostics-line-msg">{{ line.message }}</span>
                </div>
              </template>

              <div v-if="testerRunning" class="diagnostics-cursor">_</div>
            </div>
          </div>
          </div>

          <!-- ===================== STRESS TESTER SUB-TAB ===================== -->
          <div v-if="systemSubTab === 'stress'">
            <div class="panel-header">
              <h3 class="section-title">Stress Tester</h3>
            </div>

            <!-- Controls -->
            <div style="display: flex; gap: 1rem; align-items: flex-end; flex-wrap: wrap; margin-bottom: 1rem;">
              <div class="form-group" style="margin-bottom: 0;">
                <label style="font-size: 0.75rem; color: #94a3b8; display: block; margin-bottom: 0.25rem;">Level</label>
                <select aria-label="Level" v-model.number="stressLevel" class="form-input form-input--sm" style="width: 180px;" :disabled="stressRunning">
                  <option :value="1">1 - API Only</option>
                  <option :value="2">2 - Auth + API</option>
                  <option :value="3">3 - Full Load (Docker)</option>
                  <option :value="4">4 - RangeBox VNC Load</option>
                </select>
              </div>
              <div class="form-group" style="margin-bottom: 0;">
                <label style="font-size: 0.75rem; color: #94a3b8; display: block; margin-bottom: 0.25rem;">Users</label>
                <input aria-label="Users" v-model.number="stressUsers" type="number" min="1" max="200" class="form-input form-input--sm" style="width: 80px;" :disabled="stressRunning" />
              </div>
              <div v-if="stressLevel === 3 || stressLevel === 4" class="form-group" style="margin-bottom: 0;">
                <label style="font-size: 0.75rem; color: #94a3b8; display: block; margin-bottom: 0.25rem;">Concurrent Spawns</label>
                <input aria-label="Concurrent Spawns" v-model.number="stressConcurrentSpawns" type="number" min="1" max="20" class="form-input form-input--sm" style="width: 80px;" :disabled="stressRunning" />
              </div>
              <div style="display: flex; gap: 0.5rem;">
                <button @click="runStressTest" class="btn btn--primary btn--sm" :disabled="stressRunning">
                  {{ stressRunning ? 'Running...' : 'Run Test' }}
                </button>
                <button v-if="stressRunning" @click="cancelStressTest" class="btn btn--danger btn--sm">
                  Cancel
                </button>
                <button @click="downloadStressReport" class="btn btn--secondary btn--sm" :disabled="stressRunning || !stressResults" title="Download PDF report">
                  PDF Report
                </button>
                <button @click="stressCleanup" class="btn btn--secondary btn--sm" :disabled="stressRunning" title="Remove test users from database">
                  Cleanup
                </button>
              </div>
            </div>

            <div v-if="stressLevel === 3" style="background: rgba(234, 179, 8, 0.1); border: 1px solid rgba(234, 179, 8, 0.3); border-radius: 0.5rem; padding: 0.5rem 0.75rem; margin-bottom: 1rem; font-size: 0.8rem; color: #eab308;">
              <strong>Warning:</strong> Level 3 pre-spawns Docker containers for all users before the timed test. Only run on an idle system. The pre-spawn and cleanup phases are not timed.
            </div>
            <div v-if="stressLevel === 4" style="background: rgba(234, 179, 8, 0.1); border: 1px solid rgba(234, 179, 8, 0.3); border-radius: 0.5rem; padding: 0.5rem 0.75rem; margin-bottom: 1rem; font-size: 0.8rem; color: #eab308;">
              <strong>Warning:</strong> Level 4 spawns standalone RangeBoxes and opens VNC WebSocket connections to each one. Measures VNC frame latency, throughput, and host resource usage. Only run on an idle system.
            </div>

            <!-- Results Table -->
            <div v-if="stressResults && stressResults.endpoints && stressResults.endpoints.length" style="margin-bottom: 1rem;">
              <div style="overflow-x: auto;">
                <table class="data-table">
                  <thead>
                    <tr>
                      <th>Endpoint</th>
                      <th style="text-align: right;">Calls</th>
                      <th style="text-align: right;">Typical</th>
                      <th style="text-align: right;">Slow</th>
                      <th style="text-align: right;">Worst</th>
                      <th style="text-align: right;">Errors</th>
                      <th style="text-align: center;">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="ep in stressResults.endpoints" :key="ep.endpoint">
                      <td style="font-family: monospace; font-size: 0.8rem;">{{ ep.endpoint }}</td>
                      <td style="text-align: right;">{{ ep.calls }}</td>
                      <td style="text-align: right; font-family: monospace;">{{ ep.p50.toFixed(3) }}s</td>
                      <td style="text-align: right; font-family: monospace;" :style="ep.p95 > 2 ? 'color: #ef4444' : ''">{{ ep.p95.toFixed(3) }}s</td>
                      <td style="text-align: right; font-family: monospace;" :style="ep.p99 > 2 ? 'color: #ef4444' : ''">{{ ep.p99.toFixed(3) }}s</td>
                      <td style="text-align: right;" :style="ep.errors > 0 ? 'color: #ef4444' : ''">{{ ep.errors }}</td>
                      <td style="text-align: center;">
                        <span :style="{ color: ep.passed ? '#22c55e' : '#ef4444', fontWeight: 600 }">{{ ep.passed ? 'PASS' : 'FAIL' }}</span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <!-- Summary -->
              <div style="margin-top: 0.75rem; display: flex; gap: 1rem; flex-wrap: wrap;">
                <div style="background: rgba(30,41,59,0.5); border-radius: 0.5rem; padding: 0.5rem 0.75rem; font-size: 0.8rem;">
                  Total: <strong>{{ stressResults.total_calls }}</strong> calls in <strong>{{ stressResults.duration_seconds }}s</strong>
                </div>
                <div :style="{ background: stressResults.error_rate_passed ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)', border: '1px solid ' + (stressResults.error_rate_passed ? 'rgba(34,197,94,0.3)' : 'rgba(239,68,68,0.3)'), borderRadius: '0.5rem', padding: '0.5rem 0.75rem', fontSize: '0.8rem' }">
                  {{ stressResults.error_rate_passed ? 'PASS' : 'FAIL' }} — Error rate: <strong>{{ stressResults.error_rate }}%</strong> (threshold: 5%)
                </div>
                <div :style="{ background: stressResults.all_thresholds_passed ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)', border: '1px solid ' + (stressResults.all_thresholds_passed ? 'rgba(34,197,94,0.3)' : 'rgba(239,68,68,0.3)'), borderRadius: '0.5rem', padding: '0.5rem 0.75rem', fontSize: '0.8rem' }">
                  {{ stressResults.all_thresholds_passed ? 'PASS' : 'FAIL' }} — {{ stressResults.all_thresholds_passed ? 'All endpoints within thresholds' : 'Some endpoints exceeded thresholds' }}
                </div>
                <div v-if="stressResults.prespawn_total" :style="{ background: stressResults.prespawn_pass ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)', border: '1px solid ' + (stressResults.prespawn_pass ? 'rgba(34,197,94,0.3)' : 'rgba(239,68,68,0.3)'), borderRadius: '0.5rem', padding: '0.5rem 0.75rem', fontSize: '0.8rem' }">
                  {{ stressResults.prespawn_pass ? 'PASS' : 'FAIL' }} — Pre-spawn: <strong>{{ stressResults.prespawn_succeeded }}/{{ stressResults.prespawn_total }}</strong> {{ stressResults.level === 4 ? 'RangeBoxes' : 'labs' }}
                  <span v-if="stressResults.prespawn_failed > 0" style="color: #eab308;"> ({{ stressResults.prespawn_failed }} failed)</span>
                </div>
                <div v-if="stressResults.host_cpu_pct != null" style="background: rgba(30,41,59,0.5); border-radius: 0.5rem; padding: 0.5rem 0.75rem; font-size: 0.8rem;">
                  Host CPU: <strong :style="stressResults.host_cpu_pct > 85 ? 'color: #ef4444' : ''">{{ stressResults.host_cpu_pct }}%</strong> &nbsp; Memory: <strong>{{ stressResults.host_mem_pct }}%</strong>
                </div>
              </div>
            </div>

            <!-- Terminal -->
            <div class="diagnostics-terminal">
              <div class="diagnostics-terminal-header">
                <span class="diagnostics-terminal-dot" :class="{ 'diagnostics-terminal-dot--active': stressRunning }"></span>
                <span class="diagnostics-terminal-label">ocr-stress-tester</span>
                <template v-if="stressRunning">
                  <span v-if="stressPhase" class="tester-phase-label" style="margin-left: 0.5rem; font-size: 0.7rem; color: #38bdf8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">
                    {{ stressPhase === 'prespawn' ? 'Pre-spawning' : stressPhase === 'timed' ? 'Testing' : stressPhase === 'cleanup' ? 'Cleaning up' : '' }}
                  </span>
                  <template v-if="stressProgressTotal > 0">
                    <span class="tester-progress-text">{{ stressProgressCompleted }}/{{ stressProgressTotal }}</span>
                    <div class="tester-progress-bar">
                      <div class="tester-progress-fill" :style="{ width: Math.round(stressProgressCompleted / stressProgressTotal * 100) + '%' }"></div>
                    </div>
                    <span class="tester-progress-pct">{{ Math.round(stressProgressCompleted / stressProgressTotal * 100) }}%</span>
                  </template>
                </template>
              </div>
              <div class="diagnostics-terminal-body" ref="stressTerminalRef" style="max-height: 400px;">
                <div v-if="!stressSections.length && !stressRunning" class="diagnostics-empty">
                  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#475569" stroke-width="1.5">
                    <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
                  </svg>
                  <p>Configure options and click <strong>Run Test</strong> to stress test the platform.</p>
                </div>

                <div v-for="(line, idx) in stressSections" :key="idx" class="diagnostics-line">
                  <span class="diagnostics-line-time">{{ line.timestamp }}</span>
                  <span class="diagnostics-line-level" :class="'diagnostics-level--' + line.level">
                    [{{ line.level === 'ok' ? 'PASS' : line.level === 'error' ? 'FAIL' : line.level === 'warning' ? 'WARN' : 'INFO' }}]
                  </span>
                  <span class="diagnostics-line-msg">{{ line.message }}</span>
                </div>

                <div v-if="stressRunning" class="diagnostics-cursor">_</div>
              </div>
            </div>
          </div>

        </div>

      </div>

      <!-- Create Track Modal -->
      <transition name="fade">
        <div v-if="showCreateTrackModal" class="modal-overlay" @click.self="showCreateTrackModal = false">
          <div class="modal">
            <h3 class="modal-title">Create Track</h3>
            <div class="form-group">
              <label>Name</label>
              <input aria-label="Name" v-model="trackForm.name" type="text" class="form-input" placeholder="e.g. Network Security" />
            </div>
            <div class="form-group">
              <label>Slug</label>
              <input aria-label="Slug" v-model="trackForm.slug" type="text" class="form-input" placeholder="e.g. network-security" />
            </div>
            <div class="form-group">
              <label>Description</label>
              <input aria-label="Description" v-model="trackForm.description" type="text" class="form-input" placeholder="Optional description" />
            </div>
            <div class="form-group">
              <label>Icon (emoji or class)</label>
              <input aria-label="Icon (emoji or class)" v-model="trackForm.icon" type="text" class="form-input" placeholder="e.g. shield" />
            </div>
            <div class="form-group">
              <label>Color</label>
              <input aria-label="Color" v-model="trackForm.color" type="color" class="color-input" />
            </div>
            <div class="modal-actions">
              <button @click="showCreateTrackModal = false" class="btn btn--secondary">Cancel</button>
              <button @click="createTrack" class="btn btn--success">Create</button>
            </div>
          </div>
        </div>
      </transition>

      <!-- Edit Track Modal -->
      <transition name="fade">
        <div v-if="showEditTrackModal" class="modal-overlay" @click.self="showEditTrackModal = false">
          <div class="modal">
            <h3 class="modal-title">Edit Track</h3>
            <div class="form-group">
              <label>Name</label>
              <input aria-label="Name" v-model="trackForm.name" type="text" class="form-input" />
            </div>
            <div class="form-group">
              <label>Description</label>
              <input aria-label="Description" v-model="trackForm.description" type="text" class="form-input" />
            </div>
            <div class="form-group">
              <label>Icon</label>
              <input aria-label="Icon" v-model="trackForm.icon" type="text" class="form-input" />
            </div>
            <div class="form-group">
              <label>Color</label>
              <input aria-label="Color" v-model="trackForm.color" type="color" class="color-input" />
            </div>
            <label class="checkbox-label">
              <input type="checkbox" v-model="trackForm.is_active" />
              <span>Active</span>
            </label>
            <div class="modal-actions">
              <button @click="showEditTrackModal = false" class="btn btn--secondary">Cancel</button>
              <button @click="updateTrack" class="btn btn--success">Save</button>
            </div>
          </div>
        </div>
      </transition>

      <!-- Create Level Modal -->
      <transition name="fade">
        <div v-if="showCreateLevelModal" class="modal-overlay" @click.self="showCreateLevelModal = false">
          <div class="modal">
            <h3 class="modal-title">Add Level to {{ levelFormTrack?.name }}</h3>
            <div class="form-group">
              <label>Name</label>
              <input aria-label="Name" v-model="levelForm.name" type="text" class="form-input" placeholder="e.g. Getting Started" />
            </div>
            <div class="form-group">
              <label>Description</label>
              <input aria-label="Description" v-model="levelForm.description" type="text" class="form-input" placeholder="Optional description" />
            </div>
            <div class="modal-actions">
              <button @click="showCreateLevelModal = false" class="btn btn--secondary">Cancel</button>
              <button @click="createLevel" class="btn btn--success">Create</button>
            </div>
          </div>
        </div>
      </transition>

      <!-- Edit Level Modal -->
      <transition name="fade">
        <div v-if="showEditLevelModal" class="modal-overlay" @click.self="showEditLevelModal = false">
          <div class="modal">
            <h3 class="modal-title">Edit Level</h3>
            <div class="form-group">
              <label>Name</label>
              <input aria-label="Name" v-model="levelForm.name" type="text" class="form-input" />
            </div>
            <div class="form-group">
              <label>Description</label>
              <input aria-label="Description" v-model="levelForm.description" type="text" class="form-input" />
            </div>
            <div class="modal-actions">
              <button @click="showEditLevelModal = false" class="btn btn--secondary">Cancel</button>
              <button @click="updateLevel" class="btn btn--success">Save</button>
            </div>
          </div>
        </div>
      </transition>

      <!-- Disk Management Modal -->
      <transition name="fade">
        <div v-if="showDiskModal" class="modal-overlay" @click.self="showDiskModal = false">
          <div class="modal modal--large">
            <h3 class="modal-title">Disk Management</h3>
            <p class="modal-subtitle">Docker images, build cache, and disk usage</p>

            <div v-if="diskUsageLoading" style="text-align: center; padding: 2rem; color: rgba(255,255,255,0.5);">
              Loading disk usage...
            </div>
            <div v-else-if="diskUsage" class="disk-usage-grid">
              <div class="disk-card">
                <div class="disk-card__label">Images</div>
                <div class="disk-card__value">{{ formatBytes(diskUsage.images.total_bytes) }}</div>
                <div class="disk-card__detail">{{ diskUsage.images.count }} images &middot; {{ formatBytes(diskUsage.images.reclaimable_bytes) }} reclaimable</div>
              </div>
              <div class="disk-card">
                <div class="disk-card__label">Build Cache</div>
                <div class="disk-card__value">{{ formatBytes(diskUsage.build_cache.total_bytes) }}</div>
                <div class="disk-card__detail">{{ diskUsage.build_cache.count }} entries &middot; {{ formatBytes(diskUsage.build_cache.reclaimable_bytes) }} reclaimable</div>
              </div>
              <div class="disk-card">
                <div class="disk-card__label">Containers</div>
                <div class="disk-card__value">{{ formatBytes(diskUsage.containers.total_bytes) }}</div>
                <div class="disk-card__detail">{{ diskUsage.containers.count }} containers</div>
              </div>
              <div class="disk-card">
                <div class="disk-card__label">Volumes</div>
                <div class="disk-card__value">{{ formatBytes(diskUsage.volumes.total_bytes) }}</div>
                <div class="disk-card__detail">{{ diskUsage.volumes.count }} volumes &middot; {{ formatBytes(diskUsage.volumes.reclaimable_bytes) }} reclaimable</div>
              </div>
            </div>

            <div style="margin-top: 1.25rem; display: flex; flex-direction: column; gap: 0.75rem;">
              <div class="disk-action-row">
                <div>
                  <strong>Prune Unused Images</strong>
                  <div class="disk-action-desc">Remove all images not used by running containers. Exercises rebuild on next launch.</div>
                </div>
                <button @click="pruneImages" :disabled="pruningImages" class="btn btn--danger btn--sm">
                  {{ pruningImages ? 'Pruning...' : 'Prune Images' }}
                </button>
              </div>
              <div class="disk-action-row">
                <div>
                  <strong>Prune Build Cache</strong>
                  <div class="disk-action-desc">Remove cached build layers. Future builds will take longer as layers rebuild from scratch.</div>
                </div>
                <button @click="pruneBuildCache" :disabled="pruningBuildCache" class="btn btn--danger btn--sm">
                  {{ pruningBuildCache ? 'Pruning...' : 'Prune Cache' }}
                </button>
              </div>
            </div>

            <div class="modal-actions">
              <button @click="showDiskModal = false" class="btn btn--secondary">Close</button>
              <button @click="fetchDiskUsage" class="btn btn--primary" :disabled="diskUsageLoading">Refresh</button>
            </div>
          </div>
        </div>
      </transition>

      <!-- Create Lab Modal -->
      <transition name="fade">
        <div v-if="showCreateLabModal" class="modal-overlay" @click.self="showCreateLabModal = false">
          <div class="modal modal--xlarge">
            <h3 class="modal-title">Create Exercise</h3>

            <!-- Mode tabs -->
            <div class="create-lab-tabs">
              <button @click="createLabMode = 'yaml'" :class="['create-lab-tab', { active: createLabMode === 'yaml' }]">Import from YAML</button>
              <button @click="createLabMode = 'manual'" :class="['create-lab-tab', { active: createLabMode === 'manual' }]">Manual Entry</button>
            </div>

            <!-- YAML Import Mode -->
            <div v-if="createLabMode === 'yaml'" class="create-lab-yaml-mode">
              <div class="create-lab-yaml-grid">
                <div class="create-lab-yaml-col">
                  <div class="form-group">
                    <label>Lab YAML <span class="label-hint">Paste your complete lab.yaml</span></label>
                    <textarea v-model="createLabForm.lab_yaml" @blur="parseLabYaml" class="form-input compose-textarea" rows="16" placeholder="name: Exercise Name
description: ...
difficulty: beginner
category: enumeration
flag: &quot;OCR{...}&quot;
objectives:
  - First objective
scenario: |
  Your scenario text...
hints:
  - text: |
      First hint
    unlock_after_minutes: 10
test:
  steps:
    - name: Step 1
      command: curl ...
      expect: OCR{"></textarea>
                    <div v-if="yamlParseError" class="yaml-parse-error">{{ yamlParseError }}</div>
                  </div>
                </div>
                <div class="create-lab-yaml-col">
                  <div class="form-group">
                    <label>Docker Compose YAML <span class="label-hint">Paste your docker-compose.yml</span></label>
                    <textarea v-model="createLabForm.compose_file" class="form-input compose-textarea" rows="16" placeholder="services:
  target:
    build:
      context: ./containers/target
      dockerfile: Dockerfile
    hostname: target-host
    labels:
      ip_offset: &quot;10&quot;
    restart: unless-stopped"></textarea>
                  </div>
                </div>
              </div>

              <!-- Parsed YAML preview -->
              <div v-if="yamlParsed" class="yaml-preview">
                <div class="yaml-preview__title">Parsed from YAML</div>
                <div class="yaml-preview__grid">
                  <span v-if="yamlParsed.name" class="yaml-preview__tag">{{ yamlParsed.name }}</span>
                  <span v-if="yamlParsed.difficulty" class="yaml-preview__tag">{{ yamlParsed.difficulty }}</span>
                  <span v-if="yamlParsed.category" class="yaml-preview__tag">{{ yamlParsed.category }}</span>
                  <span v-if="yamlParsed.duration_minutes" class="yaml-preview__tag">{{ yamlParsed.duration_minutes }} min</span>
                  <span v-if="yamlParsed.flag" class="yaml-preview__tag yaml-preview__tag--flag">Flag detected</span>
                  <span v-if="yamlParsed.visibility" class="yaml-preview__tag">{{ yamlParsed.visibility }}</span>
                  <span v-if="yamlParsed.objectives_count" class="yaml-preview__tag">{{ yamlParsed.objectives_count }} objectives</span>
                  <span v-if="yamlParsed.hints_count" class="yaml-preview__tag">{{ yamlParsed.hints_count }} hints</span>
                  <span v-if="yamlParsed.test_steps_count" class="yaml-preview__tag yaml-preview__tag--test">{{ yamlParsed.test_steps_count }} test steps</span>
                  <span v-if="yamlParsed.scenario" class="yaml-preview__tag">Scenario included</span>
                </div>
              </div>

              <!-- Required overrides for YAML mode -->
              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-top: 0.75rem;">
                <div class="form-group">
                  <label>Slug <span class="label-hint">Required</span></label>
                  <input v-model="createLabForm.slug" type="text" class="form-input" placeholder="track-level-num-name" />
                </div>
                <div class="form-group">
                  <label>Level <span class="label-hint">Optional</span></label>
                  <select v-model="createLabForm.level_id" class="form-input">
                    <option :value="null">-- No level --</option>
                    <template v-for="track in curriculumTracks" :key="track.id">
                      <option v-for="level in track.levels" :key="level.id" :value="level.id">
                        {{ track.name }} &rarr; Level {{ level.level_number }}: {{ level.name }}
                      </option>
                    </template>
                  </select>
                </div>
              </div>
            </div>

            <!-- Manual Entry Mode -->
            <div v-if="createLabMode === 'manual'">
              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
                <div class="form-group">
                  <label>Name</label>
                  <input aria-label="Name" v-model="createLabForm.name" type="text" class="form-input" placeholder="Exercise name" />
                </div>
                <div class="form-group">
                  <label>Slug</label>
                  <input aria-label="Slug" v-model="createLabForm.slug" type="text" class="form-input" placeholder="track-level-num-name" />
                </div>
                <div class="form-group">
                  <label>Difficulty</label>
                  <select aria-label="Difficulty" v-model="createLabForm.difficulty" class="form-input">
                    <option value="beginner">Beginner</option>
                    <option value="intermediate">Intermediate</option>
                    <option value="advanced">Advanced</option>
                  </select>
                </div>
                <div class="form-group">
                  <label>Duration (min)</label>
                  <input aria-label="Duration (min)" v-model.number="createLabForm.duration_minutes" type="number" class="form-input" />
                </div>
                <div class="form-group">
                  <label>Category</label>
                  <input aria-label="Category" v-model="createLabForm.category" type="text" class="form-input" placeholder="enumeration, web, network..." />
                </div>
                <div class="form-group">
                  <label>Visibility</label>
                  <select aria-label="Visibility" v-model="createLabForm.visibility" class="form-input">
                    <option value="public">Public</option>
                    <option value="course">Course Only</option>
                    <option value="draft">Draft</option>
                  </select>
                </div>
                <div class="form-group">
                  <label>Flag</label>
                  <input aria-label="Flag" v-model="createLabForm.flag" type="text" class="form-input" placeholder="OCR{...}" />
                </div>
                <div class="form-group">
                  <label>Level</label>
                  <select aria-label="Level" v-model="createLabForm.level_id" class="form-input">
                    <option :value="null">-- No level --</option>
                    <template v-for="track in curriculumTracks" :key="track.id">
                      <option v-for="level in track.levels" :key="level.id" :value="level.id">
                        {{ track.name }} &rarr; Level {{ level.level_number }}: {{ level.name }}
                      </option>
                    </template>
                  </select>
                </div>
              </div>
              <div class="form-group">
                <label>Description</label>
                <textarea aria-label="Description" v-model="createLabForm.description" class="form-input" rows="2" placeholder="Brief exercise description"></textarea>
              </div>
              <div class="form-group">
                <label>Scenario <span class="label-hint">Immersive narrative shown to students</span></label>
                <textarea v-model="createLabForm.scenario" class="form-input" rows="4" placeholder="You've been hired by ACME Corp to assess..."></textarea>
              </div>
              <div class="form-group">
                <label>Docker Compose YAML</label>
                <textarea aria-label="Docker Compose YAML" v-model="createLabForm.compose_file" class="form-input compose-textarea" rows="8" placeholder="services:
  target:
    build: ..."></textarea>
              </div>
            </div>

            <div class="modal-actions">
              <button @click="showCreateLabModal = false" class="btn btn--secondary">Cancel</button>
              <button @click="createNewLab" class="btn btn--success">Create Exercise</button>
            </div>
          </div>
        </div>
      </transition>

      <!-- Edit Exercise Modal (Details + Compose tabs) -->
      <transition name="fade">
        <div v-if="showLabEditModal" class="modal-overlay" @click.self="showLabEditModal = false">
          <div class="modal modal--large">
            <h3 class="modal-title">Edit Exercise</h3>
            <p class="modal-subtitle">{{ editLab?.name }}</p>
            <div class="lab-edit-tabs">
              <button :class="['lab-edit-tab', { 'lab-edit-tab--active': labEditTab === 'details' }]" @click="labEditTab = 'details'">Details</button>
              <button :class="['lab-edit-tab', { 'lab-edit-tab--active': labEditTab === 'compose' }]" @click="labEditTab = 'compose'">Compose</button>
            </div>
            <div v-if="labEditTab === 'details'" class="form-stack">
              <div class="form-group">
                <label class="form-label">Name</label>
                <input aria-label="Name" v-model="editLab.name" placeholder="Exercise name" class="form-input">
              </div>
              <div class="form-group">
                <label class="form-label">Duration (minutes)</label>
                <input aria-label="Duration (minutes)" v-model="editLab.duration_minutes" type="number" placeholder="60" class="form-input">
              </div>
              <div class="form-group">
                <label class="form-label">Difficulty</label>
                <select aria-label="Difficulty" v-model="editLab.difficulty" class="form-input">
                  <option value="beginner">Beginner</option>
                  <option value="intermediate">Intermediate</option>
                  <option value="advanced">Advanced</option>
                </select>
              </div>
              <div class="form-group">
                <label class="form-label">Track</label>
                <select aria-label="Track" v-model="editTrackId" @change="onEditTrackChange" class="form-input">
                  <option :value="null">Course Assessments (no track)</option>
                  <option v-for="t in trackCatalog" :key="t.id" :value="t.id">{{ t.name }}</option>
                </select>
              </div>
              <div v-if="editTrackId" class="form-group">
                <label class="form-label">Level</label>
                <select aria-label="Level" v-model="editLab.level_id" class="form-input">
                  <option :value="null">Select a level...</option>
                  <option v-for="lv in editLevelOptions" :key="lv.id" :value="lv.id">
                    Level {{ lv.level_number }} - {{ lv.name }}
                  </option>
                </select>
              </div>
              <!-- Answer key. Masked until asked for, so it is not on screen
                   when the admin panel is being projected to a room. -->
              <div class="form-group">
                <label class="form-label">Flag</label>
                <div class="flag-reveal">
                  <button
                    v-if="!revealedFlag"
                    @click="revealFlag(editLab.id)"
                    class="btn btn--secondary btn--sm"
                    :disabled="flagRevealLoading"
                  >{{ flagRevealLoading ? 'Loading...' : 'Reveal flag' }}</button>
                  <template v-else>
                    <code class="flag-reveal__value">{{ revealedFlag.flag || 'not set in lab.yaml' }}</code>
                    <button
                      v-if="revealedFlag.flag"
                      @click="copyFlag"
                      class="btn btn--secondary btn--sm"
                    >{{ flagCopied ? 'Copied' : 'Copy' }}</button>
                    <button @click="revealedFlag = null" class="btn btn--secondary btn--sm">Hide</button>
                  </template>
                </div>
                <p v-if="revealedFlag && revealedFlag.message" class="flag-reveal__note">
                  {{ revealedFlag.message }}
                </p>
                <p v-if="flagRevealError" class="flag-reveal__note flag-reveal__note--error">
                  {{ flagRevealError }}
                </p>
              </div>
            </div>
            <div v-if="labEditTab === 'compose'" class="form-group">
              <label class="form-label">Docker Compose</label>
              <textarea aria-label="Docker Compose" v-model="editLab.compose_file" class="form-input compose-textarea" rows="20" placeholder="docker-compose.yml content"></textarea>
            </div>
            <div class="modal-actions">
              <button @click="showLabEditModal = false" class="btn btn--secondary">Cancel</button>
              <button @click="saveLabEdit" class="btn btn--primary">Save Changes</button>
            </div>
          </div>
        </div>
      </transition>

      <!-- Edit User Modal -->
      <transition name="fade">
        <div v-if="showEditUserModal" class="modal-overlay" @click.self="showEditUserModal = false">
          <div class="modal modal--large">
            <h3 class="modal-title">Edit User: {{ editUser?.username }}</h3>
            
            <form @submit.prevent="saveUserEdits" class="edit-user-form">
              <div class="form-section">
                <h4 class="section-title">Account Information</h4>
                
                <div class="form-group">
                  <label for="edit-username">Username</label>
                  <input aria-label="Username"
                    id="edit-username"
                    v-model="editForm.username"
                    type="text"
                    placeholder="Username"
                    class="form-input"
                    :class="{ 'error': editErrors.username }"
                  />
                  <p v-if="editErrors.username" class="error-text">{{ editErrors.username }}</p>
                </div>

                <div class="form-group">
                  <label for="edit-email">Email</label>
                  <input aria-label="Email"
                    id="edit-email"
                    v-model="editForm.email"
                    type="email"
                    placeholder="Email"
                    class="form-input"
                    :class="{ 'error': editErrors.email }"
                  />
                  <p v-if="editErrors.email" class="error-text">{{ editErrors.email }}</p>
                </div>

                <div class="form-group">
                  <label for="edit-password">New Password (leave blank to keep current)</label>
                  <input aria-label="New Password (leave blank to keep current)"
                    id="edit-password"
                    v-model="editForm.password"
                    type="password"
                    placeholder="New password"
                    class="form-input"
                    :class="{ 'error': editErrors.password }"
                  />
                  <p v-if="editErrors.password" class="error-text">{{ editErrors.password }}</p>
                </div>

                <div class="form-group">
                  <label for="edit-confirm-password">Confirm New Password</label>
                  <input aria-label="Confirm New Password"
                    id="edit-confirm-password"
                    v-model="editForm.confirmPassword"
                    type="password"
                    placeholder="Confirm new password"
                    class="form-input"
                    :class="{ 'error': editErrors.confirmPassword }"
                  />
                  <p v-if="editErrors.confirmPassword" class="error-text">{{ editErrors.confirmPassword }}</p>
                </div>
              </div>

              <div class="form-section">
                <h4 class="section-title">Account Status</h4>
                
                <div class="checkbox-group">
                  <label class="checkbox-label">
                    <input
                      v-model="editForm.is_approved"
                      type="checkbox"
                      class="checkbox-input"
                    />
                    <span>Approved</span>
                  </label>

                  <div class="form-group form-group--inline">
                    <label>Role</label>
                    <select aria-label="Role" v-model="editForm.role" class="form-select">
                      <option value="student">Student</option>
                      <option value="instructor">Instructor</option>
                      <option value="admin">Admin</option>
                    </select>
                  </div>

                  <label class="checkbox-label">
                    <input
                      v-model="editForm.is_active"
                      type="checkbox"
                      class="checkbox-input"
                    />
                    <span>Active</span>
                  </label>

                  <label class="checkbox-label">
                    <input
                      v-model="editForm.must_change_password"
                      type="checkbox"
                      class="checkbox-input"
                    />
                    <span>Force password change on next login</span>
                  </label>
                </div>
              </div>

              <p v-if="editErrorMessage" class="error-message">{{ editErrorMessage }}</p>
              <p v-if="editSuccessMessage" class="success-message">{{ editSuccessMessage }}</p>

              <div class="modal-actions">
                <button type="button" @click="showEditUserModal = false" class="btn btn--secondary">Cancel</button>
                <button type="submit" :disabled="editLoading" class="btn btn--primary">
                  <span v-if="editLoading">Saving...</span>
                  <span v-else>Save Changes</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      </transition>


      <!-- User Details Modal -->
      <transition name="fade">
        <div v-if="showUserDetailsModal" class="modal-overlay" @click.self="showUserDetailsModal = false">
          <div class="modal modal--large">
            <h3 class="modal-title">User Details: {{ userDetails?.username }}</h3>
            
            <div v-if="loadingUserDetails" class="loading-state">
              <p>Loading user details...</p>
            </div>
            
            <div v-else-if="userDetails" class="user-details-content">
              <!-- User Information Section -->
              <div class="form-section">
                <h4 class="section-title">Account Information</h4>
                <div class="info-grid">
                  <div class="info-item">
                    <span class="info-label">Username:</span>
                    <span class="info-value">{{ userDetails.username }}</span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">Email:</span>
                    <span class="info-value">{{ userDetails.email }}</span>
                  </div>
                  <div class="info-item" v-if="userDetails.student_id">
                    <span class="info-label">Student ID:</span>
                    <span class="info-value">{{ userDetails.student_id }}</span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">Role:</span>
                    <span class="info-value">
                      <span v-if="userDetails.role === 'admin'" class="status-badge status-badge--admin">Admin</span>
                      <span v-else-if="userDetails.role === 'instructor'" class="status-badge status-badge--instructor">Instructor</span>
                      <span v-else class="status-badge status-badge--approved">Student</span>
                    </span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">Status:</span>
                    <span class="info-value">
                      <span v-if="userDetails.is_locked" class="status-badge status-badge--locked">Locked</span>
                      <span v-else-if="!userDetails.is_approved" class="status-badge status-badge--pending">Pending</span>
                      <span v-else class="status-badge status-badge--approved">Active</span>
                    </span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">VPN Registered:</span>
                    <span class="info-value">
                      <span v-if="userDetails.vpn_registered" class="status-badge status-badge--approved">Yes</span>
                      <span v-else class="status-badge status-badge--pending">No</span>
                    </span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">Account Created:</span>
                    <span class="info-value">{{ formatDate(userDetails.created_at) }}</span>
                  </div>
                </div>
              </div>

              <!-- Statistics Section -->
              <div class="form-section">
                <h4 class="section-title">Statistics</h4>
                <div class="stats-grid">
                  <div class="stat-item">
                    <span class="stat-label">Exercises Completed</span>
                    <span class="stat-value">{{ userDetails.total_labs_completed }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">Total Flag Attempts</span>
                    <span class="stat-value">{{ userDetails.total_flag_attempts }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">Total Hints Used</span>
                    <span class="stat-value">{{ userDetails.total_hints_used }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">Avg Time per Exercise</span>
                    <span class="stat-value">
                      {{ userDetails.average_time_per_lab ? `${userDetails.average_time_per_lab} min` : 'N/A' }}
                    </span>
                  </div>
                </div>
              </div>

              <!-- Active Sessions Section -->
              <div class="form-section" v-if="userDetails.active_sessions && userDetails.active_sessions.length > 0">
                <h4 class="section-title">Active Sessions</h4>
                <div class="table-container">
                  <table class="data-table data-table--compact">
                    <thead>
                      <tr>
                        <th>Exercise</th>
                        <th>Started</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="session in userDetails.active_sessions" :key="session.id">
                        <td>{{ session.lab_name }}</td>
                        <td>{{ formatDate(session.started_at) }}</td>
                        <td>
                          <span class="session-status session-status--running">{{ session.status }}</span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <!-- Completed Labs Section -->
              <div class="form-section">
                <h4 class="section-title">Completed Exercises</h4>
                <div v-if="!userDetails.completions || userDetails.completions.length === 0" class="empty-state">
                  <p>No exercises completed yet</p>
                </div>
                <div v-else class="table-container">
                  <table class="data-table">
                    <thead>
                      <tr>
                        <th>Exercise Name</th>
                        <th>Track</th>
                        <th>Level</th>
                        <th>Completed</th>
                        <th>Attempts</th>
                        <th>Hints</th>
                        <th>Time</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="completion in userDetails.completions" :key="completion.lab_id">
                        <td class="cell-primary">{{ completion.lab_name }}</td>
                        <td>{{ completion.track_name || '-' }}</td>
                        <td>{{ completion.level_number || '-' }}</td>
                        <td>{{ formatDate(completion.completed_at) }}</td>
                        <td>{{ completion.attempts }}</td>
                        <td>{{ completion.hints_used }}</td>
                        <td>{{ completion.time_spent_minutes ? `${completion.time_spent_minutes} min` : '-' }}</td>
                        <td class="cell-actions">
                          <button 
                            @click="resetLabForUser(userDetails.id, completion.lab_id, completion.lab_name)"
                            class="btn btn--secondary btn--sm"
                            :disabled="resettingLab"
                            title="Reset this exercise for the user"
                          >
                            Reset
                          </button>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            <div class="modal-actions">
              <button @click="showUserDetailsModal = false" class="btn btn--secondary">Close</button>
            </div>
          </div>
        </div>
      </transition>

      <!-- Launch As Student Modal -->
      <transition name="fade">
        <div v-if="showLaunchAsModal" class="modal-overlay" @click.self="showLaunchAsModal = false">
          <div class="modal">
            <h3 class="modal-title">Launch Lab As Student</h3>
            <p class="modal-subtitle">Start a lab environment under a student's account. The session will be marked as admin-initiated and your RangeBox will be bridged to their network.</p>

            <div class="form-group">
              <label class="form-label">Student</label>
              <select aria-label="Student" v-model="launchAsForm.userId" class="form-input">
                <option value="">Select a student...</option>
                <option
                  v-for="u in launchAsStudentList"
                  :key="u.id"
                  :value="u.id"
                >{{ u.username }} ({{ u.email }})</option>
              </select>
            </div>

            <div class="form-group">
              <label class="form-label">Lab Exercise</label>
              <select aria-label="Lab Exercise" v-model="launchAsForm.labSlug" class="form-input">
                <option value="">Select a lab...</option>
                <option
                  v-for="l in launchAsLabList"
                  :key="l.slug"
                  :value="l.slug"
                >{{ l.name }}</option>
              </select>
            </div>

            <div v-if="launchAsError" class="alert alert--error" style="margin-bottom: 1rem;">
              {{ launchAsError }}
            </div>

            <div class="modal-actions">
              <button @click="showLaunchAsModal = false" class="btn btn--secondary">Cancel</button>
              <button
                @click="launchAsStudent"
                class="btn impersonate-btn"
                :disabled="!launchAsForm.userId || !launchAsForm.labSlug || launchAsLoading"
                style="background: rgba(139, 92, 246, 0.15); border: 1px solid #8b5cf6; color: #8b5cf6;"
              >
                {{ launchAsLoading ? 'Launching...' : 'Launch' }}
              </button>
            </div>
          </div>
        </div>
      </transition>
    </div>
  </div>
</template>

<script setup>
import InfoTip from '../components/InfoTip.vue'
import Toast, { showToast } from '../components/Toast.vue'
import AdminPendingTab from '../components/AdminPendingTab.vue'
import { ref, reactive, onMounted, onUnmounted, computed, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from '../api/axios'
import { useModules } from '../composables/useModules'
import { usePrivacy } from '../composables/usePrivacy'

const route = useRoute()
const router = useRouter()
const { privacyMode, maskUsername, maskEmail } = usePrivacy()

const legacyTabMap = { sessions: 'monitoring', vpn: 'monitoring', activity: 'monitoring', labs: 'exercises', curriculum: 'exercises', tester: 'system' }
const legacySubTabMap = { sessions: 'sessions', vpn: 'vpn', activity: 'activity', labs: 'manage', curriculum: 'tracks' }
const validTabs = ['users', 'pending', 'courses', 'exercises', 'monitoring', 'settings', 'system']

const monitoringSubTab = ref('sessions')

// Stress Tester state
const stressLevel = ref(1)
const stressUsers = ref(45)
const stressConcurrentSpawns = ref(5)
const stressRunning = ref(false)
const stressRunId = ref(null)
const stressSections = ref([])
const stressResults = ref(null)
const stressTerminalRef = ref(null)
const stressProgressCompleted = ref(0)
const stressProgressTotal = ref(0)
const stressPhase = ref(null)

const serverResources = ref(null)
// CPU: actual load as percentage of total cores
const cpuUsagePct = computed(() => {
  if (!serverResources.value || !serverResources.value.host_cpu_cores) return 0
  return Math.min(100, Math.round(serverResources.value.host_load_1m / serverResources.value.host_cpu_cores * 100))
})
// RAM: actual used memory as percentage of total
const ramUsagePct = computed(() => {
  if (!serverResources.value || !serverResources.value.host_ram_gb) return 0
  const used = serverResources.value.host_ram_gb - serverResources.value.host_available_ram_gb
  return Math.min(100, Math.round(used / serverResources.value.host_ram_gb * 100))
})
const cpuBarClass = computed(() => cpuUsagePct.value > 80 ? 'resource-summary__bar--warn' : cpuUsagePct.value > 50 ? 'resource-summary__bar--mid' : 'resource-summary__bar--ok')
const ramBarClass = computed(() => ramUsagePct.value > 85 ? 'resource-summary__bar--warn' : ramUsagePct.value > 65 ? 'resource-summary__bar--mid' : 'resource-summary__bar--ok')
const provisionRunning = ref(false)
const provisionRunId = ref(null)
const setupRunningVms = ref(new Set())
const provisionVmName = ref('')
const provisionStep = ref(0)
const provisionStepLabel = ref('')
const provisionSections = ref([])
const provisionTerminalRef = ref(null)

// Multi-terminal state: each VM gets its own terminal panel
// Key = vm container name, value = { displayName, runId, status, step, totalSteps, stepLabel, lines, eventSource }
const vmTerminals = ref({})
const vmTerminalRefs = ref({})
const showVmLogsModal = ref(false)
const vmLogsName = ref('')
const vmLogsContent = ref('')

const soImport = ref({ building: false, running: false, iso_default: '' })
const soIso = ref('')
const soFlyoutOpen = ref(false)
const soBusy = ref(false)
const fetchSoStatus = async () => {
  try {
    const { data } = await axios.get('/admin/so-import/status')
    soImport.value = data
    if (!soIso.value) soIso.value = data.iso_default || ''
  } catch (e) { /* not a SOC edition */ }
}
const openSoSetup = () => {
  soFlyoutOpen.value = true
  // Auto-populate with the backend's default (a discovered ISO, an env override,
  // or a suggested path) so the operator can accept it as-is or pick another.
  fetchSoStatus().then(() => {
    if (!soIso.value) soIso.value = soImport.value.iso_default || ''
  })
}

const buildStartedAt = reactive({})
const nowTick = ref(Date.now())
let _buildTicker = null
function _buildPhase(name, phases) {
  const term = vmTerminals.value[name]
  const text = ((term && term.lines) ? term.lines : []).map(l => (l && l.message) ? l.message : '').join('\n')
  let idx = 0
  for (let i = phases.length - 1; i >= 0; i--) { if (phases[i].re.test(text)) { idx = i; break } }
  return { ...phases[idx], index: idx }
}
function buildElapsed(name) {
  const start = buildStartedAt[name]
  if (!start) return ''
  const s = Math.max(0, Math.floor((nowTick.value - start) / 1000))
  return `${Math.floor(s / 60)}m ${String(s % 60).padStart(2, '0')}s`
}
watch(() => soImport.value.building, (b) => {
  if (b && !buildStartedAt['so-import']) buildStartedAt['so-import'] = Date.now()
  if (!b) delete buildStartedAt['so-import']
})
onMounted(() => { _buildTicker = setInterval(() => { nowTick.value = Date.now() }, 1000) })
onUnmounted(() => { if (_buildTicker) clearInterval(_buildTicker) })

// VM Definition CRUD state
const vmDefinitions = ref([])
const showVmDefPanel = ref(false)
const editingVmDefId = ref(null)
const editingVmIsActive = ref(false)
const vmDefSaving = ref(false)
const vmDefForm = reactive({
  container_name: '',
  display_name: '',
  description: '',
  vm_type: 'windows',
  os_version: '',
  image: '',
  ram: '4G',
  cpu_cores: '2',
  subnet: '',
  forward_ports: '',
  local_iso: '',
  setup_script: '',
  setup_script_container_path: '',
  shared_volume_host: '',
  shared_volume_container: '/storage/shared',
  two_phase: false,
  committed_tag: 'configured',
  winrm_user: '',
  winrm_pass: '',
  docker_command: '',
  environment_vars: '',
  extra_volumes: '',
  extra_cap_add: '',
  health_check_port: null,
  is_enabled: true,
})

const exercisesSubTab = ref('manage')
const systemSubTab = ref('health')

// Workbook management state
const workbookChapters = ref([])
const workbookChaptersLoading = ref(false)
const workbookUploading = ref(false)
const workbookBuilding = ref(false)
const workbookUploadDir = ref('')
const workbookUploadSection = ref('Course Weekly Challenges')
const workbookFile = ref(null)
const workbookFileInput = ref(null)
const workbookUploadResult = ref(null)
const workbookBuildResult = ref(null)
const expandedChapter = ref(null)

function handleWorkbookFileSelect(e) {
  workbookFile.value = e.target.files?.[0] || null
}

function toggleChapterExpand(dir) {
  expandedChapter.value = expandedChapter.value === dir ? null : dir
}

async function loadWorkbookChapters() {
  workbookChaptersLoading.value = true
  try {
    const res = await axios.get('/api/admin/workbook/chapters')
    workbookChapters.value = res.data
  } catch (e) {
    console.error('Failed to load workbook chapters:', e)
    workbookChapters.value = []
  } finally {
    workbookChaptersLoading.value = false
  }
}

async function uploadWorkbook() {
  if (!workbookFile.value || !workbookUploadDir.value) return
  workbookUploading.value = true
  workbookUploadResult.value = null
  workbookBuildResult.value = null
  try {
    const form = new FormData()
    form.append('file', workbookFile.value)
    form.append('chapter_dir', workbookUploadDir.value)
    form.append('section_name', workbookUploadSection.value)
    form.append('auto_build', 'true')
    const res = await axios.post('/api/admin/workbook/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    workbookUploadResult.value = res.data
    // Reset file input
    workbookFile.value = null
    if (workbookFileInput.value) workbookFileInput.value.value = ''
    await loadWorkbookChapters()
  } catch (e) {
    workbookUploadResult.value = { warnings: [e.response?.data?.detail || e.message] }
  } finally {
    workbookUploading.value = false
  }
}

async function triggerWorkbookBuild() {
  workbookBuilding.value = true
  workbookBuildResult.value = null
  workbookUploadResult.value = null
  try {
    const res = await axios.post('/api/admin/workbook/build')
    workbookBuildResult.value = res.data
  } catch (e) {
    workbookBuildResult.value = { success: false, output: e.response?.data?.detail || e.message, duration_seconds: 0 }
  } finally {
    workbookBuilding.value = false
  }
}

async function deleteWorkbookChapter(dir) {
  if (!confirm(`Delete chapter "${dir}" and all its files? This cannot be undone.`)) return
  try {
    await axios.delete(`/api/admin/workbook/chapter/${encodeURIComponent(dir)}`)
    await loadWorkbookChapters()
  } catch (e) {
    // Was a bare alert(), which threw at runtime because the old local
    // `alert` reactive shadowed window.alert in this scope.
    showAlert('Delete failed: ' + (e.response?.data?.detail || e.message), 'error')
  }
}

function resolveTab(tab) {
  if (tab && legacyTabMap[tab]) {
    if (tab === 'sessions' || tab === 'vpn' || tab === 'activity') monitoringSubTab.value = legacySubTabMap[tab]
    if (tab === 'labs' || tab === 'curriculum') exercisesSubTab.value = legacySubTabMap[tab]
    if (tab === 'tester') systemSubTab.value = 'tester'
    return legacyTabMap[tab]
  }
  return tab
}

const initTab = resolveTab(route.query.tab)
const activeTab = ref(validTabs.includes(initTab) ? initTab : 'users')

// Sync tab from route query param (e.g. /admin?tab=labs)
watch(() => route.query.tab, (newTab) => {
  const resolved = resolveTab(newTab)
  if (resolved && validTabs.includes(resolved)) {
    activeTab.value = resolved
  }
})
const stats = ref({ total_users: 0, pending_users: 0, locked_users: 0, active_labs: 0, vpn_registered: 0 })
const users = ref([])
const pendingUsers = ref([])
const userSearch = ref('')
const userStatusFilter = ref('')
const userRoleFilter = ref('')
const userPage = ref(1)
const usersPerPage = 25

const filteredUsers = computed(() => {
  let list = users.value
  if (userSearch.value) {
    const q = userSearch.value.toLowerCase()
    list = list.filter(u => u.username.toLowerCase().includes(q) || (u.email && u.email.toLowerCase().includes(q)))
  }
  if (userStatusFilter.value) {
    switch (userStatusFilter.value) {
      case 'locked': list = list.filter(u => u.is_locked); break
      case 'pending': list = list.filter(u => !u.is_approved && u.is_active); break
      case 'active': list = list.filter(u => u.is_active && u.is_approved && !u.is_locked); break
      case 'disabled': list = list.filter(u => !u.is_active); break
    }
  }
  if (userRoleFilter.value) {
    list = list.filter(u => u.role === userRoleFilter.value)
  }
  return list
})

const userTotalPages = computed(() => Math.ceil(filteredUsers.value.length / usersPerPage))

const paginatedUsers = computed(() => {
  const start = (userPage.value - 1) * usersPerPage
  return filteredUsers.value.slice(start, start + usersPerPage)
})

// Reset to page 1 when filters change
watch([userSearch, userStatusFilter, userRoleFilter], () => { userPage.value = 1 })
const labs = ref([])
const activeSessions = ref([])
const sessionHistory = ref([])
const sessionsHealth = ref({ total_sessions: 0, sessions: [] })
const loadingHealth = ref(false)
const vpnPeers = ref([])
const vpnStatus = ref({ registered_count: 0, unregistered_count: 0, registered: [], unregistered: [] })
const vpnTimeRange = ref('24h')
const vpnCustomStart = ref('')
const vpnCustomEnd = ref('')

const sessionsTimeRange = ref('24h')
const sessionsCustomStart = ref('')
const sessionsCustomEnd = ref('')
const sessionHistoryPage = ref(1)
const sessionHistoryTotal = ref(0)
const sessionHistoryPages = ref(0)
const sessionHistoryLoading = ref(false)

const activityTimeRange = ref('')
const activityCustomStart = ref('')
const activityCustomEnd = ref('')

const sortByHandshakeDesc = (peers) => {
  return [...peers].sort((a, b) => {
    const tsA = a.last_handshake_raw ? new Date(a.last_handshake_raw).getTime() : 0
    const tsB = b.last_handshake_raw ? new Date(b.last_handshake_raw).getTime() : 0
    return tsB - tsA
  })
}

const filteredVpnPeers = computed(() => {
  if (!vpnPeers.value.length) return vpnPeers.value
  if (vpnTimeRange.value === '') return sortByHandshakeDesc(vpnPeers.value)
  const now = new Date()
  let cutoff = null
  switch (vpnTimeRange.value) {
    case '1h': cutoff = new Date(now.getTime() - 60 * 60 * 1000); break
    case '6h': cutoff = new Date(now.getTime() - 6 * 60 * 60 * 1000); break
    case '24h': cutoff = new Date(now.getTime() - 24 * 60 * 60 * 1000); break
    case '7d': cutoff = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000); break
    case 'custom': {
      const s = vpnCustomStart.value ? new Date(vpnCustomStart.value) : null
      const e = vpnCustomEnd.value ? new Date(vpnCustomEnd.value) : now
      return sortByHandshakeDesc(vpnPeers.value.filter(p => {
        if (!p.last_handshake_raw) return false
        const hs = new Date(p.last_handshake_raw)
        return (!s || hs >= s) && hs <= e
      }))
    }
    default: return sortByHandshakeDesc(vpnPeers.value)
  }
  return sortByHandshakeDesc(vpnPeers.value.filter(p => {
    if (!p.last_handshake_raw) return false
    return new Date(p.last_handshake_raw) >= cutoff
  }))
})

// Client-side pagination for the VPN peers table (mirrors the users table), so
// a large fleet does not render every row into the DOM at once.
const vpnPage = ref(1)
const vpnPerPage = 25
const vpnTotalPages = computed(() => Math.ceil(filteredVpnPeers.value.length / vpnPerPage))
const paginatedVpnPeers = computed(() => {
  const start = (vpnPage.value - 1) * vpnPerPage
  return filteredVpnPeers.value.slice(start, start + vpnPerPage)
})
watch([vpnTimeRange], () => { vpnPage.value = 1 })

// Same for the admin exercise list.
const labPage = ref(1)
const labsPerPage = 25
const labTotalPages = computed(() => Math.ceil(adminFilteredLabs.value.length / labsPerPage))
const paginatedAdminLabs = computed(() => {
  const start = (labPage.value - 1) * labsPerPage
  return adminFilteredLabs.value.slice(start, start + labsPerPage)
})
// The reset watcher lives with the filter refs further down, because watch()
// evaluates its source array immediately and those refs are declared later.

const filteredSessionHistory = computed(() => {
  if (sessionsTimeRange.value === '' || !sessionHistory.value.length) return sessionHistory.value
  const now = new Date()
  let cutoff = null
  switch (sessionsTimeRange.value) {
    case '1h': cutoff = new Date(now.getTime() - 60 * 60 * 1000); break
    case '6h': cutoff = new Date(now.getTime() - 6 * 60 * 60 * 1000); break
    case '24h': cutoff = new Date(now.getTime() - 24 * 60 * 60 * 1000); break
    case '7d': cutoff = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000); break
    case 'custom': {
      const s = sessionsCustomStart.value ? new Date(sessionsCustomStart.value) : null
      const e = sessionsCustomEnd.value ? new Date(sessionsCustomEnd.value) : now
      return sessionHistory.value.filter(sess => {
        if (!sess.started_at) return false
        const dt = new Date(sess.started_at)
        return (!s || dt >= s) && dt <= e
      })
    }
    default: return sessionHistory.value
  }
  return sessionHistory.value.filter(sess => {
    if (!sess.started_at) return false
    return new Date(sess.started_at) >= cutoff
  })
})

function getTimeRangeDates(rangeVal, customStart, customEnd) {
  const now = new Date()
  let start = null, end = null
  switch (rangeVal) {
    case '1h': start = new Date(now.getTime() - 60 * 60 * 1000).toISOString(); break
    case '6h': start = new Date(now.getTime() - 6 * 60 * 60 * 1000).toISOString(); break
    case '24h': start = new Date(now.getTime() - 24 * 60 * 60 * 1000).toISOString(); break
    case '7d': start = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000).toISOString(); break
    case 'custom':
      if (customStart) start = new Date(customStart).toISOString()
      if (customEnd) end = new Date(customEnd).toISOString()
      break
  }
  return { start, end }
}

const showCreateForm = ref(false)
const newUser = reactive({ username: '', email: '', password: '', is_approved: false, role: 'student' })

const showEditUserModal = ref(false)
const editUser = ref(null)
const editForm = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  is_approved: false,
  role: 'student',
  is_active: true,
  must_change_password: false
})
const editErrors = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: ''
})
const editLoading = ref(false)
const editErrorMessage = ref('')
const editSuccessMessage = ref('')

const editLab = ref(null)
const trackCatalog = ref([])  // [{id, name, slug, levels: [{id,name,level_number}]}]
const editTrackId = ref(null)  // selected track in edit modal (null = uncategorized)
const editLevelOptions = computed(() => {
  if (!editTrackId.value) return []
  const t = trackCatalog.value.find(t => t.id === editTrackId.value)
  return t ? t.levels : []
})

const showUserDetailsModal = ref(false)
const userDetails = ref(null)
const loadingUserDetails = ref(false)
const resettingLab = ref(false)

const syncing = ref(false)
const activeLabTab = ref('enabled')
const expandedCategories = ref({})
const labInstructorFilter = ref('')
const labVisibilityFilter = ref('')

// Sidebar-based exercise filtering
const exercisesView = ref('manage')
const selectedTrack = ref(null)
const labSearch = ref('')
const difficultyFilter = ref('')
const activeLabStatus = ref('all')

// Any filter change sends the exercise list back to page 1. Declared here, after
// the refs it watches: watch() reads its source array during setup, so placing
// this above these declarations throws a temporal dead zone ReferenceError and
// the whole Admin view fails to mount.
watch([activeLabStatus, selectedTrack, labSearch, difficultyFilter, labInstructorFilter, labVisibilityFilter], () => { labPage.value = 1 })

// Settings state
// 'modules' is a dev-only runtime toggle: shown only when developer tools are
// enabled (OCR_DEV_TOOLS) AND the build actually ships an optional module.
// Editions determine modules by build+entitlement, so the tab stays hidden
// there even when a module is present.
const settingsCategories = computed(() => {
  // Only show a category tab if it has at least one visible setting (so an
  // emptied category -- e.g. General after platform_name/deployment_mode were
  // removed -- doesn't render as a blank tab).
  const order = ['general', 'security', 'labs', 'vpn']
  const populated = new Set(
    Object.entries(allSettings.value)
      .filter(([key]) => !hiddenSettingKeys.value.has(key))
      .map(([, val]) => val.category)
  )
  const base = order.filter(c => populated.has(c))
  // The Modules tab (optional-module enable/disable) is a real admin control,
  // not a dev tool: show it whenever the edition ships optional modules, so an
  // operator can turn SOC on/off on a production install.
  if (Object.keys(modules.value || {}).length > 0) base.push('modules')
  return base
})
const categoryLabels = { general: 'General', security: 'Security', labs: 'Exercises', vpn: 'VPN', modules: 'Modules' }
const categoryLabel = (cat) => categoryLabels[cat] || cat.charAt(0).toUpperCase() + cat.slice(1)
const activeSettingsCategory = ref('security')
const allSettings = ref({})
const settingsEdits = reactive({})
const togglesSaving = reactive({})
const settingsLoading = ref(false)
const savingSettings = ref(false)

const settingMeta = {
  setup_complete:            { label: 'Setup Complete',          desc: 'Indicates whether the first-run setup wizard has been completed.' },
  jwt_expiration_hours:      { label: 'Session Lifetime',       desc: 'How long a user stays logged in before they must re-authenticate.', unit: 'hours' },
  max_failed_attempts:       { label: 'Max Failed Logins',      desc: 'Number of consecutive wrong-password attempts before the account is temporarily locked.', unit: 'attempts' },
  lockout_duration_minutes:  { label: 'Lockout Duration',       desc: 'How long a locked-out account remains inaccessible after exceeding the failed login limit.', unit: 'minutes' },
  require_approval:          { label: 'Require Approval',       desc: 'When enabled, new user registrations must be approved by an admin before the account can log in.' },
  enable_api_docs:           { label: 'API Documentation',      desc: 'Exposes the Swagger UI (/docs) and ReDoc (/redoc) endpoints for the backend API. Disable in production.' },
  default_session_hours:     { label: 'Default Exercise Duration',   desc: 'The default time limit for an exercise session before it is automatically stopped.', unit: 'hours' },
  max_session_hours:         { label: 'Max Exercise Duration',       desc: 'The maximum time a student can extend a single exercise session.', unit: 'hours' },
  container_cpu_limit:       { label: 'CPU Limit per Container', desc: 'Docker CPU allocation per exercise container (e.g. 0.5 = half a core, 1 = one full core).', unit: 'cores' },
  container_memory_limit:    { label: 'Memory Limit per Container', desc: 'Docker memory limit per exercise container (e.g. 512M, 1G).' },
  vpn_enabled:               { label: 'VPN Enabled',            desc: 'Enables WireGuard VPN connectivity for students to access lab environments.' },
  vpn_endpoint:              { label: 'VPN Endpoint',           desc: 'The public host:port of the WireGuard server that students connect to.', ph: 'vpn.yourdomain.com:51820' },
  vpn_public_key:            { label: 'VPN Server Public Key',  desc: 'The WireGuard server public key included in student config files.', ph: 'xTIBA5rboUvnH4htodjb6e697QjLERt1NAB4mZqp8Dg=' },
  vpn_wstunnel_enabled:      { label: 'WebSocket Tunnel',       desc: 'Wraps WireGuard traffic in a WebSocket tunnel, useful for Cloudflare Tunnel deployments.' },
  vpn_wstunnel_url:          { label: 'WebSocket Tunnel URL',   desc: 'The WSS URL for the WebSocket tunnel (e.g. wss://vpn.yourdomain.com).', ph: 'wss://vpn.yourdomain.com' },
}

// --- Module panel state ---
const { fetchModules, modules, devTools, exerciseTester, stressTester } = useModules()
const moduleToggling = ref('')
const moduleLog = reactive({})
const moduleStagedEdits = reactive({})  // tracks unsaved toggle state per key

// Optional modules are a paid-tier concept; this edition ships none.
const MODULE_DEFS = []

const moduleCards = computed(() => {
  return MODULE_DEFS.map(m => {
    const saved = (settingsEdits[m.key] || 'false').toLowerCase() === 'true'
    const staged = moduleStagedEdits[m.key] !== undefined ? moduleStagedEdits[m.key] : saved
    return {
      ...m,
      enabled: saved,
      staged,
      dirty: staged !== saved,
    }
  })
})

function stageModuleToggle(key) {
  const saved = (settingsEdits[key] || 'false').toLowerCase() === 'true'
  const current = moduleStagedEdits[key] !== undefined ? moduleStagedEdits[key] : saved
  moduleStagedEdits[key] = !current
}

function moduleLogPush(key, level, message) {
  if (!moduleLog[key]) moduleLog[key] = []
  const now = new Date()
  const time = now.toLocaleTimeString('en-US', { hour12: false })
  moduleLog[key].push({ time, level, message })
}

async function saveModule(key) {
  const newValue = moduleStagedEdits[key]
  if (newValue === undefined) return

  moduleToggling.value = key
  moduleLog[key] = []
  const label = MODULE_DEFS.find(m => m.key === key)?.label || key
  const action = newValue ? 'Enabling' : 'Disabling'

  moduleLogPush(key, 'info', `${action} ${label}...`)

  try {
    // Save the setting
    moduleLogPush(key, 'info', 'Saving setting...')
    await axios.put('/settings/', { settings: { [key]: String(newValue) } })
    settingsEdits[key] = String(newValue)
    delete moduleStagedEdits[key]
    moduleLogPush(key, 'success', 'Setting saved.')

    // Refresh module status cache so sidebar updates
    moduleLogPush(key, 'info', 'Refreshing module status...')
    await fetchModules()
    moduleLogPush(key, 'success', 'Module status refreshed.')

    // Verify against the modules registry, which is always mounted and reflects
    // the true enabled state. (The old check pinged /<id>/status, which many
    // modules do not expose, so it 404'd even when the module was live.)
    moduleLogPush(key, 'info', 'Verifying module status...')
    const modId = MODULE_DEFS.find(m => m.key === key)?.id
    try {
      const { data } = await axios.get('/modules/')
      const live = !!data?.modules?.[modId]?.enabled
      if (live === !!newValue) {
        moduleLogPush(key, 'success', `Module ${live ? 'active' : 'gated'} and verified.`)
      } else {
        moduleLogPush(key, 'warn', `Module status did not match (expected ${newValue ? 'enabled' : 'disabled'}).`)
      }
    } catch (verifyErr) {
      moduleLogPush(key, 'warn', `Could not verify module status (${verifyErr.response?.status || 'error'}).`)
    }

    moduleLogPush(key, 'success', `${label} ${newValue ? 'enabled' : 'disabled'} successfully.`)
  } catch (e) {
    moduleLogPush(key, 'error', e.response?.data?.detail || 'Failed to save setting.')
  } finally {
    moduleToggling.value = ''
  }
}

function friendlyLabel(key) {
  return settingMeta[key]?.label || key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function settingDescription(key) {
  return settingMeta[key]?.desc || allSettings.value[key]?.description || ''
}

function settingUnit(key) {
  return settingMeta[key]?.unit || ''
}

function settingPlaceholder(key) {
  return settingMeta[key]?.ph || ''
}

// Activity log state
const activityEvents = ref([])
const activityLoading = ref(false)
const activityPage = ref(1)
const activityTotal = ref(0)
const activityPages = ref(0)
const activityFilter = ref('')
const activityEventTypes = ref([])

const eventTypeLabelMap = {
  lab_started: 'Lab Started',
  lab_stopped: 'Lab Stopped',
  lab_completed: 'Lab Completed',
  flag_correct: 'Flag Correct',
  flag_incorrect: 'Flag Incorrect',
  hint_used: 'Hint Used',
  user_registered: 'User Registered',
  user_approved: 'User Approved',
  session_expired: 'Session Expired',
  vpn_downloaded: 'VPN Downloaded',
  course_enrolled: 'Course Enrolled',
  achievement_awarded: 'Achievement Awarded',
}

const eventTypeLabel = (et) => {
  if (eventTypeLabelMap[et]) return eventTypeLabelMap[et]
  return et.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

// System status state
const systemStatus = ref({})
const systemStatusLoading = ref(false)
const backups = ref([])
const backupsLoading = ref(false)
const creatingBackup = ref(false)
const restoringBackup = ref(false)
const calendarDays = ref({})
const deletingBackup = ref(null)

// Header system-health dot state (proactive, runs on mount)
const dashboardHealthStatus = ref('')
const dashboardHealthItems = ref([])
const dashboardHealthLoaded = ref(false)
let healthPollTimer = null


// Lab scanning state
const scanningLabs = ref(false)
const scanWarnings = ref([])

// Disk management state
const showDiskModal = ref(false)
const diskUsage = ref(null)
const diskUsageLoading = ref(false)
const pruningImages = ref(false)
const pruningBuildCache = ref(false)
const deletingLabImages = ref({})

// ── Exercise Tester state ──
const testerLabList = ref([])
const testerTracks = ref([])
const testerCategories = ref([])
const testerLabSelection = ref([])
const testerTrackFilter = ref('')
const testerCategoryFilter = ref('')
const testerCourseFilter = ref('')
const testerCourses = ref([])
const testerSearchQuery = ref('')
const testerStatusFilter = ref('')
const testerRunning = ref(false)
const testerCancelling = ref(false)
const testerSections = ref([])
const testerComplete = ref(null)
const testerTerminalRef = ref(null)
const testerResults = ref({})  // slug → { status, date, labName, category, duration, sections }
const testerRunId = ref(null)
const quickTestSlug = ref(null)
const quickTestTerminalRef = ref(null)
// (testerAbortController removed — polling-based now, no fetch to abort)

// Progress tracking
const testerProgressCurrent = ref(0)   // labs completed so far
const testerProgressTotal = ref(0)     // total labs in this run
const testerProgressStarted = ref(0)   // Date.now() when run started
const testerLabDurations = ref([])     // durations of completed labs (seconds)

const testerProgress = computed(() => {
  const current = testerProgressCurrent.value
  const total = testerProgressTotal.value
  if (!total) return { current: 0, total: 0, pct: 0 }
  const pct = Math.round((current / total) * 100)
  return { current, total, pct }
})

const filteredTesterLabs = computed(() => {
  let labs = testerLabList.value
  if (testerTrackFilter.value) labs = labs.filter(l => l.track === testerTrackFilter.value)
  if (testerCategoryFilter.value) labs = labs.filter(l => l.category === testerCategoryFilter.value)
  if (testerCourseFilter.value) {
    const cid = Number(testerCourseFilter.value)
    labs = labs.filter(l => l.courses && l.courses.some(c => c.id === cid))
  }
  return labs
})

const testerSummaryPassed = computed(() =>
  Object.values(testerResults.value).filter(r => r.status === 'ok').length
)
const testerSummaryWarned = computed(() =>
  Object.values(testerResults.value).filter(r => r.status === 'warning').length
)
const testerSummaryFailed = computed(() =>
  Object.values(testerResults.value).filter(r => r.status === 'error' || r.status === 'cancelled').length
)

const searchedTesterLabs = computed(() => {
  let labs = filteredTesterLabs.value
  const sf = testerStatusFilter.value
  if (sf === 'ok') labs = labs.filter(l => testerResults.value[l.slug]?.status === 'ok')
  else if (sf === 'warning') labs = labs.filter(l => testerResults.value[l.slug]?.status === 'warning')
  else if (sf === 'failed') labs = labs.filter(l => testerResults.value[l.slug]?.status === 'error' || testerResults.value[l.slug]?.status === 'cancelled')
  else if (sf === 'untested') labs = labs.filter(l => !testerResults.value[l.slug])
  const q = testerSearchQuery.value.toLowerCase().trim()
  if (q) labs = labs.filter(l => l.name.toLowerCase().includes(q) || l.slug.toLowerCase().includes(q))
  // Sort by week when a course filter is active
  if (testerCourseFilter.value) {
    labs = [...labs].sort((a, b) => (a.week ?? 999) - (b.week ?? 999))
  }
  return labs
})

// Clear lab selections when filters change so hidden checked labs don't silently run
watch([testerStatusFilter, testerTrackFilter, testerCategoryFilter, testerCourseFilter], () => {
  testerLabSelection.value = []
})

// Container logs state
const sessionLogs = ref({})
const sessionLogsLoading = ref(false)
const viewingLogsSessionId = ref(null)

// Internal flags that should not be editable from the GUI
const hiddenSettingKeys = computed(() => {
  // Removed dead settings: platform_name (branding is fixed to OCR) and
  // deployment_mode (only ever toggled a cosmetic banner). Hide them if an
  // older DB still carries the rows.
  const s = new Set(['setup_complete', 'platform_name', 'deployment_mode'])
  // API docs (Swagger /docs + ReDoc /redoc) is a developer surface and a real
  // exposure if a non-technical admin enables it. Hide the toggle off-dev; it
  // stays settable via the ENABLE_API_DOCS env var for dev/integration.
  if (!devTools.value) s.add('enable_api_docs')
  return s
})

const filteredSettings = computed(() => {
  const result = {}
  for (const [key, val] of Object.entries(allSettings.value)) {
    if (val.category === activeSettingsCategory.value && !hiddenSettingKeys.value.has(key)) {
      result[key] = settingsEdits[key] !== undefined ? settingsEdits[key] : val.value
    }
  }
  return result
})

const fetchSettings = async () => {
  settingsLoading.value = true
  try {
    const { data } = await axios.get('/settings/')
    allSettings.value = {}
    // API returns array of {key, value, category, description, is_secret}
    for (const item of data) {
      allSettings.value[item.key] = item
      settingsEdits[item.key] = item.value
    }
  } catch (e) {
    showAlert('Failed to load settings', 'error')
  } finally {
    settingsLoading.value = false
  }
}

// A toggle reads as a commit, not an edit in progress, so it persists on click
// rather than waiting for Save Settings. Text inputs still batch behind Save,
// where that model fits: nobody wants a half-typed value written on each
// keystroke. The switch is applied optimistically and rolled back if the write
// fails, so what the toggle shows is always what is stored.
const toggleSetting = async (key) => {
  if (togglesSaving[key]) return
  const previous = settingsEdits[key]
  const next = previous === 'true' ? 'false' : 'true'
  settingsEdits[key] = next
  togglesSaving[key] = true
  try {
    await axios.put('/settings/', { settings: { [key]: next } })
    if (allSettings.value[key]) allSettings.value[key].value = next
  } catch (e) {
    settingsEdits[key] = previous
    showAlert(e.response?.data?.detail || 'Failed to save setting', 'error')
  } finally {
    togglesSaving[key] = false
  }
}

const saveSettings = async () => {
  savingSettings.value = true
  try {
    const payload = {}
    for (const [key, val] of Object.entries(settingsEdits)) {
      if (val !== '••••••••') payload[key] = val
    }
    await axios.put('/settings/', { settings: payload })
    showAlert('Settings saved')
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Failed to save settings', 'error')
  } finally {
    savingSettings.value = false
  }
}

// Lab Discovery
const scanLabs = async () => {
  scanningLabs.value = true
  scanWarnings.value = []
  try {
    const { data } = await axios.post('/admin/labs/discover')
    showAlert(data.message)
    if (data.errors && data.errors.length) {
      scanWarnings.value = data.errors
    }
    fetchAll()
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Exercise scan failed', 'error')
  } finally {
    scanningLabs.value = false
  }
}

// Activity log
const fetchActivity = async (page = 1) => {
  activityLoading.value = true
  try {
    const params = { page, per_page: 50 }
    if (activityFilter.value) params.event_type = activityFilter.value
    const { start, end } = getTimeRangeDates(activityTimeRange.value, activityCustomStart.value, activityCustomEnd.value)
    if (start) params.start_date = start
    if (end) params.end_date = end
    const { data } = await axios.get('/admin/activity', { params })
    activityEvents.value = data.events
    activityTotal.value = data.total
    activityPages.value = data.pages
    activityPage.value = data.page
    activityEventTypes.value = data.event_types
  } catch (e) {
    showAlert('Failed to load activity log', 'error')
  } finally {
    activityLoading.value = false
  }
}

// Minimal, install-aware status (the default System view)
const fetchSystemStatus = async () => {
  systemStatusLoading.value = true
  try {
    const { data } = await axios.get('/admin/system/status')
    systemStatus.value = data
    // Keep the top System card in sync: a user refreshing health here expects
    // the summary card to match, not lag until the next poll.
    fetchDashboardHealth()
  } catch (e) {
    showAlert('Failed to load status', 'error')
  } finally {
    systemStatusLoading.value = false
  }
}

// Header system-health dot -- driven by the minimal, install-aware status.
const fetchDashboardHealth = async () => {
  try {
    const { data } = await axios.get('/admin/system/status')
    dashboardHealthStatus.value = data.overall || 'error'
    dashboardHealthItems.value = data.items || []
  } catch {
    dashboardHealthStatus.value = 'error'
    dashboardHealthItems.value = []
  } finally {
    dashboardHealthLoaded.value = true
  }
}

// Map the status 'ok' to the 'healthy' CSS class the card styling expects.
const dashboardHealthClass = computed(() =>
  dashboardHealthStatus.value === 'ok' ? 'healthy' : dashboardHealthStatus.value
)

// Tooltip mirrors the live checks: when anything is amber or red it names the
// exact item and its plain-language detail, so the dot never alarms without
// saying why. Newlines render because the InfoTip bubble uses pre-line.
const dashboardHealthTip = computed(() => {
  if (!dashboardHealthLoaded.value) return 'Checking platform health...'
  const items = dashboardHealthItems.value
  if (!items.length) return 'The status check did not respond. The backend may be down or unreachable.'
  const bad = items.filter(i => i.status !== 'ok')
  if (!bad.length) return 'All checks passing: platform and database, disk space, active sessions, backups, and core secrets.'
  return bad.map(i => `${i.name}: ${i.detail}`).join('\n')
})


// ── Exercise Tester functions ──

const fetchTesterLabs = async () => {
  try {
    const { data } = await axios.get('/admin/exercise-test/labs')
    testerLabList.value = data
    const tracks = new Set(data.map(l => l.track).filter(Boolean))
    testerTracks.value = [...tracks].sort()
    const cats = new Set(data.map(l => l.category).filter(Boolean))
    testerCategories.value = [...cats].sort()
    // Extract unique courses from lab data
    const courseMap = {}
    for (const lab of data) {
      for (const c of (lab.courses || [])) {
        courseMap[c.id] = c
      }
    }
    testerCourses.value = Object.values(courseMap).sort((a, b) => a.name.localeCompare(b.name))
  } catch {}
}

const fetchTesterResults = async () => {
  // Editions without the exercise tester do not ship these routes, so calling
  // them 404s on every visit and leaves the panel dead. The backend already
  // reports availability; ask it instead of guessing.
  if (!exerciseTester.value) return
  try {
    const { data } = await axios.get('/admin/exercise-test/results')
    // Always apply DB results so status badges stay current after re-tests
    const merged = { ...testerResults.value }
    for (const [slug, result] of Object.entries(data)) {
      merged[slug] = result
    }
    testerResults.value = merged
  } catch {}
}

const clearTesterResults = async () => {
  testerSections.value = []
  testerComplete.value = null
  testerResults.value = {}
  // Also clear from backend
  if (!exerciseTester.value) return
  try { await axios.delete('/admin/exercise-test/results') } catch {}
}

const runExerciseTestAll = () => {
  testerLabSelection.value = searchedTesterLabs.value.map(l => l.slug)
  nextTick(() => runExerciseTest())
}

let _testerPollTimer = null

const _processTestEvents = (events, ctx) => {
  for (const event of events) {
    if (event.type === 'started' && event.run_id) {
      testerRunId.value = event.run_id
      testerProgressTotal.value = event.total_labs || 0
      if (!testerProgressStarted.value) testerProgressStarted.value = Date.now()
    } else if (event.type === 'lab_start') {
      ctx.currentLabSlug = event.lab_slug
      ctx.currentLabName = event.lab_name
      ctx.labSections[ctx.currentLabSlug] = []
      const sep = { name: `Lab ${event.lab_index}/${event.total_labs}: ${event.lab_name}`, test_key: `_lab_${event.lab_slug}`, status: 'running', lines: [] }
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
      const labInfo = testerLabList.value.find(l => l.slug === event.lab_slug)
      testerResults.value = {
        ...testerResults.value,
        [event.lab_slug]: {
          status: event.status,
          date: new Date().toLocaleString(),
          labName: ctx.currentLabName || event.lab_slug,
          category: labInfo?.category || '',
          duration: event.duration_seconds,
          sections: JSON.parse(JSON.stringify(ctx.labSections[event.lab_slug] || []))
        }
      }
    } else if (event.type === 'complete') {
      testerComplete.value = event
    }
  }
  // Auto-scroll terminal(s)
  nextTick(() => {
    if (testerTerminalRef.value) {
      testerTerminalRef.value.scrollTop = testerTerminalRef.value.scrollHeight
    }
    if (quickTestTerminalRef.value) {
      quickTestTerminalRef.value.scrollTop = quickTestTerminalRef.value.scrollHeight
    }
  })
}

const _startPolling = (runId) => {
  if (_testerPollTimer) { clearTimeout(_testerPollTimer); _testerPollTimer = null }
  let afterIdx = 0
  const ctx = { sectionMap: {}, labSections: {}, currentLabSlug: null, currentLabName: null }

  const poll = async () => {
    try {
      const res = await axios.get(`/admin/exercise-test/events/${runId}`, { params: { after: afterIdx } })
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

const runQuickTest = async (lab) => {
  quickTestSlug.value = lab.slug
  testerRunning.value = true
  testerCancelling.value = false
  testerRunId.value = null
  testerSections.value = []
  testerComplete.value = null
  testerProgressCurrent.value = 0
  testerProgressTotal.value = 0
  testerProgressStarted.value = Date.now()
  testerLabDurations.value = []
  try {
    const res = await axios.post('/admin/exercise-test', { lab_slugs: [lab.slug] })
    const { run_id, total_labs } = res.data
    testerRunId.value = run_id
    testerProgressTotal.value = total_labs
    _startPolling(run_id)
  } catch (e) {
    showAlert(`Exercise tester failed: ${e.response?.data?.detail || e.message}`, 'error')
    testerRunning.value = false
  }
}

const runExerciseTest = async () => {
  if (testerLabSelection.value.length === 0) return
  testerRunning.value = true
  testerCancelling.value = false
  testerRunId.value = null
  testerSections.value = []
  testerComplete.value = null
  testerProgressCurrent.value = 0
  testerProgressTotal.value = 0
  testerProgressStarted.value = Date.now()
  testerLabDurations.value = []

  // Send all selected labs (selection is cleared on filter change, so stale picks are not possible)
  const slugsToTest = [...testerLabSelection.value]
  if (slugsToTest.length === 0) { testerRunning.value = false; return }
  const payload = { lab_slugs: slugsToTest }
  try {
    const res = await axios.post('/admin/exercise-test', payload)
    const { run_id, total_labs } = res.data
    testerRunId.value = run_id
    testerProgressTotal.value = total_labs
    _startPolling(run_id)
  } catch (e) {
    showAlert(`Exercise tester failed: ${e.response?.data?.detail || e.message}`, 'error')
    testerRunning.value = false
  }
}

const cancelExerciseTest = async () => {
  testerCancelling.value = true
  if (testerRunId.value) {
    try {
      await axios.post('/admin/exercise-test/cancel', { run_id: testerRunId.value })
    } catch (e) {
      console.error('Cancel request failed', e)
    }
  }
  // Polling will detect status change and stop automatically.
  // Fetch persisted results after a short delay for reports.
  setTimeout(async () => {
    await fetchTesterResults()
  }, 3000)
}

const checkActiveTestRun = async () => {
  if (!exerciseTester.value) return
  try {
    const res = await axios.get('/admin/exercise-test/active')
    if (res.data.run_id && res.data.status === 'running') {
      testerRunning.value = true
      testerRunId.value = res.data.run_id
      testerProgressTotal.value = res.data.total_labs
      testerProgressCurrent.value = res.data.labs_completed
      testerProgressStarted.value = Date.now()
      testerSections.value = []
      testerComplete.value = null
      testerLabDurations.value = []
      // Restore inline quick-test panel for single-lab runs
      const slugs = res.data.lab_slugs || []
      if (slugs.length === 1 && !quickTestSlug.value) {
        quickTestSlug.value = slugs[0]
      }
      _startPolling(res.data.run_id)
    }
  } catch {}
}

const generateTestReport = async (slug) => {
  const result = testerResults.value[slug]
  if (!result) return

  try {
    const res = await axios.post('/admin/exercise-test/report', result, { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
    const a = document.createElement('a')
    a.href = url
    const safeName = result.labName.replace(/[^a-zA-Z0-9_-]/g, '_').toLowerCase()
    a.download = `exercise_test_${safeName}.pdf`
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (e) {
    console.error('Failed to download exercise test report', e)
    showAlert('Failed to generate report PDF', 'error')
  }
}

// ── Stress Tester ────────────────────────────────────────────────────────

let _stressPollTimer = null

const runStressTest = async () => {
  stressRunning.value = true
  stressRunId.value = null
  stressSections.value = []
  stressResults.value = null
  stressProgressCompleted.value = 0
  stressProgressTotal.value = 0
  stressPhase.value = null

  try {
    const payload = {
      level: stressLevel.value,
      users: stressUsers.value,
      concurrent_spawns: stressConcurrentSpawns.value,
    }
    const res = await axios.post('/admin/stress-test', payload)
    stressRunId.value = res.data.run_id
    stressProgressTotal.value = res.data.users
    _startStressPolling(res.data.run_id)
  } catch (e) {
    showAlert(`Stress test failed: ${e.response?.data?.detail || e.message}`, 'error')
    stressRunning.value = false
  }
}

const _startStressPolling = (runId) => {
  if (_stressPollTimer) { clearTimeout(_stressPollTimer); _stressPollTimer = null }
  let afterIdx = 0

  const poll = async () => {
    try {
      const res = await axios.get(`/admin/stress-test/events/${runId}`, { params: { after: afterIdx } })
      const { events, status, event_count, results } = res.data
      if (events && events.length) {
        for (const event of events) {
          if (event.type === 'line') {
            stressSections.value.push(event)
          } else if (event.type === 'phase') {
            stressPhase.value = event.phase
            // Reset progress bar when entering timed phase
            if (event.phase === 'timed') {
              stressProgressCompleted.value = 0
            }
          } else if (event.type === 'progress') {
            stressProgressCompleted.value = event.completed || 0
            stressProgressTotal.value = event.total || stressProgressTotal.value
          } else if (event.type === 'endpoint_result') {
            // Update results table in real time
            if (!stressResults.value) {
              stressResults.value = { endpoints: [], total_calls: 0, total_errors: 0, error_rate: 0, error_rate_passed: true, all_thresholds_passed: true, duration_seconds: 0 }
            }
            // Check if endpoint already exists (shouldn't, but be safe)
            const existing = stressResults.value.endpoints.find(e => e.endpoint === event.endpoint)
            if (!existing) {
              stressResults.value.endpoints.push({
                endpoint: event.endpoint,
                calls: event.calls,
                p50: event.p50,
                p95: event.p95,
                p99: event.p99,
                errors: event.errors,
                passed: event.passed,
              })
            }
          } else if (event.type === 'complete' && event.results) {
            stressResults.value = event.results
          }
        }
        // Auto-scroll terminal
        nextTick(() => {
          if (stressTerminalRef.value) {
            stressTerminalRef.value.scrollTop = stressTerminalRef.value.scrollHeight
          }
        })
      }
      afterIdx = event_count

      // If results came with the response (for completed runs)
      if (results && status !== 'running') {
        stressResults.value = results
      }

      if (status !== 'running') {
        stressRunning.value = false
        _stressPollTimer = null
        return
      }
    } catch (e) {
      console.error('Stress test poll error:', e)
    }
    _stressPollTimer = setTimeout(poll, 2000)
  }
  poll()
}

const cancelStressTest = async () => {
  if (stressRunId.value) {
    try {
      await axios.post('/admin/stress-test/cancel', { run_id: stressRunId.value })
      showAlert('Cancelling stress test...')
    } catch (e) {
      console.error('Cancel stress test failed', e)
    }
  }
}

const checkActiveStressTest = async () => {
  try {
    const res = await axios.get('/admin/stress-test/active')
    if (res.data.run_id && res.data.status === 'running') {
      stressRunning.value = true
      stressRunId.value = res.data.run_id
      stressProgressTotal.value = res.data.users
      stressSections.value = []
      stressResults.value = null
      _startStressPolling(res.data.run_id)
      return
    }
    // No active test — try to restore last completed results
    if (!stressResults.value) {
      const last = await axios.get('/admin/stress-test/last-result')
      if (last.data.results) {
        stressResults.value = last.data.results
        stressLevel.value = last.data.level || 1
        stressUsers.value = last.data.users || 45
      }
    }
  } catch {}
}

const downloadStressReport = async () => {
  if (!stressResults.value) return
  try {
    const res = await axios.post('/admin/stress-test/report', stressResults.value, { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
    const a = document.createElement('a')
    a.href = url
    const now = new Date()
    const ts = String(now.getMonth()+1).padStart(2,'0') + String(now.getDate()).padStart(2,'0') + now.getFullYear() + '_' + String(now.getHours()).padStart(2,'0') + String(now.getMinutes()).padStart(2,'0')
    const lvl = stressLevel.value || stressResults.value?.level || 1
    a.download = `${ts}_Type${lvl}_StressTest.pdf`
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (e) {
    console.error('Failed to download stress test report', e)
    showAlert('Failed to generate report PDF', 'error')
  }
}

const stressCleanup = async () => {
  if (!confirm('Remove all stress test users and data from the database?')) return
  try {
    const res = await axios.post('/admin/stress-test/cleanup')
    showAlert(res.data.messages?.join('; ') || 'Cleanup complete')
  } catch (e) {
    showAlert(`Cleanup failed: ${e.response?.data?.detail || e.message}`, 'error')
  }
}

// ── End Stress Tester ───────────────────────────────────────────────────

const closeVmTerminal = (vmName) => {
  const term = vmTerminals.value[vmName]
  if (term?.eventSource) term.eventSource.close()
  delete vmTerminals.value[vmName]
}

// ── Provision event streaming (SSE) ─────────────────────────────────────
// Uses Server-Sent Events for real-time event delivery from the backend.
// The backend pushes events as they happen — no polling, no timers, no race conditions.
let _provisionEventSource = null

// ── VM Definition CRUD ──────────────────────────────────────────────────

const resetVmDefForm = () => {
  Object.assign(vmDefForm, {
    container_name: '',
    display_name: '',
    description: '',
    vm_type: 'windows',
    os_version: '',
    image: 'dockurr/windows',
    ram: '4G',
    cpu_cores: '2',
    subnet: '',
    forward_ports: '',
    local_iso: '',
    setup_script: '',
    setup_script_container_path: '',
    shared_volume_host: '',
    shared_volume_container: '/storage/shared',
    two_phase: false,
    committed_tag: 'configured',
    winrm_user: '',
    winrm_pass: '',
    docker_command: '',
    environment_vars: '',
    extra_volumes: '',
    extra_cap_add: '',
    health_check_port: null,
    is_enabled: true,
  })
}

const openEditVmDef = (def, vm = null) => {
  editingVmDefId.value = def.id
  editingVmIsActive.value = vm ? (vm.status === 'running' || vm.status === 'created') : false
  Object.assign(vmDefForm, {
    container_name: def.container_name,
    display_name: def.display_name,
    description: def.description || '',
    vm_type: def.vm_type || 'windows',
    os_version: def.os_version || '',
    image: def.image,
    ram: def.ram || '4G',
    cpu_cores: def.cpu_cores || '2',
    subnet: def.subnet,
    forward_ports: Array.isArray(def.forward_ports) ? def.forward_ports.join(', ') : (def.forward_ports || ''),
    local_iso: def.local_iso || '',
    setup_script: def.setup_script || '',
    setup_script_container_path: def.setup_script_container_path || '',
    shared_volume_host: def.shared_volume_host || '',
    shared_volume_container: def.shared_volume_container || '/storage/shared',
    two_phase: def.two_phase || false,
    committed_tag: def.committed_tag || 'configured',
    winrm_user: def.winrm_user || '',
    winrm_pass: def.winrm_pass || '',
    docker_command: def.docker_command || '',
    environment_vars: def.environment_vars || '',
    extra_volumes: def.extra_volumes || '',
    extra_cap_add: def.extra_cap_add || '',
    health_check_port: def.health_check_port,
    is_enabled: def.is_enabled !== false,
  })
  showVmDefPanel.value = true
}

const getVmDefForVm = (vm) => {
  return vmDefinitions.value.find(d => d.container_name === vm.name)
}

const fetchBackups = async () => {
  backupsLoading.value = true
  try {
    const { data } = await axios.get('/admin/system/backups')
    backups.value = data.backups
  } catch (e) {
    showAlert('Failed to load backups', 'error')
  } finally {
    backupsLoading.value = false
  }
}

const fetchActivityCalendar = async () => {
  try {
    const { data } = await axios.get('/admin/system/activity-calendar')
    calendarDays.value = data.days || {}
  } catch (e) { /* silent */ }
}

const createBackup = async () => {
  creatingBackup.value = true
  try {
    const { data } = await axios.post('/admin/system/backup')
    showAlert(data.message)
    fetchBackups()
    fetchActivityCalendar()
    // A fresh backup clears the "last backup was N days ago" warning, so refresh
    // both health views now rather than leaving them stale until the 5-min poll
    // or a page reload: the top card (dashboard health) and the System panel.
    fetchDashboardHealth()
    fetchSystemStatus()
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Backup failed', 'error')
  } finally {
    creatingBackup.value = false
  }
}

const downloadBackup = (filename) => {
  const token = localStorage.getItem('token')
  const url = `${axios.defaults.baseURL || ''}/admin/system/backups/${filename}`
  const a = document.createElement('a')
  a.href = url
  a.setAttribute('download', filename)
  const headers = token ? { Authorization: `Bearer ${token}` } : {}
  axios.get(`/admin/system/backups/${filename}`, { responseType: 'blob', headers })
    .then(resp => {
      const blob = new Blob([resp.data], { type: 'application/sql' })
      const objUrl = URL.createObjectURL(blob)
      a.href = objUrl
      a.click()
      URL.revokeObjectURL(objUrl)
    })
    .catch(() => showAlert('Failed to download backup', 'error'))
}

const confirmRestore = (backup) => {
  const dateStr = formatDate(backup.created)
  if (!confirm(`RESTORE DATABASE\n\nThis will replace ALL current data with the snapshot from ${dateStr}.\n\nFilename: ${backup.filename}\n\nThis action cannot be undone. Are you sure?`)) return
  if (!confirm('Final confirmation: All current data will be overwritten. Continue?')) return
  restoreBackup(backup.filename)
}

const restoreBackup = async (filename) => {
  restoringBackup.value = true
  try {
    const { data } = await axios.post('/admin/system/restore', { filename })
    showAlert(data.message || 'Database restored successfully')
    fetchSystemStatus()
    fetchBackups()
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Restore failed', 'error')
  } finally {
    restoringBackup.value = false
  }
}

const confirmDeleteBackup = (backup) => {
  if (!confirm(`Delete snapshot "${backup.filename}"?\n\nThis cannot be undone.`)) return
  deleteBackup(backup.filename)
}

const deleteBackup = async (filename) => {
  deletingBackup.value = filename
  try {
    await axios.delete(`/admin/system/backups/${filename}`)
    showAlert('Snapshot deleted')
    fetchBackups()
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Delete failed', 'error')
  } finally {
    deletingBackup.value = null
  }
}

const formatBackupSize = (bytes) => {
  if (bytes >= 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  return (bytes / 1024).toFixed(1) + ' KB'
}

const diskBarClass = (pct) => {
  if (pct >= 91) return 'disk-bar--critical'
  if (pct >= 76) return 'disk-bar--warning'
  return 'disk-bar--healthy'
}

const backupHeatmapData = computed(() => {
  const now = new Date()
  const oneYearAgo = new Date(now)
  oneYearAgo.setFullYear(oneYearAgo.getFullYear() - 1)
  oneYearAgo.setDate(oneYearAgo.getDate() - oneYearAgo.getDay())

  const days = calendarDays.value

  const backupTimestamps = []
  for (const b of backups.value) {
    backupTimestamps.push(new Date(b.created).getTime())
  }
  backupTimestamps.sort()
  const lastGlobalBackupTs = backupTimestamps.length
    ? backupTimestamps[backupTimestamps.length - 1] : 0

  const weeks = []
  let currentWeek = []
  const cursor = new Date(oneYearAgo)
  const startDow = cursor.getDay()
  for (let i = 0; i < startDow; i++) currentWeek.push(null)

  const monthLabels = []
  let lastMonth = -1
  let weekIdx = 0
  let totalBackups = 0

  while (cursor <= now) {
    const m = cursor.getMonth()
    if (m !== lastMonth) {
      const names = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
      monthLabels.push({ label: names[m], col: weekIdx + 1, span: 1, key: `${cursor.getFullYear()}-${m}` })
      lastMonth = m
    }
    const key = `${cursor.getFullYear()}-${String(cursor.getMonth()+1).padStart(2,'0')}-${String(cursor.getDate()).padStart(2,'0')}`
    const dayData = days[key] || {}
    const hasBackup = (dayData.backups || 0) > 0
    const hasChanges = (dayData.changes || 0) > 0
    const dayBackupTs = dayData.last_backup_ts ? new Date(dayData.last_backup_ts).getTime() : 0
    const dayChangeTs = dayData.last_change_ts ? new Date(dayData.last_change_ts).getTime() : 0

    let color = 'none'
    let tooltip = key + ': No activity'

    if (hasBackup && hasChanges && dayChangeTs > dayBackupTs) {
      color = 'split'
      tooltip = key + ': Backup created, but changes occurred after'
      totalBackups++
    } else if (hasBackup) {
      color = 'green'
      tooltip = key + ': Snapshot created'
      totalBackups++
    } else if (hasChanges && dayChangeTs > lastGlobalBackupTs) {
      color = 'yellow'
      tooltip = key + ': System changes (not yet backed up)'
    } else if (hasChanges) {
      color = 'none'
      tooltip = key + ': System changes (covered by later backup)'
    }

    currentWeek.push({ date: key, color, tooltip })

    if (cursor.getDay() === 6) {
      weeks.push(currentWeek)
      currentWeek = []
      weekIdx++
    }
    cursor.setDate(cursor.getDate() + 1)
  }
  if (currentWeek.length > 0) {
    while (currentWeek.length < 7) currentWeek.push(null)
    weeks.push(currentWeek)
  }

  for (let i = 1; i < monthLabels.length; i++) {
    monthLabels[i-1].span = monthLabels[i].col - monthLabels[i-1].col
  }
  if (monthLabels.length > 0) {
    monthLabels[monthLabels.length-1].span = weeks.length - monthLabels[monthLabels.length-1].col + 1
  }

  return { weeks, monthLabels, totalBackups }
})

// Container logs
const viewSessionLogs = async (sessionId) => {
  viewingLogsSessionId.value = sessionId
  sessionLogsLoading.value = true
  try {
    const { data } = await axios.get(`/admin/sessions/${sessionId}/logs`)
    sessionLogs.value = data.containers
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Failed to get logs', 'error')
  } finally {
    sessionLogsLoading.value = false
  }
}

const closeSessionLogs = () => {
  viewingLogsSessionId.value = null
  sessionLogs.value = {}
}

// Impersonation
const impersonatingSessionId = ref(null)

const impersonateSession = async (sessionId, username) => {
  // If already impersonating this session, disconnect
  if (impersonatingSessionId.value === sessionId) {
    try {
      await axios.post('/admin/impersonate/disconnect')
      impersonatingSessionId.value = null
      showAlert(`Disconnected from ${username}'s lab network`)
    } catch (e) {
      showAlert(e.response?.data?.detail || 'Failed to disconnect', 'error')
    }
    return
  }

  // Connect to new session (auto-disconnects previous)
  try {
    const { data } = await axios.post(`/admin/impersonate/${sessionId}`)
    impersonatingSessionId.value = sessionId
    showAlert(`Connected to ${data.target_user}'s lab network. Open your RangeBox to test.`)
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Failed to impersonate. Make sure you have a standalone RangeBox running.', 'error')
  }
}

// Check impersonation status on load
const checkImpersonationStatus = async () => {
  try {
    const { data } = await axios.get('/admin/impersonate/status')
    if (data.active) {
      // Find the matching session
      const sessions = sessionsHealth.value?.sessions || []
      const match = sessions.find(s => s.user_id === data.user_id && s.lab_slug === data.lab_slug)
      if (match) impersonatingSessionId.value = match.session_id
    }
  } catch {
    // Ignore — not critical
  }
}

// Launch As Student
const showLaunchAsModal = ref(false)
const launchAsForm = reactive({ userId: '', labSlug: '' })
const launchAsLoading = ref(false)
const launchAsError = ref('')

const launchAsStudentList = computed(() => {
  return users.value
    .filter(u => u.is_approved && u.is_active && u.role !== 'admin')
    .sort((a, b) => a.username.localeCompare(b.username))
})

const launchAsLabList = computed(() => {
  return labs.value
    .filter(l => l.is_active !== false)
    .sort((a, b) => (a.name || '').localeCompare(b.name || ''))
})

const launchAsStudent = async () => {
  if (!launchAsForm.userId || !launchAsForm.labSlug) return

  launchAsLoading.value = true
  launchAsError.value = ''

  try {
    const { data } = await axios.post('/admin/impersonate/launch', {
      user_id: Number(launchAsForm.userId),
      lab_slug: launchAsForm.labSlug,
    })

    showLaunchAsModal.value = false
    launchAsForm.userId = ''
    launchAsForm.labSlug = ''

    showAlert(
      data.bridged
        ? `${data.message}. Open your RangeBox to access the lab.`
        : `${data.message}. Launch a standalone RangeBox first, then use the Impersonate button.`
    )

    // Refresh sessions to show the new admin-initiated session
    await refreshSessionsHealth()
  } catch (e) {
    launchAsError.value = e.response?.data?.detail || 'Failed to launch lab. Check that the student has no active session.'
  } finally {
    launchAsLoading.value = false
  }
}

// Curriculum state
const curriculumTracks = ref([])
const curriculumLoading = ref(false)
const expandedCurriculumTracks = ref({})
const showCreateTrackModal = ref(false)
const showEditTrackModal = ref(false)
const showCreateLevelModal = ref(false)
const showEditLevelModal = ref(false)
const trackForm = reactive({ name: '', slug: '', description: '', icon: '', color: '#3b82f6', is_active: true })
const levelForm = reactive({ name: '', description: '' })
const levelFormTrack = ref(null)
const editingTrackId = ref(null)
const editingLevelId = ref(null)

const toggleCurriculumTrack = (id) => {
  expandedCurriculumTracks.value[id] = !expandedCurriculumTracks.value[id]
}

const fetchCurriculum = async () => {
  curriculumLoading.value = true
  try {
    const { data } = await axios.get('/admin/curriculum/tracks')
    curriculumTracks.value = data
  } catch (e) {
    showAlert('Failed to load curriculum', 'error')
  } finally {
    curriculumLoading.value = false
  }
}

const createTrack = async () => {
  try {
    await axios.post('/admin/curriculum/tracks', trackForm)
    showCreateTrackModal.value = false
    Object.assign(trackForm, { name: '', slug: '', description: '', icon: '', color: '#3b82f6', is_active: true })
    fetchCurriculum()
    showAlert('Track created')
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Failed to create track', 'error')
  }
}

const editTrack = (track) => {
  editingTrackId.value = track.id
  Object.assign(trackForm, { name: track.name, description: track.description || '', icon: track.icon || '', color: track.color || '#3b82f6', is_active: track.is_active })
  showEditTrackModal.value = true
}

const updateTrack = async () => {
  try {
    await axios.put(`/admin/curriculum/tracks/${editingTrackId.value}`, trackForm)
    showEditTrackModal.value = false
    fetchCurriculum()
    showAlert('Track updated')
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Failed to update track', 'error')
  }
}

const deleteTrack = async (track) => {
  const msg = track.lab_count > 0
    ? `Delete track "${track.name}"?\n\nThis will remove ${track.level_count} levels and unassign ${track.lab_count} labs. Labs will not be deleted but will no longer belong to this track.`
    : `Delete track "${track.name}" and its ${track.level_count} levels?\n\nThis cannot be undone.`
  if (!confirm(msg)) return
  try {
    const { data } = await axios.delete(`/admin/curriculum/tracks/${track.id}`)
    fetchCurriculum()
    showAlert(data.message || 'Track deleted')
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Failed to delete track', 'error')
  }
}

const openCreateLevelModal = (track) => {
  levelFormTrack.value = track
  Object.assign(levelForm, { name: '', description: '' })
  showCreateLevelModal.value = true
}

const createLevel = async () => {
  try {
    await axios.post(`/admin/curriculum/tracks/${levelFormTrack.value.id}/levels`, levelForm)
    showCreateLevelModal.value = false
    fetchCurriculum()
    showAlert('Level created')
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Failed to create level', 'error')
  }
}

const editLevel = (level) => {
  editingLevelId.value = level.id
  Object.assign(levelForm, { name: level.name, description: level.description || '' })
  showEditLevelModal.value = true
}

const updateLevel = async () => {
  try {
    await axios.put(`/admin/curriculum/levels/${editingLevelId.value}`, levelForm)
    showEditLevelModal.value = false
    fetchCurriculum()
    showAlert('Level updated')
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Failed to update level', 'error')
  }
}

const deleteLevel = async (level) => {
  if (!confirm(`Delete level "${level.name}"?`)) return
  try {
    await axios.delete(`/admin/curriculum/levels/${level.id}`)
    fetchCurriculum()
    showAlert('Level deleted')
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Failed to delete level', 'error')
  }
}

// Create Lab state
const showCreateLabModal = ref(false)
const createLabMode = ref('yaml')
const createLabForm = reactive({
  name: '', slug: '', description: '', scenario: '', difficulty: 'beginner', category: 'general',
  duration_minutes: 60, level_id: null, compose_file: '', flag: '', visibility: 'public',
  lab_yaml: '', objectives: '', hints: ''
})
const yamlParsed = ref(null)
const yamlParseError = ref('')

const openCreateLabModal = () => {
  Object.assign(createLabForm, {
    name: '', slug: '', description: '', scenario: '', difficulty: 'beginner', category: 'general',
    duration_minutes: 60, level_id: null, compose_file: '', flag: '', visibility: 'public',
    lab_yaml: '', objectives: '', hints: ''
  })
  createLabMode.value = 'yaml'
  yamlParsed.value = null
  yamlParseError.value = ''
  if (curriculumTracks.value.length === 0) fetchCurriculum()
  showCreateLabModal.value = true
}

const parseLabYaml = () => {
  yamlParsed.value = null
  yamlParseError.value = ''
  if (!createLabForm.lab_yaml.trim()) return
  try {
    // Simple YAML parser for lab.yaml — handles the key fields we need
    const text = createLabForm.lab_yaml
    const parsed = {}
    // Extract simple key: value fields
    const simpleFields = ['name', 'description', 'difficulty', 'category', 'duration_minutes', 'flag', 'visibility']
    for (const field of simpleFields) {
      const match = text.match(new RegExp(`^${field}:\\s*(?:"([^"]*?)"|'([^']*?)'|(.+?))\\s*$`, 'm'))
      if (match) parsed[field] = (match[1] ?? match[2] ?? match[3]).trim()
    }
    // Extract scenario (multiline block after "scenario: |")
    const scenarioMatch = text.match(/^scenario:\s*\|\s*\n((?:[ \t]+.+\n?)+)/m)
    if (scenarioMatch) parsed.scenario = scenarioMatch[1].replace(/^ {2}/gm, '').trim()
    // Extract objectives count
    const objMatches = text.match(/^objectives:\s*\n((?:\s*-\s*.+\n?)+)/m)
    if (objMatches) {
      const items = objMatches[1].match(/^\s*-\s*(.+)/gm)
      parsed.objectives_count = items ? items.length : 0
    }
    // Extract hints count
    const hintMatches = text.match(/^hints:\s*\n((?:\s+.+\n?)+)/m)
    if (hintMatches) {
      const items = hintMatches[1].match(/^\s*-\s*text:/gm)
      parsed.hints_count = items ? items.length : 0
    }
    // Extract test steps count
    const testMatch = text.match(/^test:\s*\n\s*steps:\s*\n((?:\s+.+\n?)+)/m)
    if (testMatch) {
      const items = testMatch[1].match(/^\s*-\s*name:/gm)
      parsed.test_steps_count = items ? items.length : 0
    }
    yamlParsed.value = parsed
    // Auto-fill form fields from parsed YAML
    if (parsed.name) createLabForm.name = parsed.name
    if (parsed.difficulty) createLabForm.difficulty = parsed.difficulty
    if (parsed.category) createLabForm.category = parsed.category
    if (parsed.duration_minutes) createLabForm.duration_minutes = parseInt(parsed.duration_minutes) || 60
    if (parsed.flag) createLabForm.flag = parsed.flag
    if (parsed.visibility) createLabForm.visibility = parsed.visibility
    if (parsed.description) createLabForm.description = parsed.description
  } catch (e) {
    yamlParseError.value = 'Failed to parse YAML: ' + e.message
  }
}

const createNewLab = async () => {
  try {
    const payload = { ...createLabForm }
    if (!payload.level_id) delete payload.level_id
    // Clean up empty strings to let backend use YAML-parsed values
    for (const key of ['scenario', 'objectives', 'hints', 'flag', 'lab_yaml']) {
      if (!payload[key]) delete payload[key]
    }
    await axios.post('/admin/labs', payload)
    showCreateLabModal.value = false
    showAlert('Exercise created')
    fetchAll()
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Failed to create exercise', 'error')
  }
}

// Compose modal state
const showLabEditModal = ref(false)
const labEditTab = ref('details')

// Delegates to the shared global toast (components/Toast.vue), which also
// carries the FastAPI 422 normalization this function used to do inline.
// Kept as a wrapper so the ~150 existing call sites stay unchanged.
const showAlert = (message, type = 'success') => showToast(message, type, 5000)

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  // Backend stores naive UTC — append 'Z' so JS knows it's UTC, then display in CST
  const d = new Date(dateStr.endsWith('Z') || dateStr.includes('+') ? dateStr : dateStr + 'Z')
  return d.toLocaleString('en-US', { timeZone: 'America/Chicago' })
}

const isDiagnosticEvent = (event) => {
  if (event.actor_role === 'admin') return true
  if (event.detail) {
    try {
      const obj = JSON.parse(event.detail)
      if (obj.source === 'diagnostic') return true
    } catch {}
  }
  return false
}

const formatActivityDetail = (detail) => {
  if (!detail) return ''
  try {
    const obj = JSON.parse(detail)
    const parts = []
    if (obj.time_to_solve_seconds != null) {
      const mins = Math.floor(obj.time_to_solve_seconds / 60)
      const secs = obj.time_to_solve_seconds % 60
      parts.push(mins > 0 ? `Solve time: ${mins}m ${secs}s` : `Solve time: ${secs}s`)
    }
    if (obj.attempts != null) parts.push(`Attempts: ${obj.attempts}`)
    if (obj.hints_used != null) parts.push(`Hints: ${obj.hints_used}`)
    if (obj.hint_number != null) parts.push(`Hint #${obj.hint_number}`)
    for (const [k, v] of Object.entries(obj)) {
      if (['time_to_solve_seconds', 'attempts', 'hints_used', 'hint_number', 'source'].includes(k)) continue
      parts.push(`${k.replace(/_/g, ' ')}: ${v}`)
    }
    return parts.join(' · ')
  } catch {
    return detail
  }
}

const fetchAll = async () => {
  try {
    const [statsRes, usersRes, pendingRes, labsRes, sessionsRes, historyRes, vpnPeersRes, vpnStatusRes] = await Promise.all([
      axios.get('/admin/stats'),
      axios.get('/admin/users'),
      axios.get('/admin/users/pending'),
      axios.get('/admin/labs'),
      axios.get('/admin/sessions/active'),
      axios.get('/admin/sessions/history', { params: { per_page: 50 } }),
      axios.get('/admin/vpn/peers').catch(() => ({ data: { peers: [] } })),
      axios.get('/admin/vpn/status').catch(() => ({ data: { registered_count: 0, unregistered_count: 0, registered: [], unregistered: [] } }))
    ])
    stats.value = statsRes.data
    users.value = usersRes.data
    pendingUsers.value = pendingRes.data
    labs.value = labsRes.data
    activeSessions.value = sessionsRes.data
    // Session history now returns paginated response
    sessionHistory.value = historyRes.data.sessions || historyRes.data
    sessionHistoryTotal.value = historyRes.data.total || 0
    sessionHistoryPages.value = historyRes.data.pages || 0
    sessionHistoryPage.value = historyRes.data.page || 1
    vpnPeers.value = vpnPeersRes.data.peers || []
    vpnStatus.value = vpnStatusRes.data
  } catch (e) {
    showAlert('Failed to load data', 'error')
  }
  // Load session health in background — it queries Docker per-session and can take 30s+
  axios.get('/admin/sessions/health').then(res => {
    sessionsHealth.value = res.data
    checkImpersonationStatus()
  }).catch(() => {})
}

const refreshSessionsHealth = async () => {
  loadingHealth.value = true
  try {
    const { data } = await axios.get('/admin/sessions/health')
    sessionsHealth.value = data
  } catch (e) {
    showAlert('Failed to refresh session health', 'error')
  } finally {
    loadingHealth.value = false
  }
}

const formatTimeRemaining = (seconds) => {
  if (!seconds || seconds <= 0) return '00:00:00'
  const hrs = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60
  return `${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
}

onMounted(() => {
  fetchAll()
  fetchCurriculum()
  fetchDashboardHealth()
  healthPollTimer = setInterval(fetchDashboardHealth, 5 * 60 * 1000)
})

onUnmounted(() => {
  if (healthPollTimer) clearInterval(healthPollTimer)
  if (_testerPollTimer) { clearTimeout(_testerPollTimer); _testerPollTimer = null }
  if (_provisionEventSource) { _provisionEventSource.close(); _provisionEventSource = null }
})

/**
 * Extract a human-readable error message from an API error response.
 * Handles both string details (HTTPException) and array details (Pydantic 422).
 */
const parseApiError = (error, fallback = 'An error occurred') => {
  const detail = error.response?.data?.detail
  if (!detail) return fallback
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map(err => {
        const field = err.loc?.slice(-1)[0] || 'field'
        const label = field.replace(/_/g, ' ')
        return `${label.charAt(0).toUpperCase() + label.slice(1)}: ${err.msg}`
      })
      .join('. ')
  }
  return fallback
}

/**
 * Validate a password against complexity requirements.
 * Returns an array of failure reasons (empty if valid).
 */
const validatePasswordComplexity = (password) => {
  const errors = []
  if (!password || password.length < 8) errors.push('Password must be at least 8 characters')
  if (password && !/[A-Z]/.test(password)) errors.push('Password must contain at least one uppercase letter')
  if (password && !/[a-z]/.test(password)) errors.push('Password must contain at least one lowercase letter')
  if (password && !/[0-9]/.test(password)) errors.push('Password must contain at least one number')
  return errors
}

// User actions
const createUser = async () => {
  // Frontend validation
  const errors = []
  if (!newUser.username || newUser.username.trim().length < 3) {
    errors.push('Username must be at least 3 characters')
  } else if (!/^[a-zA-Z][a-zA-Z0-9_-]*$/.test(newUser.username)) {
    errors.push('Username must start with a letter and contain only letters, numbers, underscores, and hyphens')
  }
  if (!newUser.email || !/^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/.test(newUser.email)) {
    errors.push('A valid email address is required')
  }
  errors.push(...validatePasswordComplexity(newUser.password))
  if (errors.length) {
    showAlert(errors.join('. '), 'error')
    return
  }

  try {
    await axios.post('/admin/users/create', newUser)
    showAlert('User created successfully')
    Object.assign(newUser, { username: '', email: '', password: '', is_approved: false, role: 'student' })
    showCreateForm.value = false
    fetchAll()
  } catch (e) {
    showAlert(parseApiError(e, 'Failed to create user'), 'error')
  }
}

const approveUser = async (id) => {
  try {
    await axios.post(`/admin/users/approve?user_id=${id}&approved=true`)
    showAlert('User approved')
    fetchAll()
  } catch (e) {
    showAlert('Failed to approve user', 'error')
  }
}

const unlockUser = async (id) => {
  try {
    await axios.post(`/admin/users/${id}/unlock`)
    showAlert('User unlocked')
    fetchAll()
  } catch (e) {
    showAlert('Failed to unlock user', 'error')
  }
}

const toggleUserActive = async (user) => {
  // Prevent admin from disabling themselves
  try {
    const me = JSON.parse(localStorage.getItem('user') || '{}')
    if (user.id === me.id && user.is_active) {
      showAlert('You cannot disable your own account', 'error')
      return
    }
  } catch {}
  try {
    await axios.put(`/admin/users/${user.id}`, { is_active: !user.is_active })
    showAlert(user.is_active ? `${user.username} disabled` : `${user.username} enabled`)
    fetchAll()
  } catch (e) {
    showAlert('Failed to toggle user status', 'error')
  }
}

const deleteUser = async (id) => {
  if (!confirm('Are you sure you want to delete this user?')) return
  try {
    await axios.delete(`/admin/users/${id}`)
    showAlert('User deleted')
    fetchAll()
  } catch (e) {
    showAlert('Failed to delete user', 'error')
  }
}

const openUserDetailsModal = async (userId) => {
  showUserDetailsModal.value = true
  loadingUserDetails.value = true
  userDetails.value = null
  
  try {
    const { data } = await axios.get(`/admin/users/${userId}/details`)
    userDetails.value = data
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Failed to load user details', 'error')
    showUserDetailsModal.value = false
  } finally {
    loadingUserDetails.value = false
  }
}

const resetLabForUser = async (userId, labId, labName) => {
  if (!confirm(`Are you sure you want to reset "${labName}" for this user? This will:\n\n- Delete the completion record\n- Clear all flag attempts and hint requests\n- Stop any active session for this exercise\n\nThe user will be able to replay this exercise from the beginning.`)) {
    return
  }
  
  resettingLab.value = true
  try {
    const { data } = await axios.post(`/admin/users/${userId}/labs/${labId}/reset`)
    showAlert(data.message || 'Exercise reset successfully', 'success')
    // Refresh user details
    await openUserDetailsModal(userId)
    // Refresh main user list
    fetchAll()
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Failed to reset exercise', 'error')
  } finally {
    resettingLab.value = false
  }
}

const openEditUserModal = (user) => {
  editUser.value = user
  editForm.username = user.username || ''
  editForm.email = user.email || ''
  editForm.password = ''
  editForm.confirmPassword = ''
  editForm.is_approved = user.is_approved || false
  editForm.role = user.role || 'student'
  editForm.is_active = user.is_active !== undefined ? user.is_active : true
  editForm.must_change_password = user.must_change_password || false
  
  // Clear errors
  editErrors.username = ''
  editErrors.email = ''
  editErrors.password = ''
  editErrors.confirmPassword = ''
  editErrorMessage.value = ''
  editSuccessMessage.value = ''
  
  showEditUserModal.value = true
}

const validateEditForm = () => {
  let isValid = true
  
  // Clear previous errors
  editErrors.username = ''
  editErrors.email = ''
  editErrors.password = ''
  editErrors.confirmPassword = ''
  
  // Validate username if provided
  if (editForm.username) {
    if (editForm.username.length < 3 || editForm.username.length > 50) {
      editErrors.username = 'Username must be between 3 and 50 characters'
      isValid = false
    } else if (!/^[a-zA-Z][a-zA-Z0-9_-]*$/.test(editForm.username)) {
      editErrors.username = 'Username must start with a letter and contain only letters, numbers, underscores, and hyphens'
      isValid = false
    }
  }
  
  // Validate email if provided
  if (editForm.email) {
    const emailRegex = /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/
    if (!emailRegex.test(editForm.email)) {
      editErrors.email = 'Invalid email format'
      isValid = false
    }
  }
  
  // Validate password if provided
  if (editForm.password) {
    if (editForm.password.length < 8) {
      editErrors.password = 'Password must be at least 8 characters'
      isValid = false
    } else if (!/[A-Z]/.test(editForm.password)) {
      editErrors.password = 'Password must contain at least one uppercase letter'
      isValid = false
    } else if (!/[a-z]/.test(editForm.password)) {
      editErrors.password = 'Password must contain at least one lowercase letter'
      isValid = false
    } else if (!/[0-9]/.test(editForm.password)) {
      editErrors.password = 'Password must contain at least one number'
      isValid = false
    }
    
    // Validate password confirmation
    if (editForm.password !== editForm.confirmPassword) {
      editErrors.confirmPassword = 'Passwords do not match'
      isValid = false
    }
  } else if (editForm.confirmPassword) {
    editErrors.confirmPassword = 'Please enter a password first'
    isValid = false
  }
  
  return isValid
}

const saveUserEdits = async () => {
  editErrorMessage.value = ''
  editSuccessMessage.value = ''
  
  if (!validateEditForm()) {
    return
  }
  
  editLoading.value = true
  
  try {
    // Build update payload - only include fields that have changed
    const payload = {}
    
    if (editForm.username !== editUser.value.username) {
      payload.username = editForm.username
    }
    if (editForm.email !== editUser.value.email) {
      payload.email = editForm.email
    }
    if (editForm.password) {
      payload.password = editForm.password
    }
    if (editForm.is_approved !== editUser.value.is_approved) {
      payload.is_approved = editForm.is_approved
    }
    if (editForm.role !== (editUser.value.role || 'student')) {
      payload.role = editForm.role
    }
    if (editForm.is_active !== (editUser.value.is_active !== undefined ? editUser.value.is_active : true)) {
      payload.is_active = editForm.is_active
    }
    if (editForm.must_change_password !== (editUser.value.must_change_password || false)) {
      payload.must_change_password = editForm.must_change_password
    }
    
    await axios.put(`/admin/users/${editUser.value.id}`, payload)
    
    editSuccessMessage.value = 'User updated successfully'
    showAlert('User updated successfully')
    
    // Refresh user list
    await fetchAll()
    
    // Close modal after short delay
    setTimeout(() => {
      showEditUserModal.value = false
    }, 1000)
  } catch (error) {
    const msg = parseApiError(error, 'Failed to update user. Please try again.')
    editErrorMessage.value = msg
    showAlert(msg, 'error')
  } finally {
    editLoading.value = false
  }
}

// Disk management actions
const formatBytes = (bytes) => {
  if (bytes >= 1073741824) return (bytes / 1073741824).toFixed(1) + ' GB'
  if (bytes >= 1048576) return (bytes / 1048576).toFixed(1) + ' MB'
  if (bytes >= 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return bytes + ' B'
}

const fetchDiskUsage = async () => {
  diskUsageLoading.value = true
  try {
    const { data } = await axios.get('/admin/docker/disk-usage')
    diskUsage.value = data
  } catch (e) {
    showAlert('Failed to load disk usage: ' + (e.response?.data?.detail || e.message), 'error')
  } finally {
    diskUsageLoading.value = false
  }
}

const openDiskManagement = () => {
  showDiskModal.value = true
  fetchDiskUsage()
}

const pruneImages = async () => {
  if (!confirm('Remove all unused Docker images?\n\nExercises will rebuild their images on next student launch (1-3 minute delay).')) return
  pruningImages.value = true
  try {
    const { data } = await axios.post('/admin/docker/prune-images')
    showAlert(data.message)
    fetchDiskUsage()
  } catch (e) {
    showAlert('Failed to prune images: ' + (e.response?.data?.detail || e.message), 'error')
  } finally {
    pruningImages.value = false
  }
}

const pruneBuildCache = async () => {
  if (!confirm('Remove Docker build cache?\n\nFuture image builds will take longer as cached layers must be rebuilt from scratch.')) return
  pruningBuildCache.value = true
  try {
    const { data } = await axios.post('/admin/docker/prune-build-cache')
    showAlert(data.message)
    fetchDiskUsage()
  } catch (e) {
    showAlert('Failed to prune build cache: ' + (e.response?.data?.detail || e.message), 'error')
  } finally {
    pruningBuildCache.value = false
  }
}

const deleteLabImages = async (lab) => {
  if (!confirm(`Delete cached Docker images for "${lab.name}"?\n\nThe exercise will rebuild on its next launch (1-3 minute delay for the first student).`)) return
  deletingLabImages.value = { ...deletingLabImages.value, [lab.id]: true }
  try {
    const { data } = await axios.delete(`/admin/labs/${lab.id}/images`)
    showAlert(data.message)
  } catch (e) {
    showAlert('Failed to delete images: ' + (e.response?.data?.detail || e.message), 'error')
  } finally {
    deletingLabImages.value = { ...deletingLabImages.value, [lab.id]: false }
  }
}

// Lab actions
const toggleLab = async (id) => {
  try {
    await axios.post(`/admin/labs/${id}/toggle`)
    fetchAll()
  } catch (e) {
    showAlert('Failed to toggle exercise', 'error')
  }
}

const openLabEditModal = async (lab) => {
  try {
    const [{ data }, _] = await Promise.all([
      axios.get(`/admin/labs/${lab.id}/details`),
      trackCatalog.value.length ? Promise.resolve() :
        axios.get('/instructor/tracks-and-levels').then(r => { trackCatalog.value = r.data.tracks || [] })
    ])
    editLab.value = { ...data }
    // Resolve current track from level_id
    const lvlId = data.level_id
    editTrackId.value = null
    if (lvlId) {
      const owner = trackCatalog.value.find(t => t.levels.some(l => l.id === lvlId))
      if (owner) editTrackId.value = owner.id
    }
    labEditTab.value = 'details'
    // Never carry a revealed flag from the previously opened exercise into this
    // one: the value would be wrong AND still on screen.
    revealedFlag.value = null
    flagRevealError.value = ''
    flagCopied.value = false
    showLabEditModal.value = true
  } catch (e) {
    showAlert('Failed to load exercise details', 'error')
  }
}

const revealedFlag = ref(null)
const flagRevealLoading = ref(false)
const flagRevealError = ref('')
const flagCopied = ref(false)

const revealFlag = async (labId) => {
  flagRevealLoading.value = true
  flagRevealError.value = ''
  try {
    const { data } = await axios.get(`/instructor/labs/${labId}/flag`)
    revealedFlag.value = data
  } catch (e) {
    flagRevealError.value = e.response?.data?.detail || 'Could not load the flag for this exercise.'
  } finally {
    flagRevealLoading.value = false
  }
}

const copyFlag = async () => {
  if (!revealedFlag.value?.flag) return
  try {
    await navigator.clipboard.writeText(revealedFlag.value.flag)
    flagCopied.value = true
    setTimeout(() => { flagCopied.value = false }, 1500)
  } catch (e) {
    flagRevealError.value = 'Clipboard unavailable. Select the flag and copy it manually.'
  }
}

const saveLabEdit = async () => {
  try {
    // Build payload explicitly so we can send level_id: null when uncategorizing
    const payload = {
      name: editLab.value.name,
      duration_minutes: editLab.value.duration_minutes,
      difficulty: editLab.value.difficulty,
      level_id: editLab.value.level_id ?? null,
    }
    await Promise.all([
      axios.put(`/admin/labs/${editLab.value.id}`, payload),
      axios.put(`/admin/labs/${editLab.value.id}/compose`, { compose_file: editLab.value.compose_file || '' })
    ])
    showAlert('Exercise updated successfully')
    showLabEditModal.value = false
    fetchAll()
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Failed to update exercise', 'error')
  }
}

const onEditTrackChange = () => {
  // When the user picks a different track, clear the level selection until they pick one
  if (editLab.value) editLab.value.level_id = null
}

// Computed list of instructors who have created labs (for filter dropdown)
const labCreators = computed(() => {
  const creators = new Map()
  labs.value.forEach(lab => {
    if (lab.created_by && lab.created_by_username) {
      creators.set(lab.created_by, lab.created_by_username)
    }
  })
  return [...creators.entries()].sort((a, b) => a[1].localeCompare(b[1]))
})

// Sidebar track summaries (derived from labs + curriculumTracks for colors)
const adminTrackSummaries = computed(() => {
  const trackMap = new Map()
  for (const lab of labs.value) {
    const slug = lab.track_slug || '__uncategorized__'
    const name = lab.track_name || 'Uncategorized'
    if (!trackMap.has(slug)) {
      const ctMatch = curriculumTracks.value.find(ct => ct.name === name)
      trackMap.set(slug, { slug, name, color: ctMatch?.color || '#3b82f6', lab_count: 0 })
    }
    trackMap.get(slug).lab_count++
  }
  return [...trackMap.values()].sort((a, b) => a.name.localeCompare(b.name))
})

const adminTrackColorMap = computed(() => {
  const m = {}
  for (const t of adminTrackSummaries.value) m[t.name] = t.color
  return m
})

// Flat filtered+sorted list for sidebar-based table view
const adminFilteredLabs = computed(() => {
  let result = labs.value
  if (activeLabStatus.value === 'enabled') result = result.filter(lab => lab.is_active)
  else if (activeLabStatus.value === 'disabled') result = result.filter(lab => !lab.is_active)
  if (selectedTrack.value) result = result.filter(lab => (lab.track_slug || '__uncategorized__') === selectedTrack.value)
  if (labSearch.value.trim()) {
    const q = labSearch.value.toLowerCase()
    result = result.filter(lab => lab.name.toLowerCase().includes(q) || (lab.description || '').toLowerCase().includes(q))
  }
  if (difficultyFilter.value) result = result.filter(lab => lab.difficulty === difficultyFilter.value)
  if (labInstructorFilter.value) result = result.filter(lab => lab.created_by === labInstructorFilter.value)
  if (labVisibilityFilter.value) result = result.filter(lab => (lab.visibility || 'public') === labVisibilityFilter.value)
  return [...result].sort((a, b) => {
    if (a.track_name !== b.track_name) return (a.track_name || '').localeCompare(b.track_name || '')
    const lvA = a.level_number ?? 999; const lvB = b.level_number ?? 999
    if (lvA !== lvB) return lvA - lvB
    return (a.sort_order ?? 0) - (b.sort_order ?? 0)
  })
})

// Computed properties for lab organization by Track → Level
const labsByTrackLevel = computed(() => {
  const grouped = {}
  // Apply filters before grouping
  let filteredLabs = labs.value
  if (labInstructorFilter.value) {
    filteredLabs = filteredLabs.filter(lab => lab.created_by === labInstructorFilter.value)
  }
  if (labVisibilityFilter.value) {
    filteredLabs = filteredLabs.filter(lab => (lab.visibility || 'public') === labVisibilityFilter.value)
  }
  filteredLabs.forEach(lab => {
    const trackName = lab.track_name || 'Uncategorized'
    const levelName = lab.level_name || 'Uncategorized'
    const levelKey = `${trackName}::${levelName}`
    
    if (!grouped[levelKey]) {
      grouped[levelKey] = {
        track_name: trackName,
        level_name: levelName,
        level_number: lab.level_number || 999,
        enabled: [],
        disabled: []
      }
    }
    if (lab.is_active) {
      grouped[levelKey].enabled.push(lab)
    } else {
      grouped[levelKey].disabled.push(lab)
    }
  })
  
  // Sort labs within each level by sort_order or name
  Object.keys(grouped).forEach(key => {
    grouped[key].enabled.sort((a, b) => {
      if (a.sort_order !== undefined && b.sort_order !== undefined) {
        return a.sort_order - b.sort_order
      }
      return a.name.localeCompare(b.name)
    })
    grouped[key].disabled.sort((a, b) => {
      if (a.sort_order !== undefined && b.sort_order !== undefined) {
        return a.sort_order - b.sort_order
      }
      return a.name.localeCompare(b.name)
    })
  })
  
  return grouped
})

const enabledLevels = computed(() => {
  return Object.keys(labsByTrackLevel.value)
    .filter(key => labsByTrackLevel.value[key].enabled.length > 0)
    .sort((a, b) => {
      const levelA = labsByTrackLevel.value[a]
      const levelB = labsByTrackLevel.value[b]
      // Sort by track name, then level number
      if (levelA.track_name !== levelB.track_name) {
        return levelA.track_name.localeCompare(levelB.track_name)
      }
      return (levelA.level_number || 999) - (levelB.level_number || 999)
    })
})

const disabledLevels = computed(() => {
  return Object.keys(labsByTrackLevel.value)
    .filter(key => labsByTrackLevel.value[key].disabled.length > 0)
    .sort((a, b) => {
      const levelA = labsByTrackLevel.value[a]
      const levelB = labsByTrackLevel.value[b]
      // Sort by track name, then level number
      if (levelA.track_name !== levelB.track_name) {
        return levelA.track_name.localeCompare(levelB.track_name)
      }
      return (levelA.level_number || 999) - (levelB.level_number || 999)
    })
})

const enabledLabsCount = computed(() => {
  let filtered = labs.value
  if (labInstructorFilter.value) {
    filtered = filtered.filter(lab => lab.created_by === labInstructorFilter.value)
  }
  if (labVisibilityFilter.value) {
    filtered = filtered.filter(lab => (lab.visibility || 'public') === labVisibilityFilter.value)
  }
  return filtered.filter(lab => lab.is_active).length
})

const disabledLabsCount = computed(() => {
  let filtered = labs.value
  if (labInstructorFilter.value) {
    filtered = filtered.filter(lab => lab.created_by === labInstructorFilter.value)
  }
  if (labVisibilityFilter.value) {
    filtered = filtered.filter(lab => (lab.visibility || 'public') === labVisibilityFilter.value)
  }
  return filtered.filter(lab => !lab.is_active).length
})

const toggleCategory = (category) => {
  expandedCategories.value[category] = !expandedCategories.value[category]
}

const expandAllCategories = (tab) => {
  const levels = tab === 'enabled' ? enabledLevels.value : disabledLevels.value
  levels.forEach(key => { expandedCategories.value[key] = true })
}

const collapseAllCategories = (tab) => {
  const levels = tab === 'enabled' ? enabledLevels.value : disabledLevels.value
  levels.forEach(key => { expandedCategories.value[key] = false })
}

const bulkToggleCategory = async (levelKey, enable) => {
  const group = labsByTrackLevel.value[levelKey]
  if (!group) return
  const labs = enable ? group.disabled : group.enabled
  const labIds = labs.map(l => l.id)
  if (!labIds.length) return
  try {
    await axios.post('/admin/labs/bulk-toggle', { lab_ids: labIds, is_active: enable })
    fetchAll()
    showAlert(`${enable ? 'Enabled' : 'Disabled'} ${labIds.length} exercises in ${group.track_name} → ${group.level_name}`, 'success')
  } catch (e) {
    showAlert('Failed to toggle exercises', 'error')
  }
}

const visibilityLabels = { public: 'Public', course: 'Course', pending_public: 'Pending Review', draft: 'Draft' }

const setLabVisibility = async (lab, newVisibility) => {
  try {
    await axios.put(`/admin/labs/${lab.id}`, { visibility: newVisibility })
    lab.visibility = newVisibility
    if (allLabsForAssign.value) {
      const match = allLabsForAssign.value.find(l => l.id === lab.id)
      if (match) match.visibility = newVisibility
    }
    showAlert(`"${lab.name}" visibility set to ${visibilityLabels[newVisibility] || newVisibility}`)
  } catch (e) {
    showAlert('Failed to update exercise visibility', 'error')
  }
}

// Auto-expand all levels on mount
watch(labs, () => {
  if (labs.value.length > 0) {
    const allLevels = [...enabledLevels.value, ...disabledLevels.value]
    allLevels.forEach(levelKey => {
      if (expandedCategories.value[levelKey] === undefined) {
        expandedCategories.value[levelKey] = true
      }
    })
  }
}, { immediate: true })

// Session actions
const terminateSession = async (id) => {
  try {
    await axios.post(`/admin/sessions/terminate/${id}`)
    showAlert('Session terminated')
    // Remove from local UI immediately so user doesn't double-click
    if (sessionsHealth.value.sessions) {
      sessionsHealth.value.sessions = sessionsHealth.value.sessions.filter(s => s.session_id !== id)
      sessionsHealth.value.total_sessions = sessionsHealth.value.sessions.length
    }
    fetchAll()
  } catch (e) {
    // If 400, session was already stopped — just remove it from UI
    if (e.response?.status === 400) {
      showAlert('Session already stopped')
      if (sessionsHealth.value.sessions) {
        sessionsHealth.value.sessions = sessionsHealth.value.sessions.filter(s => s.session_id !== id)
        sessionsHealth.value.total_sessions = sessionsHealth.value.sessions.length
      }
    } else {
      showAlert('Failed to terminate session', 'error')
    }
  }
}

const resetStaleSession = async (sessionId, username) => {
  if (!confirm(`Reset stale session for ${username}? This marks the session as stopped so they can start a new lab.`)) return
  try {
    const res = await axios.post(`/admin/sessions/${sessionId}/reset-stale`)
    showAlert(res.data.message)
    refreshSessionsHealth()
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Failed to reset stale session', 'error')
  }
}

const resyncSessionVpn = async (sessionId, username) => {
  if (!confirm(`Re-sync VPN for ${username}? This removes and re-adds their WireGuard peer and refreshes firewall rules.`)) return
  try {
    const res = await axios.post(`/admin/sessions/${sessionId}/resync-vpn`)
    showAlert(res.data.message)
    refreshSessionsHealth()
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Failed to re-sync VPN', 'error')
  }
}

const terminateAll = async () => {
  if (!confirm('Are you sure you want to terminate ALL active sessions?')) return
  try {
    const res = await axios.post('/admin/sessions/terminate-all')
    showAlert(res.data.message)
    fetchAll()
  } catch (e) {
    showAlert('Failed to terminate sessions', 'error')
  }
}


const fetchSessionHistory = async (page = 1) => {
  sessionHistoryLoading.value = true
  try {
    const params = { page, per_page: 50 }
    const { start, end } = getTimeRangeDates(sessionsTimeRange.value, sessionsCustomStart.value, sessionsCustomEnd.value)
    if (start) params.start_date = start
    if (end) params.end_date = end
    const { data } = await axios.get('/admin/sessions/history', { params })
    sessionHistory.value = data.sessions
    sessionHistoryTotal.value = data.total
    sessionHistoryPages.value = data.pages
    sessionHistoryPage.value = data.page
  } catch (e) {
    showAlert('Failed to load session history', 'error')
  } finally {
    sessionHistoryLoading.value = false
  }
}

const clearSessionHistory = async () => {
  if (!confirm('Are you sure you want to clear all session history? This cannot be undone.')) return
  try {
    const res = await axios.delete('/admin/sessions/history')
    showAlert(res.data.message)
    sessionHistory.value = []
    sessionHistoryTotal.value = 0
    sessionHistoryPages.value = 0
    sessionHistoryPage.value = 1
  } catch (e) {
    showAlert('Failed to clear history', 'error')
  }
}

// VPN actions
const syncVpnPeers = async () => {
  syncing.value = true
  try {
    const res = await axios.post('/admin/vpn/sync')
    showAlert(res.data.message)
    fetchAll()
  } catch (e) {
    showAlert('Failed to sync peers', 'error')
  } finally {
    syncing.value = false
  }
}

const registerPeer = async (userId) => {
  try {
    await axios.post(`/admin/vpn/register/${userId}`)
    showAlert('Peer registered successfully')
    fetchAll()
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Failed to register peer', 'error')
  }
}

const removePeer = async (userId) => {
  if (!confirm('Are you sure you want to remove this VPN peer?')) return
  try {
    await axios.delete(`/admin/vpn/peer/${userId}`)
    showAlert('Peer removed')
    fetchAll()
  } catch (e) {
    showAlert('Failed to remove peer', 'error')
  }
}

const removePeerByKey = async (publicKey) => {
  if (!confirm('Are you sure you want to remove this unknown VPN peer?')) return
  try {
    // URL encode the public key for the path
    const encodedKey = encodeURIComponent(publicKey)
    await axios.delete(`/admin/vpn/peer-by-key/${encodedKey}`)
    showAlert('Peer removed')
    fetchAll()
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Failed to remove peer', 'error')
  }
}

const repairPeer = async (userId) => {
  if (!confirm('Repair this peer? Any conflicting peer registrations will be removed and the DB peer will be re-added.')) return
  try {
    const res = await axios.post(`/admin/vpn/peers/${userId}/repair`)
    const removedCount = (res.data?.removed_peers || []).length
    showAlert(`${res.data?.message || 'Peer repaired'} (cleared ${removedCount} stale peer${removedCount === 1 ? '' : 's'})`)
    fetchAll()
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Failed to repair peer', 'error')
  }
}

// ==================== Course Management ====================
const adminCourses = ref([])
const managingCourse = ref(null)
const courseManageTab = ref('students')
const courseStudents = ref([])
const courseLabs = ref([])
const allLabsForAssign = ref([])
const selectedLabIds = ref([])
const showAdminCreateCourse = ref(false)
const creatingAdminCourse = ref(false)
const newCourseForm = ref({ name: '', code: '', semester: '', description: '', start_date: '', end_date: '', instructor_id: '' })
const downloadingAdminReport = ref(false)
const expandedAssignCategories = ref({})
const courseFilter = ref('all')
const courseSortKey = ref('created_at')
const courseSortDir = ref('desc')
const studentLabDetails = ref({})  // { userId: [...labs] | 'loading' }
const resettingCourseLab = ref(null)  // "userId-labId" while resetting

const instructorUsers = computed(() => {
  return users.value.filter(u => u.role === 'instructor' || u.role === 'admin')
})

const enrollableUsers = computed(() => {
  const enrolledIds = new Set(courseStudents.value.map(s => s.id))
  return users.value.filter(u => u.role !== 'admin' && !enrolledIds.has(u.id))
})

// Group labs for assignment by Track > Level, excluding already-assigned labs
const assignLabsByTrackLevel = computed(() => {
  const assignedIds = new Set(courseLabs.value.map(l => l.id))
  const grouped = {}
  allLabsForAssign.value.forEach(lab => {
    if (assignedIds.has(lab.id)) return          // skip already-assigned
    const trackName = lab.track_name || 'Uncategorized'
    const levelName = lab.level_name || 'Uncategorized'
    const levelKey = `${trackName}::${levelName}`
    if (!grouped[levelKey]) {
      grouped[levelKey] = {
        track_name: trackName,
        level_name: levelName,
        level_number: lab.level_number || 999,
        labs: []
      }
    }
    grouped[levelKey].labs.push(lab)
  })
  Object.keys(grouped).forEach(key => {
    grouped[key].labs.sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0) || a.name.localeCompare(b.name))
  })
  return grouped
})

const assignLevelKeys = computed(() => {
  return Object.keys(assignLabsByTrackLevel.value).sort((a, b) => {
    const la = assignLabsByTrackLevel.value[a]
    const lb = assignLabsByTrackLevel.value[b]
    if (la.track_name !== lb.track_name) return la.track_name.localeCompare(lb.track_name)
    return (la.level_number || 999) - (lb.level_number || 999)
  })
})

const toggleAssignCategory = (key) => {
  expandedAssignCategories.value[key] = !expandedAssignCategories.value[key]
}

const allAssignExpanded = computed(() => {
  const keys = assignLevelKeys.value
  if (keys.length === 0) return false
  return keys.every(k => expandedAssignCategories.value[k])
})

const toggleAllAssignCategories = () => {
  const expand = !allAssignExpanded.value
  const updated = {}
  assignLevelKeys.value.forEach(k => { updated[k] = expand })
  expandedAssignCategories.value = updated
}

const selectAllInGroup = (levelKey) => {
  const group = assignLabsByTrackLevel.value[levelKey]
  if (!group) return
  const ids = group.labs.map(l => l.id)
  const current = new Set(selectedLabIds.value)
  ids.forEach(id => current.add(id))
  selectedLabIds.value = [...current]
}

// Sort and filter courses
const sortedFilteredCourses = computed(() => {
  let list = [...adminCourses.value]
  // Filter
  if (courseFilter.value === 'active') {
    list = list.filter(c => c.is_active && !c.is_archived)
  } else if (courseFilter.value === 'pending') {
    list = list.filter(c => !c.is_active && !c.is_archived)
  } else if (courseFilter.value === 'archived') {
    list = list.filter(c => c.is_archived)
  }
  // Sort
  const key = courseSortKey.value
  const dir = courseSortDir.value === 'asc' ? 1 : -1
  list.sort((a, b) => {
    let va = a[key], vb = b[key]
    if (key === 'status') {
      va = adminCourseStatus(a).text
      vb = adminCourseStatus(b).text
    }
    if (va == null) va = ''
    if (vb == null) vb = ''
    if (typeof va === 'string') return dir * va.localeCompare(vb)
    return dir * ((va > vb ? 1 : va < vb ? -1 : 0))
  })
  return list
})

const fetchAdminCourses = async () => {
  try {
    const res = await axios.get('/courses/')
    adminCourses.value = res.data.courses
  } catch (e) {
    console.error('Failed to fetch courses', e)
  }
}

const adminCourseStatus = (course) => {
  if (course.is_archived) return { text: 'Archived', class: 'status-badge--muted' }
  const now = new Date()
  const end = new Date(course.end_date)
  const start = new Date(course.start_date)
  if (!course.is_active) return { text: 'Pending Review', class: 'status-badge--warning' }
  if (now > end) return { text: 'Ended', class: 'status-badge--muted' }
  if (now < start) return { text: 'Upcoming', class: 'status-badge--warning' }
  return { text: 'Active', class: 'status-badge--success' }
}

const createAdminCourse = async () => {
  if (!newCourseForm.value.name || !newCourseForm.value.code || !newCourseForm.value.start_date || !newCourseForm.value.end_date) {
    showAlert('Please fill in name, code, start date, and end date', 'error')
    return
  }
  creatingAdminCourse.value = true
  try {
    const payload = {
      name: newCourseForm.value.name,
      code: newCourseForm.value.code,
      semester: newCourseForm.value.semester || '',
      description: newCourseForm.value.description || null,
      start_date: new Date(newCourseForm.value.start_date).toISOString(),
      end_date: new Date(newCourseForm.value.end_date).toISOString(),
    }
    if (newCourseForm.value.instructor_id) {
      payload.instructor_id = Number(newCourseForm.value.instructor_id)
    }
    await axios.post('/courses/', payload)
    showAlert('Course created successfully')
    newCourseForm.value = { name: '', code: '', semester: '', description: '', start_date: '', end_date: '', instructor_id: '' }
    showAdminCreateCourse.value = false
    fetchAdminCourses()
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Failed to create course', 'error')
  } finally {
    creatingAdminCourse.value = false
  }
}

const updateCourseInstructor = async (newId) => {
  if (!managingCourse.value) return
  try {
    await axios.put(`/courses/${managingCourse.value.id}`, { instructor_id: Number(newId) })
    managingCourse.value.instructor_id = Number(newId)
    showAlert('Instructor updated')
    fetchAdminCourses()
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Failed to update instructor', 'error')
  }
}

const openCourseManager = (course) => {
  // Toggle: clicking same course closes panel
  if (managingCourse.value && managingCourse.value.id === course.id) {
    managingCourse.value = null
  } else {
    managingCourse.value = course
  }
}

const fetchCourseStudents = async () => {
  try {
    const res = await axios.get(`/courses/${managingCourse.value.id}/students`)
    courseStudents.value = res.data.students
  } catch (e) {
    showAlert('Failed to load students: ' + (e.response?.data?.detail || e.message), 'error')
  }
}

const fetchCourseLabs = async () => {
  try {
    const res = await axios.get(`/courses/${managingCourse.value.id}`)
    courseLabs.value = res.data.labs
  } catch (e) {
    showAlert('Failed to load course exercises: ' + (e.response?.data?.detail || e.message), 'error')
  }
}

const fetchAllLabsForAssign = async () => {
  try {
    const res = await axios.get('/admin/labs')
    allLabsForAssign.value = res.data
  } catch (e) {
    showAlert('Failed to load exercises for assignment: ' + (e.response?.data?.detail || e.message), 'error')
  }
}

const removeStudent = async (student) => {
  if (!confirm(`Remove ${student.username} from this course?`)) return
  try {
    await axios.delete(`/courses/${managingCourse.value.id}/enroll/${student.id}`)
    showAlert('Student removed')
    fetchCourseStudents()
    fetchAdminCourses()
  } catch (e) {
    showAlert('Failed to remove student', 'error')
  }
}

const toggleStudentLabs = async (student) => {
  // Toggle: if already showing, hide
  if (studentLabDetails.value[student.id]) {
    delete studentLabDetails.value[student.id]
    studentLabDetails.value = { ...studentLabDetails.value }
    return
  }
  // Show loading
  studentLabDetails.value = { ...studentLabDetails.value, [student.id]: 'loading' }
  try {
    const res = await axios.get(`/courses/${managingCourse.value.id}/scoreboard`)
    const entry = res.data.scoreboard.find(e => e.user_id === student.id)
    const labs = res.data.labs.map(lab => {
      const scores = entry?.lab_scores?.[String(lab.id)] || {}
      return {
        lab_id: lab.id,
        lab_name: lab.name,
        completed: scores.completed || false,
        score: scores.score || 0,
        attempts: scores.attempts || 0,
        hints_used: scores.hints_used || 0,
      }
    })
    studentLabDetails.value = { ...studentLabDetails.value, [student.id]: labs }
  } catch (e) {
    showAlert('Failed to load exercise details', 'error')
    delete studentLabDetails.value[student.id]
    studentLabDetails.value = { ...studentLabDetails.value }
  }
}

const resetStudentLab = async (student, lab) => {
  if (!confirm(`Reset "${lab.lab_name}" for ${student.username}? They will need to resubmit.`)) return
  resettingCourseLab.value = `${student.id}-${lab.lab_id}`
  try {
    await axios.post(`/courses/${managingCourse.value.id}/labs/${lab.lab_id}/reset/${student.id}`)
    showAlert(`Reset ${lab.lab_name} for ${student.username}`)
    // Refresh the expanded lab details
    delete studentLabDetails.value[student.id]
    studentLabDetails.value = { ...studentLabDetails.value }
    await toggleStudentLabs(student)
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Failed to reset exercise', 'error')
  } finally {
    resettingCourseLab.value = null
  }
}

const assignSelectedLabs = async () => {
  if (selectedLabIds.value.length === 0) return
  try {
    await axios.post(`/courses/${managingCourse.value.id}/labs`, { lab_ids: selectedLabIds.value })
    showAlert('Exercises assigned')
    selectedLabIds.value = []
    fetchCourseLabs()
    fetchAdminCourses()
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Failed to assign exercises', 'error')
  }
}

const unassignLab = async (lab) => {
  if (!confirm(`Remove "${lab.name}" from this course?`)) return
  try {
    await axios.delete(`/courses/${managingCourse.value.id}/labs/${lab.id}`)
    showAlert('Exercise removed from course')
    fetchCourseLabs()
    fetchAdminCourses()
  } catch (e) {
    showAlert('Failed to remove exercise', 'error')
  }
}


const toggleCourseActive = async (course) => {
  try {
    const res = await axios.post(`/courses/${course.id}/toggle-active`)
    showAlert(res.data.is_active ? 'Course activated' : 'Course deactivated')
    fetchAdminCourses()
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Failed to toggle active', 'error')
  }
}

const archiveCourse = async (course) => {
  if (!confirm(`Archive "${course.name}"? It will be deactivated and hidden from students.`)) return
  try {
    await axios.post(`/courses/${course.id}/archive`)
    showAlert('Course archived')
    fetchAdminCourses()
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Failed to archive', 'error')
  }
}

const unarchiveCourse = async (course) => {
  try {
    await axios.post(`/courses/${course.id}/unarchive`)
    showAlert('Course unarchived (still inactive — activate manually)')
    fetchAdminCourses()
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Failed to unarchive', 'error')
  }
}

const deleteCourse = async (course) => {
  if (!confirm(`Delete course "${course.name}"? This cannot be undone.`)) return
  try {
    await axios.delete(`/courses/${course.id}`)
    showAlert('Course deleted')
    if (managingCourse.value && managingCourse.value.id === course.id) {
      managingCourse.value = null
    }
    fetchAdminCourses()
  } catch (e) {
    showAlert(e.response?.data?.detail || 'Failed to delete course', 'error')
  }
}

const downloadStudentReport = async (student) => {
  try {
    const res = await axios.get(`/courses/${managingCourse.value.id}/report/${student.id}`, {
      responseType: 'blob'
    })
    const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `report_${managingCourse.value.code}_${student.username}.pdf`
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (e) {
    showAlert('Failed to download report', 'error')
  }
}

const downloadClassReportAdmin = async () => {
  downloadingAdminReport.value = true
  try {
    const res = await axios.get(`/courses/${managingCourse.value.id}/report`, {
      responseType: 'blob'
    })
    const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `report_${managingCourse.value.code}_class.pdf`
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (e) {
    showAlert('Failed to download report', 'error')
  } finally {
    downloadingAdminReport.value = false
  }
}

const copyToClipboard = (text) => {
  navigator.clipboard.writeText(text)
  showAlert('Copied to clipboard')
}

const formatDateShort = (dt) => {
  if (!dt) return ''
  const d = new Date(dt.endsWith('Z') || dt.includes('+') ? dt : dt + 'Z')
  return d.toLocaleDateString('en-US', { timeZone: 'America/Chicago', month: 'short', day: 'numeric', year: 'numeric' })
}

// Fetch tab-specific data when switching tabs (immediate: true ensures it
// also fires on mount, so direct navigation like /admin?tab=courses works)
watch(activeTab, (tab) => {
  if (tab === 'courses' && adminCourses.value.length === 0) {
    fetchAdminCourses()
  }
  if (tab === 'settings' && Object.keys(allSettings.value).length === 0) {
    fetchSettings()
  }
  if (tab === 'monitoring') {
    if (activityEvents.value.length === 0) fetchActivity()
  }
  if (tab === 'exercises') {
    if (curriculumTracks.value.length === 0) fetchCurriculum()
    if (!testerRunning.value) checkActiveTestRun()
    if (Object.keys(testerResults.value).length === 0) fetchTesterResults()
  }
  if (tab === 'system') {
    fetchSystemStatus()
    fetchBackups()
    fetchActivityCalendar()
    if (systemSubTab.value === 'tester') {
      if (testerLabList.value.length === 0) fetchTesterLabs()
      if (Object.keys(testerResults.value).length === 0) fetchTesterResults()
      if (!testerRunning.value) checkActiveTestRun()
    }
  }
}, { immediate: true })

// Lazy-load tester data when switching to the Tester sub-tab within System
</script>

<style scoped>
.admin-page {
  min-height: 100vh;
  background: var(--bg-primary);
  padding: 1rem 1.25rem;
}

.admin-container {
  max-width: 1400px;
  margin: 0 auto;
}

/* Header */
.admin-header {
  margin-bottom: 2rem;
}

.page-title {
  font-size: 2rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 0.5rem 0;
}

.page-subtitle {
  font-size: 1rem;
  color: var(--text-muted);
  margin: 0;
}

/* Scan Warnings */
.scan-warnings {
  background: rgba(234, 179, 8, 0.1);
  border: 1px solid rgba(234, 179, 8, 0.3);
  border-radius: 8px;
  margin-bottom: 1rem;
  overflow: hidden;
}
.scan-warnings__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.6rem 1rem;
  color: #eab308;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
}
.scan-warnings__dismiss {
  font-size: 1.2rem;
  opacity: 0.7;
}
.scan-warnings__dismiss:hover { opacity: 1; }
.scan-warnings__list {
  list-style: none;
  padding: 0 1rem 0.6rem;
  margin: 0;
}
.scan-warnings__list li {
  font-size: 0.8rem;
  color: rgba(234, 179, 8, 0.85);
  padding: 0.2rem 0;
  border-top: 1px solid rgba(234, 179, 8, 0.1);
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.stat-card {
  background: var(--bg-secondary);
  border-radius: 12px;
  padding: 1.25rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  border: 1px solid var(--border-color);
  position: relative;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.stat-card--alert {
  border-color: #f59e0b;
  box-shadow: 0 0 0 1px rgba(245, 158, 11, 0.3);
  animation: pending-pulse 2s ease-in-out infinite;
}

.stat-card--alert:hover {
  box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.5);
}

@keyframes pending-pulse {
  0%, 100% { box-shadow: 0 0 0 1px rgba(245, 158, 11, 0.3); }
  50% { box-shadow: 0 0 8px 2px rgba(245, 158, 11, 0.25); }
}

.stat-card__badge {
  position: absolute;
  top: -6px;
  right: -6px;
  background: #ef4444;
  color: white;
  font-size: 0.7rem;
  font-weight: 700;
  min-width: 20px;
  height: 20px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 5px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.stat-card__icon {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-card__icon svg {
  width: 24px;
  height: 24px;
  color: white;
}

.stat-card__icon--users { background: linear-gradient(135deg, #3b82f6, #1d4ed8); }
.stat-card__icon--pending { background: linear-gradient(135deg, #f59e0b, #d97706); }
.stat-card__icon--locked { background: linear-gradient(135deg, #ef4444, #dc2626); }
.stat-card__icon--active { background: linear-gradient(135deg, #22c55e, #16a34a); }
.stat-card__icon--vpn { background: linear-gradient(135deg, #8b5cf6, #7c3aed); }

.stat-card__content {
  display: flex;
  flex-direction: column;
}

.stat-card__value {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1;
}

.stat-card__label {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-top: 0.25rem;
}

/* Panel */
.panel {
  background: var(--bg-secondary);
  border-radius: 12px;
  padding: 1rem;
  border: 1px solid var(--border-color);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.panel-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.panel-section {
  margin-bottom: 1.5rem;
}

.section-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-secondary);
  margin: 0 0 1rem 0;
}

.section-title--warning {
  color: var(--warning);
}

/* Buttons */
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

.btn--primary {
  background: var(--accent);
  color: white;
}

.btn--primary:hover {
  background: #2563eb;
}

.btn--secondary {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.btn--secondary:hover {
  background: var(--nav-label);
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

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Expand Button */
.expand-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: transparent;
  border: none;
  color: var(--accent);
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  padding: 0;
  margin-bottom: 1rem;
}

.expand-icon {
  width: 16px;
  height: 16px;
  transition: transform 0.2s ease;
}

.expand-icon--open {
  transform: rotate(90deg);
}

/* Forms */
.create-form {
  background: var(--bg-tertiary);
  border-radius: 8px;
  padding: 1rem;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.form-stack {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.form-input {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 0.625rem 0.875rem;
  color: var(--text-primary);
  font-size: 0.875rem;
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

.form-select {
  padding: 0.5rem 0.75rem;
  background: var(--bg-deeper);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 0.8125rem;
}

.form-select--inline {
  padding: 0.375rem 0.5rem;
  font-size: 0.8125rem;
}

.select-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--text-secondary);
  font-size: 0.875rem;
}

.form-select--vis {
  padding: 0.25rem 0.375rem;
  font-size: 0.6875rem;
  font-weight: 600;
  border-radius: 4px;
}

.form-select--public { background: rgba(34, 197, 94, 0.15); color: #4ade80; border-color: rgba(34, 197, 94, 0.3); }
.form-select--course { background: rgba(59, 130, 246, 0.15); color: #60a5fa; border-color: rgba(59, 130, 246, 0.3); }
.form-select--pending_public { background: rgba(234, 179, 8, 0.15); color: #facc15; border-color: rgba(234, 179, 8, 0.3); }
.form-select--draft { background: rgba(148, 163, 184, 0.15); color: var(--text-secondary); border-color: rgba(148, 163, 184, 0.3); }

.form-group--inline {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0;
}

.form-group--inline label {
  color: var(--text-secondary);
  font-size: 0.875rem;
  white-space: nowrap;
}

.form-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--text-secondary);
  font-size: 0.875rem;
  cursor: pointer;
}

.checkbox-label input {
  accent-color: var(--accent);
}

/* Tables */
.table-container {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: 0.5rem 0.75rem;
  text-align: left;
  border-bottom: 1px solid var(--border-color);
}

.data-table th {
  font-size: 0.6875rem;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.data-table td {
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.data-table--compact td {
  padding: 0.625rem 1rem;
  font-size: 0.8125rem;
}

.cell-primary {
  color: var(--text-primary);
  font-weight: 500;
}

.masked-email {
  color: var(--text-muted);
  font-size: 0.8rem;
  letter-spacing: 0.02em;
}

.cell-muted {
  color: var(--text-muted);
}

.cell-mono {
  font-family: monospace;
  font-size: 0.8125rem;
}

.cell-actions {
  display: flex;
  gap: 0.5rem;
}

/* Action Buttons */
.action-btn {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  border: none;
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  color: var(--text-secondary);
}

.action-btn svg {
  width: 16px;
  height: 16px;
}

.action-btn--unlock {
  background: rgba(59, 130, 246, 0.15);
  color: var(--accent);
}

.action-btn--unlock:hover {
  background: var(--accent);
  color: white;
}

.action-btn--approve {
  background: rgba(34, 197, 94, 0.15);
  color: var(--success);
}

.action-btn--approve:hover {
  background: var(--success);
  color: white;
}

.action-btn--reset {
  background: rgba(245, 158, 11, 0.15);
  color: var(--warning);
}

.action-btn--reset:hover {
  background: var(--warning);
  color: white;
}

.action-btn--delete {
  background: rgba(239, 68, 68, 0.15);
  color: var(--danger);
}

.action-btn--delete:hover {
  background: var(--danger);
  color: white;
}

.action-btn--test {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
}

.action-btn--test:hover {
  background: #f59e0b;
  color: white;
}

.action-btn--test:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.action-btn--cache {
  background: rgba(168, 85, 247, 0.15);
  color: #a855f7;
}

.action-btn--cache:hover {
  background: #a855f7;
  color: white;
}

.action-btn--cache:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.action-btn--cache .spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.action-btn--available {
  background: rgba(34, 197, 94, 0.15);
  color: #22c55e;
}

.action-btn--available:hover {
  background: #22c55e;
  color: white;
}

/* Status Badges */
.status-badge {
  display: inline-block;
  padding: 0.25rem 0.625rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
}

.status-badge--locked {
  background: rgba(239, 68, 68, 0.15);
  color: var(--danger);
}

.status-badge--admin {
  background: rgba(139, 92, 246, 0.15);
  color: var(--purple);
}

.status-badge--instructor {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
}

.status-badge--approved {
  background: rgba(34, 197, 94, 0.15);
  color: var(--success);
}

.status-badge--pending {
  background: rgba(245, 158, 11, 0.15);
  color: var(--warning);
}

/* VPN Status */
.vpn-status {
  display: flex;
  align-items: center;
  justify-content: center;
}

.vpn-status svg {
  width: 16px;
  height: 16px;
}

.vpn-status--yes {
  color: var(--success);
}

.vpn-status--no {
  color: var(--text-muted);
}

/* Event Badges (color-coded pills for activity/session feeds) */
.event-badge {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  white-space: nowrap;
}

.event-badge--lab_started       { background: rgba(59, 130, 246, 0.15); color: #60a5fa; }
.event-badge--lab_stopped       { background: rgba(100, 116, 139, 0.2); color: #94a3b8; }
.event-badge--lab_completed     { background: rgba(34, 197, 94, 0.15); color: #4ade80; }
.event-badge--flag_correct      { background: rgba(34, 197, 94, 0.15); color: #4ade80; }
.event-badge--flag_incorrect    { background: rgba(239, 68, 68, 0.15); color: #f87171; }
.event-badge--hint_used         { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }
.event-badge--user_registered   { background: rgba(168, 85, 247, 0.15); color: #c084fc; }
.event-badge--user_approved     { background: rgba(168, 85, 247, 0.15); color: #c084fc; }
.event-badge--session_expired   { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }
.event-badge--vpn_downloaded    { background: rgba(6, 182, 212, 0.15); color: #22d3ee; }
.event-badge--course_enrolled   { background: rgba(236, 72, 153, 0.15); color: #f472b6; }
.event-badge--achievement_awarded { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }

/* Diagnostic activity (admin-initiated) */
.event-badge--diagnostic        { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }

.admin-session-tag {
  display: inline-block;
  margin-left: 0.375rem;
  padding: 0.125rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.625rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.diagnostic-tag {
  display: inline-block;
  margin-left: 0.375rem;
  padding: 0.125rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.625rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  background: rgba(245, 158, 11, 0.1);
  color: #d97706;
  border: 1px solid rgba(245, 158, 11, 0.25);
  vertical-align: middle;
}

.activity-row--diagnostic {
  background: rgba(245, 158, 11, 0.03);
}

.activity-row--diagnostic td {
  opacity: 0.75;
}

.activity-row--diagnostic td:nth-child(2) {
  opacity: 1;
}

/* Session status badges */
.event-badge--session-running   { background: rgba(34, 197, 94, 0.15); color: #4ade80; }
.event-badge--session-stopped   { background: rgba(100, 116, 139, 0.2); color: #94a3b8; }
.event-badge--session-expired   { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }
.event-badge--session-error     { background: rgba(239, 68, 68, 0.15); color: #f87171; }

/* Empty State */
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

/* Pending list styles moved to components/AdminPendingTab.vue */

/* Labs List */
.lab-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
  border-bottom: 2px solid var(--border-primary);
}

.lab-tab {
  padding: 0.75rem 1.5rem;
  background: transparent;
  border: none;
  border-bottom: 3px solid transparent;
  color: var(--text-muted);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  margin-bottom: -2px;
}

.lab-tab:hover {
  color: var(--text-primary);
  background: var(--bg-tertiary);
}

.lab-tab--active {
  color: var(--primary);
  border-bottom-color: var(--primary);
}

.labs-toolbar {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-bottom: 0.25rem;
}

.labs-content {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.lab-category-section {
  background: var(--bg-secondary);
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--border-primary);
}

.lab-category-header {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  background: var(--bg-tertiary);
  border: none;
  cursor: pointer;
  transition: background 0.2s ease;
  text-align: left;
}

.lab-category-header:hover {
  background: var(--bg-primary);
}

.lab-category-name {
  font-weight: 600;
  color: var(--text-primary);
  text-transform: capitalize;
  font-size: 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.lab-track-name {
  color: var(--primary);
  font-weight: 600;
}

.lab-level-separator {
  color: var(--text-muted);
  margin: 0 0.25rem;
}

.lab-level-name {
  color: var(--text-primary);
  font-weight: 500;
}

.lab-category-count {
  color: var(--text-muted);
  font-size: 0.875rem;
  margin-left: 0.5rem;
}

.lab-category-toggle {
  color: var(--text-muted);
  font-size: 1.25rem;
  font-weight: 300;
  width: 24px;
  text-align: center;
}

.lab-category-content {
  padding: 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.lab-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.875rem 1rem;
  background: var(--bg-tertiary);
  border-radius: 6px;
  margin: 0 0.5rem 0.5rem 0.5rem;
}

.lab-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.lab-status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.lab-status-dot--active {
  background: var(--success);
}

.lab-status-dot--inactive {
  background: var(--text-muted);
}

.lab-name {
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 0.25rem 0;
}

.lab-meta {
  font-size: 0.8125rem;
  color: var(--text-muted);
  margin: 0;
}

.lab-actions {
  display: flex;
  gap: 0.5rem;
}

/* Exercise Management - Tester-style flat list */
.exercise-list {
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-primary);
  margin: 0.25rem 0.5rem 0.5rem;
  overflow: hidden;
}

.exercise-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.75rem;
  font-size: 0.8125rem;
  color: var(--text-secondary);
  border-bottom: 1px solid rgba(51, 65, 85, 0.4);
  transition: background 0.15s ease;
}

.exercise-item:last-child {
  border-bottom: none;
}

.exercise-item:hover {
  background: var(--hover-bg);
}

.exercise-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.exercise-status-dot--active {
  background: #22c55e;
  box-shadow: 0 0 4px rgba(34, 197, 94, 0.5);
}

.exercise-status-dot--inactive {
  background: #6b7280;
}

.exercise-name {
  flex: 1;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.exercise-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.0625rem 0.375rem;
  border-radius: 3px;
  font-size: 0.6875rem;
  font-weight: 600;
  flex-shrink: 0;
  text-transform: capitalize;
}

.exercise-badge--difficulty {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.exercise-badge--duration {
  background: rgba(100, 116, 139, 0.15);
  color: #94a3b8;
  border: 1px solid rgba(100, 116, 139, 0.3);
}

.exercise-badge--creator {
  background: var(--bg-tertiary);
  color: var(--text-muted);
  font-size: 0.625rem;
  padding: 0.0625rem 0.375rem;
  border-radius: 3px;
}

.exercise-vis-select {
  appearance: none;
  -webkit-appearance: none;
  padding: 0.125rem 1.125rem 0.125rem 0.375rem;
  border-radius: 3px;
  font-size: 0.6875rem;
  font-weight: 600;
  border: 1px solid rgba(100, 116, 139, 0.3);
  background-color: rgba(100, 116, 139, 0.1);
  color: #94a3b8;
  cursor: pointer;
  flex-shrink: 0;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='8' height='8' viewBox='0 0 8 8'%3E%3Cpath fill='%2394a3b8' d='M0 2l4 4 4-4z'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 0.25rem center;
}

.exercise-vis-select--public {
  border-color: rgba(34, 197, 94, 0.3);
  color: #4ade80;
  background-color: rgba(34, 197, 94, 0.1);
}

.exercise-vis-select--course {
  border-color: rgba(59, 130, 246, 0.3);
  color: #60a5fa;
  background-color: rgba(59, 130, 246, 0.1);
}

.exercise-vis-select--pending_public {
  border-color: rgba(245, 158, 11, 0.3);
  color: #fbbf24;
  background-color: rgba(245, 158, 11, 0.1);
}

.exercise-vis-select--draft {
  border-color: rgba(100, 116, 139, 0.3);
  color: #94a3b8;
  background-color: rgba(100, 116, 139, 0.1);
}

.exercise-actions {
  display: flex;
  gap: 0.5rem;
  flex-shrink: 0;
}

.exercise-action-btn {
  display: inline-flex;
  align-items: center;
  padding: 0.125rem 0.4rem;
  border-radius: 3px;
  font-size: 0.625rem;
  font-weight: 700;
  border: 1px solid rgba(100, 116, 139, 0.3);
  background: rgba(100, 116, 139, 0.15);
  color: #94a3b8;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease;
  line-height: 1.5;
}

.exercise-action-btn:hover {
  background: rgba(100, 116, 139, 0.25);
  filter: brightness(1.2);
}

.exercise-action-btn--danger {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
  border-color: rgba(239, 68, 68, 0.3);
}

.exercise-action-btn--danger:hover {
  background: rgba(239, 68, 68, 0.25);
}

.exercise-action-btn--success {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
  border-color: rgba(34, 197, 94, 0.3);
}

.exercise-action-btn--success:hover {
  background: rgba(34, 197, 94, 0.25);
}

.exercise-action-btn--test {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
  border-color: rgba(245, 158, 11, 0.3);
}

.exercise-action-btn--test:hover {
  background: rgba(245, 158, 11, 0.25);
}

.exercise-action-btn--test:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Inline quick-test row */
.quick-test-row td {
  background: var(--bg-secondary);
  border-bottom: 2px solid var(--border-color);
}

.category-toggle-btn {
  margin-left: auto;
  margin-right: 0.5rem;
}

.empty-state {
  text-align: center;
  padding: 3rem;
  color: var(--text-muted);
}

/* Session History */
.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.session-history {
  margin-top: 2rem;
}

/* Sessions Health Dashboard */
.sessions-health-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 1.5rem;
}

.session-health-card {
  background: var(--bg-tertiary);
  border-radius: 12px;
  padding: 1.25rem;
  border: 1px solid var(--border-primary);
  transition: all 0.2s ease;
}

.session-health-card--warning {
  border-color: var(--warning);
  background: rgba(245, 158, 11, 0.05);
}

.session-health-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.session-user-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.session-username {
  font-weight: 600;
  font-size: 1.1rem;
  color: var(--text-primary);
}

.session-lab {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.session-time {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--success);
  background: rgba(34, 197, 94, 0.1);
  padding: 0.25rem 0.75rem;
  border-radius: 6px;
}

.session-time--warning {
  color: var(--danger);
  background: var(--danger-bg);
  animation: pulse 1s infinite;
}

.session-network {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--border-primary);
}

.network-label {
  color: var(--text-secondary);
  font-size: 0.875rem;
}

.network-value {
  font-family: 'JetBrains Mono', monospace;
  color: var(--text-primary);
}

.containers-section {
  margin-bottom: 1rem;
}

.containers-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.containers-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.container-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0.75rem;
  background: var(--bg-secondary);
  border-radius: 6px;
  font-size: 0.875rem;
}

.container-name {
  font-weight: 500;
  color: var(--text-primary);
  flex: 1;
}

.container-status {
  padding: 0.125rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.container-status--running {
  background: rgba(34, 197, 94, 0.15);
  color: var(--success);
}

.container-status--exited {
  background: rgba(239, 68, 68, 0.15);
  color: var(--danger);
}

.container-status--paused {
  background: rgba(245, 158, 11, 0.15);
  color: var(--warning);
}

.container-health {
  padding: 0.125rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
}

.container-health--healthy {
  background: rgba(34, 197, 94, 0.15);
  color: var(--success);
}

.container-health--unhealthy {
  background: rgba(239, 68, 68, 0.15);
  color: var(--danger);
}

.container-health--starting {
  background: rgba(245, 158, 11, 0.15);
  color: var(--warning);
}

.container-ports {
  color: var(--accent);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  font-weight: 500;
}

.container-resources {
  color: var(--text-secondary);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
}

.container-port-test {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  margin-left: 0.25rem;
}

.port-test-result .status-badge {
  font-size: 0.6875rem;
  padding: 0.1rem 0.35rem;
  font-family: 'JetBrains Mono', monospace;
}

.no-containers {
  color: var(--text-secondary);
  font-style: italic;
  font-size: 0.875rem;
}

.session-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--border-primary);
}

/* Stale session card */
.session-health-card--stale {
  border-color: var(--danger);
  background: rgba(239, 68, 68, 0.05);
}

.session-health-card--diagnostic {
  border-color: rgba(245, 158, 11, 0.4);
  background: rgba(245, 158, 11, 0.04);
  opacity: 0.8;
}

.session-health-card--diagnostic .session-username {
  opacity: 0.75;
}

/* VPN status row */
.session-vpn-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.vpn-status-label {
  color: var(--text-secondary);
  font-size: 0.875rem;
  font-weight: 500;
}

.vpn-badge {
  padding: 0.125rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.vpn-badge--connected {
  background: rgba(34, 197, 94, 0.15);
  color: #22c55e;
}

.vpn-badge--disconnected {
  background: rgba(245, 158, 11, 0.15);
  color: var(--warning);
}

.vpn-badge--unregistered {
  background: rgba(239, 68, 68, 0.15);
  color: var(--danger);
}

.vpn-badge--none {
  background: rgba(100, 116, 139, 0.2);
  color: #94a3b8;
}

.vpn-handshake {
  font-weight: 400;
  font-size: 0.7rem;
  text-transform: none;
  opacity: 0.8;
}

.session-connectivity-status {
  display: flex;
  gap: 1rem;
  align-items: center;
  flex-wrap: wrap;
}

.session-rangebox-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.rangebox-view-link {
  text-decoration: none;
  cursor: pointer;
  transition: background 0.15s, transform 0.1s;
}

.rangebox-view-link:hover {
  background: rgba(34, 197, 94, 0.3) !important;
  transform: scale(1.05);
}

.impersonate-btn {
  border-color: #8b5cf6 !important;
  color: #8b5cf6 !important;
}

.impersonate-btn:hover {
  background: rgba(139, 92, 246, 0.15) !important;
}

/* Stale warning banner */
.stale-warning {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 6px;
  margin-bottom: 0.75rem;
  color: var(--danger);
  font-size: 0.8rem;
  font-weight: 500;
}

.stale-warning-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

/* Container IP badge */
.container-ip {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  color: var(--text-secondary);
  background: var(--bg-primary);
  padding: 0.125rem 0.375rem;
  border-radius: 3px;
}

/* Warning button variant */
.btn--warning {
  background: rgba(245, 158, 11, 0.15);
  color: var(--warning);
  border: 1px solid rgba(245, 158, 11, 0.3);
}
.btn--warning:hover {
  background: rgba(245, 158, 11, 0.25);
}

.panel-actions {
  display: flex;
  gap: 0.75rem;
}

/* VPN Time Filter */
.vpn-filter-bar {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}

.vpn-filter-presets {
  display: flex;
  gap: 0.375rem;
}

.vpn-filter-pill {
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  padding: 0.3125rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.vpn-filter-pill:hover {
  border-color: var(--nav-label);
}

.vpn-filter-pill--active {
  background: var(--accent);
  border-color: var(--accent);
  color: #ffffff;
}

.vpn-filter-pill--active:hover {
  background: #2563eb;
  border-color: #2563eb;
}

.vpn-filter-custom {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

/* VPN Tab */
.vpn-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.vpn-stat-card {
  padding: 1.25rem;
  border-radius: 8px;
  text-align: center;
}

.vpn-stat-card--registered {
  background: rgba(34, 197, 94, 0.15);
  border: 1px solid var(--success);
}

.vpn-stat-card--unregistered {
  background: rgba(245, 158, 11, 0.15);
  border: 1px solid var(--warning);
}

.vpn-stat-value {
  display: block;
  font-size: 2rem;
  font-weight: 700;
  color: var(--text-primary);
}

.vpn-stat-label {
  font-size: 0.8125rem;
  color: var(--text-muted);
}

.unregistered-section {
  margin-bottom: 1.5rem;
}

.unregistered-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.unregistered-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background: var(--bg-tertiary);
  border-radius: 6px;
}

.unregistered-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.unregistered-name {
  font-weight: 500;
  color: var(--text-primary);
}

.unregistered-ip {
  font-family: monospace;
  font-size: 0.8125rem;
  color: var(--text-muted);
}

.peers-section {
  margin-top: 1.5rem;
}

.server-badge {
  background: var(--purple);
  color: white;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
}

.handshake-active {
  color: var(--success);
}

.health-badge {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  cursor: help;
}

.health-badge--ok {
  background: rgba(34, 197, 94, 0.15);
  color: var(--success);
}

.health-badge--warn {
  background: rgba(234, 179, 8, 0.18);
  color: #ca8a04;
}

.health-badge--bad {
  background: rgba(239, 68, 68, 0.18);
  color: var(--danger);
}

.transfer-down::before {
  content: '↓';
  margin-right: 0.25rem;
}

.transfer-up::before {
  content: '↑';
  margin-right: 0.25rem;
}

.transfer-up {
  margin-left: 0.75rem;
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal {
  background: var(--bg-secondary);
  border-radius: 12px;
  padding: 1.5rem;
  width: 100%;
  max-width: 400px;
  border: 1px solid var(--border-color);
}

.modal--large {
  max-width: 900px;
  max-height: 90vh;
  overflow-y: auto;
}

.lab-edit-tabs {
  display: flex;
  gap: 0.25rem;
  margin-bottom: 1.25rem;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 0;
}

.lab-edit-tab {
  padding: 0.5rem 1.25rem;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  transition: color 0.2s, border-color 0.2s;
}

.lab-edit-tab:hover {
  color: var(--text-primary);
}

.lab-edit-tab--active {
  color: var(--accent);
  border-bottom-color: var(--accent);
}

.modal--xlarge {
  max-width: 1100px;
  max-height: 90vh;
  overflow-y: auto;
}

/* Create Lab Tabs */
.create-lab-tabs {
  display: flex;
  gap: 0;
  margin-bottom: 1rem;
  border-bottom: 1px solid var(--border);
}
.create-lab-tab {
  background: none;
  border: none;
  color: var(--text-secondary);
  padding: 0.5rem 1rem;
  font-size: 0.85rem;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}
.create-lab-tab:hover { color: var(--text-primary); }
.create-lab-tab.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
}

/* YAML Import layout */
.create-lab-yaml-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}
.create-lab-yaml-col { min-width: 0; }

.label-hint {
  font-size: 0.75rem;
  font-weight: 400;
  color: var(--text-secondary);
  margin-left: 0.25rem;
}

/* YAML parse feedback */
.yaml-parse-error {
  margin-top: 0.4rem;
  font-size: 0.8rem;
  color: var(--danger);
}
.yaml-preview {
  background: rgba(99, 102, 241, 0.08);
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: 8px;
  padding: 0.75rem 1rem;
  margin-top: 0.75rem;
}
.yaml-preview__title {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-secondary);
  margin-bottom: 0.5rem;
}
.yaml-preview__grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}
.yaml-preview__tag {
  display: inline-block;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  padding: 0.2rem 0.5rem;
  font-size: 0.78rem;
  color: var(--text-primary);
}
.yaml-preview__tag--flag {
  border-color: rgba(34, 197, 94, 0.3);
  color: var(--success);
}
.yaml-preview__tag--test {
  border-color: rgba(99, 102, 241, 0.3);
  color: var(--accent);
}

.modal-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 0.25rem 0;
}

.modal-subtitle {
  font-size: 0.875rem;
  color: var(--text-muted);
  margin: 0 0 1rem 0;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 1.5rem;
}

/* Spinner */
.spinner-icon {
  width: 16px;
  height: 16px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-enter-active,
.slide-leave-active {
  transition: all 0.3s ease;
  overflow: hidden;
}

.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  max-height: 0;
}

.slide-enter-to,
.slide-leave-from {
  max-height: 300px;
}

/* Responsive */
@media (max-width: 768px) {
  .admin-page {
    padding: 1rem;
  }

  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

  .lab-item {
    flex-direction: column;
    gap: 1rem;
    align-items: flex-start;
  }

  .lab-actions {
    width: 100%;
  }

  .lab-actions .btn {
    flex: 1;
  }

  .vpn-stats {
    grid-template-columns: 1fr;
  }
}

/* Course Management Styles */
.invite-code-admin {
  font-size: 0.8rem;
  color: var(--warning);
  background: rgba(245, 158, 11, 0.1);
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  cursor: pointer;
  font-family: 'JetBrains Mono', monospace;
}

.invite-code-admin:hover {
  background: rgba(245, 158, 11, 0.2);
}

.course-manage-section {
  margin-top: 1.5rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 12px;
  padding: 1.25rem;
}

.assign-instructor-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
  padding: 0.5rem 0;
}

.assign-instructor-label {
  font-size: 0.85rem;
  color: var(--text-secondary);
  white-space: nowrap;
}

.assign-instructor-select {
  max-width: 300px;
}

.sub-tabs {
  display: flex;
  gap: 0.25rem;
  margin-bottom: 1rem;
  border-bottom: 1px solid var(--border-primary);
}

.sub-tab {
  background: none;
  border: none;
  color: var(--text-muted);
  padding: 0.6rem 1rem;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}

.sub-tab:hover {
  color: var(--text-primary);
}

.sub-tab.active {
  color: var(--primary);
  border-bottom-color: var(--primary);
}

.sub-tab-content {
  padding: 0.5rem 0;
}

.enroll-form {
  display: flex;
  gap: 0.75rem;
  margin-bottom: 1rem;
  align-items: center;
}

.enroll-form .form-input {
  flex: 1;
  max-width: 400px;
}

.form-input--sm {
  padding: 0.45rem 0.75rem;
  font-size: 0.85rem;
}

.assign-labs-form h4 {
  color: var(--text-primary);
  margin: 0;
}

.assign-labs-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}

.assign-selected-btn {
  margin-top: 1rem;
  padding: 0.5rem 1.25rem;
  font-size: 0.8125rem;
}

.btn--outline {
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-muted);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;
}

.btn--outline:hover {
  color: var(--text-primary);
  border-color: var(--text-secondary);
}

.btn--xs {
  padding: 0.25rem 0.625rem;
  font-size: 0.7rem;
  font-weight: 500;
}

/* Lab Assignment Accordion */
.assign-accordion {
  max-height: 450px;
  overflow-y: auto;
  background: var(--bg-primary);
  border-radius: 8px;
  padding: 0.25rem;
}

.assign-group {
  margin-bottom: 0.125rem;
}

.assign-group__header-row {
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.assign-group__header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 1;
  min-width: 0;
  padding: 0.5rem 0.75rem;
  background: var(--bg-tertiary);
  border: none;
  border-radius: 6px 0 0 6px;
  color: var(--text-primary);
  cursor: pointer;
  font-size: 0.8125rem;
  font-weight: 600;
  transition: background 0.15s;
}

.assign-group__add-all {
  flex-shrink: 0;
  border-radius: 0 6px 6px 0 !important;
  padding: 0.5rem 0.625rem !important;
  font-size: 0.7rem !important;
  letter-spacing: 0.02em;
  height: auto;
  align-self: stretch;
}

.assign-group__header:hover {
  background: #3b4f6b;
}

.assign-group__chevron {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
  transition: transform 0.2s;
  color: var(--text-muted);
}

.assign-group__chevron--open {
  transform: rotate(90deg);
}

.assign-group__track {
  color: var(--accent);
}

.assign-group__sep {
  color: var(--text-muted);
  font-weight: 400;
}

.assign-group__level {
  color: var(--text-secondary);
  font-weight: 500;
}

.assign-group__count {
  color: var(--text-muted);
  font-size: 0.75rem;
  margin-left: auto;
}

.assign-group__body {
  padding: 0.25rem 0 0.25rem 1.75rem;
}

.lab-checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 0.5rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
  color: var(--text-secondary);
  transition: background 0.15s;
}

.lab-checkbox-label:hover {
  background: var(--bg-tertiary);
}

.lab-checkbox-label input[type="checkbox"] {
  accent-color: var(--primary);
}

.lab-checkbox-name {
  flex: 1;
}

.lab-checkbox-diff {
  font-size: 0.7rem;
  color: var(--text-muted);
  text-transform: capitalize;
}

.exclusive-badge {
  font-size: 0.6rem;
  padding: 0.1rem 0.35rem;
  border-radius: 3px;
  border: 1px solid rgba(167, 139, 250, 0.4);
  background: rgba(167, 139, 250, 0.12);
  color: #a78bfa;
  white-space: nowrap;
}

.visibility-toggle {
  font-size: 0.7rem;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  border: 1px solid var(--nav-label);
  background: transparent;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
  font-weight: 500;
}

.visibility-toggle--public {
  color: var(--success);
  border-color: rgba(34, 197, 94, 0.3);
  background: rgba(34, 197, 94, 0.1);
}

.visibility-toggle--public:hover {
  border-color: rgba(34, 197, 94, 0.5);
  background: rgba(34, 197, 94, 0.2);
}

.visibility-toggle--exclusive {
  color: #a78bfa;
  border-color: rgba(167, 139, 250, 0.3);
  background: rgba(167, 139, 250, 0.1);
}

.visibility-toggle--exclusive:hover {
  border-color: rgba(167, 139, 250, 0.5);
  background: rgba(167, 139, 250, 0.2);
}

.visibility-toggle--off {
  color: var(--text-muted);
  border-color: rgba(100, 116, 139, 0.2);
  background: transparent;
}

.visibility-toggle--off:hover {
  border-color: rgba(100, 116, 139, 0.4);
  background: rgba(100, 116, 139, 0.1);
}

.visibility-group {
  display: inline-flex;
  gap: 0.25rem;
}

.status-badge--exclusive {
  color: #a78bfa;
  background: rgba(167, 139, 250, 0.15);
}

/* Course Controls */
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

.action-btn--archive {
  background: rgba(148, 163, 184, 0.15);
  color: var(--text-secondary);
}

.action-btn--archive:hover {
  background: var(--text-secondary);
  color: white;
}

.student-labs-row td {
  padding: 0 !important;
  background: var(--bg-secondary);
}

.student-labs-detail {
  padding: 0.75rem 1rem;
}

.data-table--nested {
  margin: 0;
  font-size: 0.8125rem;
}

.data-table--nested th {
  background: var(--bg-tertiary);
  padding: 0.375rem 0.5rem;
}

.data-table--nested td {
  padding: 0.375rem 0.5rem;
}

.status-badge--success {
  color: var(--success);
  background: rgba(34, 197, 94, 0.15);
}

.status-badge--warning {
  color: var(--warning);
  background: rgba(245, 158, 11, 0.15);
}

.status-badge--danger {
  color: var(--danger);
  background: rgba(239, 68, 68, 0.15);
}

.status-badge--muted {
  color: var(--text-secondary);
  background: rgba(148, 163, 184, 0.15);
}

.report-actions {
  margin-bottom: 1rem;
}

.report-description {
  color: var(--text-muted);
  font-size: 0.85rem;
}

.empty-state {
  color: var(--text-muted);
  text-align: center;
  padding: 2rem;
  font-size: 0.9rem;
}

/* === Exercises Catalog Layout (sidebar + table) === */
.catalog-layout { display: flex; gap: 1rem; }

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

.filter-bar { display: flex; flex-wrap: wrap; gap: 0.75rem; margin-bottom: 1rem; }

.search-input {
  flex: 1;
  min-width: 160px;
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

.results-count { font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.75rem; }

.table-wrapper {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
}

.lab-name { font-weight: 500; color: var(--text-primary); }
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
.row--inactive { opacity: 0.65; }

@media (max-width: 768px) {
  .catalog-layout { flex-direction: column; }
  .topic-sidebar { width: 100%; min-width: unset; position: static; display: flex; flex-wrap: wrap; gap: 0.5rem; padding: 0.75rem; }
  .sidebar-title { width: 100%; padding-bottom: 0.5rem; }
  .topic-item { width: auto; padding: 0.375rem 0.75rem; }
}

/* Global modal styles (not scoped to work with CSS variables) */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.8) !important;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: var(--bg-secondary) !important;
  border-radius: 12px;
  padding: 1.5rem;
  width: 100%;
  max-width: 400px;
  border: 1px solid var(--border-color) !important;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
}

.modal-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--hover-text) !important;
  margin: 0 0 0.25rem 0;
}

.modal-subtitle {
  font-size: 0.875rem;
  color: var(--text-muted) !important;
  margin: 0 0 1rem 0;
}

.modal .form-input {
  background: var(--bg-tertiary) !important;
  border: 1px solid var(--nav-label) !important;
  border-radius: 6px;
  padding: 0.75rem 1rem;
  color: var(--hover-text) !important;
  font-size: 1rem;
  width: 100%;
}

.modal .form-input:focus {
  outline: none;
  border-color: var(--accent) !important;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 1.5rem;
}

.modal-actions .btn {
  padding: 0.625rem 1.25rem;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
  border: none;
}

.modal-actions .btn--secondary {
  background: var(--bg-tertiary) !important;
  color: var(--hover-text) !important;
}

.modal-actions .btn--secondary:hover {
  background: var(--nav-label) !important;
}

.modal-actions .btn--primary {
  background: var(--accent) !important;
  color: white !important;
}

.modal-actions .btn--primary:hover {
  background: #2563eb !important;
}

/* Edit User Form */
.edit-user-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.edit-user-form .section-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--border-color);
}

.edit-user-form .form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.edit-user-form .form-group label {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.edit-user-form .form-input {
  width: 100%;
  padding: 0.75rem;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 0.9375rem;
}

.edit-user-form .form-input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px var(--accent-bg);
}

.edit-user-form .form-input.error {
  border-color: var(--error);
}

.edit-user-form .checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.edit-user-form .checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-size: 0.9375rem;
  color: var(--text-primary);
}

.edit-user-form .checkbox-label input[type="checkbox"] {
  width: 1.125rem;
  height: 1.125rem;
  cursor: pointer;
}

.edit-user-form .error-text {
  font-size: 0.8125rem;
  color: var(--error);
  margin-top: 0.25rem;
}

.edit-user-form .error-message {
  font-size: 0.875rem;
  color: var(--error);
  padding: 0.75rem;
  background: rgba(220, 38, 38, 0.1);
  border-radius: 6px;
  border: 1px solid var(--error);
}

.edit-user-form .success-message {
  font-size: 0.875rem;
  color: var(--success);
  padding: 0.75rem;
  background: rgba(34, 197, 94, 0.1);
  border-radius: 6px;
  border: 1px solid var(--success);
}

.password-change-badge {
  margin-left: 0.5rem;
  font-size: 0.875rem;
  opacity: 0.8;
}

/* User Details Modal */
.user-details-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.loading-state {
  text-align: center;
  padding: 2rem;
  color: var(--text-muted);
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.info-label {
  font-size: 0.8125rem;
  color: var(--text-muted);
  font-weight: 500;
}

.info-value {
  font-size: 0.9375rem;
  color: var(--text-primary);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1rem;
  background: var(--bg-primary);
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.stat-label {
  font-size: 0.8125rem;
  color: var(--text-muted);
  font-weight: 500;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--text-primary);
}

.action-btn--view {
  background: rgba(59, 130, 246, 0.15);
  color: var(--accent);
}

.action-btn--view:hover {
  background: var(--accent);
  color: white;
}

@media (max-width: 768px) {
  .info-grid,
  .stats-grid {
    grid-template-columns: 1fr;
  }
}

/* Settings */
.settings-categories {
  display: flex;
  gap: 0.25rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}

.settings-form {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.75rem 1rem;
  background: var(--bg-primary);
  border-radius: 6px;
  border: 1px solid var(--bg-secondary);
}

.setting-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-width: 0;
}

.setting-key {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.setting-info-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  font-size: 0.625rem;
  font-weight: 700;
  font-style: italic;
  color: var(--text-secondary);
  border: 1px solid var(--nav-label);
  border-radius: 50%;
  cursor: help;
  flex-shrink: 0;
  position: relative;
}

.setting-info-icon:hover,
.setting-info-icon:focus {
  color: #e2e8f0;
  border-color: var(--text-secondary);
}

.setting-tooltip {
  display: none;
  position: absolute;
  left: 50%;
  bottom: calc(100% + 8px);
  transform: translateX(-50%);
  background: #1e293b;
  color: #e2e8f0;
  font-size: 0.75rem;
  font-weight: 400;
  font-style: normal;
  line-height: 1.45;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  border: 1px solid #334155;
  white-space: normal;
  width: 260px;
  text-align: left;
  z-index: 100;
  box-shadow: 0 4px 12px rgba(0,0,0,0.4);
  pointer-events: none;
}

.setting-tooltip::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 6px solid transparent;
  border-top-color: #334155;
}

.setting-info-icon:hover .setting-tooltip,
.setting-info-icon:focus .setting-tooltip {
  display: block;
}

.setting-input-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.setting-unit {
  font-size: 0.75rem;
  color: var(--text-muted, #64748b);
  white-space: nowrap;
}

.setting-control {
  flex-shrink: 0;
  min-width: 280px;
}

.setting-control .form-input--sm {
  width: 100%;
  min-width: 280px;
}

.color-input {
  width: 48px;
  height: 32px;
  border: 1px solid var(--nav-label);
  border-radius: 4px;
  background: transparent;
  cursor: pointer;
}

/* Curriculum */
.curriculum-list {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

/* Compose textarea */
.compose-textarea {
  font-family: 'Courier New', monospace;
  font-size: 0.8125rem;
  line-height: 1.5;
  tab-size: 2;
  resize: vertical;
}

.flag-reveal {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.flag-reveal__value {
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
  color: #4ade80;
  background: rgba(34, 197, 94, 0.12);
  border: 1px solid rgba(34, 197, 94, 0.3);
  border-radius: 4px;
  padding: 0.35rem 0.6rem;
  user-select: all;
  word-break: break-all;
}

.flag-reveal__note {
  margin: 0.4rem 0 0;
  font-size: 0.8125rem;
  color: #fbbf24;
}

.flag-reveal__note--error {
  color: #f87171;
}

/* Extra button styles */
.btn--outline {
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--nav-label);
}

.btn--outline:hover {
  background: var(--hover-bg);
  color: var(--hover-text);
}

.btn--xs {
  padding: 0.25rem 0.5rem;
  font-size: 0.6875rem;
}

.system-health-overall {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.875rem 1.25rem;
  border-radius: 8px;
  margin-bottom: 1rem;
  font-weight: 600;
  font-size: 0.9375rem;
}

.system-health-overall--healthy {
  background: rgba(22, 101, 52, 0.15);
  border: 1px solid #166534;
  color: #4ade80;
}

.system-health-overall--warning {
  background: rgba(133, 77, 14, 0.15);
  border: 1px solid #854d0e;
  color: #fbbf24;
}

.system-health-overall--error {
  background: rgba(153, 27, 27, 0.15);
  border: 1px solid #991b1b;
  color: #f87171;
}

.system-health-overall-icon {
  font-size: 1.25rem;
}

.system-health-overall-text {
  flex: 1;
}

.system-health-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 1rem;
}

.system-health-card {
  background: var(--bg-primary);
  border: 1px solid var(--bg-secondary);
  border-radius: 8px;
  padding: 1rem;
}

.system-health-card--healthy {
  border-color: #166534;
}

.system-health-card--warning {
  border-color: #854d0e;
}

.system-health-card--error,
.system-health-card--unreachable {
  border-color: #991b1b;
}

.system-health-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.system-health-name {
  font-weight: 600;
  color: #e2e8f0;
}

.system-health-details {
  font-size: 0.8125rem;
  color: var(--text-secondary);
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  overflow-wrap: break-word;
  word-break: break-word;
  min-width: 0;
}

.status-badge--healthy { color: #4ade80; }
.status-badge--warning { color: #fbbf24; }
.status-badge--error { color: #f87171; }
.status-badge--unreachable { color: #f87171; }
.status-badge--unknown { color: var(--text-muted); }
.status-badge--running { color: #4ade80; }
.status-badge--exited { color: #f87171; }

/* Security Audit */
.security-overall {
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  margin-bottom: 1rem;
  font-size: 0.875rem;
}

.security-overall--ok {
  background: rgba(34, 197, 94, 0.1);
  border: 1px solid #166534;
  color: #4ade80;
}

.security-overall--warning {
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid #854d0e;
  color: #fbbf24;
}

.security-overall--error {
  background: var(--danger-bg);
  border: 1px solid #991b1b;
  color: #f87171;
}

/* Health Status Card (in stats grid) */
.stat-card--health {
  transition: border-color 0.3s ease;
}

.stat-card--health:hover {
  border-color: var(--accent) !important;
}

.stat-card--health-healthy {
  border-color: rgba(22, 101, 52, 0.4);
}

.stat-card--health-warning {
  border-color: #854d0e;
}

.stat-card--health-error {
  border-color: #991b1b;
}

.stat-card__icon--health {
  color: var(--text-muted);
}

.stat-card__icon--health-healthy {
  background: rgba(22, 101, 52, 0.15);
  color: #4ade80;
}

.stat-card__icon--health-warning {
  background: rgba(133, 77, 14, 0.15);
  color: #fbbf24;
}

.stat-card__icon--health-error {
  background: rgba(153, 27, 27, 0.15);
  color: #f87171;
}

.health-card-indicators {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.health-card-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.health-card-label {
  font-size: 0.75rem;
  color: var(--text-secondary);
  font-weight: 500;
}

/* Health dots (shared) */
.health-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
  flex-shrink: 0;
}

.health-dot--green {
  background: #4ade80;
  box-shadow: 0 0 4px rgba(74, 222, 128, 0.4);
}

.health-dot--amber {
  background: #fbbf24;
  box-shadow: 0 0 4px rgba(251, 191, 36, 0.4);
  animation: pulse-amber 2s ease-in-out infinite;
}

.health-dot--red {
  background: #f87171;
  box-shadow: 0 0 6px rgba(248, 113, 113, 0.5);
  animation: pulse-red 1.5s ease-in-out infinite;
}

@keyframes pulse-amber {
  0%, 100% { box-shadow: 0 0 4px rgba(251, 191, 36, 0.4); }
  50% { box-shadow: 0 0 8px rgba(251, 191, 36, 0.7); }
}

@keyframes pulse-red {
  0%, 100% { box-shadow: 0 0 6px rgba(248, 113, 113, 0.5); }
  50% { box-shadow: 0 0 12px rgba(248, 113, 113, 0.8); }
}

/* Compact inline health indicator (replaces big green banners when OK) */
.health-inline {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0;
  margin-bottom: 0.75rem;
}

.health-inline__text {
  font-size: 0.8125rem;
  color: var(--text-muted);
  font-weight: 500;
}

.security-checks-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 0.75rem;
}

.security-check-card {
  background: var(--bg-secondary, #1e293b);
  border: 1px solid var(--border-color, #334155);
  border-radius: 0.5rem;
  padding: 1rem;
  border-left: 3px solid;
}

.security-check-card--ok {
  border-left-color: var(--success);
}

.security-check-card--warning {
  border-left-color: var(--warning);
}

.security-check-card--error {
  border-left-color: var(--danger);
}

.security-check-card--info {
  border-left-color: var(--accent);
}

.security-check-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.security-check-icon {
  font-size: 1rem;
  width: 1.25rem;
  text-align: center;
}

.security-check-card--ok .security-check-icon { color: #4ade80; }
.security-check-card--warning .security-check-icon { color: #fbbf24; }
.security-check-card--error .security-check-icon { color: #f87171; }
.security-check-card--info .security-check-icon { color: #60a5fa; }

.security-check-name {
  font-weight: 600;
  color: #e2e8f0;
  font-size: 0.875rem;
}

.security-check-detail {
  font-size: 0.8125rem;
  color: var(--text-secondary);
  line-height: 1.4;
}

.security-note {
  margin-top: 1rem;
  font-size: 0.8125rem;
  color: var(--text-muted);
}

.security-note code {
  background: var(--bg-tertiary, #334155);
  padding: 0.15rem 0.4rem;
  border-radius: 0.25rem;
  font-family: monospace;
  color: #e2e8f0;
}

/* Disk usage bar */
.disk-bar-container {
  width: 100%;
  height: 8px;
  background: var(--bg-tertiary, #1e293b);
  border-radius: 4px;
  margin-top: 0.5rem;
  overflow: hidden;
}

.disk-bar {
  height: 100%;
  border-radius: 4px;
  transition: width 0.6s ease;
}

.disk-bar--healthy { background: #4ade80; }
.disk-bar--warning { background: #fbbf24; }
.disk-bar--critical { background: #f87171; }

/* Backup actions */
.backup-actions {
  display: flex;
  gap: 0.4rem;
  justify-content: flex-end;
  flex-wrap: wrap;
}

.btn--xs {
  font-size: 0.7rem;
  padding: 0.25rem 0.5rem;
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
}

.btn--warning {
  background: rgba(251, 191, 36, 0.15);
  color: #fbbf24;
  border: 1px solid rgba(251, 191, 36, 0.3);
}

.btn--warning:hover {
  background: rgba(251, 191, 36, 0.25);
  border-color: #fbbf24;
}

.section-desc {
  font-size: 0.8125rem;
  color: var(--text-muted);
  margin-bottom: 1.25rem;
  line-height: 1.5;
}

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

/* Restore overlay */
.restore-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.restore-overlay-content {
  text-align: center;
  color: var(--text-primary, #e2e8f0);
  background: var(--bg-secondary, #1e293b);
  padding: 2.5rem 3rem;
  border-radius: 12px;
  border: 1px solid var(--border-color, #334155);
}

.restore-overlay-content p {
  margin-top: 1rem;
  font-size: 1rem;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--border-color, #334155);
  border-top-color: var(--accent, #38bdf8);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Backup Heatmap */
.backup-heatmap-card {
  background: var(--bg-tertiary, #0f172a);
  border: 1px solid var(--border-color, #1e293b);
  border-radius: 8px;
  padding: 1rem 1.25rem;
  margin-bottom: 1.25rem;
}

.backup-heatmap-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.backup-heatmap-title {
  font-size: 0.8125rem;
  color: var(--text-secondary, #94a3b8);
}

.backup-heatmap-legend {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 0.6875rem;
}

.heatmap-swatch {
  width: 10px;
  height: 10px;
  border-radius: 2px;
}

.heatmap-swatch--green { background: #39d353; }
.heatmap-swatch--yellow { background: #d4a017; }
.heatmap-swatch--split {
  background: linear-gradient(135deg, #39d353 45%, #d4a017 55%);
}

.backup-heatmap-scroll {
  overflow-x: auto;
  overflow-y: visible;
  padding-bottom: 4px;
}

.backup-heatmap-grid {
  display: inline-flex;
  gap: 4px;
  min-width: min-content;
}

.heatmap-day-labels {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding-top: 22px;
  flex-shrink: 0;
}

.heatmap-day-labels span {
  height: 11px;
  font-size: 0.5625rem;
  line-height: 11px;
  color: var(--text-muted, #64748b);
  text-align: right;
  padding-right: 6px;
  min-width: 26px;
}

.heatmap-columns {
  min-width: 0;
}

.heatmap-month-labels {
  display: grid;
  grid-auto-columns: 14px;
  grid-auto-flow: column;
  height: 18px;
  margin-bottom: 3px;
  font-size: 0.625rem;
  color: var(--text-muted, #64748b);
  white-space: nowrap;
  overflow: visible;
}

.heatmap-cells {
  display: flex;
  gap: 3px;
}

.heatmap-week {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.heatmap-cell {
  width: 11px;
  height: 11px;
  border-radius: 2px;
  cursor: default;
}

.heatmap-cell--empty {
  visibility: hidden;
}

.heatmap-cell--none { background: #161b22; }
.heatmap-cell--green { background: #39d353; }
.heatmap-cell--yellow { background: #d4a017; }
.heatmap-cell--split {
  background: linear-gradient(135deg, #39d353 45%, #d4a017 55%);
}

.heatmap-cell:not(.heatmap-cell--empty):not(.heatmap-cell--none):hover {
  outline: 1px solid rgba(255,255,255,0.5);
  outline-offset: -1px;
}

/* ── Diagnostics Terminal ── */
.vm-terminals-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
  gap: 0.75rem;
}
.vm-terminal-panel {
  min-width: 0;
}
.vm-terminal-body {
  max-height: 250px;
}
.vm-terminal-close {
  background: none;
  border: none;
  color: #64748b;
  font-size: 1.1rem;
  cursor: pointer;
  padding: 0 0.3rem;
  margin-left: 0.5rem;
  line-height: 1;
}
.vm-terminal-close:hover {
  color: #f87171;
}
.diagnostics-terminal {
  border: 1px solid #1e293b;
  border-radius: 0.5rem;
  overflow: hidden;
  background: #020617;
}

.diagnostics-terminal-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: #0f172a;
  border-bottom: 1px solid #1e293b;
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 0.7rem;
  color: #94a3b8;
}

.diagnostics-terminal-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #475569;
  flex-shrink: 0;
}

.diagnostics-terminal-dot--active {
  background: #6aaa64;
  box-shadow: 0 0 6px rgba(106, 170, 100, 0.6);
}

.diagnostics-terminal-label {
  font-weight: 600;
  color: #e2e8f0;
}

/* Tester progress bar */
.tester-progress-text {
  color: #94a3b8;
  font-size: 0.65rem;
  margin-left: 0.5rem;
}
.tester-progress-bar {
  width: 120px;
  height: 6px;
  background: #1e293b;
  border-radius: 3px;
  overflow: hidden;
  flex-shrink: 0;
}
.tester-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #22c55e, #4ade80);
  border-radius: 3px;
  transition: width 0.4s ease;
}
.tester-progress-pct {
  color: #4ade80;
  font-weight: 600;
  font-size: 0.65rem;
  min-width: 32px;
}
.diagnostics-terminal-time {
  margin-left: auto;
  color: #64748b;
}

.diagnostics-terminal-body {
  padding: 0.75rem;
  max-height: 500px;
  overflow-y: auto;
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 0.75rem;
  line-height: 1.6;
}

.diagnostics-terminal-body::-webkit-scrollbar {
  width: 6px;
}
.diagnostics-terminal-body::-webkit-scrollbar-track {
  background: #020617;
}
.diagnostics-terminal-body::-webkit-scrollbar-thumb {
  background: #334155;
  border-radius: 3px;
}

.diagnostics-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 3rem 1rem;
  color: #475569;
  text-align: center;
}

.diagnostics-empty p {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 0.85rem;
  margin: 0;
}

.diagnostics-section-header {
  color: #60a5fa;
  padding: 0.5rem 0 0.25rem 0;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.diagnostics-line {
  display: flex;
  gap: 0.75rem;
  padding: 1px 0;
  white-space: nowrap;
}

.diagnostics-line-time {
  color: #475569;
  flex-shrink: 0;
}

.diagnostics-line-level {
  flex-shrink: 0;
  font-weight: 700;
  min-width: 48px;
}

.diagnostics-level--ok { color: #6aaa64; }
.diagnostics-level--info { color: #60a5fa; }
.diagnostics-level--warning { color: #e8a735; }
.diagnostics-level--error { color: #d9534f; }

.diagnostics-line-msg {
  color: #cbd5e1;
  white-space: pre-wrap;
  word-break: break-word;
}

.diagnostics-cursor {
  color: #6aaa64;
  font-weight: 700;
  animation: diagnostics-blink 1s step-end infinite;
}

@keyframes diagnostics-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* ── Exercise Tester ── */
.tester-controls {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.tester-filters {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.tester-filter-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.tester-track-select,
.tester-category-select,
.tester-status-select {
  width: 160px;
  flex-shrink: 0;
}

.tester-search {
  flex: 1;
  max-width: 300px;
  padding: 0.5rem 0.75rem !important;
  font-size: 0.8125rem !important;
}

.tester-selection-count {
  font-size: 0.75rem;
  color: var(--text-muted);
  white-space: nowrap;
  margin-left: 0.25rem;
}

/* Results summary bar */
.tester-results-summary {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.5rem 0.75rem;
  margin-bottom: 0.375rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  font-size: 0.75rem;
  color: var(--text-secondary);
}
.tester-summary-item {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-weight: 500;
}
.tester-summary-item--ok { color: #4ade80; }
.tester-summary-item--warning { color: #fbbf24; }
.tester-summary-item--error { color: #f87171; }
.tester-summary-item--total {
  margin-left: auto;
  color: var(--text-muted);
  font-weight: 400;
}

.tester-lab-picker {
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-primary);
}

.tester-lab-picker::-webkit-scrollbar {
  width: 6px;
}
.tester-lab-picker::-webkit-scrollbar-track {
  background: var(--bg-primary);
}
.tester-lab-picker::-webkit-scrollbar-thumb {
  background: var(--bg-tertiary);
  border-radius: 3px;
}

.tester-week-divider {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.625rem;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--accent-blue, #60a5fa);
  background: rgba(96, 165, 250, 0.08);
  border-bottom: 1px solid rgba(96, 165, 250, 0.2);
}

.tester-week-divider::before,
.tester-week-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: rgba(96, 165, 250, 0.25);
}

.tester-course-select {
  min-width: 160px;
}

.tester-lab-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.625rem;
  cursor: pointer;
  font-size: 0.8125rem;
  color: var(--text-secondary);
  border-bottom: 1px solid rgba(51, 65, 85, 0.4);
  transition: background 0.15s ease;
}

.tester-lab-item:last-child {
  border-bottom: none;
}

.tester-lab-item:hover {
  background: var(--hover-bg);
}

.tester-lab-item--selected {
  background: rgba(59, 130, 246, 0.08);
  color: var(--text-primary);
}

.tester-lab-item--ok {
  border-left: 3px solid #22c55e;
}
.tester-lab-item--warning {
  border-left: 3px solid #f59e0b;
}
.tester-lab-item--error {
  border-left: 3px solid #ef4444;
}
.tester-lab-item--cancelled {
  border-left: 3px solid #6b7280;
}

.tester-lab-checkbox {
  accent-color: var(--accent);
  flex-shrink: 0;
  width: 14px;
  height: 14px;
}

/* Status dot indicator */
.tester-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
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

.tester-lab-name {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tester-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 3px;
  font-size: 0.625rem;
  font-weight: 700;
  flex-shrink: 0;
  line-height: 1;
}

.tester-badge--test {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
  border: 1px solid rgba(34, 197, 94, 0.3);
}

.tester-badge--flag {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.tester-badge--report {
  width: auto;
  padding: 0 0.375rem;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease;
  background: rgba(100, 116, 139, 0.15);
  color: #94a3b8;
  border: 1px solid rgba(100, 116, 139, 0.3);
}
.tester-badge--report:hover {
  filter: brightness(1.2);
}
.tester-badge--report-ok {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
  border-color: rgba(34, 197, 94, 0.4);
}
.tester-badge--report-ok:hover {
  background: rgba(34, 197, 94, 0.25);
}
.tester-badge--report-warning {
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
  border-color: rgba(245, 158, 11, 0.4);
}
.tester-badge--report-warning:hover {
  background: rgba(245, 158, 11, 0.25);
}
.tester-badge--report-error {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
  border-color: rgba(239, 68, 68, 0.4);
}
.tester-badge--report-error:hover {
  background: rgba(239, 68, 68, 0.25);
}
.tester-badge--report-cancelled {
  background: rgba(107, 114, 128, 0.15);
  color: #9ca3af;
  border-color: rgba(107, 114, 128, 0.4);
}

.tester-lab-track {
  font-size: 0.6875rem;
  color: var(--text-muted);
  background: var(--bg-tertiary);
  padding: 0.125rem 0.375rem;
  border-radius: 3px;
  flex-shrink: 0;
  text-transform: capitalize;
}

.tester-lab-empty {
  padding: 1.5rem;
  text-align: center;
  color: var(--text-muted);
  font-size: 0.8125rem;
}

.tester-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

/* Module Cards */
.module-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  overflow: hidden;
  transition: border-color 0.25s;
  margin-bottom: 1rem;
}

.module-card--enabled {
  border-color: var(--success);
}

.module-card__header {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.25rem 1.5rem;
}

.module-card__icon {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
}

.module-card--enabled .module-card__icon {
  background: var(--success-bg);
  color: var(--success);
}

.module-card__icon svg {
  width: 22px;
  height: 22px;
}

.module-card__info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.module-card__name {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--text-primary);
}

.module-card__desc {
  font-size: 0.8125rem;
  color: var(--text-muted);
}

.module-card__toggle {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 1.125rem;
  border-radius: 6px;
  font-size: 0.8125rem;
  font-weight: 600;
  border: 1px solid;
  cursor: pointer;
  min-width: 90px;
  justify-content: center;
  transition: all 0.2s;
}

.module-card__toggle--on {
  background: var(--success-bg);
  color: var(--success);
  border-color: var(--success);
}

.module-card__toggle--off {
  background: rgba(100, 116, 139, 0.12);
  color: var(--text-secondary);
  border-color: var(--nav-label);
}

.module-card__actions {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  flex-shrink: 0;
}

.module-card__toggle:hover:not(:disabled) {
  filter: brightness(1.15);
}

.module-card__toggle:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.module-card__save {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 1.125rem;
  border-radius: 6px;
  font-size: 0.8125rem;
  font-weight: 600;
  border: none;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
  background: var(--accent);
  color: #fff;
}

.module-card__save:hover:not(:disabled) {
  background: #2563eb;
}

.module-card__save:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.module-toggle-spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: module-spin 0.6s linear infinite;
}

@keyframes module-spin {
  to { transform: rotate(360deg); }
}

/* Module Log (terminal-style) */
.module-card__log {
  border-top: 1px solid var(--border-color);
  background: #0c0c0c;
}

.module-log-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border-bottom: 1px solid #1e293b;
}

.module-log-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--success);
}

.module-log-dot--active {
  animation: module-dot-pulse 1s ease-in-out infinite;
}

@keyframes module-dot-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.module-log-label {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 0.6875rem;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.module-log-body {
  padding: 0.625rem 1rem;
  max-height: 180px;
  overflow-y: auto;
}

.module-log-line {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 0.8125rem;
  line-height: 1.7;
  display: flex;
  gap: 0.75rem;
}

.module-log-time {
  color: #475569;
  flex-shrink: 0;
}

.module-log-line--info .module-log-msg { color: #94a3b8; }
.module-log-line--success .module-log-msg { color: #4ade80; }
.module-log-line--warn .module-log-msg { color: #fbbf24; }
.module-log-line--error .module-log-msg { color: #f87171; }

.resource-summary {
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(71, 85, 105, 0.3);
  border-radius: 0.5rem;
  padding: 0.75rem 1rem;
  margin-top: 0.75rem;
}
.resource-summary__row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
}
.resource-summary__item {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}
.resource-summary__label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-muted);
  min-width: 70px;
}
.resource-summary__bar-wrap {
  flex: 1;
  height: 8px;
  background: rgba(51, 65, 85, 0.6);
  border-radius: 4px;
  overflow: hidden;
  position: relative;
}
.resource-summary__bar {
  height: 100%;
  border-radius: 4px;
  transition: width 0.4s ease;
}
.resource-summary__bar--ok { background: #4ade80; }
.resource-summary__bar--mid { background: #facc15; }
.resource-summary__bar--warn { background: #f87171; }
.resource-summary__values {
  font-size: 0.7rem;
  color: var(--text-muted);
  white-space: nowrap;
  min-width: 140px;
}
.resource-summary__load {
  color: rgba(148, 163, 184, 0.6);
}
.resource-summary__legend {
  display: flex;
  gap: 1rem;
  margin-top: 0.5rem;
}
.resource-summary__legend-item {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.65rem;
  color: var(--text-muted);
}
.resource-summary__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}
.resource-summary__dot--running { background: #4ade80; }
.resource-summary__dot--defined { background: rgba(148, 163, 184, 0.35); }
.resource-summary__warning {
  margin: 0.5rem 0 0;
  font-size: 0.75rem;
  color: #f87171;
  line-height: 1.4;
}
.resource-summary__warning--mild {
  color: #facc15;
}

/* Provision step indicators */
.provision-steps {
  display: flex;
  gap: 0.25rem;
}

.provision-step {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.6rem;
  font-weight: 700;
  border: 1.5px solid #475569;
  color: #64748b;
  background: transparent;
  transition: all 0.3s ease;
}

.provision-step--done {
  background: rgba(34, 197, 94, 0.2);
  border-color: #22c55e;
  color: #4ade80;
}

.provision-step--active {
  background: rgba(59, 130, 246, 0.2);
  border-color: #3b82f6;
  color: #60a5fa;
  animation: provision-pulse 1.5s ease-in-out infinite;
}

.provision-step--pending {
  opacity: 0.4;
}

@keyframes provision-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.3); }
  50% { box-shadow: 0 0 0 4px rgba(59, 130, 246, 0); }
}

/* ── VM Definition Slide Panel ─────────────────────────────── */

.vm-def-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1000;
  display: flex;
  justify-content: flex-end;
}

.vm-def-panel {
  width: 480px;
  max-width: 90vw;
  background: var(--card-bg, #1e293b);
  border-left: 1px solid var(--border-primary, #334155);
  display: flex;
  flex-direction: column;
  height: 100vh;
  box-shadow: -8px 0 30px rgba(0, 0, 0, 0.3);
}

.vm-def-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid var(--border-primary, #334155);
  flex-shrink: 0;
}

.vm-def-panel-header h3 {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-primary, #e2e8f0);
  margin: 0;
}

.vm-def-close-btn {
  background: none;
  border: none;
  color: var(--text-muted, #64748b);
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 0.25rem;
  transition: color 0.2s;
}

.vm-def-close-btn:hover {
  color: var(--text-primary, #e2e8f0);
}

.vm-def-panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 1.25rem 1.5rem;
}

.vm-def-panel-footer {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem 1.5rem;
  border-top: 1px solid var(--border-primary, #334155);
  flex-shrink: 0;
}

.vm-def-section-title {
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted, #64748b);
  margin: 1.25rem 0 0.75rem;
  padding-bottom: 0.35rem;
  border-bottom: 1px solid var(--border-primary, #334155);
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.vm-type-toggle {
  display: flex;
  gap: 0;
  border: 1px solid var(--border-primary, #334155);
  border-radius: 0.5rem;
  overflow: hidden;
}

.vm-type-toggle button {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  padding: 0.5rem 1rem;
  background: transparent;
  border: none;
  color: var(--text-muted, #64748b);
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.vm-type-toggle button:first-child {
  border-right: 1px solid var(--border-primary, #334155);
}

.vm-type-toggle button.active {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
}

.vm-type-toggle button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.vm-def-edit-btn {
  background: none;
  border: 1px solid transparent;
  color: var(--text-muted, #64748b);
  cursor: pointer;
  padding: 0.3rem;
  border-radius: 0.25rem;
  transition: all 0.2s;
  display: flex;
  align-items: center;
}

.vm-def-edit-btn:hover {
  color: #60a5fa;
  border-color: rgba(59, 130, 246, 0.3);
  background: rgba(59, 130, 246, 0.1);
}

.vm-def-type-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-muted, #94a3b8);
  padding: 0.5rem 0;
}

.vm-def-active-banner {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.6rem 0.75rem;
  margin-bottom: 0.75rem;
  font-size: 0.75rem;
  color: #60a5fa;
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 0.5rem;
}

.vm-def-edit-warning {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.6rem 0.75rem;
  margin-top: 1rem;
  font-size: 0.75rem;
  color: #fbbf24;
  background: rgba(234, 179, 8, 0.1);
  border: 1px solid rgba(234, 179, 8, 0.2);
  border-radius: 0.5rem;
}

.form-hint {
  font-size: 0.65rem;
  color: var(--text-muted, #64748b);
  font-weight: 400;
}

.form-row {
  display: flex;
  gap: 0.75rem;
}

.form-row .form-group {
  flex: 1;
}

/* Slide-right transition */
.slide-right-enter-active,
.slide-right-leave-active {
  transition: opacity 0.25s ease;
}

.slide-right-enter-active .vm-def-panel,
.slide-right-leave-active .vm-def-panel {
  transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.slide-right-enter-from {
  opacity: 0;
}

.slide-right-enter-from .vm-def-panel {
  transform: translateX(100%);
}

.slide-right-leave-to {
  opacity: 0;
}

.slide-right-leave-to .vm-def-panel {
  transform: translateX(100%);
}

/* Disk Management Modal */
.disk-usage-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
  margin-top: 0.5rem;
}

.disk-card {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 0.5rem;
  padding: 0.75rem 1rem;
}

.disk-card__label {
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.5);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.25rem;
}

.disk-card__value {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text-primary);
}

.disk-card__detail {
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.4);
  margin-top: 0.25rem;
}

.disk-action-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem 1rem;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 0.5rem;
}

.disk-action-row strong {
  font-size: 0.875rem;
  color: var(--text-primary);
}

.disk-action-desc {
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.4);
  margin-top: 0.125rem;
}

/* Live build status: a long background build must never read as hung. */
.build-status { margin-top: 0.8rem; padding: 0.6rem 0.7rem; border-radius: 8px;
  background: rgba(245,165,36,.06); border: 1px solid rgba(245,165,36,.22); }
.build-status__row { display: flex; align-items: center; gap: 0.5rem; font-size: 0.8rem; }
.build-status__dot { width: 8px; height: 8px; border-radius: 50%; background: #f5a524; flex: none;
  animation: bs-pulse 1.4s ease-in-out infinite; }
@keyframes bs-pulse { 0%,100% { opacity: 1; transform: scale(1); } 50% { opacity: .35; transform: scale(.72); } }
.build-status__phase { font-weight: 600; color: var(--text, #e5e7eb); }
.build-status__time { margin-left: auto; color: var(--text-muted); font-size: 0.72rem; font-variant-numeric: tabular-nums; white-space: nowrap; }
.build-status__track { height: 5px; border-radius: 3px; background: rgba(255,255,255,.08); overflow: hidden; margin: 0.5rem 0 0.45rem; }
.build-status__fill { height: 100%; border-radius: 3px; transition: width .6s ease;
  background: linear-gradient(90deg,#f5a524,#fbbf24); }
.build-status__note { font-size: 0.7rem; color: var(--text-muted); line-height: 1.4; }
</style>


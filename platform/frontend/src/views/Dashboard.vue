<template>
  <div class="dashboard-page">
    <div class="dashboard-container">
      <!-- Welcome Header -->
      <div class="welcome-header">
        <img src="/ocr-logo-dark.png" alt="OpenCyberRange" class="welcome-logo" />
        <div class="welcome-text">
          <h1 class="page-title">Welcome, {{ username }}</h1>
          <p class="page-subtitle">Configure your VPN connection to access lab environments</p>
        </div>
      </div>

      <!-- Background lab pre-build banner (fresh installs) -->
      <transition name="fade">
        <div v-if="prebuild.active && !prebuildDismissed" class="prebuild-banner">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex:none;"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
          <span>Lab environments are finishing setup<template v-if="prebuild.total"> ({{ prebuild.done }}/{{ prebuild.total }} ready)</template>. Exercises not yet built will show &ldquo;preparing&rdquo; for a few minutes.</span>
          <button @click="prebuildDismissed = true" class="prebuild-banner__x" aria-label="Dismiss">&times;</button>
        </div>
      </transition>

      <!-- Connection Cards Row -->
      <div class="cards-row">
        <!-- VPN Configuration Card -->
        <div class="vpn-card">
          <div class="vpn-card__header">
            <div class="vpn-card__icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2L3 7V12C3 16.97 7.02 21.45 12 22C16.98 21.45 21 16.97 21 12V7L12 2Z"/>
              </svg>
            </div>
            <div class="vpn-card__title-group">
              <h2 class="vpn-card__title">VPN Configuration</h2>
              <p class="vpn-card__description">Download your WireGuard config to connect from your own machine</p>
            </div>
          </div>

          <div class="vpn-card__content">
            <div class="vpn-status">
              <div class="vpn-status__item">
                <span class="vpn-status__label">Status</span>
                <span class="vpn-status__value" :class="getVpnStatusClass()" :title="vpnStatusHint">
                  {{ getVpnStatusText() }}
                </span>
              </div>
              <div class="vpn-status__item" v-if="vpnStatus.client_ip">
                <span class="vpn-status__label">Your VPN IP</span>
                <span class="vpn-status__value vpn-status__value--ip">{{ vpnStatus.client_ip }}</span>
              </div>
            </div>

            <button
              @click="downloadVpnConfig"
              :disabled="!vpnStatus.enabled"
              class="btn btn--lg vpn-download-btn"
              :class="vpnStatus.enabled ? 'btn--primary' : 'btn--disabled'"
              :title="vpnStatus.enabled ? '' : 'An administrator has turned VPN access off for this platform'"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-icon">
                <path d="M21 15V19C21 20.1 20.1 21 19 21H5C3.9 21 3 20.1 3 19V15"/>
                <polyline points="7 10 12 15 17 10"/>
                <line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
              {{ vpnStatus.enabled ? 'Download VPN Config' : 'VPN Disabled' }}
            </button>
            <p v-if="!vpnStatus.enabled" class="vpn-card__description" style="margin-top:0.5rem;">
              VPN access is turned off for this platform. Launch a RangeBox to reach your labs from the browser instead.
            </p>
          </div>
        </div>

        <!-- RangeBox Card -->
        <div class="vpn-card rangebox-card">
          <div class="vpn-card__header">
            <div class="vpn-card__icon rangebox-card__icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
                <line x1="8" y1="21" x2="16" y2="21"/>
                <line x1="12" y1="17" x2="12" y2="21"/>
              </svg>
            </div>
            <div class="vpn-card__title-group">
              <h2 class="vpn-card__title">RangeBox</h2>
              <p class="vpn-card__description">Browser-based Linux desktop, no VPN or local tools required</p>
            </div>
          </div>

          <div class="vpn-card__content">
            <div class="vpn-status">
              <div class="vpn-status__item">
                <span class="vpn-status__label">Status</span>
                <span class="vpn-status__value" :class="statusDisplayClass">
                  {{ statusDisplayLabel }}
                </span>
              </div>
              <div class="vpn-status__item">
                <span class="vpn-status__label">Capacity</span>
                <span class="vpn-status__value" :class="capacityClass">
                  {{ rangeboxCapacity.running }}/{{ rangeboxCapacity.max }}
                </span>
              </div>
              <div v-if="rangeboxStatus !== 'running'" class="vpn-status__item">
                <span class="vpn-status__label">Image</span>
                <div class="image-toggle">
                  <button
                    class="image-toggle__btn"
                    :class="{ 'image-toggle__btn--active': rangeboxImage === 'kali' }"
                    @click="rangeboxImage = 'kali'"
                  >Kali</button>
                  <button
                    class="image-toggle__btn"
                    :class="{ 'image-toggle__btn--active': rangeboxImage === 'ubuntu' }"
                    @click="rangeboxImage = 'ubuntu'"
                  >Ubuntu</button>
                </div>
              </div>
            </div>

            <button
              @click="onPrimaryLaunch()"
              :disabled="primaryDisabled"
              class="btn btn--lg"
              :class="primaryButtonClass"
            >
              <svg v-if="primaryLoading" class="btn-icon rangebox-spinner" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
              </svg>
              <svg v-else-if="primaryIsStop" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-icon">
                <rect x="6" y="6" width="12" height="12" rx="1"/>
              </svg>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-icon">
                <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
                <line x1="8" y1="21" x2="16" y2="21"/>
                <line x1="12" y1="17" x2="12" y2="21"/>
              </svg>
              {{ primaryButtonLabel }}
            </button>
          </div>
        </div>
      </div>

      <!-- RangeBox Viewer (full width, below cards) -->
      <transition name="slide">
        <div v-if="showRangebox && rangeboxStatus === 'running'" class="rangebox-viewer-panel">
          <RangeBox :standalone="true" :image-name="rangeboxImage" :status-data="rangeboxStatusData" />
        </div>
      </transition>


      <!-- VPN Setup Instructions (Expandable, per-OS) -->
      <div class="instructions-card">
        <button class="instructions-header" @click="showInstructions = !showInstructions">
          <div class="instructions-header__left">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="instructions-icon">
              <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
              <line x1="8" y1="21" x2="16" y2="21"/>
              <line x1="12" y1="17" x2="12" y2="21"/>
            </svg>
            <span>VPN Setup Instructions</span>
          </div>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
               class="chevron-icon" :class="{ 'chevron-icon--open': showInstructions }">
            <polyline points="6 9 12 15 18 9"/>
          </svg>
        </button>

        <transition name="slide">
          <div v-if="showInstructions" class="instructions-content">

            <!-- OS selector -->
            <div class="os-toggle image-toggle" role="tablist" aria-label="Operating system">
              <button
                v-for="os in osTabs"
                :key="os.id"
                class="image-toggle__btn"
                :class="{ 'image-toggle__btn--active': instructionsOs === os.id }"
                role="tab"
                :aria-selected="instructionsOs === os.id"
                @click="instructionsOs = os.id"
              >{{ os.label }}</button>
            </div>

            <!-- Linux -->
            <template v-if="instructionsOs === 'linux'">
              <div class="instruction-step">
                <div class="step-number">1</div>
                <div class="step-content">
                  <h3 class="step-title">Install WireGuard</h3>
                  <p class="step-description">Open a terminal and run the following command:</p>
                  <div class="code-block">
                    <code>sudo apt update && sudo apt install wireguard -y</code>
                    <CopyButton text="sudo apt update && sudo apt install wireguard -y" />
                  </div>
                  <p class="step-note">This is the only prerequisite. All other VPN components are installed automatically when you connect.</p>
                </div>
              </div>

              <div class="instruction-step">
                <div class="step-number">2</div>
                <div class="step-content">
                  <h3 class="step-title">Download and Save Configuration</h3>
                  <ol class="step-list">
                    <li>Click the <strong>"Download VPN Config"</strong> button above</li>
                    <li>Move it to WireGuard's config directory:</li>
                  </ol>
                  <div class="code-block">
                    <code>sudo mv ~/Downloads/ocr-vpn.conf /etc/wireguard/ && sudo chmod 600 /etc/wireguard/ocr-vpn.conf</code>
                    <CopyButton text="sudo mv ~/Downloads/ocr-vpn.conf /etc/wireguard/ && sudo chmod 600 /etc/wireguard/ocr-vpn.conf" />
                  </div>
                </div>
              </div>

              <div class="instruction-step">
                <div class="step-number">3</div>
                <div class="step-content">
                  <h3 class="step-title">Connect</h3>
                  <div class="code-block">
                    <code>sudo wg-quick up ocr-vpn</code>
                    <CopyButton text="sudo wg-quick up ocr-vpn" />
                  </div>
                  <p class="step-note">The first connection may take a few extra seconds while networking components are installed automatically.</p>
                  <div class="step-output">
                    <p class="output-label">Expected output:</p>
                    <pre>[#] ip link add ocr-vpn type wireguard
[#] /bin/bash -c '...'
[#] wg setconf ocr-vpn /dev/fd/63
[#] ip -4 address add 10.0.0.X/24 dev ocr-vpn
[#] ip link set mtu ... up dev ocr-vpn
[#] ip -4 route add 10.100.0.0/16 dev ocr-vpn</pre>
                  </div>
                </div>
              </div>

              <div class="instruction-step">
                <div class="step-number">4</div>
                <div class="step-content">
                  <h3 class="step-title">Verify Connection</h3>
                  <p class="step-description">Check your connection status:</p>
                  <div class="code-block">
                    <code>sudo wg show</code>
                    <CopyButton text="sudo wg show" />
                  </div>
                  <p class="step-note step-note--success">Look for <strong>"latest handshake"</strong> with a recent time and <strong>"transfer"</strong> showing received bytes. If both appear, you're connected! Start a lab from the Exercises page and scan its network.</p>
                </div>
              </div>

              <div class="instruction-step">
                <div class="step-number">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/>
                    <line x1="15" y1="9" x2="9" y2="15"/>
                    <line x1="9" y1="9" x2="15" y2="15"/>
                  </svg>
                </div>
                <div class="step-content">
                  <h3 class="step-title">Disconnecting</h3>
                  <p class="step-description">When you're done with labs:</p>
                  <div class="code-block">
                    <code>sudo wg-quick down ocr-vpn</code>
                    <CopyButton text="sudo wg-quick down ocr-vpn" />
                  </div>
                  <p class="step-note">This stops the VPN and cleans up all tunnel connections automatically.</p>
                </div>
              </div>
            </template>

            <!-- Windows -->
            <template v-else-if="instructionsOs === 'windows'">
              <div class="instruction-step">
                <div class="step-number">1</div>
                <div class="step-content">
                  <h3 class="step-title">Install WireGuard for Windows</h3>
                  <p class="step-description">Download the official installer from <a href="https://www.wireguard.com/install/" target="_blank" rel="noopener" class="step-link">wireguard.com/install</a> and run it. Installation requires administrator rights.</p>
                </div>
              </div>

              <div class="instruction-step">
                <div class="step-number">2</div>
                <div class="step-content">
                  <h3 class="step-title">Download and Import Configuration</h3>
                  <ol class="step-list">
                    <li>Click the <strong>"Download VPN Config"</strong> button above; the file saves as <code>ocr-vpn.conf</code></li>
                    <li>Open the WireGuard app and click <strong>"Import tunnel(s) from file"</strong></li>
                    <li>Select <code>ocr-vpn.conf</code> from your Downloads folder</li>
                  </ol>
                </div>
              </div>

              <div class="instruction-step">
                <div class="step-number">3</div>
                <div class="step-content">
                  <h3 class="step-title">Connect and Verify</h3>
                  <p class="step-description">Select the <strong>ocr-vpn</strong> tunnel and click <strong>Activate</strong>.</p>
                  <p class="step-note step-note--success">In the tunnel details, look for <strong>"Latest handshake"</strong> with a recent time and <strong>"Transfer"</strong> showing received bytes. If both appear, you're connected! Start a lab from the Exercises page and scan its network.</p>
                  <p class="step-note">When you're done with labs, click <strong>Deactivate</strong> on the same screen.</p>
                </div>
              </div>

              <div class="instruction-step">
                <div class="step-number">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/>
                    <line x1="12" y1="8" x2="12" y2="12"/>
                    <line x1="12" y1="16" x2="12.01" y2="16"/>
                  </svg>
                </div>
                <div class="step-content">
                  <h3 class="step-title">Can't install software?</h3>
                  <p class="step-description">If your machine is locked down (no admin rights, managed laptop), launch a <strong>RangeBox</strong> from the card above instead. It runs entirely in the browser and already sits on the lab network, so no VPN is needed.</p>
                </div>
              </div>
            </template>

            <!-- macOS -->
            <template v-else>
              <div class="instruction-step">
                <div class="step-number">1</div>
                <div class="step-content">
                  <h3 class="step-title">Install WireGuard</h3>
                  <p class="step-description">Install the WireGuard app from the <strong>Mac App Store</strong> (search for "WireGuard"), or grab it from <a href="https://www.wireguard.com/install/" target="_blank" rel="noopener" class="step-link">wireguard.com/install</a>.</p>
                </div>
              </div>

              <div class="instruction-step">
                <div class="step-number">2</div>
                <div class="step-content">
                  <h3 class="step-title">Download and Import Configuration</h3>
                  <ol class="step-list">
                    <li>Click the <strong>"Download VPN Config"</strong> button above; the file saves as <code>ocr-vpn.conf</code></li>
                    <li>Open WireGuard and choose <strong>"Import Tunnel(s) from File..."</strong> (also available from the menu bar icon)</li>
                    <li>Select <code>ocr-vpn.conf</code> from your Downloads folder</li>
                  </ol>
                </div>
              </div>

              <div class="instruction-step">
                <div class="step-number">3</div>
                <div class="step-content">
                  <h3 class="step-title">Connect and Verify</h3>
                  <p class="step-description">Select the <strong>ocr-vpn</strong> tunnel and click <strong>Activate</strong>. macOS may ask you to allow the VPN configuration the first time.</p>
                  <p class="step-note step-note--success">In the tunnel details, look for <strong>"Latest handshake"</strong> with a recent time and data received. If both appear, you're connected! Start a lab from the Exercises page and scan its network.</p>
                  <p class="step-note">When you're done with labs, click <strong>Deactivate</strong> or toggle the tunnel off from the menu bar icon.</p>
                </div>
              </div>

              <div class="instruction-step">
                <div class="step-number">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/>
                    <line x1="12" y1="8" x2="12" y2="12"/>
                    <line x1="12" y1="16" x2="12.01" y2="16"/>
                  </svg>
                </div>
                <div class="step-content">
                  <h3 class="step-title">Can't install software?</h3>
                  <p class="step-description">If your machine is locked down (managed laptop, no App Store access), launch a <strong>RangeBox</strong> from the card above instead. It runs entirely in the browser and already sits on the lab network, so no VPN is needed.</p>
                </div>
              </div>
            </template>

            <!-- Troubleshooting -->
            <div v-if="instructionsOs === 'linux'" class="troubleshooting-section">
              <h3 class="troubleshooting-title">Troubleshooting</h3>
              <table class="troubleshooting-table">
                <thead>
                  <tr>
                    <th>Issue</th>
                    <th>Solution</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td><code>RTNETLINK answers: Operation not permitted</code></td>
                    <td>Run with <code>sudo</code></td>
                  </tr>
                  <tr>
                    <td><code>Unable to access interface</code></td>
                    <td>WireGuard not installed — run Step 1</td>
                  </tr>
                  <tr>
                    <td><code>ocr-vpn already exists</code></td>
                    <td>Run: <code>sudo nmcli connection delete ocr-vpn 2>/dev/null; sudo wg-quick up ocr-vpn</code></td>
                  </tr>
                  <tr>
                    <td>No handshake appearing</td>
                    <td>Ensure outbound HTTPS (port 443) is allowed on your network</td>
                  </tr>
                  <tr>
                    <td>No route to 10.100.x.x</td>
                    <td>Restart VPN: <code>sudo wg-quick down ocr-vpn && sudo wg-quick up ocr-vpn</code></td>
                  </tr>
                  <tr>
                    <td>Connected but no lab traffic</td>
                    <td>Make sure you have a lab running from the Exercises page, then scan with <code>nmap</code></td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div v-else class="troubleshooting-section">
              <h3 class="troubleshooting-title">Troubleshooting</h3>
              <table class="troubleshooting-table">
                <thead>
                  <tr>
                    <th>Issue</th>
                    <th>Solution</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>No handshake appearing</td>
                    <td>Ensure outbound HTTPS (port 443) is allowed on your network</td>
                  </tr>
                  <tr>
                    <td>Tunnel active but no lab traffic</td>
                    <td>Make sure you have a lab running from the Exercises page, then try again</td>
                  </tr>
                  <tr>
                    <td>Import rejected or tunnel fails to start</td>
                    <td>Re-download the config; each download issues a fresh, valid file</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </transition>
      </div>

      <!-- Go to Exercises Button -->
      <div class="dashboard-actions">
        <router-link to="/exercises" class="btn btn--primary btn--lg">
          Go to Exercises
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-icon btn-icon--right">
            <line x1="5" y1="12" x2="19" y2="12"/>
            <polyline points="12 5 19 12 12 19"/>
          </svg>
        </router-link>
      </div>

      <!-- Global toast (copy feedback, download errors) -->
      <Toast />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, h } from 'vue'
import axios from '../api/axios'
import { useVpnStatus } from '../composables/useVpnStatus'
import { usePoll } from '../composables/usePoll'
import { useClipboard } from '../composables/useClipboard'
import RangeBox from '../components/RangeBox.vue'
import Toast, { showToast } from '../components/Toast.vue'

// The composable's getters are connected-aware: "Connected" needs a live
// WireGuard handshake (vpn_connected), while "Registered (tunnel down)"
// flags a config that was activated once but has no tunnel up right now.
const { vpnStatus, fetchVpnStatus, getVpnStatusText, getVpnStatusClass } = useVpnStatus()

// Hover hint explaining what the status value means and what to do next.
const vpnStatusHint = computed(() => {
  const s = vpnStatus.value
  if (!s.has_config) return 'Download the config below to get started'
  if (s.vpn_connected) return 'Recent WireGuard handshake seen; the tunnel is up'
  if (s.vpn_registered) return 'Your peer is registered on the server but no recent handshake was seen; activate the tunnel on your machine'
  return 'Config downloaded but the peer is not registered yet'
})

// Shared clipboard helper; feedback goes through the global toast.
const { copyText } = useClipboard(2000)
const copyToClipboard = async (text) => {
  await copyText(text)
  showToast('Copied to clipboard', 'info', 2000)
}

// Copy-to-clipboard button rendered beside every command. Extracted as a
// small functional component so the icon SVG is defined once instead of
// pasted per code block. Sizes are set inline because Dashboard's scoped
// styles do not reach elements nested inside a child component.
const CopyButton = (props) => h(
  'button',
  { class: 'copy-btn', title: 'Copy to clipboard', type: 'button', onClick: () => copyToClipboard(props.text) },
  [h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2', width: '16', height: '16' }, [
    h('rect', { x: '9', y: '9', width: '13', height: '13', rx: '2', ry: '2' }),
    h('path', { d: 'M5 15H4C2.9 15 2 14.1 2 13V4C2 2.9 2.9 2 4 2H13C14.1 2 15 2.9 15 4V5' })
  ])]
)
CopyButton.props = { text: { type: String, required: true } }

const showInstructions = ref(false)

// Per-OS setup instructions; Linux stays the default (most common client here).
const instructionsOs = ref('linux')
const osTabs = [
  { id: 'linux', label: 'Linux' },
  { id: 'windows', label: 'Windows' },
  { id: 'macos', label: 'macOS' }
]

// Get username from localStorage and format in sentence case
const username = computed(() => {
  try {
    const userStr = localStorage.getItem('user')
    if (!userStr) return 'Student'
    const user = JSON.parse(userStr)
    if (!user.username) return 'Student'
    // Format in sentence case: first letter uppercase, rest lowercase
    return user.username.charAt(0).toUpperCase() + user.username.slice(1).toLowerCase()
  } catch (error) {
    return 'Student'
  }
})

// RangeBox state
const rangeboxStatus = ref('not_found')
// Full /rangebox/standalone/status payload, handed to <RangeBox> so it does
// not re-fetch the same endpoint for its session timer.
const rangeboxStatusData = ref(null)
const rangeboxLoading = ref(false)
const showRangebox = ref(false)
const rangeboxImage = ref('kali')
const rangeboxCapacity = ref({ running: 0, max: 0, available: true })

const fetchRangeboxCapacity = async () => {
  try {
    const { data } = await axios.get('/rangebox/capacity')
    rangeboxCapacity.value = data
  } catch {
    // Keep previous values on error
  }
}

const fetchRangeboxStatus = async () => {
  try {
    const response = await axios.get('/rangebox/standalone/status')
    rangeboxStatusData.value = response.data || null
    rangeboxStatus.value = response.data?.status || 'not_found'
    if (rangeboxStatus.value === 'running') {
      showRangebox.value = true
    }
  } catch (error) {
    rangeboxStatus.value = 'not_found'
  }
}

const launchRangebox = async () => {
  rangeboxLoading.value = true
  rangeboxStatus.value = 'starting'
  try {
    await axios.post(`/rangebox/standalone/launch?image=${rangeboxImage.value}`)
    let attempts = 0
    const poll = setInterval(async () => {
      attempts++
      await fetchRangeboxStatus()
      if (rangeboxStatus.value === 'running' || attempts > 15) {
        clearInterval(poll)
        rangeboxLoading.value = false
        showRangebox.value = true
      }
    }, 2000)
  } catch (error) {
    console.error('Failed to launch RangeBox:', error)
    rangeboxStatus.value = 'not_found'
    rangeboxLoading.value = false
  }
}

const stopRangebox = async () => {
  rangeboxLoading.value = true
  rangeboxStatus.value = 'stopping'
  showRangebox.value = false
  try {
    await axios.delete('/rangebox/standalone/destroy')
    rangeboxStatus.value = 'not_found'
  } catch (error) {
    console.error('Failed to stop RangeBox:', error)
    await fetchRangeboxStatus()
  } finally {
    rangeboxLoading.value = false
  }
}

// Background lab pre-build: dismissible "still preparing" banner while images
// finish building after a fresh install.
const prebuild = ref({ active: false, total: 0, done: 0 })
const prebuildDismissed = ref(false)
const fetchPrebuildStatus = async () => {
  try {
    const { data } = await axios.get('/labs/prebuild-status')
    prebuild.value = data
  } catch { /* endpoint absent -> ignore */ }
}

// Tearing down frees the student's slot (matches the RangeBox Stop semantics).

const rangeboxButtonLabel = computed(() => {
  switch (rangeboxStatus.value) {
    case 'running': return 'Stop RangeBox'
    case 'starting': return 'Starting...'
    case 'stopping': return 'Stopping...'
    default:
      return rangeboxCapacity.value.available ? 'Launch RangeBox' : 'Unavailable'
  }
})

const primaryLoading = computed(() => rangeboxLoading.value)
const primaryIsStop = computed(() => rangeboxStatus.value === 'running')
const primaryDisabled = computed(() =>
  rangeboxLoading.value || (!rangeboxCapacity.value.available && rangeboxStatus.value !== 'running')
)
const primaryButtonClass = computed(() => {
  if (rangeboxStatus.value === 'running') return 'btn--danger'
  return rangeboxCapacity.value.available ? 'btn--rangebox' : 'btn--disabled'
})
const primaryButtonLabel = computed(() => {
  if (primaryLoading.value) return 'Starting...'
  if (primaryIsStop.value) return 'Stop RangeBox'
  if (!rangeboxCapacity.value.available) return 'Unavailable'
  return 'Launch RangeBox'
})
const onPrimaryLaunch = () => {
  rangeboxStatus.value === 'running' ? stopRangebox() : launchRangebox()
}

const rangeboxStatusLabel = computed(() => {
  switch (rangeboxStatus.value) {
    case 'running': return 'Running'
    case 'starting': return 'Starting'
    case 'stopping': return 'Stopping'
    default:
      return rangeboxCapacity.value.available ? 'Not Running' : 'Unavailable'
  }
})

const rangeboxStatusClass = computed(() => {
  switch (rangeboxStatus.value) {
    case 'running': return 'vpn-status__value--ready'
    case 'starting':
    case 'stopping': return 'vpn-status__value--pending'
    default:
      return rangeboxCapacity.value.available ? '' : 'vpn-status__value--danger'
  }
})

const statusDisplayLabel = computed(() => {
  return rangeboxStatusLabel.value
})
const statusDisplayClass = computed(() => {
  return rangeboxStatusClass.value
})

const capacityClass = computed(() => {
  const { running, max } = rangeboxCapacity.value
  if (running >= max) return 'vpn-status__value--danger'
  if (running >= max * 0.8) return 'vpn-status__value--pending'
  return 'vpn-status__value--ready'
})

// fetchVpnStatus is now provided by useVpnStatus composable

const downloadVpnConfig = async () => {
  try {
    const response = await axios.get('/labs/vpn-config', {
      responseType: 'blob'
    })
    
    // Create download link
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'ocr-vpn.conf')
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
    
    // Refresh status
    await fetchVpnStatus()
  } catch (error) {
    console.error('Failed to download VPN config:', error)
    showToast('Failed to download VPN configuration. Please try again.', 'error')
  }
}

// Refresh VPN status every 10 seconds; capacity every 15. Both pause while the
// tab is hidden and refresh immediately when it becomes visible again.
usePoll(fetchVpnStatus, 10000)
usePoll(() => { fetchRangeboxCapacity(); fetchPrebuildStatus() }, 15000)

onMounted(() => {
  fetchVpnStatus()
  fetchRangeboxStatus()
  fetchRangeboxCapacity()
  fetchPrebuildStatus()
})
</script>

<style scoped>
.dashboard-page {
  min-height: 100vh;
  background: var(--bg-primary);
  padding: 2rem;
}

.dashboard-container {
  max-width: 900px;
  margin: 0 auto;
}

.local-banner {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  margin-bottom: 1.5rem;
  background: var(--bg-secondary);
  border: 1px solid var(--accent-blue, #4a90d9);
  border-radius: 8px;
  color: var(--text-secondary);
  font-size: 0.875rem;
  line-height: 1.4;
}

.local-banner__icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  color: var(--accent-blue, #4a90d9);
}

/* Welcome Header */
.welcome-header {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  margin-bottom: 2rem;
}

.welcome-logo {
  width: 72px;
  height: 72px;
  flex-shrink: 0;
  background: var(--bg-primary);
  border-radius: 14px;
  padding: 5px;
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

/* Cards Row */
.cards-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

/* VPN Card */
.vpn-card {
  background: var(--bg-secondary);
  border-radius: 12px;
  padding: 1.5rem;
  border: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
}

.vpn-card__header {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.vpn-card__icon {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.vpn-card__icon svg {
  width: 24px;
  height: 24px;
  color: white;
}

.vpn-card__title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 0.25rem 0;
}

.vpn-card__description {
  font-size: 0.875rem;
  color: var(--text-muted);
  margin: 0;
}

/* RangeBox Card */
.rangebox-card__icon {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
}

.vpn-card__content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  justify-content: space-between;
}

.rangebox-viewer-panel {
  background: var(--bg-secondary);
  border-radius: 12px;
  border: 1px solid var(--border-color);
  overflow: hidden;
  margin-bottom: 1.5rem;
}

.btn--rangebox {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
}

.btn--rangebox:hover {
  background: linear-gradient(135deg, #059669 0%, #047857 100%);
  transform: translateY(-1px);
}

.btn--danger {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  color: white;
}

.btn--danger:hover {
  background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
  transform: translateY(-1px);
}

.image-toggle {
  display: flex;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid var(--border-color);
}

.image-toggle__btn {
  padding: 0.3rem 0.75rem;
  font-size: 0.8125rem;
  font-weight: 600;
  cursor: pointer;
  border: none;
  background: var(--bg-primary);
  color: var(--text-muted);
  transition: all 0.2s;
}

.image-toggle__btn:first-child {
  border-right: 1px solid var(--border-color);
}

.image-toggle__btn--active {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
}

.image-toggle__btn:hover:not(.image-toggle__btn--active) {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.rangebox-spinner {
  animation: rangebox-spin 1s linear infinite;
}

@keyframes rangebox-spin {
  to { transform: rotate(360deg); }
}

/* VPN Status */
.vpn-status {
  display: flex;
  gap: 2rem;
  flex-wrap: wrap;
}

.vpn-status__item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.vpn-status__label {
  font-size: 0.75rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.vpn-status__value {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
}

.vpn-status__value--ready {
  color: var(--success);
}

.vpn-status__value--pending {
  color: var(--warning);
}

.vpn-status__value--ip {
  font-family: monospace;
  color: var(--accent);
}

.vpn-status__value--danger {
  color: var(--danger, #ef4444);
}

.btn--disabled {
  background: var(--bg-tertiary, #2a2a3e);
  color: var(--text-muted, #606080);
  cursor: not-allowed;
  opacity: 0.6;
}

.btn--disabled:hover {
  transform: none;
}

/* Buttons */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  text-decoration: none;
  transition: all 0.2s ease;
}

.btn--primary {
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  color: white;
}

.btn--primary:hover {
  background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
  transform: translateY(-1px);
}

.btn--lg {
  padding: 1rem 2rem;
  font-size: 1rem;
}

.btn-icon {
  width: 18px;
  height: 18px;
}

.btn-icon--right {
  margin-left: 0.25rem;
}

.vpn-download-btn {
  align-self: flex-start;
}

/* Instructions Card */
.instructions-card {
  background: var(--bg-secondary);
  border-radius: 12px;
  border: 1px solid var(--border-color);
  margin-bottom: 1.5rem;
  overflow: hidden;
}

.instructions-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 1rem 1.5rem;
  background: transparent;
  border: none;
  color: var(--text-primary);
  cursor: pointer;
  transition: background 0.2s ease;
}

.instructions-header:hover {
  background: var(--bg-tertiary);
}

.instructions-header__left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 1rem;
  font-weight: 600;
}

.instructions-icon {
  width: 20px;
  height: 20px;
  color: var(--accent);
}

.chevron-icon {
  width: 20px;
  height: 20px;
  color: var(--text-muted);
  transition: transform 0.2s ease;
}

.chevron-icon--open {
  transform: rotate(180deg);
}

.instructions-content {
  padding: 0 1.5rem 1.5rem;
}

/* OS selector inside the instructions card; reuses the image-toggle look */
.os-toggle {
  margin: 0.25rem 0 0.75rem;
  align-self: flex-start;
  display: inline-flex;
}

.step-link {
  color: var(--accent);
  text-decoration: underline;
}

/* Instruction Steps */
.instruction-step {
  display: flex;
  gap: 1rem;
  padding: 1.25rem 0;
  border-bottom: 1px solid var(--border-color);
}

.instruction-step:last-of-type {
  border-bottom: none;
}

.instruction-step--optional {
  opacity: 0.8;
}

.step-number {
  width: 32px;
  height: 32px;
  background: var(--accent);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 0.875rem;
  flex-shrink: 0;
}

.step-number svg {
  width: 16px;
  height: 16px;
}

.step-content {
  flex: 1;
  min-width: 0;
}

.step-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 0.5rem 0;
}

.step-description {
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin: 0 0 0.75rem 0;
}

.step-list {
  margin: 0 0 0.75rem 0;
  padding-left: 1.25rem;
  color: var(--text-secondary);
  font-size: 0.875rem;
}

.step-list li {
  margin-bottom: 0.5rem;
}

.step-list code {
  background: var(--bg-tertiary);
  padding: 0.125rem 0.375rem;
  border-radius: 4px;
  font-size: 0.8125rem;
}

.step-note {
  font-size: 0.8125rem;
  color: var(--text-muted);
  margin-top: 0.75rem;
}

.step-note--success {
  color: var(--success);
  font-weight: 500;
}

.step-note--warning {
  color: var(--warning);
  font-weight: 500;
}

.step-subtitle {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 1rem 0 0.5rem 0;
}

.step-description kbd {
  background: var(--bg-tertiary);
  padding: 0.125rem 0.5rem;
  border-radius: 4px;
  font-size: 0.8125rem;
  font-family: 'Fira Code', 'Consolas', monospace;
  border: 1px solid var(--border-color);
}

.optional-badge {
  background: var(--bg-tertiary);
  color: var(--text-muted);
  padding: 0.125rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
  margin-left: 0.5rem;
}

/* Code Block */
.code-block {
  display: flex;
  align-items: center;
  background: #0d1117;
  border-radius: 6px;
  padding: 0.75rem 1rem;
  margin-bottom: 0.75rem;
  border: 1px solid #30363d;
}

.code-block code {
  flex: 1;
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 0.8125rem;
  color: #c9d1d9;
  white-space: nowrap;
  overflow-x: auto;
}

.copy-btn {
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 0.25rem;
  margin-left: 0.5rem;
  border-radius: 4px;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.copy-btn:hover {
  color: var(--text-primary);
  background: var(--bg-tertiary);
}

.copy-btn svg {
  width: 16px;
  height: 16px;
}

/* Step Output */
.step-output {
  background: #0d1117;
  border-radius: 6px;
  padding: 0.75rem 1rem;
  margin-top: 0.75rem;
  border: 1px solid #30363d;
}

.output-label {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin: 0 0 0.5rem 0;
}

.step-output pre {
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 0.75rem;
  color: #8b949e;
  margin: 0;
  white-space: pre-wrap;
  line-height: 1.5;
}

/* Troubleshooting */
.troubleshooting-section {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--border-color);
}

.troubleshooting-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 1rem 0;
}

.troubleshooting-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8125rem;
}

.troubleshooting-table th,
.troubleshooting-table td {
  padding: 0.75rem;
  text-align: left;
  border-bottom: 1px solid var(--border-color);
}

.troubleshooting-table th {
  color: var(--text-muted);
  font-weight: 600;
  text-transform: uppercase;
  font-size: 0.75rem;
  letter-spacing: 0.05em;
}

.troubleshooting-table td {
  color: var(--text-secondary);
}

.troubleshooting-table code {
  background: var(--bg-tertiary);
  padding: 0.125rem 0.375rem;
  border-radius: 4px;
  font-size: 0.75rem;
}

/* Dashboard Actions */
.dashboard-actions {
  display: flex;
  justify-content: center;
  margin-top: 2rem;
}

/* Transitions */
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
  max-height: 2000px;
}

/* Responsive */
@media (max-width: 768px) {
  .cards-row {
    grid-template-columns: 1fr;
  }

  .dashboard-page {
    padding: 1rem;
  }

  .vpn-status {
    gap: 1rem;
  }

  .instruction-step {
    flex-direction: column;
    gap: 0.75rem;
  }

  .step-number {
    align-self: flex-start;
  }

  .code-block {
    flex-direction: column;
    align-items: stretch;
    gap: 0.5rem;
  }

  .code-block code {
    overflow-x: auto;
    padding-bottom: 0.5rem;
  }

  .copy-btn {
    align-self: flex-end;
    margin-left: 0;
  }
}

.prebuild-banner {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin: 0 0 1.25rem;
  padding: 0.7rem 1rem;
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.28);
  border-radius: 10px;
  color: #cfe0ff;
  font-size: 0.85rem;
}
.prebuild-banner__x {
  margin-left: auto;
  background: transparent;
  border: none;
  color: inherit;
  font-size: 1.2rem;
  line-height: 1;
  cursor: pointer;
  opacity: 0.7;
  padding: 0 0.25rem;
}
.prebuild-banner__x:hover { opacity: 1; }
</style>

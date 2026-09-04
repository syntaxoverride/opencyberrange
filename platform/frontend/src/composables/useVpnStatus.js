import { ref } from 'vue'
import axios from '../api/axios'

/**
 * Shared composable for VPN status
 * Ensures Dashboard and Profile pages use the exact same data and logic
 */
export function useVpnStatus() {
  const vpnStatus = ref({
    // Platform-wide VPN switch (Admin > Settings > VPN). Assume on until the
    // first response so an admin-disabled platform is the only thing that
    // greys the download, not a slow request.
    enabled: true,
    has_config: false,
    vpn_registered: false,
    vpn_connected: false,
    client_ip: null
  })

  const fetchVpnStatus = async () => {
    try {
      const response = await axios.get('/labs/vpn-status')
      vpnStatus.value = {
        enabled: response.data?.enabled !== false,
        has_config: response.data?.has_config || false,
        vpn_registered: response.data?.vpn_registered || false,
        vpn_connected: response.data?.vpn_connected || false,
        client_ip: response.data?.client_ip || null
      }
    } catch (error) {
      console.error('Failed to fetch VPN status:', error)
      // Reset to default on error, but keep VPN offered: a failed status call
      // is not evidence that an admin turned VPN off.
      vpnStatus.value = {
        enabled: true,
        has_config: false,
        vpn_registered: false,
        vpn_connected: false,
        client_ip: null
      }
    }
  }

  // Get VPN status text - same logic for both pages. "Connected" means a live
  // WireGuard handshake (vpn_connected); "Registered" alone only means the
  // config was activated once, so call out the missing tunnel explicitly.
  const getVpnStatusText = () => {
    if (!vpnStatus.value.has_config) {
      return 'Not Downloaded'
    }
    if (vpnStatus.value.vpn_connected) {
      return 'Connected'
    }
    if (vpnStatus.value.vpn_registered) {
      return 'Registered (tunnel down)'
    }
    return 'Not Registered'
  }

  // Get VPN status CSS class - same logic for both pages. Only a live tunnel
  // earns the green "ready" state; a registered-but-disconnected config shows
  // as pending so students notice the tunnel is not actually up.
  const getVpnStatusClass = () => {
    if (vpnStatus.value.has_config && vpnStatus.value.vpn_connected) {
      return 'vpn-status__value--ready'
    }
    return 'vpn-status__value--pending'
  }

  // Check if VPN is registered (for Profile page "Yes/No" display)
  const isVpnRegistered = () => {
    return vpnStatus.value.has_config && vpnStatus.value.vpn_registered
  }

  // Check if the tunnel is actually up right now
  const isVpnConnected = () => {
    return vpnStatus.value.has_config && vpnStatus.value.vpn_connected
  }

  // Note: the old setupAutoRefresh helper was removed; it duplicated the
  // usePoll composable and no view imported it. Use usePoll for refresh loops.

  return {
    vpnStatus,
    fetchVpnStatus,
    getVpnStatusText,
    getVpnStatusClass,
    isVpnRegistered,
    isVpnConnected
  }
}


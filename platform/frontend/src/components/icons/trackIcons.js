// Single source of truth for track iconography.
// Both Curriculum.vue and TrackDetail.vue import from here so the two views
// can never drift out of sync. Keys match the tracks.icon value in the DB.
import WindowsIcon from './WindowsIcon.vue'
import WindowsServerIcon from './WindowsServerIcon.vue'
import LinuxIcon from './LinuxIcon.vue'
import WebIcon from './WebIcon.vue'
import NetworkIcon from './NetworkIcon.vue'
import CapitalFlowIcon from './CapitalFlowIcon.vue'
import MeridianIcon from './MeridianIcon.vue'
import ICSIcon from './ICSIcon.vue'
import BrainIcon from './BrainIcon.vue'
import ForensicsIcon from './ForensicsIcon.vue'
import NetsecIcon from './NetsecIcon.vue'
import OtsocIcon from './OtsocIcon.vue'
import CoffeeshopIcon from './CoffeeshopIcon.vue'
import PentestIcon from './PentestIcon.vue'
import AdptIcon from './AdptIcon.vue'
import AisecIcon from './AisecIcon.vue'
import MasaIcon from './MasaIcon.vue'

export const iconComponents = {
  windows: WindowsIcon,
  'windows-server': WindowsServerIcon,
  linux: LinuxIcon,
  web: WebIcon,
  network: NetworkIcon,
  capitalflow: CapitalFlowIcon,
  server: MeridianIcon,
  ics: ICSIcon,
  brain: BrainIcon,
  forensics: ForensicsIcon,
  netsec: NetsecIcon,
  otsoc: OtsocIcon,
  coffeeshop: CoffeeshopIcon,
  pentest: PentestIcon,
  adpt: AdptIcon,
  aisec: AisecIcon,
  masa: MasaIcon
}

export const getTrackIcon = (iconName) => iconComponents[iconName] || WindowsIcon

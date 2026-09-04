import { ref, readonly } from 'vue'
import api from '../api/axios'

// Shared state across all components that call useModules()
const modules = ref({})
const devTools = ref(false)
const exerciseTester = ref(false)
const stressTester = ref(false)
const exerciseAuthoring = ref(false)
const loaded = ref(false)
let loading = false

async function fetchModules() {
  if (loading) return
  loading = true
  try {
    const { data } = await api.get('/modules/')
    modules.value = data.modules || {}
    devTools.value = data.dev_tools === true
    exerciseTester.value = data.exercise_tester === true
    stressTester.value = data.stress_tester === true
    exerciseAuthoring.value = data.exercise_authoring === true
    loaded.value = true
  } catch {
    // If fetch fails (e.g. not logged in), default to all disabled
    modules.value = {}
    devTools.value = false
    exerciseTester.value = false
    stressTester.value = false
    exerciseAuthoring.value = false
  } finally {
    loading = false
  }
}

function isModuleEnabled(moduleId) {
  return modules.value[moduleId]?.enabled === true
}

// Router-guard helper: answer from the shared cache when loaded, fetching only
// on the first module-route navigation instead of once per navigation.
async function ensureModules() {
  if (!loaded.value) await fetchModules()
  return loaded.value
}

function resetModules() {
  modules.value = {}
  loaded.value = false
}

export { ensureModules, isModuleEnabled }

export function useModules() {
  return {
    modules: readonly(modules),
    devTools: readonly(devTools),
    exerciseTester: readonly(exerciseTester),
    stressTester: readonly(stressTester),
    exerciseAuthoring: readonly(exerciseAuthoring),
    loaded: readonly(loaded),
    fetchModules,
    isModuleEnabled,
    resetModules,
  }
}

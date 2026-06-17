<template>
  <main class="app-shell">
    <TopBar
      :ws-state-text="wsStateText"
      :ws-state-class="wsStateClass"
      :is-logged-in="isLoggedIn"
      @refresh="refreshAll"
      @logout="logout"
    />

    <ConfigPanel :config="config" />

    <section :class="['workspace', { 'preview-only': !isLoggedIn }]">
      <CameraPanel
        v-if="isLoggedIn"
        :cameras="cameras"
        :selected-camera-id="selectedCameraId"
        :selected-camera="selectedCamera"
        :new-camera="newCamera"
        :camera-draft="cameraDraft"
        :loading="loading"
        @load-cameras="loadCameras"
        @create-camera="createCamera"
        @select-camera="selectCamera"
        @update-camera="updateCamera"
      />

      <VideoPreview
        :selected-camera="selectedCamera"
        :manual-camera="manualPreviewCamera"
        :preview-draft="previewDraft"
        :mjpeg-url="mjpegUrl"
        :overlay="overlay"
        :visible-boxes="visibleBoxes"
        :frame-info="frameInfo"
        :latest-alert-time="latestAlertTime"
        :task-status-text="taskStatusText"
        :task-status-class="taskStatusClass"
        :video-state="videoState"
        :loading="loading"
        @connect-ws="connectWs"
        @sync-overlay-size="syncOverlaySize"
        @video-error="handleVideoError"
        @reload-video="reloadVideo"
        @probe-video="probeVideo"
      />

      <TaskAlertsPanel
        v-if="isLoggedIn"
        :task="task"
        :selected-camera="selectedCamera"
        :task-draft="taskDraft"
        :alerts="alerts"
        @toggle-detection="toggleDetection"
        @toggle-boxes="toggleBoxes"
        @load-alerts="loadAlerts"
        @mark-alert-read="markAlertRead"
        @delete-alert="deleteAlert"
      />
    </section>

    <ToastMessage :toast="toast" />
  </main>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { createFallApi } from '../api/fall'
import { buildMjpegUrl, normalizeStreamUrl, probeVideoStream } from '../api/video'
import CameraPanel from '../components/CameraPanel.vue'
import ConfigPanel from '../components/ConfigPanel.vue'
import TaskAlertsPanel from '../components/TaskAlertsPanel.vue'
import ToastMessage from '../components/ToastMessage.vue'
import TopBar from '../components/TopBar.vue'
import VideoPreview from '../components/VideoPreview.vue'
import { useFallWs } from '../composables/useFallWs'
import { useToast } from '../composables/useToast'
import {
  DEFAULT_CLIENT_ID,
  DEFAULT_ENCRYPT_HEADER_NAME,
  DEFAULT_GATEWAY_BASE_URL,
  DEFAULT_RSA_PRIVATE_KEY,
  DEFAULT_RSA_PUBLIC_KEY,
  resolveAuthConfig,
} from '../utils/auth'
import { authStore } from '../store/auth.js'
import { formatTime } from '../utils/time'

const router = useRouter()

const browserAuth = resolveAuthConfig()
const config = reactive({
  gatewayBaseUrl: localStorage.getItem('gatewayBaseUrl') || DEFAULT_GATEWAY_BASE_URL,
  fallBaseUrl: localStorage.getItem('fallBaseUrl') || 'http://127.0.0.1:9500',
  videoBaseUrl: localStorage.getItem('videoBaseUrl') || 'http://127.0.0.1:9500',
  projectId: localStorage.getItem('projectId') || '001',
  clientid: localStorage.getItem('fallConsoleClientid') || browserAuth.clientid || DEFAULT_CLIENT_ID,
  token: authStore.token,
  videoReloadKey: '',
  loginEncrypted: readBool('fallConsoleLoginEncrypted', false),
  encryptHeaderName: DEFAULT_ENCRYPT_HEADER_NAME,
  rsaPublicKey: DEFAULT_RSA_PUBLIC_KEY,
  rsaPrivateKey: DEFAULT_RSA_PRIVATE_KEY,
})

const fallApi = createFallApi(config)
const { toast, showToast } = useToast()
const cameras = ref([])
const alerts = ref([])
const task = ref(null)
const selectedCameraId = ref('')
const lastDetection = ref({ image_width: 0, image_height: 0, detections: [] })
const overlay = reactive({ ready: false, viewBox: '0 0 1 1' })
const videoState = reactive({ failed: false, message: '', probeOk: null, probeMessage: '' })
const loading = reactive({
  login: false,
  captcha: false,
  createCamera: false,
  updateCamera: false,
  probeVideo: false,
})
const taskDraft = reactive({ detection_fps: 2, conf_threshold: 0.25 })
const newCamera = reactive({ name: '', source_url: '', suffix: '' })
const cameraDraft = reactive({ name: '', source_url: '', suffix: '', enabled: true })
const previewDraft = reactive({
  source_url: localStorage.getItem('previewSourceUrl') || '',
  suffix: localStorage.getItem('previewSuffix') || '',
})

const isLoggedIn = computed(() => authStore.isLoggedIn)
const selectedCamera = computed(() => cameras.value.find((item) => item.camera_id === selectedCameraId.value))
const manualPreviewCamera = computed(() => {
  if (isLoggedIn.value || !previewDraft.source_url) return null
  return {
    name: '视频预览',
    source_url: normalizeStreamUrl(previewDraft.source_url),
    suffix: previewDraft.suffix || null,
  }
})
const previewCamera = computed(() => selectedCamera.value || manualPreviewCamera.value)
const mjpegUrl = computed(() => buildMjpegUrl(config, previewCamera.value))
const visibleBoxes = computed(() => {
  if (!task.value?.show_boxes) return []
  return (lastDetection.value.detections || []).map((item) => {
    const [x1, y1, x2, y2] = item.bbox || [0, 0, 0, 0]
    return { x: x1, y: y1, width: Math.max(0, x2 - x1), height: Math.max(0, y2 - y1) }
  })
})
const frameInfo = computed(() => {
  const width = lastDetection.value.image_width
  const height = lastDetection.value.image_height
  return width && height ? `${width} x ${height}` : '等待数据'
})
const latestAlertTime = computed(() => (
  alerts.value[0]?.created_at ? formatTime(alerts.value[0].created_at) : '无'
))
const taskStatusText = computed(() => task.value?.status || '未加载')
const taskStatusClass = computed(() => (
  task.value?.status === 'running' ? 'ok' : task.value?.status === 'error' ? 'danger' : 'muted'
))

const {
  wsStateText,
  wsStateClass,
  connect: connectFallWs,
  disconnect: disconnectWs,
} = useFallWs(config, {
  onMessage: handleWsMessage,
  onError: (message) => showToast(message, 'danger'),
})

watch(config, () => {
  localStorage.setItem('gatewayBaseUrl', config.gatewayBaseUrl)
  localStorage.setItem('fallBaseUrl', config.fallBaseUrl)
  localStorage.setItem('videoBaseUrl', config.videoBaseUrl)
  localStorage.setItem('projectId', config.projectId)
  localStorage.setItem('fallConsoleClientid', config.clientid)
  localStorage.setItem('fallConsoleLoginEncrypted', String(config.loginEncrypted))
}, { deep: true })

watch(previewDraft, () => {
  localStorage.setItem('previewSourceUrl', previewDraft.source_url)
  localStorage.setItem('previewSuffix', previewDraft.suffix)
  resetVideoState()
}, { deep: true })

watch(selectedCameraId, async () => {
  disconnectWs()
  lastDetection.value = { image_width: 0, image_height: 0, detections: [] }
  overlay.ready = false
  resetVideoState()
  syncCameraDraft()
  await Promise.all([loadTask(), loadAlerts()])
  await nextTick()
  syncOverlaySize()
})

watch(selectedCamera, syncCameraDraft)

// 检测参数变化时自动持久化（防抖）
let paramsTimer = null
watch([() => taskDraft.detection_fps, () => taskDraft.conf_threshold], ([fps, conf]) => {
  if (!selectedCameraId.value) return
  if (task.value?.detection_fps === fps && task.value?.conf_threshold === conf) return
  clearTimeout(paramsTimer)
  paramsTimer = setTimeout(() => {
    fallApi.updateTaskParams(selectedCameraId.value, {
      detection_fps: fps,
      conf_threshold: conf,
    }).then((updated) => {
      if (task.value) Object.assign(task.value, updated)
    }).catch(() => {})
  }, 500)
})

onMounted(() => {
  clearLegacyCryptoStorage()
  loadCameras()
  window.addEventListener('resize', syncOverlaySize)
})

onBeforeUnmount(() => {
  disconnectWs()
  window.removeEventListener('resize', syncOverlaySize)
})

async function loadCameras() {
  if (!ensureLoggedIn()) return
  try {
    cameras.value = await fallApi.listCameras()
    if (!selectedCameraId.value && cameras.value.length) selectedCameraId.value = cameras.value[0].camera_id
  } catch (error) {
    showToast(error.message, 'danger')
  }
}

async function createCamera() {
  if (!ensureLoggedIn()) return
  loading.createCamera = true
  try {
    const camera = await fallApi.createCamera({
      name: newCamera.name,
      source_url: normalizeStreamUrl(newCamera.source_url),
      suffix: newCamera.suffix || null,
      enabled: true,
    })
    cameras.value.unshift(camera)
    selectedCameraId.value = camera.camera_id
    Object.assign(newCamera, { name: '', source_url: '', suffix: '' })
    showToast('摄像头已新增', 'success')
  } catch (error) {
    showToast(error.message, 'danger')
  } finally {
    loading.createCamera = false
  }
}

async function updateCamera() {
  if (!selectedCameraId.value) return
  if (!ensureLoggedIn()) return
  loading.updateCamera = true
  try {
    const updated = await fallApi.updateCamera(selectedCameraId.value, {
      name: cameraDraft.name,
      source_url: normalizeStreamUrl(cameraDraft.source_url),
      suffix: cameraDraft.suffix || null,
      enabled: cameraDraft.enabled,
    })
    const index = cameras.value.findIndex((item) => item.camera_id === updated.camera_id)
    if (index >= 0) cameras.value.splice(index, 1, updated)
    await loadTask()
    showToast('摄像头已保存', 'success')
  } catch (error) {
    showToast(error.message, 'danger')
    syncCameraDraft()
  } finally {
    loading.updateCamera = false
  }
}

function selectCamera(cameraId) {
  selectedCameraId.value = cameraId
  resetVideoState()
}

async function loadTask() {
  if (!selectedCameraId.value) return
  if (!ensureLoggedIn()) return
  try {
    task.value = await fallApi.getTask(selectedCameraId.value)
    taskDraft.detection_fps = task.value.detection_fps
    taskDraft.conf_threshold = task.value.conf_threshold
  } catch (error) {
    showToast(error.message, 'danger')
  }
}

async function toggleDetection(event) {
  if (!selectedCameraId.value) return
  if (!ensureLoggedIn()) {
    event.target.checked = !event.target.checked
    return
  }
  try {
    task.value = await fallApi.setDetection(selectedCameraId.value, {
      enabled: event.target.checked,
      detection_fps: taskDraft.detection_fps,
      conf_threshold: taskDraft.conf_threshold,
    })
    if (event.target.checked) connectWs()
    showToast('检测开关已更新', 'success')
  } catch (error) {
    event.target.checked = !event.target.checked
    showToast(error.message, 'danger')
  }
}

async function toggleBoxes(event) {
  if (!selectedCameraId.value) return
  if (!ensureLoggedIn()) {
    event.target.checked = !event.target.checked
    return
  }
  try {
    task.value = await fallApi.setBoxes(selectedCameraId.value, event.target.checked)
    if (event.target.checked) connectWs()
    showToast('框选显示已更新', 'success')
  } catch (error) {
    event.target.checked = !event.target.checked
    showToast(error.message, 'danger')
  }
}

async function loadAlerts() {
  if (!selectedCameraId.value) return
  if (!ensureLoggedIn()) return
  try {
    alerts.value = await fallApi.listAlerts(selectedCameraId.value)
  } catch (error) {
    showToast(error.message, 'danger')
  }
}

async function markAlertRead(alert) {
  if (!ensureLoggedIn()) return
  try {
    const updated = await fallApi.markAlertRead(alert.alert_id)
    Object.assign(alert, updated)
  } catch (error) {
    showToast(error.message, 'danger')
  }
}

async function deleteAlert(alert) {
  if (!ensureLoggedIn()) return
  try {
    await fallApi.deleteAlert(alert.alert_id)
    const index = alerts.value.indexOf(alert)
    if (index >= 0) alerts.value.splice(index, 1)
    showToast('告警已删除', 'success')
  } catch (error) {
    showToast(error.message, 'danger')
  }
}

function connectWs() {
  if (!ensureLoggedIn()) return
  connectFallWs(selectedCameraId.value)
}

function handleWsMessage(message) {
  if (!message || typeof message !== 'object') return
  if (message.type === 'bbox_update') {
    lastDetection.value = message
    overlay.viewBox = `0 0 ${message.image_width || 1} ${message.image_height || 1}`
    overlay.ready = true
  }
  if (message.type === 'fall_alert') {
    alerts.value.unshift({ ...message, is_read: false, created_at: message.created_at || new Date().toISOString() })
    showToast('检测到摔倒告警', 'danger')
  }
  if (message.type === 'task_status') {
    if (task.value) task.value.status = message.status
  }
  if (message.type === 'error') {
    if (task.value) task.value.status = 'error'
    showToast(message.message || '检测任务异常', 'danger')
  }
}

function syncCameraDraft() {
  if (!selectedCamera.value) {
    Object.assign(cameraDraft, { name: '', source_url: '', suffix: '', enabled: true })
    return
  }
  Object.assign(cameraDraft, {
    name: selectedCamera.value.name,
    source_url: normalizeStreamUrl(selectedCamera.value.source_url),
    suffix: selectedCamera.value.suffix || '',
    enabled: selectedCamera.value.enabled,
  })
}

function refreshAll() {
  loadCameras()
  loadTask()
  loadAlerts()
}

function syncOverlaySize() {
  videoState.failed = false
  videoState.message = ''
  const width = lastDetection.value.image_width
  const height = lastDetection.value.image_height
  if (width && height) {
    overlay.viewBox = `0 0 ${width} ${height}`
    overlay.ready = true
  }
}

function handleVideoError() {
  videoState.failed = true
  videoState.message = '视频加载失败'
  showToast('视频加载失败，请点击“探测视频”查看 OpenCV 是否能打开该地址', 'danger')
}

function reloadVideo() {
  videoState.failed = false
  videoState.message = ''
  config.videoReloadKey = String(Date.now())
}

async function probeVideo() {
  if (!previewCamera.value) return
  loading.probeVideo = true
  try {
    const result = await probeVideoStream(config, previewCamera.value)
    videoState.probeOk = result.opened
    videoState.probeMessage = `${result.message}；OpenCV URL: ${result.opencv_url}`
    showToast(result.message, result.opened ? 'success' : 'danger')
  } catch (error) {
    videoState.probeOk = false
    videoState.probeMessage = error.message
    showToast(error.message, 'danger')
  } finally {
    loading.probeVideo = false
  }
}

function resetVideoState() {
  videoState.failed = false
  videoState.message = ''
  videoState.probeOk = null
  videoState.probeMessage = ''
}

function logout() {
  authStore.clearToken()
  config.token = ''
  disconnectWs()
  cameras.value = []
  alerts.value = []
  task.value = null
  selectedCameraId.value = ''
  lastDetection.value = { image_width: 0, image_height: 0, detections: [] }
  overlay.ready = false
  router.replace({ name: 'Login' })
}

function ensureLoggedIn() {
  if (config.token) return true
  showToast('请先登录系统', 'danger')
  return false
}

function readBool(key, fallback) {
  const value = localStorage.getItem(key)
  if (value == null) return fallback
  return value === 'true'
}

function clearLegacyCryptoStorage() {
  localStorage.removeItem('fallConsoleEncryptHeaderName')
  localStorage.removeItem('fallConsoleRsaPublicKey')
  localStorage.removeItem('fallConsoleRsaPrivateKey')
}
</script>

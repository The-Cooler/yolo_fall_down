import { computed, ref } from 'vue'
import { trimSlash } from '../api/fall'
import { normalizeBearerToken } from '../utils/auth'

export function useFallWs(config, handlers) {
  const ws = ref(null)
  const wsState = ref('idle')

  const wsStateText = computed(() => ({
    idle: '未连接',
    connecting: '连接中',
    open: '已连接',
    closed: '已断开',
  }[wsState.value]))

  const wsStateClass = computed(() => (
    wsState.value === 'open' ? 'ok' : wsState.value === 'connecting' ? 'warning' : 'muted'
  ))

  function connect(cameraId) {
    if (!cameraId || !config.token) {
      handlers.onError?.('需要选择摄像头并填写 token')
      return
    }

    disconnect()
    wsState.value = 'connecting'

    const base = trimSlash(config.fallBaseUrl).replace(/^http/, 'ws')
    const url = new URL(`${base}/ws/fall`)
    url.searchParams.set('project_id', config.projectId)
    url.searchParams.set('camera_id', cameraId)
    url.searchParams.set('token', normalizeBearerToken(config.token).replace(/^Bearer\s+/i, ''))
    url.searchParams.set('clientid', config.clientid)

    ws.value = new WebSocket(url)
    ws.value.onopen = () => {
      wsState.value = 'open'
    }
    ws.value.onclose = () => {
      wsState.value = 'closed'
    }
    ws.value.onerror = () => {
      wsState.value = 'closed'
      handlers.onError?.('WebSocket 连接失败')
    }
    ws.value.onmessage = (event) => {
      try {
        handlers.onMessage?.(JSON.parse(event.data))
      } catch {
        handlers.onError?.('WebSocket 消息格式异常')
      }
    }
  }

  function disconnect() {
    if (ws.value) ws.value.close()
    ws.value = null
  }

  return {
    wsState,
    wsStateText,
    wsStateClass,
    connect,
    disconnect,
  }
}

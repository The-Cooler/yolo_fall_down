<template>
  <section class="panel video-panel" aria-label="视频预览">
    <div class="panel-header video-header">
      <div>
        <p class="section-kicker">Live View</p>
        <h2>{{ activeCamera?.name || '视频预览' }}</h2>
      </div>
      <div class="video-actions">
        <span :class="['status-pill', taskStatusClass]">
          <span class="status-dot"></span>
          {{ taskStatusText }}
        </span>
        <button class="secondary-button" type="button" :disabled="!selectedCamera" @click="$emit('connect-ws')">
          <Radio :size="17" />
          连接推送
        </button>
        <button class="secondary-button" type="button" :disabled="!activeCamera || loading.probeVideo" @click="$emit('probe-video')">
          <SearchCheck :size="17" />
          探测视频
        </button>
      </div>
    </div>

    <div v-if="!selectedCamera" class="preview-form">
      <label>
        <span>视频源 URL</span>
        <input v-model.trim="previewDraft.source_url" placeholder="rtsp://localhost:8554/live/streamkey" />
      </label>
      <label>
        <span>后缀</span>
        <input v-model.trim="previewDraft.suffix" placeholder=".flv / .m3u8 / 留空" />
      </label>
    </div>

    <div class="video-frame">
      <img
        v-if="activeCamera"
        class="video-stream"
        :src="mjpegUrl"
        alt="实时视频预览"
        @load="$emit('sync-overlay-size')"
        @error="$emit('video-error')"
      />
      <div v-else class="video-placeholder">
        <MonitorPlay :size="44" />
        <span>选择摄像头后查看实时画面</span>
      </div>
      <div v-if="activeCamera && videoState.failed" class="video-status-overlay">
        <MonitorX :size="18" />
        <span>{{ videoState.message || '视频加载失败' }}</span>
        <button type="button" @click="$emit('reload-video')">
          <RefreshCw :size="15" />
          重载
        </button>
      </div>
      <svg v-if="selectedCamera && overlay.ready" class="bbox-layer" :viewBox="overlay.viewBox" aria-hidden="true">
        <rect
          v-for="(box, index) in visibleBoxes"
          :key="index"
          class="bbox"
          :x="box.x"
          :y="box.y"
          :width="box.width"
          :height="box.height"
          rx="2"
        />
      </svg>
    </div>

    <div v-if="activeCamera" class="stream-debug">
      <span>MJPEG</span>
      <code>{{ mjpegUrl }}</code>
    </div>
    <div v-if="videoState.probeMessage" :class="['stream-debug', videoState.probeOk ? 'ok' : 'danger']">
      <span>Probe</span>
      <code>{{ videoState.probeMessage }}</code>
    </div>

    <div class="telemetry-grid">
      <div>
        <span>画面尺寸</span>
        <strong>{{ frameInfo }}</strong>
      </div>
      <div>
        <span>检测框</span>
        <strong>{{ visibleBoxes.length }}</strong>
      </div>
      <div>
        <span>最新告警</span>
        <strong>{{ latestAlertTime }}</strong>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { MonitorPlay, MonitorX, Radio, RefreshCw, SearchCheck } from 'lucide-vue-next'

const props = defineProps({
  selectedCamera: { type: Object, default: null },
  manualCamera: { type: Object, default: null },
  previewDraft: { type: Object, required: true },
  mjpegUrl: { type: String, required: true },
  overlay: { type: Object, required: true },
  visibleBoxes: { type: Array, required: true },
  frameInfo: { type: String, required: true },
  latestAlertTime: { type: String, required: true },
  taskStatusText: { type: String, required: true },
  taskStatusClass: { type: String, required: true },
  videoState: { type: Object, required: true },
  loading: { type: Object, required: true },
})

defineEmits(['connect-ws', 'sync-overlay-size', 'video-error', 'reload-video', 'probe-video'])

const activeCamera = computed(() => props.selectedCamera || props.manualCamera)
</script>

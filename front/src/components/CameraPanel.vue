<template>
  <aside class="panel side-panel" aria-label="摄像头列表">
    <div class="panel-header">
      <div>
        <p class="section-kicker">Cameras</p>
        <h2>摄像头</h2>
      </div>
      <button class="icon-button" type="button" title="刷新摄像头" aria-label="刷新摄像头" @click="$emit('load-cameras')">
        <RotateCw :size="17" />
      </button>
    </div>

    <form class="camera-form" @submit.prevent="$emit('create-camera')">
      <label>
        <span>名称</span>
        <input v-model.trim="newCamera.name" placeholder="走廊摄像头" required />
      </label>
      <label>
        <span>视频源 URL</span>
        <input v-model.trim="newCamera.source_url" placeholder="rtsp:// 或 http://..." required />
      </label>
      <label>
        <span>后缀</span>
        <input v-model.trim="newCamera.suffix" placeholder=".flv / .m3u8 / 留空" />
      </label>
      <button class="primary-button" type="submit" :disabled="loading.createCamera">
        <Plus :size="18" />
        新增摄像头
      </button>
    </form>

    <div class="camera-list">
      <button
        v-for="camera in cameras"
        :key="camera.camera_id"
        :class="['camera-item', { active: camera.camera_id === selectedCameraId }]"
        type="button"
        @click="$emit('select-camera', camera.camera_id)"
      >
        <span class="camera-icon"><Video :size="18" /></span>
        <span>
          <strong>{{ camera.name }}</strong>
          <small>{{ camera.enabled ? '已启用' : '已禁用' }}</small>
        </span>
      </button>
      <div v-if="!cameras.length" class="empty-state">暂无摄像头</div>
    </div>

    <form v-if="selectedCamera" class="camera-form camera-edit" @submit.prevent="$emit('update-camera')">
      <div class="form-title">
        <p class="section-kicker">Selected</p>
        <h3>当前摄像头</h3>
      </div>
      <label>
        <span>名称</span>
        <input v-model.trim="cameraDraft.name" required />
      </label>
      <label>
        <span>视频源 URL</span>
        <input v-model.trim="cameraDraft.source_url" required />
      </label>
      <label>
        <span>后缀</span>
        <input v-model.trim="cameraDraft.suffix" placeholder=".flv / .m3u8 / 留空" />
      </label>
      <label class="switch-row compact">
        <span>
          <strong>摄像头启用</strong>
          <small>关闭会停止检测，不影响保存配置</small>
        </span>
        <input type="checkbox" v-model="cameraDraft.enabled" />
      </label>
      <button class="secondary-button" type="submit" :disabled="loading.updateCamera">
        <Save :size="17" />
        保存摄像头
      </button>
    </form>
  </aside>
</template>

<script setup>
import { Plus, RotateCw, Save, Video } from 'lucide-vue-next'

defineProps({
  cameras: { type: Array, required: true },
  selectedCameraId: { type: String, required: true },
  selectedCamera: { type: Object, default: null },
  newCamera: { type: Object, required: true },
  cameraDraft: { type: Object, required: true },
  loading: { type: Object, required: true },
})

defineEmits(['load-cameras', 'create-camera', 'select-camera', 'update-camera'])
</script>

<template>
  <aside class="panel control-panel" aria-label="任务控制与告警">
    <div class="panel-header">
      <div>
        <p class="section-kicker">Controls</p>
        <h2>检测任务</h2>
      </div>
    </div>

    <div class="switch-stack">
      <label class="switch-row">
        <span>
          <strong>摔倒检测</strong>
          <small>开启后后台抽帧并调用 YOLO</small>
        </span>
        <input type="checkbox" :checked="task?.detection_enabled" :disabled="!selectedCamera" @change="$emit('toggle-detection', $event)" />
      </label>
      <label class="switch-row">
        <span>
          <strong>显示人物框</strong>
          <small>开启后前端叠加检测框</small>
        </span>
        <input type="checkbox" :checked="task?.show_boxes" :disabled="!selectedCamera" @change="$emit('toggle-boxes', $event)" />
      </label>
    </div>

    <div class="task-fields">
      <label>
        <span>检测频率 FPS</span>
        <input v-model.number="taskDraft.detection_fps" min="0.1" max="30" step="0.1" type="number" />
      </label>
      <label>
        <span>置信度</span>
        <input v-model.number="taskDraft.conf_threshold" min="0.01" max="1" step="0.01" type="number" />
      </label>
    </div>

    <div class="alerts-header">
      <div>
        <p class="section-kicker">Alerts</p>
        <h2>告警</h2>
      </div>
      <button class="icon-button" type="button" title="刷新告警" aria-label="刷新告警" @click="$emit('load-alerts')">
        <BellRing :size="17" />
      </button>
    </div>

    <div class="alert-list">
      <article v-for="alert in alerts" :key="alert.alert_id" :class="['alert-item', { unread: !alert.is_read }]">
        <div>
          <strong>{{ alert.camera_name || alert.camera_id }}</strong>
          <span>{{ formatTime(alert.created_at) }}</span>
        </div>
        <p>检测到 {{ alert.fall_count }} 个摔倒目标</p>
        <button type="button" @click="$emit('mark-alert-read', alert)" :disabled="alert.is_read">
          {{ alert.is_read ? '已读' : '标记已读' }}
        </button>
        <button type="button" class="danger-button" @click="$emit('delete-alert', alert)">删除</button>
      </article>
      <div v-if="!alerts.length" class="empty-state">暂无告警</div>
    </div>
  </aside>
</template>

<script setup>
import { BellRing } from 'lucide-vue-next'
import { formatTime } from '../utils/time'

defineProps({
  task: { type: Object, default: null },
  selectedCamera: { type: Object, default: null },
  taskDraft: { type: Object, required: true },
  alerts: { type: Array, required: true },
})

defineEmits(['toggle-detection', 'toggle-boxes', 'load-alerts', 'mark-alert-read', 'delete-alert'])
</script>

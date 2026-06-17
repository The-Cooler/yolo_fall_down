<template>
  <details class="config-panel" aria-label="服务连接配置">
    <summary>连接配置</summary>
    <div class="config-grid">
      <label>
        <span>Fall 服务</span>
        <input v-model.trim="config.fallBaseUrl" />
      </label>
      <label>
        <span>Video 服务</span>
        <input v-model.trim="config.videoBaseUrl" />
      </label>
      <label>
        <span>Project ID</span>
        <input v-model.trim="config.projectId" />
      </label>
      <label>
        <span>网关 API</span>
        <input v-model.trim="config.gatewayBaseUrl" />
      </label>
    </div>
  </details>
</template>

<script setup>
defineProps({
  config: { type: Object, required: true },
})
</script>

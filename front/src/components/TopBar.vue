<template>
  <header class="topbar">
    <div>
      <p class="eyebrow">Fall Detection Console</p>
      <h1>摔倒检测工作台</h1>
    </div>
    <div class="topbar-actions">
      <span :class="['status-pill', wsStateClass]">
        <span class="status-dot"></span>
        {{ wsStateText }}
      </span>
      <span :class="['status-pill', isLoggedIn ? 'ok' : 'warning']">
        <span class="status-dot"></span>
        {{ isLoggedIn ? '已登录' : '未登录' }}
      </span>
      <button class="icon-button" type="button" title="刷新" aria-label="刷新" @click="$emit('refresh')">
        <RefreshCw :size="18" />
      </button>
      <button v-if="isLoggedIn" class="secondary-button" type="button" @click="$emit('logout')">
        <LogOut :size="17" />
        退出
      </button>
    </div>
  </header>
</template>

<script setup>
import { LogOut, RefreshCw } from 'lucide-vue-next'

defineProps({
  wsStateText: { type: String, required: true },
  wsStateClass: { type: String, required: true },
  isLoggedIn: { type: Boolean, required: true },
})

defineEmits(['refresh', 'logout'])
</script>

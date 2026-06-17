<template>
  <section class="panel login-panel auth-panel" aria-label="登录">
    <div class="panel-header">
      <div>
        <p class="section-kicker">Account</p>
        <h2>登录系统</h2>
      </div>
      <span :class="['status-pill', isLoggedIn ? 'ok' : 'warning']">
        <span class="status-dot"></span>
        {{ isLoggedIn ? '已登录' : '未登录' }}
      </span>
    </div>

    <form class="login-form" @submit.prevent="$emit('login')">
      <label>
        <span>网关 API</span>
        <input v-model.trim="config.gatewayBaseUrl" placeholder="http://ljy.wbbb2333.asia/prod-api" />
      </label>
      <div class="login-row">
        <label>
          <span>租户 ID</span>
          <input v-model.trim="loginForm.tenantId" autocomplete="organization" />
        </label>
        <label>
          <span>Client ID</span>
          <input v-model.trim="config.clientid" autocomplete="off" />
        </label>
      </div>
      <div class="login-row">
        <label>
          <span>用户名</span>
          <input v-model.trim="loginForm.username" autocomplete="username" required />
        </label>
        <label>
          <span>密码</span>
          <input v-model="loginForm.password" type="password" autocomplete="current-password" required />
        </label>
      </div>

      <div v-if="captcha.enabled" class="captcha-row">
        <label>
          <span>验证码</span>
          <input v-model.trim="loginForm.code" autocomplete="off" :required="captcha.enabled" />
        </label>
        <button class="captcha-image" type="button" title="刷新验证码" @click="$emit('refresh-captcha')">
          <img v-if="captcha.image" :src="captcha.image" alt="验证码" />
          <span v-else>刷新验证码</span>
        </button>
      </div>

      <div class="login-actions">
        <button class="primary-button" type="submit" :disabled="loading.login">
          <LogIn :size="17" />
          {{ loading.login ? '登录中' : '登录' }}
        </button>
        <button class="secondary-button" type="button" :disabled="loading.captcha" @click="$emit('refresh-captcha')">
          <RefreshCw :size="17" />
          验证码
        </button>
        <button class="secondary-button" type="button" :disabled="!isLoggedIn" @click="$emit('logout')">
          <LogOut :size="17" />
          退出
        </button>
      </div>
    </form>
  </section>
</template>

<script setup>
import { LogIn, LogOut, RefreshCw } from 'lucide-vue-next'

defineProps({
  config: { type: Object, required: true },
  loginForm: { type: Object, required: true },
  captcha: { type: Object, required: true },
  loading: { type: Object, required: true },
  isLoggedIn: { type: Boolean, required: true },
})

defineEmits(['login', 'logout', 'refresh-captcha'])
</script>

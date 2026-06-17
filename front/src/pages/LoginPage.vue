<template>
  <main class="app-shell">
    <header class="topbar">
      <div>
        <p class="eyebrow">Fall Detection Console</p>
        <h1>摔倒检测工作台</h1>
      </div>
    </header>

    <section class="panel auth-panel login-panel" aria-label="登录">
      <div class="panel-header">
        <div>
          <p class="section-kicker">Account</p>
          <h2>{{ isRegistering ? '创建管理员账号' : '登录系统' }}</h2>
        </div>
        <span :class="['status-pill', 'warning']">
          <span class="status-dot"></span>
          未登录
        </span>
      </div>

      <!-- Registration mode: shown when no users exist -->
      <form v-if="isRegistering" class="login-form" @submit.prevent="doRegister">
        <p style="color: var(--muted); margin: 0 0 8px;">
          系统中尚无用户，请创建第一个管理员账号。
        </p>
        <label>
          <span>用户名</span>
          <input v-model.trim="registerForm.username" autocomplete="username" required />
        </label>
        <label>
          <span>密码</span>
          <input v-model="registerForm.password" type="password" autocomplete="new-password" required />
        </label>
        <label>
          <span>确认密码</span>
          <input v-model.trim="registerForm.confirmPassword" type="password" autocomplete="new-password" required />
        </label>
        <div class="login-actions">
          <button class="primary-button" type="submit" :disabled="loading.register">
            <UserPlus :size="17" />
            {{ loading.register ? '创建中' : '创建账号' }}
          </button>
        </div>
      </form>

      <!-- Login mode -->
      <form v-else class="login-form" @submit.prevent="doLogin">
        <label>
          <span>用户名</span>
          <input v-model.trim="loginForm.username" autocomplete="username" required />
        </label>
        <label>
          <span>密码</span>
          <input v-model="loginForm.password" type="password" autocomplete="current-password" required />
        </label>
        <div class="login-actions">
          <button class="primary-button" type="submit" :disabled="loading.login">
            <LogIn :size="17" />
            {{ loading.login ? '登录中' : '登录' }}
          </button>
        </div>
      </form>

      <p v-if="errorMessage" style="color: var(--danger); margin: 8px 0 0;">{{ errorMessage }}</p>
    </section>
  </main>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { LogIn, UserPlus } from 'lucide-vue-next'
import { authStore } from '../store/auth.js'
import { trimSlash } from '../api/fall.js'

const router = useRouter()

const DEFAULT_BASE = 'http://127.0.0.1:9500'

const gatewayBaseUrl = localStorage.getItem('gatewayBaseUrl') || DEFAULT_BASE
const clientId = localStorage.getItem('fallConsoleClientid') || 'e5cd7e4891bf95d1d19206ce24a7b32e'

const loginForm = reactive({
  username: localStorage.getItem('fallConsoleUsername') || '',
  password: '',
})

const registerForm = reactive({
  username: '',
  password: '',
  confirmPassword: '',
})

const loading = reactive({ login: false, register: false, check: false })
const isRegistering = ref(false)
const errorMessage = ref('')

onMounted(async () => {
  loading.check = true
  try {
    const resp = await fetch(`${trimSlash(gatewayBaseUrl)}/auth/code`, {
      headers: { clientid: clientId },
    })
    const payload = await resp.json()
    if (payload.registerMode) {
      isRegistering.value = true
    }
  } catch {
    // 网络错误，保持登录模式
  } finally {
    loading.check = false
  }
})

async function doLogin() {
  errorMessage.value = ''
  loading.login = true
  try {
    const payload = {
      tenantId: '000000',
      username: loginForm.username,
      password: loginForm.password,
      grantType: 'password',
    }
    const resp = await fetch(`${trimSlash(gatewayBaseUrl)}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        clientid: clientId,
      },
      body: JSON.stringify(payload),
    })
    const data = await resp.json()
    if (data.code !== 200) {
      errorMessage.value = data.msg || '登录失败'
      return
    }
    const token = data.token || data.access_token || ''
    if (!token) {
      errorMessage.value = '登录响应中没有 token'
      return
    }
    authStore.setToken(token)
    localStorage.setItem('fallConsoleUsername', loginForm.username)
    loginForm.password = ''
    router.replace({ name: 'Console' })
  } catch (err) {
    errorMessage.value = err.message || '登录失败'
  } finally {
    loading.login = false
  }
}

async function doRegister() {
  errorMessage.value = ''
  if (!registerForm.username) {
    errorMessage.value = '请输入用户名'
    return
  }
  if (!registerForm.password) {
    errorMessage.value = '请输入密码'
    return
  }
  if (registerForm.password !== registerForm.confirmPassword) {
    errorMessage.value = '两次密码不一致'
    return
  }
  loading.register = true
  try {
    const payload = {
      tenantId: '000000',
      username: registerForm.username,
      password: registerForm.password,
      grantType: 'password',
    }
    const resp = await fetch(`${trimSlash(gatewayBaseUrl)}/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        clientid: clientId,
      },
      body: JSON.stringify(payload),
    })
    const data = await resp.json()
    if (data.code !== 200) {
      errorMessage.value = data.msg || '注册失败'
      return
    }
    const token = data.token || data.access_token || ''
    authStore.setToken(token)
    localStorage.setItem('fallConsoleUsername', registerForm.username)
    router.replace({ name: 'Console' })
  } catch (err) {
    errorMessage.value = err.message || '注册失败'
  } finally {
    loading.register = false
  }
}
</script>

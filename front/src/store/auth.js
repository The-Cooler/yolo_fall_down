import { reactive } from 'vue'

const TOKEN_KEY = 'fallConsoleToken'

export const authStore = reactive({
  token: localStorage.getItem(TOKEN_KEY) || '',

  setToken(token) {
    this.token = token
    localStorage.setItem(TOKEN_KEY, token)
  },

  clearToken() {
    this.token = ''
    localStorage.removeItem(TOKEN_KEY)
  },

  get isLoggedIn() {
    return Boolean(this.token)
  },
})

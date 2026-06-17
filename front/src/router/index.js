import { createRouter, createWebHashHistory } from 'vue-router'
import { authStore } from '../store/auth.js'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../pages/LoginPage.vue'),
  },
  {
    path: '/',
    name: 'Console',
    component: () => import('../pages/FallConsole.vue'),
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

router.beforeEach((to) => {
  if (to.name !== 'Login' && !authStore.isLoggedIn) {
    return { name: 'Login' }
  }
})

export default router

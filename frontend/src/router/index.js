import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../stores/user'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/Home.vue'),
    meta: { title: '首页' }
  },
  {
    path: '/search',
    name: 'Search',
    component: () => import('../views/Search.vue'),
    meta: { title: '论文搜索', requiresAuth: true }
  },
  {
    path: '/ai-chat',
    name: 'AiChat',
    component: () => import('../views/AiChat.vue'),
    meta: { title: 'AI助手', requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  
  if (to.meta.requiresAuth && !userStore.isLoggedIn) {
    // 需要登录但未登录，重定向到首页
    next('/')
  } else {
    next()
  }
})

export default router

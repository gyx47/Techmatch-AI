import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../stores/user'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { title: '登录', requiresAuth: false }
  },
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue'),
    meta: { title: '仪表盘', requiresAuth: true }
  },
  {
    path: '/new-request',
    name: 'NewRequest',
    component: () => import('../views/NewRequest.vue'),
    meta: { title: '提交需求', requiresAuth: true }
  },
  {
    path: '/matches',
    name: 'MatchingResults',
    component: () => import('../views/MatchingResults.vue'),
    meta: { title: '匹配结果', requiresAuth: true }
  },
  {
    path: '/solution/:id',
    name: 'SolutionViewer',
    component: () => import('../views/SolutionViewer.vue'),
    meta: { title: '方案详情', requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  const isAuthed = userStore.isLoggedIn

  if (to.name === 'Login' && isAuthed) {
    const redirect = (to.query.redirect || '/').toString()
    return next(redirect)
  }

  if (to.meta.requiresAuth && !isAuthed) {
    return next({ name: 'Login', query: { redirect: to.fullPath } })
  }

  next()
})

export default router

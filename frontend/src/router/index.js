import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../stores/user'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/Home.vue'),
    meta: { title: '首页', requiresAuth: false }
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { title: '登录', requiresAuth: false }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/Register.vue'),
    meta: { title: '注册', requiresAuth: false }
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue'),
    meta: { title: '资源大厅', requiresAuth: true }
  },
  {
    path: '/publish',
    name: 'PublishCenter',
    component: () => import('../views/PublishCenter.vue'),
    meta: { title: '发布中心', requiresAuth: true }
  },
  {
    path: '/smart-match',
    name: 'SmartMatch',
    component: () => import('../views/SmartMatch.vue'),
    meta: { title: 'AI智能匹配', requiresAuth: true }
  },
  {
    path: '/new-request',
    name: 'NewRequest',
    component: () => import('../views/NewRequest.vue'),
    meta: { title: '提交新需求', requiresAuth: true }
  },
  {
    path: '/matches',
    name: 'MatchingResults',
    component: () => import('../views/MatchingResults.vue'),
    meta: { title: '匹配结果', requiresAuth: true }
  },
  {
    path: '/proposal/:id',
    name: 'MatchProposal',
    component: () => import('../views/MatchProposal.vue'),
    meta: { title: '合作方案详情', requiresAuth: true }
  },
        {
          path: '/history',
          redirect: '/profile'
        },
  {
    path: '/profile',
    name: 'UserProfile',
    component: () => import('../views/UserProfile.vue'),
    meta: { title: '个人中心', requiresAuth: true }
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

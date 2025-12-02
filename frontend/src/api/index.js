import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../stores/user'

// 创建axios实例
const api = axios.create({
  baseURL: '/api',
  timeout: 300000, // 5分钟超时（匹配服务需要较长时间）
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 添加认证token
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    if (error.response) {
      const { status, data } = error.response
      
      switch (status) {
        case 401:
          {
            // 当前用户凭证无效：统一登出并禁止继续使用功能
            const userStore = useUserStore()
            userStore.logout()

            ElMessage.error('登录已过期或凭证无效，请重新登录')

            // 跳转到登录页，并带上原始地址，方便重新登录后返回
            const currentPath = window.location.pathname + window.location.search
            const loginUrl = `/login?redirect=${encodeURIComponent(currentPath)}`
            if (window.location.pathname !== '/login') {
              window.location.href = loginUrl
            }
          }
          break
        case 403:
          ElMessage.error('权限不足')
          break
        case 404:
          ElMessage.error('请求的资源不存在')
          break
        case 500:
          ElMessage.error('服务器内部错误')
          break
        default:
          ElMessage.error(data?.detail || '请求失败')
      }
    } else if (error.request) {
      // 检查是否是超时错误
      if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
        ElMessage.error('请求超时，匹配服务可能需要较长时间，请稍后重试')
      } else {
        ElMessage.error('网络连接失败，请检查网络')
      }
    } else {
      ElMessage.error('请求配置错误')
    }
    
    return Promise.reject(error)
  }
)

export default api

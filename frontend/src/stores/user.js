import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api'

export const useUserStore = defineStore('user', () => {
  // 状态
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref(JSON.parse(localStorage.getItem('userInfo') || 'null'))

  // 计算属性
  const isLoggedIn = computed(() => !!token.value)

  // 登录
  const login = async (loginData) => {
    try {
      const response = await api.post('/auth/login', loginData)
      const { access_token } = response.data
      
      token.value = access_token
      localStorage.setItem('token', access_token)
      
      // 获取用户信息
      await getUserInfo()
      
      // 清除之前用户的所有匹配相关状态（新用户登录，不应该看到之前用户的状态）
      localStorage.removeItem('smartMatchTaskState')
      localStorage.removeItem('smartMatchState')
      // 清除所有用户的匹配历史（使用通配符方式清除所有 matchHistory_* 的key）
      const keysToRemove = []
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i)
        if (key && key.startsWith('matchHistory_')) {
          keysToRemove.push(key)
        }
      }
      keysToRemove.forEach(key => localStorage.removeItem(key))
      // 清除 sessionStorage 中的匹配结果
      sessionStorage.removeItem('matchingResults')
      
      return response.data
    } catch (error) {
      throw new Error(error.response?.data?.detail || '登录失败')
    }
  }

  // 注册
  const register = async (registerData) => {
    try {
      const response = await api.post('/auth/register', registerData)
      const { access_token } = response.data
      
      token.value = access_token
      localStorage.setItem('token', access_token)
      
      // 获取用户信息
      await getUserInfo()
      
      // 清除之前用户的所有匹配相关状态（新用户注册，不应该看到之前用户的状态）
      localStorage.removeItem('smartMatchTaskState')
      localStorage.removeItem('smartMatchState')
      // 清除所有用户的匹配历史（使用通配符方式清除所有 matchHistory_* 的key）
      const keysToRemove = []
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i)
        if (key && key.startsWith('matchHistory_')) {
          keysToRemove.push(key)
        }
      }
      keysToRemove.forEach(key => localStorage.removeItem(key))
      // 清除 sessionStorage 中的匹配结果
      sessionStorage.removeItem('matchingResults')
      
      return response.data
    } catch (error) {
      throw new Error(error.response?.data?.detail || '注册失败')
    }
  }

  // 获取用户信息
  const getUserInfo = async () => {
    try {
      const response = await api.get('/auth/me')
      userInfo.value = response.data
      localStorage.setItem('userInfo', JSON.stringify(response.data))
      return response.data
    } catch (error) {
      console.error('获取用户信息失败:', error)
      throw error
    }
  }

  // 退出登录
  const logout = () => {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('userInfo')
    // 清除所有匹配相关状态（用户退出登录，不应该保留任何状态）
    localStorage.removeItem('smartMatchTaskState')
    localStorage.removeItem('smartMatchState')
    // 清除所有用户的匹配历史（使用通配符方式清除所有 matchHistory_* 的key）
    const keysToRemove = []
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i)
      if (key && key.startsWith('matchHistory_')) {
        keysToRemove.push(key)
      }
    }
    keysToRemove.forEach(key => localStorage.removeItem(key))
    // 清除 sessionStorage 中的匹配结果
    sessionStorage.removeItem('matchingResults')
  }

  return {
    token,
    userInfo,
    isLoggedIn,
    login,
    register,
    getUserInfo,
    logout
  }
})

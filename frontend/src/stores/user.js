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

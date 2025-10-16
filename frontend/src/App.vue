<template>
  <div id="app">
    <el-container>
      <!-- 头部导航 -->
      <el-header class="header">
        <div class="header-content">
          <div class="logo">
            <el-icon><Search /></el-icon>
            <span>AI论文搜索系统</span>
          </div>
          <div class="nav-menu">
            <el-menu
              :default-active="$route.path"
              mode="horizontal"
              router
              class="nav-menu"
            >
              <el-menu-item index="/">首页</el-menu-item>
              <el-menu-item index="/search">论文搜索</el-menu-item>
              <el-menu-item index="/ai-chat">AI助手</el-menu-item>
            </el-menu>
          </div>
          <div class="user-actions">
            <el-button v-if="!userStore.isLoggedIn" @click="showLogin = true">
              登录
            </el-button>
            <el-button v-if="!userStore.isLoggedIn" @click="showRegister = true">
              注册
            </el-button>
            <el-dropdown v-else>
              <el-button>
                {{ userStore.userInfo?.username }}
                <el-icon><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="logout">退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </el-header>

      <!-- 主要内容区域 -->
      <el-main class="main-content">
        <router-view />
      </el-main>

      <!-- 登录对话框 -->
      <el-dialog v-model="showLogin" title="用户登录" width="400px">
        <el-form :model="loginForm" :rules="loginRules" ref="loginFormRef">
          <el-form-item label="用户名" prop="username">
            <el-input v-model="loginForm.username" placeholder="请输入用户名" />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input
              v-model="loginForm.password"
              type="password"
              placeholder="请输入密码"
              show-password
            />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="showLogin = false">取消</el-button>
          <el-button type="primary" @click="handleLogin">登录</el-button>
        </template>
      </el-dialog>

      <!-- 注册对话框 -->
      <el-dialog v-model="showRegister" title="用户注册" width="400px">
        <el-form :model="registerForm" :rules="registerRules" ref="registerFormRef">
          <el-form-item label="用户名" prop="username">
            <el-input v-model="registerForm.username" placeholder="请输入用户名" />
          </el-form-item>
          <el-form-item label="邮箱" prop="email">
            <el-input v-model="registerForm.email" placeholder="请输入邮箱" />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input
              v-model="registerForm.password"
              type="password"
              placeholder="请输入密码"
              show-password
            />
          </el-form-item>
          <el-form-item label="确认密码" prop="confirmPassword">
            <el-input
              v-model="registerForm.confirmPassword"
              type="password"
              placeholder="请再次输入密码"
              show-password
            />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="showRegister = false">取消</el-button>
          <el-button type="primary" @click="handleRegister">注册</el-button>
        </template>
      </el-dialog>
    </el-container>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from './stores/user'
import { ElMessage } from 'element-plus'
import { Search, ArrowDown } from '@element-plus/icons-vue'

const router = useRouter()
const userStore = useUserStore()

// 对话框状态
const showLogin = ref(false)
const showRegister = ref(false)

// 登录表单
const loginForm = reactive({
  username: '',
  password: ''
})

const loginRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

// 注册表单
const registerForm = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: ''
})

const registerRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== registerForm.password) {
          callback(new Error('两次输入密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

// 表单引用
const loginFormRef = ref()
const registerFormRef = ref()

// 处理登录
const handleLogin = async () => {
  if (!loginFormRef.value) return
  
  await loginFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        await userStore.login(loginForm)
        ElMessage.success('登录成功')
        showLogin.value = false
        loginForm.username = ''
        loginForm.password = ''
      } catch (error) {
        ElMessage.error(error.message || '登录失败')
      }
    }
  })
}

// 处理注册
const handleRegister = async () => {
  if (!registerFormRef.value) return
  
  await registerFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        await userStore.register(registerForm)
        ElMessage.success('注册成功')
        showRegister.value = false
        Object.assign(registerForm, {
          username: '',
          email: '',
          password: '',
          confirmPassword: ''
        })
      } catch (error) {
        ElMessage.error(error.message || '注册失败')
      }
    }
  })
}

// 退出登录
const logout = () => {
  userStore.logout()
  ElMessage.success('已退出登录')
}
</script>

<style scoped>
.header {
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0;
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.logo {
  display: flex;
  align-items: center;
  font-size: 20px;
  font-weight: bold;
  color: #409eff;
}

.logo .el-icon {
  margin-right: 8px;
  font-size: 24px;
}

.nav-menu {
  flex: 1;
  margin: 0 40px;
}

.nav-menu .el-menu-item {
  border-bottom: none;
}

.user-actions {
  display: flex;
  gap: 10px;
}

.main-content {
  min-height: calc(100vh - 60px);
  background: #f5f5f5;
}
</style>

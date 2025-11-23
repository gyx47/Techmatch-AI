<template>
  <div id="app">
    <el-container>
      <!-- 头部导航 -->
      <el-header class="header">
        <div class="header-content">
          <div class="logo">
            <el-icon><Search /></el-icon>
            <span>成果需求智能匹配平台</span>
          </div>
          <div class="nav-menu">
            <el-menu
              :default-active="$route.path"
              mode="horizontal"
              router
              class="nav-menu"
            >
              <el-menu-item index="/">首页</el-menu-item>
              <el-menu-item index="/dashboard">资源大厅</el-menu-item>
              <el-menu-item index="/publish">发布中心</el-menu-item>
              <el-menu-item index="/smart-match">智能匹配</el-menu-item>
              <el-menu-item index="/profile">个人中心</el-menu-item>
            </el-menu>
          </div>
          <div class="user-actions">
            <template v-if="!userStore.isLoggedIn">
              <el-button @click="$router.push('/login')">登录</el-button>
              <el-button @click="$router.push('/register')">注册</el-button>
            </template>
            <el-dropdown v-else>
              <el-button>
                {{ userStore.userInfo?.username }} [{{ getRoleText(userStore.userInfo?.role) }}]
                <el-icon><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item divided @click="logout">退出登录</el-dropdown-item>
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


    </el-container>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useUserStore } from './stores/user'
import { ElMessage } from 'element-plus'
import { Search, ArrowDown } from '@element-plus/icons-vue'

const router = useRouter()
const userStore = useUserStore()


// 退出登录
const logout = () => {
  userStore.logout()
  ElMessage.success('已退出登录')
  router.push('/login')
}

// 获取角色文本
const getRoleText = (role) => {
  if (role === 'researcher') return '科研人员'
  if (role === 'enterprise') return '企业用户'
  return '未知'
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

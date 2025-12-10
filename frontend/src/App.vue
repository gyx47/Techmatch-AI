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
  gap: 10px;
  flex-wrap: wrap;
}

@media (max-width: 768px) {
  .header-content {
    padding: 0 15px;
    gap: 8px;
  }
}

@media (max-width: 480px) {
  .header-content {
    padding: 0 10px;
    gap: 6px;
  }
}

.logo {
  display: flex;
  align-items: center;
  font-size: 20px;
  font-weight: bold;
  color: #409eff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
  flex-shrink: 1;
  min-width: 0;
}

.logo span {
  word-break: break-word;
  overflow-wrap: break-word;
  white-space: normal;
}

.logo .el-icon {
  margin-right: 8px;
  font-size: 24px;
  flex-shrink: 0;
}

@media (max-width: 768px) {
  .logo {
    font-size: 16px;
  }
  
  .logo .el-icon {
    font-size: 20px;
    margin-right: 6px;
  }
}

@media (max-width: 480px) {
  .logo {
    font-size: 14px;
  }
  
  .logo .el-icon {
    font-size: 18px;
    margin-right: 4px;
  }
  
  .logo span {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1.3;
  }
}

.nav-menu {
  flex: 1;
  margin: 0 40px;
  min-width: 0;
}

@media (max-width: 768px) {
  .nav-menu {
    margin: 0 20px;
  }
}

@media (max-width: 480px) {
  .nav-menu {
    margin: 0 10px;
  }
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

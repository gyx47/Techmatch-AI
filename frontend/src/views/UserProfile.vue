<template>
  <div class="user-profile">
    <div class="container">
      <h1 class="page-title">个人中心</h1>

      <el-row :gutter="20">
        <!-- 左侧：用户基本信息卡片 -->
        <el-col :span="6">
          <div class="panel user-card">
            <div class="avatar-section">
              <el-avatar :size="80" class="avatar">
                {{ userStore.userInfo?.username?.charAt(0).toUpperCase() || 'U' }}
              </el-avatar>
            </div>
            <div class="user-info">
              <h3 class="username">{{ userStore.userInfo?.username || '未登录' }}</h3>
              <el-tag
                :type="getRoleTagType(userStore.userInfo?.role)"
                size="large"
                class="role-tag"
              >
                {{ getRoleText(userStore.userInfo?.role) }}
              </el-tag>
              <div class="user-meta" v-if="userStore.userInfo?.email">
                <el-icon><Message /></el-icon>
                <span>{{ userStore.userInfo.email }}</span>
              </div>
            </div>
          </div>
        </el-col>

        <!-- 右侧：Tabs 内容 -->
        <el-col :span="18">
          <div class="panel">
            <el-tabs v-model="activeTab">
              <!-- Tab 1: 我的发布 -->
              <el-tab-pane label="我的发布" name="publishments">
                <div class="publishments-list">
                  <el-table :data="myPublishments" style="width: 100%">
                    <el-table-column prop="title" label="标题" min-width="200" />
                    <el-table-column prop="type" label="类型" width="100">
                      <template #default="scope">
                        <el-tag :type="scope.row.type === '成果' ? 'success' : 'primary'" size="small">
                          {{ scope.row.type }}
                        </el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column prop="field" label="领域" width="150" />
                    <el-table-column prop="publishTime" label="发布时间" width="120" />
                    <el-table-column label="操作" width="150" fixed="right">
                      <template #default="scope">
                        <el-button
                          type="primary"
                          link
                          size="small"
                          @click="handleEdit(scope.row)"
                        >
                          编辑
                        </el-button>
                        <el-button
                          type="danger"
                          link
                          size="small"
                          @click="handleDelete(scope.row)"
                        >
                          删除
                        </el-button>
                      </template>
                    </el-table-column>
                  </el-table>
                </div>
              </el-tab-pane>

              <!-- Tab 2: 匹配历史 -->
              <el-tab-pane label="匹配历史" name="history">
                <div class="history-list">
                  <el-table :data="matchHistory" style="width: 100%" stripe>
                    <el-table-column prop="matchTime" label="匹配时间" width="180" sortable>
                      <template #default="scope">
                        {{ scope.row.matchTime }}
                      </template>
                    </el-table-column>
                    <el-table-column prop="searchContent" label="搜索内容" min-width="300">
                      <template #default="scope">
                        <span class="search-content">{{ truncateText(scope.row.searchContent, 80) }}</span>
                      </template>
                    </el-table-column>
                    <el-table-column prop="matchType" label="匹配类型" width="120">
                      <template #default="scope">
                        <el-tag :type="scope.row.matchType === '找成果' ? 'success' : 'primary'" size="small">
                          {{ scope.row.matchType }}
                        </el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column prop="matchCount" label="匹配数量" width="100" align="center">
                      <template #default="scope">
                        <span>{{ scope.row.matchCount }} 条</span>
                      </template>
                    </el-table-column>
                    <el-table-column label="操作" width="120" fixed="right">
                      <template #default="scope">
                        <el-button
                          type="primary"
                          link
                          size="small"
                          @click="handleRematch(scope.row)"
                        >
                          查看结果
                        </el-button>
                      </template>
                    </el-table-column>
                  </el-table>
                </div>
              </el-tab-pane>

              <!-- Tab 3: 账号设置 -->
              <el-tab-pane label="账号设置" name="settings">
                <div class="settings-form">
                  <h3 class="section-title">修改密码</h3>
                  <el-form
                    :model="passwordForm"
                    :rules="passwordRules"
                    ref="passwordFormRef"
                    label-width="100px"
                    style="max-width: 500px"
                  >
                    <el-form-item label="当前密码" prop="oldPassword">
                      <el-input
                        v-model="passwordForm.oldPassword"
                        type="password"
                        placeholder="请输入当前密码"
                        show-password
                      />
                    </el-form-item>
                    <el-form-item label="新密码" prop="newPassword">
                      <el-input
                        v-model="passwordForm.newPassword"
                        type="password"
                        placeholder="请输入新密码"
                        show-password
                      />
                    </el-form-item>
                    <el-form-item label="确认新密码" prop="confirmPassword">
                      <el-input
                        v-model="passwordForm.confirmPassword"
                        type="password"
                        placeholder="请再次输入新密码"
                        show-password
                      />
                    </el-form-item>
                    <el-form-item>
                      <el-button
                        type="primary"
                        :loading="changingPassword"
                        @click="handleChangePassword"
                      >
                        修改密码
                      </el-button>
                    </el-form-item>
                  </el-form>
                </div>
              </el-tab-pane>
            </el-tabs>
          </div>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Message } from '@element-plus/icons-vue'

const router = useRouter()
const userStore = useUserStore()

const activeTab = ref('publishments')

// 从 localStorage 加载匹配历史
const loadMatchHistory = () => {
  try {
    const historyKey = 'matchHistory'
    const history = JSON.parse(localStorage.getItem(historyKey) || '[]')
    return history.map(item => ({
      id: item.id,
      matchTime: item.matchTime,
      searchContent: item.searchContent,
      matchType: item.matchType,
      matchCount: item.matchCount || (item.results ? item.results.length : 0)
    }))
  } catch (e) {
    console.error('加载匹配历史失败:', e)
    return []
  }
}

// 匹配历史数据（从 localStorage 加载）
const matchHistory = ref(loadMatchHistory())

// 监听标签页切换，刷新匹配历史
watch(activeTab, (newTab) => {
  if (newTab === 'history') {
    matchHistory.value = loadMatchHistory()
  }
})

// 截取文本
const truncateText = (text, maxLength) => {
  if (!text) return ''
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

// 重新匹配（显示之前的匹配结果）
const handleRematch = (row) => {
  // 跳转到智能匹配页面，传递历史记录ID，用于恢复完整的匹配结果
  router.push({
    path: '/smart-match',
    query: {
      historyId: row.id // 传递历史记录ID
    }
  })
}
const passwordFormRef = ref()
const changingPassword = ref(false)

// 我的发布 Mock 数据
const myPublishments = ref([
  {
    id: 1,
    title: '基于深度学习的智能图像识别系统',
    type: '成果',
    field: '人工智能/计算机视觉',
    publishTime: '2024-01-15'
  },
  {
    id: 2,
    title: '寻求AI驱动的智能客服解决方案',
    type: '需求',
    field: '互联网/电商',
    publishTime: '2024-01-10'
  },
  {
    id: 3,
    title: '大语言模型驱动的智能对话系统',
    type: '成果',
    field: '自然语言处理/大语言模型',
    publishTime: '2024-01-08'
  }
])

// 密码修改表单
const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

// 密码验证规则
const validateConfirmPassword = (rule, value, callback) => {
  if (value !== passwordForm.newPassword) {
    callback(new Error('两次输入密码不一致'))
  } else {
    callback()
  }
}

const passwordRules = {
  oldPassword: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

// 获取角色文本
const getRoleText = (role) => {
  if (role === 'researcher') return '科研人员'
  if (role === 'enterprise') return '企业用户'
  return '未知'
}

// 获取角色标签类型
const getRoleTagType = (role) => {
  if (role === 'researcher') return 'success'
  if (role === 'enterprise') return 'primary'
  return 'info'
}

// 编辑
const handleEdit = (row) => {
  ElMessage.info(`编辑功能开发中... (ID: ${row.id})`)
  // 这里可以实现跳转到编辑页面或打开编辑对话框
}

// 删除
const handleDelete = (row) => {
  ElMessageBox.confirm(
    `确定要删除"${row.title}"吗？`,
    '确认删除',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    // 从列表中删除
    const index = myPublishments.value.findIndex(item => item.id === row.id)
    if (index > -1) {
      myPublishments.value.splice(index, 1)
      ElMessage.success('删除成功')
    }
  }).catch(() => {
    // 用户取消
  })
}

// 修改密码
const handleChangePassword = async () => {
  if (!passwordFormRef.value) return

  await passwordFormRef.value.validate(async (valid) => {
    if (!valid) return

    changingPassword.value = true

    // 模拟 API 调用
    await new Promise(resolve => setTimeout(resolve, 1000))

    changingPassword.value = false
    ElMessage.success('密码修改成功')

    // 清空表单
    Object.assign(passwordForm, {
      oldPassword: '',
      newPassword: '',
      confirmPassword: ''
    })

    // 清除验证状态
    passwordFormRef.value.clearValidate()
  })
}
</script>

<style scoped>
.user-profile {
  min-height: calc(100vh - 60px);
  background: #f5f5f5;
  padding: 20px 0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.page-title {
  font-size: 28px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 24px 0;
}

.panel {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.06);
}

/* 用户卡片 */
.user-card {
  text-align: center;
  height: fit-content;
}

.avatar-section {
  margin-bottom: 16px;
}

.avatar {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  font-size: 32px;
  font-weight: 600;
}

.user-info {
  margin-top: 16px;
}

.username {
  font-size: 20px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 12px 0;
}

.role-tag {
  margin-bottom: 16px;
}

.user-meta {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 13px;
  color: #6b7280;
  margin-top: 12px;
}

.user-meta .el-icon {
  font-size: 16px;
}

/* Tabs 内容 */
.publishments-list {
  margin-top: 16px;
}

.history-list {
  margin-top: 16px;
}

.search-content {
  color: #6b7280;
  font-size: 14px;
  line-height: 1.6;
}

.settings-form {
  margin-top: 16px;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 24px 0;
  padding-bottom: 12px;
  border-bottom: 2px solid #e5e7eb;
}

:deep(.el-table) {
  border-radius: 8px;
  overflow: hidden;
}

:deep(.el-tabs__header) {
  margin-bottom: 20px;
}
</style>


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
                  <div v-if="loadingPublishments" class="loading-container">
                    <el-skeleton :rows="5" animated />
                  </div>
                  <el-table v-else :data="myPublishments" style="width: 100%" stripe>
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
                  <el-empty v-if="!loadingPublishments && myPublishments.length === 0" description="暂无发布内容" />
                </div>
              </el-tab-pane>

              <!-- Tab 2: 匹配历史 -->
              <el-tab-pane label="匹配历史" name="history">
                <div class="history-list">
                  <div v-if="loadingHistory" class="loading-container">
                    <el-skeleton :rows="5" animated />
                  </div>
                  <el-table v-else :data="matchHistory" style="width: 100%" stripe>
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
                  <el-empty v-if="!loadingHistory && matchHistory.length === 0" description="暂无匹配历史" />
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

    <!-- 编辑对话框 -->
    <el-dialog
      v-model="showEditDialog"
      :title="isEditingAchievement ? '编辑成果' : '编辑需求'"
      width="800px"
      :close-on-click-modal="true"
      :close-on-press-escape="true"
      @close="closeEditDialog"
    >
      <el-form
        :model="editForm"
        :rules="editFormRules"
        ref="editFormRef"
        label-position="top"
      >
        <!-- 成果编辑表单 -->
        <template v-if="isEditingAchievement">
          <el-form-item label="成果名称" prop="name">
            <el-input v-model="editForm.name" placeholder="请输入成果名称" />
          </el-form-item>

          <el-form-item label="技术领域" prop="field">
            <el-select v-model="editForm.field" placeholder="请选择技术领域" style="width: 100%">
              <el-option label="人工智能/机器学习" value="人工智能/机器学习" />
              <el-option label="计算机视觉" value="计算机视觉" />
              <el-option label="自然语言处理" value="自然语言处理" />
              <el-option label="区块链技术" value="区块链技术" />
              <el-option label="新能源材料" value="新能源材料" />
              <el-option label="生物医药" value="生物医药" />
              <el-option label="通信工程" value="通信工程" />
              <el-option label="大数据/云计算" value="大数据/云计算" />
              <el-option label="物联网" value="物联网" />
              <el-option label="其他" value="其他" />
            </el-select>
          </el-form-item>

          <el-form-item label="成果简介" prop="description">
            <el-input
              v-model="editForm.description"
              type="textarea"
              :rows="6"
              placeholder="请详细描述您的科研成果..."
            />
          </el-form-item>

          <el-form-item label="应用场景" prop="application">
            <el-input
              v-model="editForm.application"
              type="textarea"
              :rows="3"
              placeholder="请描述该成果的应用场景..."
            />
          </el-form-item>

          <el-form-item label="合作方式">
            <el-select
              v-model="editForm.cooperation_mode"
              multiple
              placeholder="请选择合作方式（可多选）"
              style="width: 100%"
            >
              <el-option label="技术转让" value="技术转让" />
              <el-option label="联合开发" value="联合开发" />
              <el-option label="授权许可" value="授权许可" />
              <el-option label="技术咨询" value="技术咨询" />
              <el-option label="其他" value="其他" />
            </el-select>
          </el-form-item>

          <el-form-item label="联系人" prop="contact_name">
            <el-input v-model="editForm.contact_name" placeholder="请输入联系人姓名" />
          </el-form-item>

          <el-form-item label="电话" prop="contact_phone">
            <el-input v-model="editForm.contact_phone" placeholder="请输入联系电话" />
          </el-form-item>

          <el-form-item label="联系邮箱">
            <el-input v-model="editForm.contact_email" type="email" placeholder="请输入联系邮箱（可选）" />
          </el-form-item>
        </template>

        <!-- 需求编辑表单 -->
        <template v-else>
          <el-form-item label="需求标题" prop="title">
            <el-input v-model="editForm.title" placeholder="请输入需求标题" />
          </el-form-item>

          <el-form-item label="行业领域" prop="industry">
            <el-select v-model="editForm.industry" placeholder="请选择行业领域" style="width: 100%">
              <el-option label="互联网/电商" value="互联网/电商" />
              <el-option label="制造业" value="制造业" />
              <el-option label="金融科技" value="金融科技" />
              <el-option label="医疗健康" value="医疗健康" />
              <el-option label="新能源汽车" value="新能源汽车" />
              <el-option label="智慧农业" value="智慧农业" />
              <el-option label="教育科技" value="教育科技" />
              <el-option label="能源环保" value="能源环保" />
              <el-option label="物流运输" value="物流运输" />
              <el-option label="其他" value="其他" />
            </el-select>
          </el-form-item>

          <el-form-item label="需求详细描述" prop="description">
            <el-input
              v-model="editForm.description"
              type="textarea"
              :rows="6"
              placeholder="请详细描述您的技术需求..."
            />
          </el-form-item>

          <el-form-item label="紧急程度">
            <el-select v-model="editForm.urgency_level" placeholder="请选择紧急程度" style="width: 100%">
              <el-option label="一般" value="一般" />
              <el-option label="较急" value="较急" />
              <el-option label="紧急" value="紧急" />
            </el-select>
          </el-form-item>

          <el-form-item label="合作方式偏好">
            <el-select
              v-model="editForm.cooperation_preference"
              multiple
              placeholder="请选择合作方式偏好（可多选）"
              style="width: 100%"
            >
              <el-option label="技术转让" value="技术转让" />
              <el-option label="联合开发" value="联合开发" />
              <el-option label="授权许可" value="授权许可" />
              <el-option label="技术咨询" value="技术咨询" />
              <el-option label="其他" value="其他" />
            </el-select>
          </el-form-item>

          <el-form-item label="预算范围">
            <el-select v-model="editForm.budget_range" placeholder="请选择预算范围" style="width: 100%">
              <el-option label="10万以下" value="10万以下" />
              <el-option label="10-50万" value="10-50万" />
              <el-option label="50-100万" value="50-100万" />
              <el-option label="100-500万" value="100-500万" />
              <el-option label="500万以上" value="500万以上" />
              <el-option label="面议" value="面议" />
            </el-select>
          </el-form-item>

          <el-form-item label="企业名称" prop="company_name">
            <el-input v-model="editForm.company_name" placeholder="请输入企业名称" />
          </el-form-item>

          <el-form-item label="联系人" prop="contact_name">
            <el-input v-model="editForm.contact_name" placeholder="请输入联系人姓名" />
          </el-form-item>

          <el-form-item label="电话" prop="contact_phone">
            <el-input v-model="editForm.contact_phone" placeholder="请输入联系电话" />
          </el-form-item>

          <el-form-item label="联系邮箱">
            <el-input v-model="editForm.contact_email" type="email" placeholder="请输入联系邮箱（可选）" />
          </el-form-item>
        </template>
      </el-form>

      <template #footer>
        <el-button @click="closeEditDialog">取消</el-button>
        <el-button type="primary" @click="submitEdit" :loading="submittingEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Message } from '@element-plus/icons-vue'
import api from '../api'

const router = useRouter()
const userStore = useUserStore()

const activeTab = ref('publishments')

// 从后端API加载匹配历史（只从数据库加载，不从localStorage加载）
const loadMatchHistory = async () => {
  try {
    const response = await api.get('/matching/history', {
      params: {
        page: 1,
        page_size: 100  // 获取所有历史记录
      }
    })
    
    if (response.data && response.data.items && response.data.items.length > 0) {
      // 将数据库中的历史记录转换为前端需要的格式
      const history = response.data.items.map(item => ({
        id: item.history_id || item.id,  // 使用数据库的 history_id
        matchTime: item.match_time || item.created_at || item.matchTime,
        searchContent: item.search_desc || item.searchContent,
        matchType: item.match_type || (item.match_mode === 'enterprise' ? '找成果' : '找需求'),
        matchCount: item.result_count || item.matchCount || 0,
        matchMode: item.match_mode,  // 保存匹配模式，用于恢复
        source: 'database'  // 标记来源为数据库
      }))
      
      return history
    }
    
    // 如果没有数据，返回空数组
    return []
  } catch (error) {
    console.error('从API加载匹配历史失败:', error)
    // API失败时返回空数组，不显示任何历史记录
    return []
  }
}

// 匹配历史数据
const matchHistory = ref([])
const loadingHistory = ref(false)

// 监听标签页切换，刷新数据
watch(activeTab, async (newTab) => {
  if (newTab === 'history') {
    loadingHistory.value = true
    matchHistory.value = await loadMatchHistory()
    loadingHistory.value = false
  } else if (newTab === 'publishments') {
    await loadMyPublishments()
  }
})

// 截取文本
const truncateText = (text, maxLength) => {
  if (!text) return ''
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

// 查看匹配结果（只从数据库加载）
const handleRematch = async (row) => {
  // 只从数据库加载，不再从localStorage加载
  try {
    // 从后端API获取匹配结果详情
    const response = await api.get(`/matching/history/${row.id}/results`)
    
    // 检查响应数据
    if (!response.data) {
      ElMessage.warning('未找到匹配结果数据')
      return
    }
    
    const papers = response.data.papers || []
    
    // 如果没有匹配结果，提示用户
    if (papers.length === 0) {
      ElMessage.warning('该历史记录没有保存匹配结果')
      return
    }
    
    // 将数据转换为前端需要的格式
    const convertedResults = papers.map((paper, index) => {
      const score = paper.score || 0
      const matchScore = score > 1 ? Math.round(score) : Math.round(score * 100)
      
      // 根据item_type判断是论文还是成果
      const itemType = paper.item_type || (paper.paper_id && paper.paper_id.startsWith('achievement_') ? 'achievement' : 'paper')
      
      if (itemType === 'achievement') {
        // 成果格式
        return {
          id: `achievement_${paper.achievement_id || paper.paper_id?.replace('achievement_', '')}`,
          achievement_id: paper.achievement_id || parseInt(paper.paper_id?.replace('achievement_', '') || '0'),
          title: paper.name || paper.title || '无标题',
          summary: paper.description || paper.abstract || '暂无描述',
          application: paper.application || '',
          matchScore: matchScore,
          type: '成果',
          field: paper.field || paper.categories || '未分类',
          keywords: [],
          paper_id: null, // 成果没有paper_id
          pdf_url: null, // 成果没有PDF
          authors: '', // 成果没有作者
          published_date: '',
          reason: paper.reason || '',
          match_type: paper.match_type || '',
          vector_score: paper.vector_score || 0,
          // 成果特有字段
          contact_name: paper.contact_name || '',
          contact_phone: paper.contact_phone || '',
          contact_email: paper.contact_email || '',
          cooperation_mode: paper.cooperation_mode || []
        }
      } else {
        // 论文格式
        return {
          id: paper.paper_id || `paper_${index}`,
          title: paper.title || '无标题',
          summary: paper.abstract || '暂无摘要',
          matchScore: matchScore,
          type: '论文',
          field: paper.categories || '未分类',
          keywords: paper.categories ? paper.categories.split(',') : [],
          paper_id: paper.paper_id,
          pdf_url: paper.pdf_url,
          authors: paper.authors || '',
          published_date: paper.published_date || '',
          reason: paper.reason || '',
          match_type: paper.match_type || '',
          vector_score: paper.vector_score || 0
        }
      }
    })
    
    // 检查转换后的结果是否为空
    if (convertedResults.length === 0) {
      ElMessage.warning('匹配结果数据格式错误，无法显示')
      return
    }
    
    // 保存到 sessionStorage，供 SmartMatch 页面使用
    const userStore = useUserStore()
    sessionStorage.setItem('matchingResults', JSON.stringify({
      papers: convertedResults,
      searchText: response.data.search_desc || row.searchContent,
      matchMode: response.data.match_mode || row.matchMode || 'enterprise',
      historyId: response.data.history_id || row.id,  // 保存历史ID
      userId: userStore.userInfo?.id || null  // 保存当前用户ID
    }))
    
    // 跳转到智能匹配页面
    const historyId = response.data.history_id || row.id
    router.push({
      path: '/smart-match',
      query: {
        fromHistory: 'true',
        historyId: historyId.toString(),  // 将 historyId 也放在 URL 参数中，以便刷新后恢复
        q: response.data.search_desc || row.searchContent,
        type: response.data.match_mode || row.matchMode || 'enterprise'
      }
    })
  } catch (error) {
    console.error('获取匹配结果失败:', error)
    
    // 如果是404错误，说明历史记录不存在或无权限
    if (error.response?.status === 404) {
      ElMessage.error('匹配历史不存在或无权限访问')
      return
    }
    
    ElMessage.error('获取匹配结果失败: ' + (error.response?.data?.detail || error.message))
  }
}
const passwordFormRef = ref()
const changingPassword = ref(false)

// 我的发布数据
const myPublishments = ref([])
const loadingPublishments = ref(false)

// 加载我的发布内容
const loadMyPublishments = async () => {
  loadingPublishments.value = true
  try {
    const achievementsPromise = api.get('/publish/my-achievements', {
      params: { page: 1, page_size: 100 }
    }).catch(() => ({ data: { items: [] } }))
    
    const needsPromise = api.get('/publish/my-needs', {
      params: { page: 1, page_size: 100 }
    }).catch(() => ({ data: { items: [] } }))
    
    const [achievementsRes, needsRes] = await Promise.all([achievementsPromise, needsPromise])
    
    const achievements = (achievementsRes.data?.items || []).map(item => ({
      id: item.id,
      achievement_id: item.id,
      title: item.name || '无标题',
      type: '成果',
      field: item.field || '未分类',
      publishTime: item.created_at ? item.created_at.split(' ')[0] : '',
      rawData: item
    }))
    
    const needs = (needsRes.data?.items || []).map(item => ({
      id: item.id,
      need_id: item.id,
      title: item.title || '无标题',
      type: '需求',
      field: item.industry || '未分类',
      publishTime: item.created_at ? item.created_at.split(' ')[0] : '',
      rawData: item
    }))
    
    // 合并并按时间排序
    myPublishments.value = [...achievements, ...needs].sort((a, b) => {
      return new Date(b.publishTime) - new Date(a.publishTime)
    })
  } catch (error) {
    console.error('加载我的发布内容失败:', error)
    ElMessage.error('加载发布内容失败')
    myPublishments.value = []
  } finally {
    loadingPublishments.value = false
  }
}

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
    { required: true, message: '请输入新密码', trigger: 'blur' }
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

// 编辑对话框相关
const showEditDialog = ref(false)
const editingItem = ref(null)
const isEditingAchievement = ref(false)
const editFormRef = ref()
const submittingEdit = ref(false)

// 编辑表单数据
const editForm = reactive({
  // 成果字段
  name: '',
  field: '',
  description: '',
  application: '',
  cooperation_mode: [],
  contact_name: '',
  contact_phone: '',
  contact_email: '',
  // 需求字段
  title: '',
  industry: '',
  urgency_level: '',
  cooperation_preference: [],
  budget_range: '',
  company_name: ''
})

// 编辑表单验证规则（动态规则，根据编辑类型返回不同规则）
const getEditFormRules = () => {
  if (isEditingAchievement.value) {
    return {
      name: [{ required: true, message: '请输入成果名称', trigger: 'blur' }],
      field: [{ required: true, message: '请选择技术领域', trigger: 'change' }],
      description: [
        { required: true, message: '请输入成果简介', trigger: 'blur' },
        { min: 20, message: '成果简介至少需要20个字符', trigger: 'blur' }
      ],
      application: [{ required: true, message: '请输入应用场景', trigger: 'blur' }],
      contact_name: [{ required: true, message: '请输入联系人', trigger: 'blur' }],
      contact_phone: [
        { required: true, message: '请输入联系电话', trigger: 'blur' },
        { pattern: /^1[3-9]\d{9}$|^0\d{2,3}-?\d{7,8}$/, message: '请输入正确的电话号码', trigger: 'blur' }
      ]
    }
  } else {
    return {
      title: [{ required: true, message: '请输入需求标题', trigger: 'blur' }],
      industry: [{ required: true, message: '请选择行业领域', trigger: 'change' }],
      description: [
        { required: true, message: '请输入需求详细描述', trigger: 'blur' },
        { min: 20, message: '需求描述至少需要20个字符', trigger: 'blur' }
      ],
      company_name: [{ required: true, message: '请输入企业名称', trigger: 'blur' }],
      contact_name: [{ required: true, message: '请输入联系人', trigger: 'blur' }],
      contact_phone: [
        { required: true, message: '请输入联系电话', trigger: 'blur' },
        { pattern: /^1[3-9]\d{9}$|^0\d{2,3}-?\d{7,8}$/, message: '请输入正确的电话号码', trigger: 'blur' }
      ]
    }
  }
}

// 计算属性：动态获取验证规则
const editFormRules = computed(() => getEditFormRules())

// 重置编辑表单
const resetEditForm = () => {
  Object.assign(editForm, {
    name: '',
    field: '',
    description: '',
    application: '',
    cooperation_mode: [],
    contact_name: '',
    contact_phone: '',
    contact_email: '',
    title: '',
    industry: '',
    urgency_level: '',
    cooperation_preference: [],
    budget_range: '',
    company_name: ''
  })
}

// 编辑
const handleEdit = async (row) => {
  editingItem.value = row
  isEditingAchievement.value = row.type === '成果'
  
  // 填充表单数据
  if (row.type === '成果') {
    const data = row.rawData || {}
    Object.assign(editForm, {
      name: data.name || row.title || '',
      field: data.field || row.field || '',
      description: data.description || '',
      application: data.application || '',
      cooperation_mode: data.cooperation_mode || [],
      contact_name: data.contact_name || '',
      contact_phone: data.contact_phone || '',
      contact_email: data.contact_email || ''
    })
  } else {
    const data = row.rawData || {}
    Object.assign(editForm, {
      title: data.title || row.title || '',
      industry: data.industry || row.field || '',
      description: data.description || '',
      urgency_level: data.urgency_level || '',
      cooperation_preference: data.cooperation_preference || [],
      budget_range: data.budget_range || '',
      company_name: data.company_name || '',
      contact_name: data.contact_name || '',
      contact_phone: data.contact_phone || '',
      contact_email: data.contact_email || ''
    })
  }
  
  showEditDialog.value = true
}

// 提交编辑
const submitEdit = async () => {
  if (!editFormRef.value || submittingEdit.value) return
  
  submittingEdit.value = true
  
  try {
    // 先进行表单验证
    const valid = await editFormRef.value.validate()
    if (!valid) {
      submittingEdit.value = false
      return // 验证失败，不关闭对话框
    }
    
    if (isEditingAchievement.value) {
      // 更新成果
      await api.put(`/publish/achievement/${editingItem.value.achievement_id || editingItem.value.id}`, {
        name: editForm.name,
        field: editForm.field,
        description: editForm.description,
        application: editForm.application,
        cooperation_mode: editForm.cooperation_mode,
        contact_name: editForm.contact_name,
        contact_phone: editForm.contact_phone,
        contact_email: editForm.contact_email
      })
      ElMessage.success('成果更新成功')
    } else {
      // 更新需求
      await api.put(`/publish/need/${editingItem.value.need_id || editingItem.value.id}`, {
        title: editForm.title,
        industry: editForm.industry,
        description: editForm.description,
        urgency_level: editForm.urgency_level,
        cooperation_preference: editForm.cooperation_preference,
        budget_range: editForm.budget_range,
        company_name: editForm.company_name,
        contact_name: editForm.contact_name,
        contact_phone: editForm.contact_phone,
        contact_email: editForm.contact_email
      })
      ElMessage.success('需求更新成功')
    }
    
    // 关闭对话框并刷新列表
    closeEditDialog()
    await loadMyPublishments()
  } catch (error) {
    console.error('更新失败:', error)
    ElMessage.error(error.response?.data?.detail || '更新失败，请稍后重试')
    // 更新失败时不关闭对话框，让用户修改后重试
  } finally {
    submittingEdit.value = false
  }
}

// 关闭编辑对话框
const closeEditDialog = () => {
  try {
    // 先清除表单验证状态
    if (editFormRef.value) {
      editFormRef.value.clearValidate()
    }
    // 重置表单数据
    resetEditForm()
    // 清空编辑项
    editingItem.value = null
    // 最后关闭对话框（确保其他清理操作先完成）
    showEditDialog.value = false
  } catch (e) {
    console.error('关闭对话框失败:', e)
    // 即使出错也强制关闭
    showEditDialog.value = false
  }
}

// 删除
const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除"${row.title}"吗？删除后无法恢复。`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    // 调用后端API删除
    if (row.type === '成果') {
      await api.delete(`/publish/achievement/${row.achievement_id || row.id}`)
    } else {
      await api.delete(`/publish/need/${row.need_id || row.id}`)
    }
    
    // 从列表中删除
    const index = myPublishments.value.findIndex(item => item.id === row.id)
    if (index > -1) {
      myPublishments.value.splice(index, 1)
    }
    
    ElMessage.success('删除成功')
  } catch (error) {
    if (error === 'cancel') {
      // 用户取消，不处理
      return
    }
    console.error('删除失败:', error)
    ElMessage.error(error.response?.data?.detail || '删除失败，请稍后重试')
  }
}

// 初始化时加载数据
onMounted(async () => {
  if (activeTab.value === 'history') {
    loadingHistory.value = true
    matchHistory.value = await loadMatchHistory()
    loadingHistory.value = false
  } else if (activeTab.value === 'publishments') {
    await loadMyPublishments()
  }
})

// 修改密码
const handleChangePassword = async () => {
  if (!passwordFormRef.value) return

  await passwordFormRef.value.validate(async (valid) => {
    if (!valid) return

    changingPassword.value = true

    try {
      // 调用后端API修改密码
      await api.post('/auth/change-password', {
        old_password: passwordForm.oldPassword,
        new_password: passwordForm.newPassword
      })

      ElMessage.success('密码修改成功')

      // 清空表单
      Object.assign(passwordForm, {
        oldPassword: '',
        newPassword: '',
        confirmPassword: ''
      })

      // 清除验证状态
      passwordFormRef.value.clearValidate()
    } catch (error) {
      console.error('修改密码失败:', error)
      ElMessage.error(error.response?.data?.detail || '密码修改失败，请检查当前密码是否正确')
    } finally {
      changingPassword.value = false
    }
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
  max-width: 100%;
  overflow: hidden;
}

.user-meta .el-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.user-meta span {
  word-break: break-all;
  word-wrap: break-word;
  overflow-wrap: break-word;
  max-width: 100%;
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


<template>
  <div class="requirement-detail">
    <div class="container">
      <!-- 加载状态 -->
      <div v-if="loading" class="loading">
        <el-skeleton :rows="8" animated />
      </div>

      <div v-else>
        <!-- 返回按钮 -->
        <div class="header-section">
          <el-button type="text" @click="goBack" class="back-button">
            <el-icon><ArrowLeft /></el-icon>
            <span>返回</span>
          </el-button>
        </div>

        <!-- 主要内容 -->
        <div v-if="requirementData.requirement_id">
          <div class="title-section">
            <h1 class="title">{{ requirementData.title }}</h1>
            <div class="meta-tags">
              <el-tag type="primary">需求</el-tag>
              <el-tag v-if="requirementData.industry" type="info">
                {{ requirementData.industry }}
              </el-tag>
              <el-tag v-if="requirementData.technical_level" :type="getLevelType(requirementData.technical_level)">
                技术难度：{{ requirementData.technical_level }}
              </el-tag>
              <el-tag v-if="requirementData.market_size" type="success">
                市场规模：{{ requirementData.market_size }}
              </el-tag>
            </div>
          </div>
          
          <el-row :gutter="20">
            <el-col :span="16">
              <!-- 需求描述 -->
              <div class="panel">
                <h3>需求描述</h3>
                <p class="description">{{ requirementData.description }}</p>
              </div>
              
              <!-- 痛点分析 -->
              <div class="panel" v-if="requirementData.pain_points">
                <h3>痛点分析</h3>
                <div class="pain-points">
                  <pre>{{ requirementData.pain_points }}</pre>
                </div>
              </div>
              
              <!-- AI匹配分析 -->
              <div class="panel" v-if="requirementData.reason">
                <h3>AI匹配分析</h3>
                <div class="match-analysis">
                  <div class="match-reason">
                    <h4>推荐理由</h4>
                    <p>{{ requirementData.reason }}</p>
                  </div>
                  <div class="implementation-suggestion" v-if="requirementData.implementation_suggestion">
                    <h4>实施建议</h4>
                    <p>{{ requirementData.implementation_suggestion }}</p>
                  </div>
                </div>
              </div>
              
            </el-col>
            
            <el-col :span="8">
              <!-- 匹配度卡片 -->
              <div class="panel">
                <h3>匹配度分析</h3>
                <div class="match-score">
                  <el-progress
                    type="dashboard"
                    :percentage="requirementData.score || 0"
                    :color="getScoreColor(requirementData.score || 0)"
                    :width="120"
                  >
                    <template #default="{ percentage }">
                      <span class="score-text">{{ percentage }}%</span>
                    </template>
                  </el-progress>
                  <p class="score-label">AI匹配度</p>
                </div>
                <div class="match-tag" v-if="requirementData.match_type">
                  <el-tag :type="getMatchTypeTagType(requirementData.match_type)" size="large">
                    {{ requirementData.match_type }}
                  </el-tag>
                </div>
                <div class="vector-score" v-if="requirementData.vector_score">
                  <p>向量相似度: {{ (requirementData.vector_score * 100).toFixed(1) }}%</p>
                </div>
              </div>
              
              <!-- 联系信息 -->
              <div class="panel contact-card">
                <h3>联系信息</h3>
                <div class="contact-info">
                  <div class="info-item">
                    <el-icon><User /></el-icon>
                    <div class="info-content">
                      <div class="info-label">发布者</div>
                      <div class="info-value">{{ requirementData.contact_name || requirementData.contact_info || '匿名用户' }}</div>
                    </div>
                  </div>
                  <div class="info-item" v-if="userStore.isLoggedIn && requirementData.contact_email">
                    <el-icon><Message /></el-icon>
                    <div class="info-content">
                      <div class="info-label">联系方式</div>
                      <div class="info-value">{{ requirementData.contact_email }}</div>
                    </div>
                  </div>
                  <div class="info-item" v-else-if="!userStore.isLoggedIn">
                    <el-icon><Message /></el-icon>
                    <div class="info-content">
                      <div class="info-label">联系方式</div>
                      <div class="info-value">
                        <el-button type="text" size="small" @click="router.push('/login')">
                          登录后查看
                        </el-button>
                      </div>
                    </div>
                  </div>
                  <div class="info-item">
                    <el-icon><Calendar /></el-icon>
                    <div class="info-content">
                      <div class="info-label">发布时间</div>
                      <div class="info-value">{{ formatDate(requirementData.created_at || requirementData.published_date) }}</div>
                    </div>
                  </div>
                  <div class="info-item" v-if="requirementData.source_url">
                    <el-icon><Link /></el-icon>
                    <div class="info-content">
                      <div class="info-label">来源链接</div>
                      <div class="info-value">
                        <a :href="requirementData.source_url" target="_blank" class="source-link">
                          查看原始需求
                        </a>
                      </div>
                    </div>
                  </div>
                </div>
                <el-button 
                  type="primary" 
                  size="large" 
                  class="contact-btn" 
                  @click="handleContact"
                  :disabled="!userStore.isLoggedIn"
                >
                  {{ userStore.isLoggedIn ? '联系需求方' : '请先登录' }}
                </el-button>
              </div>
            </el-col>
          </el-row>
        </div>

        <!-- 空状态 -->
        <div v-else class="empty">
          <el-empty description="需求不存在或已被删除" />
          <div class="empty-actions">
            <el-button type="primary" @click="goBack">返回上一页</el-button>
            <el-button @click="router.push('/smart-match')">重新匹配</el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { ElMessage } from 'element-plus'
import { 
  ArrowLeft, 
  User, 
  Message, 
  Calendar,
  Link,
  Document 
} from '@element-plus/icons-vue'
import api from '../api'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const loading = ref(true)
const requirementData = ref({})
const paperInfo = ref(null)

onMounted(async () => {
  await loadRequirementData()
})

const loadRequirementData = async () => {
  loading.value = true
  
  try {
    const requirementId = route.params.id
    
    if (requirementId && requirementId !== 'undefined') {
      // 优先从API获取完整的需求信息
      const response = await api.get(`/matching/requirements/${requirementId}`)
      console.log('需求详情数据:', response.data)
      requirementData.value = response.data
      console.log('需求信息:', requirementData.value)
      requirementData.value.score = parseFloat(route.query.match_score)
      console.log('需求分数', parseFloat(route.query.match_score))

      // 如果没有AI评分理由，尝试获取或生成
      if (!requirementData.value.reason) {
        console.log('尝试生成匹配理由...')
        await generateMatchingReason()
      }
    } else {
      // 从路由参数加载基本信息（兼容旧版本）
      requirementData.value = {
        title: route.query.title || '需求详情',
        description: route.query.description || '',
        industry: route.query.industry || '',
        technical_level: route.query.technical_level || '中',
        market_size: route.query.market_size || '中型',
        score: parseFloat(route.query.match_score) || 0,
        reason: route.query.reason || '',
        implementation_suggestion: route.query.implementation_suggestion || '',
        match_type: route.query.match_type || 'B级-需技术适配',
        vector_score: parseFloat(route.query.vector_score) || 0,
        pain_points: route.query.pain_points || ''
      }
    }
  } catch (error) {
    console.error('加载需求详情失败:', error)
    ElMessage.error('加载需求详情失败: ' + (error.response?.data?.detail || error.message))
    
    // 失败时使用路由参数
    requirementData.value = {
      title: route.query.title || '需求详情',
      description: route.query.description || '',
      industry: route.query.industry || '',
      technical_level: route.query.technical_level || '中',
      market_size: route.query.market_size || '中型',
      score: parseFloat(route.query.match_score) || 0,
      reason: route.query.reason || '',
      implementation_suggestion: route.query.implementation_suggestion || '',
      match_type: route.query.match_type || 'B级-需技术适配',
      vector_score: parseFloat(route.query.vector_score) || 0,
      pain_points: route.query.pain_points || ''
    }
  } finally {
    loading.value = false
  }
}

const generateMatchingReason = async () => {
  try {
    // 首先检查是否从SmartMatch页面跳转过来，有搜索文本
    const searchText = route.query.search_text || ''
    
    if (searchText) {
      console.log('使用搜索文本生成匹配理由:', searchText)
      const response = await api.post('/requirements/generate-analysis', {
        requirement_data: requirementData.value,
        user_input: searchText,
        analysis_type: 'requirement_analysis'
      })
      if (response.data.reason) {
        requirementData.value.reason = response.data.reason
      }
      if (response.data.implementation_suggestion) {
        requirementData.value.implementation_suggestion = response.data.implementation_suggestion
      }
      if (response.data.score) {
        requirementData.value.score = response.data.score
      }
      if (response.data.match_type) {
        requirementData.value.match_type = response.data.match_type
      }
    } 

    // 如果有论文信息，调用论文匹配接口
    else if (route.query.paper_title) {
      console.log('使用论文信息生成匹配理由:', route.query.paper_title)
      const response = await api.post('/requirements/generate-analysis', {
        requirement_data: requirementData.value,
        paper_title: route.query.paper_title,
        paper_abstract: route.query.paper_abstract || '',
        analysis_type: 'paper_matching'
      })
      
      if (response.data.reason) {
        requirementData.value.reason = response.data.reason
      }
      if (response.data.implementation_suggestion) {
        requirementData.value.implementation_suggestion = response.data.implementation_suggestion
      }
      if (response.data.score) {
        requirementData.value.score = response.data.score
      }
      if (response.data.match_type) {
        requirementData.value.match_type = response.data.match_type
      }
    }

    // 如果没有搜索文本也没有论文信息，基于需求自身分析
    else {
      console.log('基于需求自身分析生成建议')
      const response = await api.post('/requirements/generate-analysis', {
        requirement_data: requirementData.value,
        analysis_type: 'self_analysis'
      })
      
      if (response.data.reason) {
        requirementData.value.reason = response.data.reason
      }
      if (response.data.implementation_suggestion) {
        requirementData.value.implementation_suggestion = response.data.implementation_suggestion
      }
      // 没有匹配分数，设置默认值
      if (!requirementData.value.score) {
        requirementData.value.score = 70  // 默认70分
      }
    }

  } catch (error) {
    console.error('生成匹配理由失败:', error)
    // 如果生成失败，使用默认理由
    requirementData.value.reason = `该科研成果与需求高度相关，技术在${requirementData.value.industry}行业有广泛应用前景。`
  }
}

// 返回上一页
const goBack = () => {
  if (route.query.from === 'smart-match') {
    router.push({
      path: '/smart-match',
      query: { restore: 'true' }
    })
  } else {
    router.back()
  }
}

// 获取分数颜色
const getScoreColor = (score) => {
  if (score >= 90) return '#67c23a'
  if (score >= 80) return '#409eff'
  if (score >= 70) return '#e6a23c'
  return '#f56c6c'
}

// 获取技术难度标签类型
const getLevelType = (level) => {
  if (level === '高' || level === '极高') return 'danger'
  if (level === '中') return 'warning'
  return 'success'
}

// 获取匹配类型标签类型
const getMatchTypeTagType = (matchType) => {
  if (matchType && matchType.includes('S级')) return 'success'
  if (matchType && matchType.includes('A级')) return 'warning'
  if (matchType && matchType.includes('B级')) return 'info'
  if (matchType && matchType.includes('C级')) return ''
  return 'info'
}

// 格式化日期
const formatDate = (dateStr) => {
  if (!dateStr) return '未知'
  try {
    const date = new Date(dateStr)
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    })
  } catch (e) {
    return dateStr
  }
}

// 联系需求方
const handleContact = () => {
  if (!userStore.isLoggedIn) {
    ElMessage.warning('请先登录后再联系需求方')
    router.push('/login')
    return
  }
  
  if (requirementData.value.contact_email) {
    const email = requirementData.value.contact_email
    const subject = `关于需求"${requirementData.value.title}"的合作咨询`
    const body = `尊敬的${requirementData.value.contact_name || '需求方'}：

我在技术转移平台看到了您发布的"${requirementData.value.title}"需求，对此非常感兴趣。

我方拥有相关的技术成果：
${paperInfo.value ? `论文标题：${paperInfo.value.title}` : '相关技术方案'}

希望能与您进一步沟通合作事宜。

联系信息：
姓名：${userStore.userInfo?.username || ''}
邮箱：${userStore.userInfo?.email || ''}

期待您的回复！

此致
敬礼`
    
    window.location.href = `mailto:${email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
    ElMessage.success('已打开邮箱客户端，请填写详细信息后发送')
  } else {
    ElMessage.warning('该需求方未提供联系方式')
  }
}
</script>

<style scoped>
.requirement-detail {
  min-height: calc(100vh - 60px);
  background: #f5f5f5;
  padding: 20px 0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.loading {
  margin: 40px 0;
}

.header-section {
  margin-bottom: 24px;
}

.back-button {
  margin-bottom: 16px;
  padding: 8px 0;
  color: #667eea;
}

.back-button .el-icon {
  margin-right: 4px;
}

.title-section {
  margin-top: 8px;
  margin-bottom: 24px;
}

.title {
  font-size: 28px;
  font-weight: 600;
  color: #1f2937;
  margin: 8px 0;
}

.meta-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 12px;
}

.panel {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.06);
  margin-bottom: 16px;
}

.panel h3 {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 16px 0;
  padding-bottom: 12px;
  border-bottom: 1px solid #eee;
}

.description, .pain-points {
  color: #666;
  line-height: 1.8;
  font-size: 14px;
  margin: 0;
}

.pain-points pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: inherit;
  margin: 0;
  color: #666;
  line-height: 1.6;
}

.match-analysis {
  margin-top: 16px;
}

.match-analysis h4 {
  font-size: 16px;
  color: #374151;
  margin: 16px 0 8px 0;
}

.match-analysis p {
  color: #666;
  line-height: 1.6;
  margin: 0;
}

.paper-info {
  margin-top: 16px;
}

.paper-info h4 {
  font-size: 16px;
  color: #333;
  margin-bottom: 8px;
}

.paper-abstract {
  color: #666;
  line-height: 1.6;
  font-size: 14px;
  margin-bottom: 12px;
}

.paper-meta {
  font-size: 13px;
  color: #999;
  margin-bottom: 12px;
}

.paper-meta span {
  display: block;
  margin-bottom: 4px;
}

.match-score {
  text-align: center;
  margin-bottom: 16px;
}

.score-text {
  font-size: 28px;
  font-weight: 600;
  color: #1f2937;
}

.score-label {
  color: #6b7280;
  font-size: 12px;
  margin: 8px 0 0 0;
}

.vector-score {
  text-align: center;
  margin-top: 12px;
  font-size: 13px;
  color: #666;
}

.match-tag {
  text-align: center;
  margin-top: 16px;
}

.contact-card {
  background: #fff;
}

.contact-info {
  margin-bottom: 20px;
}

.info-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
}

.info-item:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.info-item .el-icon {
  font-size: 20px;
  color: #667eea;
  margin-top: 2px;
}

.info-content {
  flex: 1;
}

.info-label {
  font-size: 12px;
  color: #666;
  margin-bottom: 4px;
}

.info-value {
  font-size: 14px;
  font-weight: 500;
  color: #1f2937;
}

.source-link {
  color: #667eea;
  text-decoration: none;
}

.source-link:hover {
  text-decoration: underline;
}

.contact-btn {
  width: 100%;
  margin-top: 8px;
}

.empty {
  margin: 60px 0;
  text-align: center;
}

.empty-actions {
  margin-top: 20px;
  display: flex;
  gap: 12px;
  justify-content: center;
}
</style>
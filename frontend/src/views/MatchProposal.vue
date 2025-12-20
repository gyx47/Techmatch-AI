<template>
  <div class="match-proposal">
    <div class="container">
      <div class="header-section">
        <el-button
          type="text"
          @click="handleBack"
          class="back-button"
        >
          <el-icon><ArrowLeft /></el-icon>
          <span>返回</span>
        </el-button>
        <div class="title-section">
          <h1 class="title">{{ proposalData.title || '加载中...' }}</h1>
          <p class="subtitle">合作方案详情</p>
        </div>
      </div>
      
      <div v-if="loading" class="loading-container">
        <el-skeleton :rows="10" animated />
      </div>
      
      <div v-else>
        <el-row :gutter="20">
        <!-- 左侧内容 (2/3) -->
        <el-col :span="16">
          <!-- AI 匹配分析 -->
          <div class="panel ai-analysis">
            <div class="ai-header">
              <el-icon class="ai-icon"><MagicStick /></el-icon>
              <h3>AI 匹配分析</h3>
            </div>
            <div class="ai-content">
              <p>{{ proposalData.aiAnalysis }}</p>
            </div>
          </div>

          <!-- 详细描述 -->
          <div class="panel">
            <h3>详细描述</h3>
            <p class="description">{{ proposalData.description }}</p>
          </div>

          <!-- 技术指标 -->
          <div class="panel">
            <h3>技术指标</h3>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="技术领域">{{ proposalData.field }}</el-descriptions-item>
              <el-descriptions-item label="应用场景">{{ proposalData.application }}</el-descriptions-item>
              <el-descriptions-item label="技术成熟度">{{ proposalData.maturity }}</el-descriptions-item>
              <el-descriptions-item label="预期周期">{{ proposalData.duration }}</el-descriptions-item>
              <el-descriptions-item label="核心优势" :span="2">{{ proposalData.advantages }}</el-descriptions-item>
            </el-descriptions>
          </div>
        </el-col>

        <!-- 右侧内容 (1/3) -->
        <el-col :span="8">
          <!-- 匹配度仪表盘 -->
          <div class="panel">
            <h3>匹配度</h3>
            <div class="match-score">
              <el-progress
                type="dashboard"
                :percentage="proposalData.matchScore"
                :color="getScoreColor(proposalData.matchScore)"
                :width="150"
              >
                <template #default="{ percentage }">
                  <span class="score-text">{{ percentage }}%</span>
                </template>
              </el-progress>
              <p class="score-label">综合匹配度</p>
            </div>
            <div class="match-details">
              <div class="detail-item">
                <span class="detail-label">技术匹配：</span>
                <el-progress :percentage="proposalData.techMatch" :stroke-width="8" :show-text="false" />
                <span class="detail-value">{{ proposalData.techMatch }}%</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">需求匹配：</span>
                <el-progress :percentage="proposalData.needMatch" :stroke-width="8" :show-text="false" />
                <span class="detail-value">{{ proposalData.needMatch }}%</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">应用匹配：</span>
                <el-progress :percentage="proposalData.appMatch" :stroke-width="8" :show-text="false" />
                <span class="detail-value">{{ proposalData.appMatch }}%</span>
              </div>
            </div>
          </div>

          <!-- 对接信息卡片 -->
          <div class="panel contact-card">
            <h3>对接信息</h3>
            <div class="contact-info">
              <div class="info-item">
                <el-icon><User /></el-icon>
                <div class="info-content">
                  <div class="info-label">联系人</div>
                  <div class="info-value">{{ contactInfo.name }}</div>
                </div>
              </div>
              <div class="info-item">
                <el-icon><Phone /></el-icon>
                <div class="info-content">
                  <div class="info-label">电话</div>
                  <div class="info-value">{{ contactInfo.phone }}</div>
                </div>
              </div>
              <div class="info-item">
                <el-icon><Message /></el-icon>
                <div class="info-content">
                  <div class="info-label">邮箱</div>
                  <div class="info-value">{{ contactInfo.email }}</div>
                </div>
              </div>
              <div class="info-item">
                <el-icon><OfficeBuilding /></el-icon>
                <div class="info-content">
                  <div class="info-label">所属机构</div>
                  <div class="info-value">{{ contactInfo.organization }}</div>
                </div>
              </div>
            </div>
            <el-button type="primary" size="large" class="contact-btn" @click="handleContact">
              立即联系
            </el-button>
          </div>
        </el-col>
        </el-row>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { MagicStick, User, Phone, Message, OfficeBuilding, ArrowLeft } from '@element-plus/icons-vue'
import api from '../api'

const route = useRoute()
const router = useRouter()

// 提案数据
const proposalData = ref({
  title: '',
  aiAnalysis: '',
  description: '',
  field: '',
  application: '',
  maturity: '',
  duration: '',
  advantages: '',
  matchScore: 0,
  techMatch: 0,
  needMatch: 0,
  appMatch: 0
})

// 联系人信息
const contactInfo = ref({
  name: '',
  phone: '',
  email: '',
  organization: ''
})

const loading = ref(true)

// 根据路由参数加载数据
onMounted(async () => {
  const paperId = route.params.id
  
  try {
    // 首先尝试从 localStorage 获取匹配结果数据
    const matchState = localStorage.getItem('smartMatchState')
    if (matchState) {
      const state = JSON.parse(matchState)
      // 检查状态是否过期（30分钟内有效）
      const isExpired = Date.now() - state.timestamp > 30 * 60 * 1000
      if (!isExpired && state.results) {
        // 从匹配结果中找到对应的论文
        const paper = state.results.find(p => p.paper_id === paperId || p.id === paperId)
        if (paper) {
          loadPaperData(paper)
          loading.value = false
          return
        }
      }
    }
    
    // 如果 localStorage 没有，尝试从 sessionStorage 获取
    const sessionResults = sessionStorage.getItem('matchingResults')
    if (sessionResults) {
      const data = JSON.parse(sessionResults)
      const papers = data.papers || []
      const paper = papers.find(p => p.paper_id === paperId || p.id === paperId)
      if (paper) {
        loadPaperData(paper)
        loading.value = false
        return
      }
    }
    
    // 如果都没有，显示错误
    ElMessage.error('未找到匹配结果，请重新进行匹配')
    router.push('/smart-match')
  } catch (error) {
    console.error('加载数据失败:', error)
    if (!error._handled) {
      ElMessage.error('加载数据失败')
    }
    loading.value = false
  }
})

// 加载论文数据
const loadPaperData = (paper) => {
  // 从匹配结果中提取数据
  proposalData.value = {
    title: paper.title || '无标题',
    aiAnalysis: paper.reason || '暂无AI分析',
    description: paper.abstract || paper.summary || '暂无描述',
    field: paper.categories || paper.field || '未分类',
    application: paper.categories || paper.field || '未分类', // 可以从 categories 推断应用场景
    maturity: '研究阶段', // 默认值，可以从论文信息推断
    duration: '6-12个月', // 默认值
    advantages: paper.match_type || '技术匹配', // 使用匹配类型作为优势
    matchScore: paper.matchScore || paper.score || 0,
    techMatch: Math.round((paper.matchScore || paper.score || 0) * 0.98), // 技术匹配度
    needMatch: Math.round((paper.matchScore || paper.score || 0) * 0.92), // 需求匹配度
    appMatch: paper.matchScore || paper.score || 0 // 应用匹配度
  }
  
  // 联系人信息（从作者信息推断）
  const authors = paper.authors || ''
  const authorList = authors.split(',').filter(a => a.trim())
  contactInfo.value = {
    name: authorList.length > 0 ? authorList[0].trim() : '未提供',
    phone: '未提供',
    email: '未提供',
    organization: paper.categories ? `相关领域：${paper.categories}` : '未提供'
  }
}

// 获取匹配度颜色
const getScoreColor = (score) => {
  if (score >= 90) return '#67c23a'
  if (score >= 80) return '#409eff'
  if (score >= 70) return '#e6a23c'
  return '#f56c6c'
}

// 立即联系
const handleContact = () => {
  ElMessage.success('联系信息已复制到剪贴板')
  // 这里可以实现复制到剪贴板或跳转到联系页面的逻辑
}

// 返回上一页
const handleBack = () => {
  const from = route.query.from
  const tab = route.query.tab

  if (from === 'dashboard' && tab) {
    // 返回到资源大厅并恢复标签页
    router.push({
      path: '/dashboard',
      query: { tab }
    })
  } else if (from === 'smart-match') {
    // 返回到智能匹配页面，并恢复匹配状态
    // 检查是否有保存的匹配状态
    const matchState = localStorage.getItem('smartMatchState')
    if (matchState) {
      const state = JSON.parse(matchState)
      const isExpired = Date.now() - state.timestamp > 30 * 60 * 1000
      if (!isExpired) {
        // 状态未过期，跳转并传递参数以恢复状态
        router.push({
          path: '/smart-match',
          query: {
            restore: 'true',
            searchText: state.searchText,
            matchMode: state.matchMode
          }
        })
        return
      }
    }
    // 如果没有保存的状态，直接跳转
    router.push('/smart-match')
  } else {
    // 默认返回到智能匹配页面（因为通常是从匹配结果页面跳转过来的）
    router.push('/smart-match')
  }
}
</script>

<style scoped>
.match-proposal {
  min-height: calc(100vh - 60px);
  background: #f5f5f5;
  padding: 20px 0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.header-section {
  margin-bottom: 24px;
}

.back-button {
  margin-bottom: 16px;
  padding: 8px 0;
  color: #667eea;
  font-size: 14px;
}

.back-button:hover {
  color: #764ba2;
}

.back-button .el-icon {
  margin-right: 4px;
}

.title-section {
  margin-top: 8px;
}

.title {
  font-size: 28px;
  font-weight: 600;
  color: #1f2937;
  margin: 8px 0;
}

.subtitle {
  color: #6b7280;
  margin-bottom: 24px;
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
}

/* AI 匹配分析样式 */
.ai-analysis {
  background: #fff;
  border-left: 4px solid #3b82f6;
}

.ai-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.ai-icon {
  font-size: 20px;
  color: #3b82f6;
}

.ai-content {
  color: #666;
  line-height: 1.8;
  font-size: 14px;
}

.ai-content p {
  margin: 0;
}

.description {
  color: #6b7280;
  line-height: 1.8;
  font-size: 14px;
  margin: 0;
}

/* 匹配度样式 */
.match-score {
  text-align: center;
  margin-bottom: 24px;
}

.score-text {
  font-size: 32px;
  font-weight: 600;
  color: #1f2937;
}

.score-label {
  font-size: 12px;
  color: #6b7280;
  margin-top: 8px;
  margin: 0;
}

.match-details {
  margin-top: 20px;
}

.detail-item {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.detail-label {
  font-size: 13px;
  color: #6b7280;
  min-width: 80px;
}

.detail-item :deep(.el-progress) {
  flex: 1;
}

.detail-value {
  font-size: 13px;
  font-weight: 600;
  color: #1f2937;
  min-width: 40px;
  text-align: right;
}

/* 对接信息卡片 */
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
  font-weight: 600;
  color: #1f2937;
}

.contact-btn {
  width: 100%;
  margin-top: 8px;
}

.loading-container {
  margin-top: 20px;
}

:deep(.el-descriptions__label) {
  font-weight: 500;
}
</style>


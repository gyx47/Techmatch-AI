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
          <h1 class="title">{{ proposalData.title }}</h1>
          <p class="subtitle">合作方案详情</p>
        </div>
      </div>

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
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { MagicStick, User, Phone, Message, OfficeBuilding, ArrowLeft } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

// Mock 提案数据
const proposalData = ref({
  title: '基于深度学习的智能图像识别系统',
  aiAnalysis: '根据您的需求，该项目在核心算法上高度契合。该成果采用的卷积神经网络(CNN)和Transformer架构，与您提出的"高精度图像分类"需求完美匹配。系统在医疗影像分析、工业质检等场景的应用经验，能够直接满足您的应用场景要求。技术成熟度达到产业化水平，预期合作周期合理，建议优先对接。',
  description: '本项目开发了一套基于深度学习的智能图像识别系统，采用先进的卷积神经网络(CNN)和Transformer架构，实现了高精度的图像分类和目标检测功能。系统支持多场景应用，包括医疗影像分析、工业质检、自动驾驶等领域。经过大量实验验证，系统准确率达到98.5%，处理速度相比传统方法提升40%。该技术已申请多项发明专利，具备完整的知识产权保护。',
  field: '人工智能/计算机视觉',
  application: '医疗影像、工业质检、自动驾驶',
  maturity: '产业化阶段',
  duration: '6-12个月',
  advantages: '高准确率、快速处理、多场景适配、完整知识产权',
  matchScore: 95,
  techMatch: 98,
  needMatch: 92,
  appMatch: 95
})

// Mock 联系人信息
const contactInfo = ref({
  name: '张教授',
  phone: '138-0000-1234',
  email: 'zhang.prof@ai-lab.edu.cn',
  organization: 'XX大学人工智能研究院'
})

// 根据路由参数加载数据
onMounted(() => {
  const id = route.params.id
  // 这里可以根据 id 从 API 加载数据
  // 目前使用 Mock 数据
})

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
    // 返回到智能匹配页面
    router.push('/smart-match')
  } else {
    // 默认返回到资源大厅
    router.push('/dashboard')
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

:deep(.el-descriptions__label) {
  font-weight: 500;
}
</style>


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

              <!-- 生成详细合作报告按钮 -->
              <div class="generate-report-section">
                <el-button 
                  type="primary" 
                  size="large" 
                  @click="generateDetailedCooperationReport"
                  :loading="generatingReport"
                  class="report-button"
                >
                  <el-icon><Document /></el-icon>
                  生成详细合作建议
                </el-button>
                <p class="report-tip">AI将生成包含合作建议、周期规划、风险分析等详细报告</p>
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

    <!-- 详细合作报告弹窗 -->
    <el-dialog
      v-model="showReportDialog"
      title="AI详细合作建议报告"
      width="900px"
      :fullscreen="isFullscreen"
      :lock-scroll="false"
      custom-class="cooperation-report-dialog"
    >
      <!-- 报告加载状态 -->
      <div v-if="generatingReport" class="report-generating">
        <div class="generating-content">
          <el-icon class="generating-icon"><Loading /></el-icon>
          <h3>正在生成详细合作报告...</h3>
          <p>AI正在分析需求并生成详细的合作建议，请稍候</p>
          <el-progress 
            :percentage="progressPercentage" 
            :status="progressStatus"
            :stroke-width="8"
          />
          <p class="progress-text">{{ progressText }}</p>
        </div>
      </div>

      <!-- 报告内容 -->
      <div v-else-if="reportData" class="report-content">
        <!-- 报告头部 -->
        <div class="report-header">
          <h2 class="report-title">
            <el-icon><Document /></el-icon>
            需求合作分析报告
          </h2>
          <div class="report-meta">
            <span class="meta-item">生成时间: {{ formatDateTime(reportData.generated_at) }}</span>
            <el-button 
              type="text" 
              size="small" 
              @click="toggleFullscreen"
              class="fullscreen-btn"
            >
              <el-icon><FullScreen /></el-icon>
              {{ isFullscreen ? '退出全屏' : '全屏' }}
            </el-button>
          </div>
        </div>

        <!-- 报告正文 -->
        <div class="report-body">
          <!-- 1. 项目概述 -->
          <div class="report-section">
            <h3 class="section-title">
              <el-icon><InfoFilled /></el-icon>
              项目概述
            </h3>
            <div class="section-content">
              <div class="overview-grid">
                <div class="overview-item">
                  <span class="overview-label">需求标题</span>
                  <span class="overview-value">{{ requirementData.title }}</span>
                </div>
                <div class="overview-item">
                  <span class="overview-label">所属行业</span>
                  <span class="overview-value">{{ requirementData.industry }}</span>
                </div>
                <div class="overview-item">
                  <span class="overview-label">合作潜力评分</span>
                  <div class="overview-score">
                    <span class="score-value">{{ reportData.overall_score || 0 }}</span>
                    <span class="score-label">分</span>
                  </div>
                </div>
                <div class="overview-item">
                  <span class="overview-label">建议合作类型</span>
                  <el-tag :type="getCooperationTypeTag(reportData.cooperation_type)">
                    {{ reportData.cooperation_type }}
                  </el-tag>
                </div>
              </div>
            </div>
          </div>

          <!-- 2. 详细需求分析 -->
          <div class="report-section">
            <h3 class="section-title">
              <el-icon><Search /></el-icon>
              详细需求分析
            </h3>
            <div class="section-content">
              <div class="analysis-content">
                <h4>核心需求解读</h4>
                <p>{{ reportData.detailed_analysis || '暂无详细分析' }}</p>
                
                <h4>技术需求要点</h4>
                <div class="bullet-list">
                  <div v-for="(point, index) in reportData.technical_points" 
                       :key="index" 
                       class="bullet-item">
                    <el-icon><Check /></el-icon>
                    <span>{{ point }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 3. 痛点深度剖析 -->
          <div class="report-section">
            <h3 class="section-title">
              <el-icon><Warning /></el-icon>
              痛点深度剖析
            </h3>
            <div class="section-content">
              <div class="pain-points-detail">
                <div v-for="(point, index) in reportData.pain_points_detail" 
                     :key="index" 
                     class="pain-point-item">
                  <div class="pain-point-header">
                    <span class="pain-point-title">{{ point.title }}</span>
                    <el-tag size="small" :type="getSeverityTag(point.severity)">
                      严重程度: {{ point.severity }}
                    </el-tag>
                  </div>
                  <p class="pain-point-desc">{{ point.description }}</p>
                  <div class="pain-point-impact">
                    <strong>影响范围:</strong> {{ point.impact }}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 4. AI推荐理由 -->
          <div class="report-section">
            <h3 class="section-title">
              <el-icon><Star /></el-icon>
              AI推荐理由
            </h3>
            <div class="section-content">
              <div class="recommendation-section">
                <div class="recommendation-scores">
                  <div class="score-item">
                    <div class="score-circle" :style="{ background: getScoreColor(reportData.technical_score || 0) }">
                      {{ reportData.technical_score || 0 }}
                    </div>
                    <span class="score-label">技术匹配度</span>
                  </div>
                  <div class="score-item">
                    <div class="score-circle" :style="{ background: getScoreColor(reportData.business_score || 0) }">
                      {{ reportData.business_score || 0 }}
                    </div>
                    <span class="score-label">商业价值</span>
                  </div>
                  <div class="score-item">
                    <div class="score-circle" :style="{ background: getScoreColor(reportData.implementation_score || 0) }">
                      {{ reportData.implementation_score || 0 }}
                    </div>
                    <span class="score-label">实施可行性</span>
                  </div>
                </div>
                
                <div class="recommendation-text">
                  <h4>详细推荐分析</h4>
                  <p>{{ reportData.recommendation_analysis || reportData.reason }}</p>
                </div>
              </div>
            </div>
          </div>

          <!-- 5. 合作建议 -->
          <div class="report-section">
            <h3 class="section-title">
              <el-icon><Briefcase /></el-icon>
              合作建议
            </h3>
            <div class="section-content">
              <div class="cooperation-suggestions">
                <div v-for="(suggestion, index) in reportData.cooperation_suggestions" 
                     :key="index" 
                     class="suggestion-item">
                  <div class="suggestion-header">
                    <span class="suggestion-number">建议{{ index + 1 }}</span>
                    <h4 class="suggestion-title">{{ suggestion.title }}</h4>
                  </div>
                  <p class="suggestion-content">{{ suggestion.content }}</p>
                  <div class="suggestion-details">
                    <div class="detail-row">
                      <span class="detail-label">优先级:</span>
                      <el-tag size="small" :type="getPriorityTag(suggestion.priority)">
                        {{ suggestion.priority }}
                      </el-tag>
                    </div>
                    <div class="detail-row">
                      <span class="detail-label">预计耗时:</span>
                      <span class="detail-value">{{ suggestion.estimated_time }}</span>
                    </div>
                    <div class="detail-row">
                      <span class="detail-label">所需资源:</span>
                      <span class="detail-value">{{ suggestion.resource_requirements }}</span>
                    </div>
                    <div class="detail-row">
                      <span class="detail-label">预期成果:</span>
                      <span class="detail-value">{{ suggestion.expected_outcomes }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 6. 合作周期规划 -->
          <div class="report-section">
            <h3 class="section-title">
              <el-icon><Calendar /></el-icon>
              合作周期规划
            </h3>
            <div class="section-content">
              <div class="timeline">
                <div v-for="(phase, index) in reportData.cooperation_phases" 
                     :key="index" 
                     class="phase-item">
                  <div class="phase-header">
                    <div class="phase-marker">
                      <span class="phase-number">阶段{{ index + 1 }}</span>
                    </div>
                    <div class="phase-info">
                      <h4 class="phase-name">{{ phase.name }}</h4>
                      <div class="phase-meta">
                        <span class="phase-duration">{{ phase.duration }}</span>
                        <span class="phase-budget">预算: {{ phase.budget }}</span>
                      </div>
                    </div>
                  </div>
                  <div class="phase-content">
                    <div class="phase-tasks">
                      <h5>关键任务</h5>
                      <ul>
                        <li v-for="(task, taskIndex) in phase.key_tasks" 
                            :key="taskIndex">{{ task }}</li>
                      </ul>
                    </div>
                    <div class="phase-outcomes">
                      <h5>预期成果</h5>
                      <p>{{ phase.expected_outcomes }}</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 7. 风险分析与应对 -->
          <div class="report-section">
            <h3 class="section-title">
              <el-icon><Flag /></el-icon>
              风险分析与应对
            </h3>
            <div class="section-content">
              <div class="risk-analysis">
                <div v-for="(risk, index) in reportData.risk_analysis" 
                     :key="index" 
                     class="risk-item">
                  <div class="risk-header">
                    <span class="risk-type">{{ risk.type }}</span>
                    <div class="risk-tags">
                      <el-tag size="small" :type="getRiskLevelTag(risk.level)">
                        风险等级: {{ risk.level }}
                      </el-tag>
                      <span class="risk-probability">发生概率: {{ risk.probability }}</span>
                    </div>
                  </div>
                  <p class="risk-description">{{ risk.description }}</p>
                  <div class="risk-mitigation">
                    <strong>应对措施:</strong>
                    <p>{{ risk.mitigation_strategy }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 8. 财务分析 -->
          <div class="report-section" v-if="reportData.financial_analysis">
            <h3 class="section-title">
              <el-icon><Money /></el-icon>
              财务分析
            </h3>
            <div class="section-content">
              <div class="financial-analysis">
                <div class="financial-metrics">
                  <div class="metric-item">
                    <span class="metric-label">总投资预算</span>
                    <span class="metric-value">{{ reportData.financial_analysis.total_budget }}</span>
                  </div>
                  <div class="metric-item">
                    <span class="metric-label">预计ROI</span>
                    <span class="metric-value">{{ reportData.financial_analysis.roi_estimate }}</span>
                  </div>
                  <div class="metric-item">
                    <span class="metric-label">回本周期</span>
                    <span class="metric-value">{{ reportData.financial_analysis.payback_period }}</span>
                  </div>
                  <div class="metric-item">
                    <span class="metric-label">成功概率</span>
                    <span class="metric-value">{{ reportData.financial_analysis.success_probability }}</span>
                  </div>
                </div>
                <div class="financial-note">
                  <p>{{ reportData.financial_analysis.note }}</p>
                </div>
              </div>
            </div>
          </div>

          <!-- 9. 下一步行动 -->
          <div class="report-section">
            <h3 class="section-title">
              <el-icon><Promotion /></el-icon>
              下一步行动
            </h3>
            <div class="section-content">
              <div class="next-steps">
                <div v-for="(step, index) in reportData.next_steps" 
                     :key="index" 
                     class="step-item">
                  <div class="step-header">
                    <span class="step-number">{{ index + 1 }}</span>
                    <span class="step-title">{{ step.title }}</span>
                  </div>
                  <p class="step-desc">{{ step.description }}</p>
                  <div class="step-details">
                    <span class="step-time">建议时间: {{ step.suggested_time }}</span>
                    <span class="step-resource">所需资源: {{ step.resource_needed }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 报告底部 -->
        <div class="report-footer">
          <div class="footer-actions">
            <el-button type="primary" @click="downloadReport">
              <el-icon><Download /></el-icon>
              下载报告
            </el-button>
            <el-button type="success" @click="handleContact">
              <el-icon><Message /></el-icon>
              联系需求方
            </el-button>
          </div>
          <p class="report-disclaimer">
            注：本报告由AI生成，仅供参考。实际合作请根据具体情况调整。
          </p>
        </div>
      </div>

      <template #footer v-if="!generatingReport">
        <el-button @click="showReportDialog = false">关闭报告</el-button>
        <el-button type="primary" @click="generateDetailedCooperationReport" :loading="generatingReport">
          <el-icon><Refresh /></el-icon>
          重新生成
        </el-button>
      </template>
    </el-dialog>

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
  Document,
  Loading,
  FullScreen,
  Download,
  Share,
  Refresh,
  InfoFilled,
  Search,
  Warning,
  Star,
  Briefcase,
  Flag,
  Money,
  Promotion,
  Check 
} from '@element-plus/icons-vue'
import api from '../api'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const loading = ref(true)
const requirementData = ref({})
const paperInfo = ref(null)

// 报告相关状态
const generatingReport = ref(false)
const showReportDialog = ref(false)
const isFullscreen = ref(false)
const reportData = ref(null)
const progressPercentage = ref(0)
const progressText = ref('正在初始化...')
const progressStatus = ref('')

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
      
      // 从路由query参数中获取匹配相关信息（这些信息来自SmartMatch页面）
      if (route.query.match_score) {
        requirementData.value.score = parseFloat(route.query.match_score)
      }
      if (route.query.reason) {
        requirementData.value.reason = route.query.reason
      }
      if (route.query.match_type) {
        requirementData.value.match_type = route.query.match_type
      }
      if (route.query.implementation_suggestion) {
        requirementData.value.implementation_suggestion = route.query.implementation_suggestion
      }
      if (route.query.vector_score) {
        requirementData.value.vector_score = parseFloat(route.query.vector_score)
      }
      console.log('需求分数', requirementData.value.score)

      // 如果路由参数中已经有reason等字段，就不需要再调用API生成了（避免加载慢）
      // 只有在确实没有这些信息时才生成
      if (!requirementData.value.reason && route.query.search_text) {
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
    if (!error._handled) {
      ElMessage.error('加载需求详情失败: ' + (error.response?.data?.detail || error.message))
    }
    
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

// 生成详细合作报告
const generateDetailedCooperationReport = async () => {
  if (!userStore.isLoggedIn) {
    ElMessage.warning('请先登录后再生成详细报告')
    router.push('/login')
    return
  }
  
  // 打开对话框
  showReportDialog.value = true
  generatingReport.value = true
  progressPercentage.value = 10
  progressText.value = '准备生成报告...'
  
  try {
    // 1. 准备报告数据
    progressPercentage.value = 20
    progressText.value = '分析需求信息...'
    
    const reportRequest = {
      requirement_data: {
        requirement_id: requirementData.value.requirement_id || route.params.id,
        title: requirementData.value.title,
        description: requirementData.value.description,
        industry: requirementData.value.industry,
        technical_level: requirementData.value.technical_level,
        market_size: requirementData.value.market_size,
        pain_points: requirementData.value.pain_points,
        // 如果有匹配信息，也包含进去
        match_score: requirementData.value.score,
        match_type: requirementData.value.match_type,
        match_reason: requirementData.value.reason,
        // 如果有论文信息
        paper_title: route.query.paper_title || '',
        paper_abstract: route.query.paper_abstract || ''
      },
      user_input: route.query.search_text || '',
      report_type: 'detailed_cooperation'
    }
    
    // 2. 调用后端API生成报告
    progressPercentage.value = 40
    progressText.value = '调用AI进行深度分析...'
    
    const response = await api.post('/requirements/generate-detailed-report', reportRequest, {
      timeout: 120000 // 2分钟超时
    })
    
    if (response.data.success) {
      progressPercentage.value = 80
      progressText.value = '处理分析结果...'
      
      // 处理报告数据
      reportData.value = {
        ...response.data.report,
        generated_at: new Date().toISOString()
      }
      
      // 模拟进度完成
      setTimeout(() => {
        progressPercentage.value = 100
        progressText.value = '报告生成完成！'
        progressStatus.value = 'success'
        
        setTimeout(() => {
          generatingReport.value = false
          ElMessage.success('详细合作报告生成成功！')
        }, 500)
      }, 1000)
      
    } else {
      throw new Error(response.data.message || '报告生成失败')
    }
    
  } catch (error) {
    console.error('生成详细合作报告失败:', error)
    generatingReport.value = false
    ElMessage.error(`生成报告失败: ${error.message || '未知错误'}`)
    
    // 如果API调用失败，使用模拟数据展示（用于演示）
    if (error.code === 'ECONNREFUSED' || error.response?.status === 404) {
      ElMessage.warning('使用演示数据展示报告结构')
      generateDemoReport()
    }
  }
}

// 生成演示报告（当后端API不可用时）
const generateDemoReport = () => {
  reportData.value = {
    generated_at: new Date().toISOString(),
    overall_score: 78,
    cooperation_type: '技术开发与咨询',
    detailed_analysis: '该需求针对人工智能行业在决策支持方面的挑战，寻求能够处理大规模数据、支持实时分析的技术解决方案。核心技术需求包括数据处理能力、算法优化、系统集成等。',
    technical_points: [
      '大数据处理与实时分析能力',
      '机器学习算法优化',
      '系统架构设计与集成',
      '安全性与可扩展性保障',
      '用户友好的交互界面'
    ],
    pain_points_detail: [
      {
        title: '系统集成困难',
        severity: '高',
        description: '不同平台数据无法互通，导致信息孤岛',
        impact: '影响整体业务流程效率，增加运维成本'
      },
      {
        title: '技术更新快速',
        severity: '中',
        description: '现有系统难以跟上人工智能技术发展节奏',
        impact: '技术落后，竞争力下降'
      }
    ],
    technical_score: 82,
    business_score: 75,
    implementation_score: 70,
    recommendation_analysis: '该需求与人工智能技术高度相关，技术方案成熟度较高。商业价值显著，可提升业务效率78%，降低运营成本21%。实施难度中等，建议分阶段推进。',
    cooperation_suggestions: [
      {
        title: '技术方案设计',
        content: '设计完整的技术架构和实施方案',
        priority: '高',
        estimated_time: '2-3周',
        resource_requirements: '技术架构师1名，AI工程师2名',
        expected_outcomes: '完整的技术方案文档'
      },
      {
        title: '原型开发',
        content: '开发最小可行产品(MVP)验证技术路线',
        priority: '高',
        estimated_time: '4-6周',
        resource_requirements: '开发团队3-5人',
        expected_outcomes: '可演示的原型系统'
      }
    ],
    cooperation_phases: [
      {
        name: '需求分析与设计',
        duration: '3-4周',
        budget: '5-10万',
        key_tasks: ['需求细化', '技术选型', '方案设计', '资源规划'],
        expected_outcomes: '详细需求文档和技术方案'
      },
      {
        name: '系统开发',
        duration: '8-12周',
        budget: '20-40万',
        key_tasks: ['核心功能开发', '系统集成', '单元测试', '性能优化'],
        expected_outcomes: '完整可用的系统版本'
      }
    ],
    risk_analysis: [
      {
        type: '技术风险',
        level: '中',
        probability: '30%',
        description: '技术实现难度高于预期',
        mitigation_strategy: '预留技术缓冲时间，准备备选技术方案'
      },
      {
        type: '市场风险',
        level: '低',
        probability: '15%',
        description: '市场需求变化导致项目价值降低',
        mitigation_strategy: '持续市场调研，保持方案灵活性'
      }
    ],
    financial_analysis: {
      total_budget: '25-50万',
      roi_estimate: '投资回报率预计150-200%',
      payback_period: '6-12个月',
      success_probability: '75%',
      note: '预算为初步估算，实际费用可能根据具体需求调整'
    },
    next_steps: [
      {
        title: '初步沟通',
        description: '与需求方进行初步技术沟通，明确具体需求',
        suggested_time: '1周内',
        resource_needed: '技术顾问1名'
      },
      {
        title: '方案细化',
        description: '基于沟通结果细化技术方案和报价',
        suggested_time: '2周内',
        resource_needed: '技术团队'
      }
    ]
  }
  
  generatingReport.value = false
}

// 切换全屏
const toggleFullscreen = () => {
  isFullscreen.value = !isFullscreen.value
}

// 下载报告
const downloadReport = () => {
  try {
    const reportContent = generateReportText()
    const blob = new Blob([reportContent], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `合作报告-${requirementData.value.title}-${new Date().toISOString().split('T')[0]}.txt`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
    
    ElMessage.success('报告下载成功')
  } catch (error) {
    console.error('下载报告失败:', error)
    ElMessage.error('下载报告失败')
  }
}

// 生成报告文本
const generateReportText = () => {
  if (!reportData.value) return ''
  
  const data = reportData.value
  const req = requirementData.value
  
  let text = '='.repeat(60) + '\n'
  text += '            AI详细合作分析报告\n'
  text += '='.repeat(60) + '\n\n'
  
  text += `报告生成时间: ${formatDateTime(data.generated_at)}\n`
  text += `需求标题: ${req.title}\n`
  text += `需求行业: ${req.industry}\n`
  text += `技术难度: ${req.technical_level}\n`
  text += `市场规模: ${req.market_size}\n`
  text += `\n${'='.repeat(60)}\n\n`
  
  // 项目概述
  text += '一、项目概述\n'
  text += '─'.repeat(30) + '\n'
  text += `合作潜力评分: ${data.overall_score || 0}/100\n`
  text += `建议合作类型: ${data.cooperation_type}\n\n`
  
  // 详细需求分析
  text += '二、详细需求分析\n'
  text += '─'.repeat(30) + '\n'
  text += `${data.detailed_analysis || '暂无详细分析'}\n\n`
  
  if (data.technical_points && data.technical_points.length > 0) {
    text += '技术需求要点:\n'
    data.technical_points.forEach((point, index) => {
      text += `  ${index + 1}. ${point}\n`
    })
    text += '\n'
  }
  
  // 痛点剖析
  text += '三、痛点深度剖析\n'
  text += '─'.repeat(30) + '\n'
  if (data.pain_points_detail && data.pain_points_detail.length > 0) {
    data.pain_points_detail.forEach((point, index) => {
      text += `${index + 1}. ${point.title} [${point.severity}]\n`
      text += `   描述: ${point.description}\n`
      text += `   影响: ${point.impact}\n\n`
    })
  }
  
  // AI推荐理由
  text += '四、AI推荐理由\n'
  text += '─'.repeat(30) + '\n'
  text += `技术匹配度: ${data.technical_score || 0}%\n`
  text += `商业价值: ${data.business_score || 0}%\n`
  text += `实施可行性: ${data.implementation_score || 0}%\n\n`
  text += `${data.recommendation_analysis || data.reason || ''}\n\n`
  
  // 合作建议
  text += '五、合作建议\n'
  text += '─'.repeat(30) + '\n'
  if (data.cooperation_suggestions && data.cooperation_suggestions.length > 0) {
    data.cooperation_suggestions.forEach((suggestion, index) => {
      text += `建议${index + 1}: ${suggestion.title} [优先级: ${suggestion.priority}]\n`
      text += `内容: ${suggestion.content}\n`
      text += `预计耗时: ${suggestion.estimated_time}\n`
      text += `所需资源: ${suggestion.resource_requirements}\n`
      text += `预期成果: ${suggestion.expected_outcomes}\n\n`
    })
  }
  
  // 合作周期
  text += '六、合作周期规划\n'
  text += '─'.repeat(30) + '\n'
  if (data.cooperation_phases && data.cooperation_phases.length > 0) {
    data.cooperation_phases.forEach((phase, index) => {
      text += `阶段${index + 1}: ${phase.name}\n`
      text += `持续时间: ${phase.duration}\n`
      text += `预算: ${phase.budget}\n`
      text += `关键任务:\n`
      phase.key_tasks.forEach(task => text += `  • ${task}\n`)
      text += `预期成果: ${phase.expected_outcomes}\n\n`
    })
  }
  
  // 风险分析
  text += '七、风险分析与应对\n'
  text += '─'.repeat(30) + '\n'
  if (data.risk_analysis && data.risk_analysis.length > 0) {
    data.risk_analysis.forEach((risk, index) => {
      text += `${index + 1}. ${risk.type} [等级: ${risk.level}, 概率: ${risk.probability}]\n`
      text += `描述: ${risk.description}\n`
      text += `应对措施: ${risk.mitigation_strategy}\n\n`
    })
  }
  
  // 财务分析
  if (data.financial_analysis) {
    text += '八、财务分析\n'
    text += '─'.repeat(30) + '\n'
    text += `总投资预算: ${data.financial_analysis.total_budget}\n`
    text += `预计ROI: ${data.financial_analysis.roi_estimate}\n`
    text += `回本周期: ${data.financial_analysis.payback_period}\n`
    text += `成功概率: ${data.financial_analysis.success_probability}\n`
    text += `备注: ${data.financial_analysis.note}\n\n`
  }
  
  // 下一步行动
  text += '九、下一步行动建议\n'
  text += '─'.repeat(30) + '\n'
  if (data.next_steps && data.next_steps.length > 0) {
    data.next_steps.forEach((step, index) => {
      text += `${index + 1}. ${step.title}\n`
      text += `描述: ${step.description}\n`
      text += `建议时间: ${step.suggested_time}\n`
      text += `所需资源: ${step.resource_needed}\n\n`
    })
  }
  
  text += '\n' + '='.repeat(60) + '\n'
  text += '注：本报告由AI生成，仅供参考。实际合作请根据具体情况调整。\n'
  text += '='.repeat(60)
  
  return text
}

// 辅助函数
const formatDateTime = (dateStr) => {
  if (!dateStr) return '未知'
  try {
    const date = new Date(dateStr)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch (e) {
    return dateStr
  }
}

const getCooperationTypeTag = (type) => {
  const map = {
    '技术开发': 'primary',
    '技术咨询': 'success',
    '联合研发': 'warning',
    '成果转化': 'info',
    '人才培养': '',
    '技术开发与咨询': 'primary'
  }
  return map[type] || 'info'
}

const getSeverityTag = (severity) => {
  const map = {
    '高': 'danger',
    '中': 'warning',
    '低': 'success'
  }
  return map[severity] || 'info'
}

const getPriorityTag = (priority) => {
  const map = {
    '高': 'danger',
    '中': 'warning',
    '低': 'success'
  }
  return map[priority] || 'info'
}

const getRiskLevelTag = (level) => {
  const map = {
    '高': 'danger',
    '中': 'warning',
    '低': 'success'
  }
  return map[level] || 'info'
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

.description {
  color: #666;
  line-height: 1.8;
  font-size: 14px;
  margin: 0;
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

/* 生成报告按钮区域 */
.generate-report-section {
  margin-top: 25px;
  padding-top: 20px;
  border-top: 1px solid #eee;
  text-align: center;
}

.report-button {
  width: 100%;
  margin-bottom: 10px;
}

.report-tip {
  font-size: 13px;
  color: #666;
  margin: 0;
}

/* 报告弹窗样式 */
:deep(.cooperation-report-dialog) {
  border-radius: 12px;
  overflow: hidden;
}

:deep(.cooperation-report-dialog .el-dialog__header) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  margin-right: 0;
  padding: 20px;
}

:deep(.cooperation-report-dialog .el-dialog__title) {
  color: white;
  font-size: 18px;
  font-weight: 600;
}

:deep(.cooperation-report-dialog .el-dialog__headerbtn) {
  color: white;
}

:deep(.cooperation-report-dialog .el-dialog__headerbtn:hover .el-dialog__close) {
  color: #ffd04b;
}

:deep(.cooperation-report-dialog .el-dialog__body) {
  padding: 0;
  max-height: calc(100vh - 200px);
  overflow-y: auto;
}

/* 报告生成中状态 */
.report-generating {
  padding: 60px 20px;
  text-align: center;
}

.generating-content {
  max-width: 500px;
  margin: 0 auto;
}

.generating-icon {
  font-size: 60px;
  color: #667eea;
  margin-bottom: 20px;
  animation: rotate 2s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.generating-content h3 {
  margin: 20px 0 10px;
  color: #1f2937;
}

.generating-content p {
  color: #666;
  margin-bottom: 30px;
}

.progress-text {
  margin-top: 10px;
  font-size: 14px;
  color: #667eea;
}

/* 报告内容 */
.report-content {
  padding: 30px;
}

.report-header {
  margin-bottom: 30px;
  padding-bottom: 20px;
  border-bottom: 2px solid #667eea;
}

.report-title {
  font-size: 24px;
  font-weight: 600;
  color: #1f2937;
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0;
}

.report-meta {
  margin-top: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.meta-item {
  font-size: 14px;
  color: #666;
}

.fullscreen-btn {
  margin-left: auto;
}

/* 报告正文 */
.report-body {
  margin-bottom: 30px;
}

.report-section {
  margin-bottom: 25px;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  overflow: hidden;
}

.section-title {
  background: #f8fafc;
  padding: 15px 20px;
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  display: flex;
  align-items: center;
  gap: 10px;
  border-bottom: 1px solid #e5e7eb;
}

.section-title .el-icon {
  color: #667eea;
}

.section-content {
  padding: 20px;
}

/* 项目概述 */
.overview-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 15px;
}

.overview-item {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.overview-label {
  font-size: 13px;
  color: #666;
}

.overview-value {
  font-size: 15px;
  font-weight: 500;
  color: #1f2937;
}

.overview-score {
  display: flex;
  align-items: baseline;
  gap: 2px;
}

.score-value {
  font-size: 24px;
  font-weight: 600;
  color: #667eea;
}

.score-label {
  font-size: 14px;
  color: #666;
}

/* 详细需求分析 */
.analysis-content h4 {
  margin: 15px 0 10px;
  color: #374151;
  font-size: 15px;
}

.analysis-content p {
  line-height: 1.6;
  color: #4b5563;
  margin: 0;
}

.bullet-list {
  margin: 15px 0;
}

.bullet-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 10px;
  color: #4b5563;
}

.bullet-item .el-icon {
  color: #67c23a;
  margin-top: 2px;
  flex-shrink: 0;
}

/* 痛点剖析 */
.pain-points-detail {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.pain-point-item {
  padding: 15px;
  background: #f9fafb;
  border-radius: 6px;
  border-left: 4px solid #f56c6c;
}

.pain-point-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.pain-point-title {
  font-weight: 600;
  color: #1f2937;
}

.pain-point-desc {
  line-height: 1.6;
  color: #4b5563;
  margin: 8px 0;
}

.pain-point-impact {
  font-size: 14px;
  color: #dc2626;
}

/* AI推荐理由 */
.recommendation-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.recommendation-scores {
  display: flex;
  justify-content: space-around;
  gap: 20px;
}

.score-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.score-circle {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 18px;
  font-weight: 600;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.score-label {
  font-size: 14px;
  color: #666;
}

.recommendation-text h4 {
  margin: 0 0 10px;
  color: #374151;
}

.recommendation-text p {
  line-height: 1.8;
  color: #4b5563;
}

/* 合作建议 */
.cooperation-suggestions {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.suggestion-item {
  padding: 15px;
  background: #f9fafb;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.suggestion-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.suggestion-number {
  background: #667eea;
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.suggestion-title {
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
}

.suggestion-content {
  line-height: 1.6;
  color: #4b5563;
  margin: 10px 0;
}

.suggestion-details {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  font-size: 13px;
}

.detail-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.detail-label {
  color: #666;
  min-width: 60px;
}

.detail-value {
  color: #4b5563;
}

/* 合作周期 */
.timeline {
  position: relative;
  padding-left: 30px;
}

.timeline::before {
  content: '';
  position: absolute;
  left: 10px;
  top: 0;
  bottom: 0;
  width: 2px;
  background: #667eea;
}

.phase-item {
  position: relative;
  margin-bottom: 25px;
}

.phase-item:last-child {
  margin-bottom: 0;
}

.phase-header {
  display: flex;
  align-items: flex-start;
  gap: 15px;
  margin-bottom: 15px;
}

.phase-marker {
  position: absolute;
  left: -30px;
  top: 0;
  width: 20px;
  height: 20px;
  background: #667eea;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.phase-number {
  color: white;
  font-size: 12px;
  font-weight: 600;
}

.phase-info {
  flex: 1;
}

.phase-name {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 5px 0;
}

.phase-meta {
  display: flex;
  gap: 15px;
  font-size: 14px;
  color: #666;
}

.phase-content {
  padding-left: 35px;
}

.phase-tasks h5,
.phase-outcomes h5 {
  margin: 10px 0 8px;
  color: #374151;
  font-size: 14px;
}

.phase-tasks ul {
  margin: 0 0 15px 0;
  padding-left: 20px;
  color: #4b5563;
}

.phase-tasks li {
  margin-bottom: 5px;
}

.phase-outcomes p {
  line-height: 1.6;
  color: #4b5563;
  margin: 0;
}

/* 风险分析 */
.risk-analysis {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.risk-item {
  padding: 15px;
  background: #f9fafb;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.risk-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.risk-type {
  font-weight: 600;
  color: #1f2937;
}

.risk-tags {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-left: auto;
}

.risk-probability {
  font-size: 13px;
  color: #666;
}

.risk-description {
  line-height: 1.6;
  color: #4b5563;
  margin: 8px 0;
}

.risk-mitigation {
  padding: 10px;
  background: #f0f9ff;
  border-radius: 6px;
  font-size: 14px;
  color: #0369a1;
}

.risk-mitigation strong {
  color: #1e40af;
}

/* 财务分析 */
.financial-analysis {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.financial-metrics {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 15px;
}

.metric-item {
  padding: 15px;
  background: white;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.metric-label {
  font-size: 13px;
  color: #666;
  margin-bottom: 5px;
}

.metric-value {
  font-size: 18px;
  font-weight: 600;
  color: #667eea;
}

.financial-note p {
  font-size: 13px;
  color: #666;
  font-style: italic;
  margin: 0;
  padding: 10px;
  background: #f9fafb;
  border-radius: 6px;
}

/* 下一步行动 */
.next-steps {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.step-item {
  padding: 15px;
  background: #f9fafb;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.step-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.step-number {
  width: 24px;
  height: 24px;
  background: #667eea;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}

.step-title {
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
}

.step-desc {
  line-height: 1.6;
  color: #4b5563;
  margin: 8px 0;
}

.step-details {
  display: flex;
  gap: 15px;
  font-size: 13px;
  color: #666;
}

/* 报告底部 */
.report-footer {
  padding-top: 20px;
  border-top: 1px solid #e5e7eb;
}

.footer-actions {
  display: flex;
  gap: 10px;
  justify-content: center;
  margin-bottom: 15px;
}

.report-disclaimer {
  text-align: center;
  font-size: 12px;
  color: #999;
  margin: 0;
  font-style: italic;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .overview-grid {
    grid-template-columns: 1fr;
  }
  
  .recommendation-scores {
    flex-direction: column;
    align-items: center;
  }
  
  .financial-metrics {
    grid-template-columns: 1fr;
  }
  
  .suggestion-details {
    grid-template-columns: 1fr;
  }
  
  :deep(.cooperation-report-dialog) {
    width: 95% !important;
    margin: 10px auto;
  }
  
  :deep(.cooperation-report-dialog .el-dialog__body) {
    max-height: calc(100vh - 150px);
  }
  
  .footer-actions {
    flex-direction: column;
  }
  
  .footer-actions .el-button {
    width: 100%;
  }
}
</style>
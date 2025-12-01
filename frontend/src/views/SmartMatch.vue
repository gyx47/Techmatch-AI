<template>
  <div class="smart-match">
    <!-- Hero Section 搜索区域 -->
    <div class="hero-section">
      <div class="hero-content">
        <h1 class="hero-title">成果需求智能匹配</h1>
        <p class="hero-subtitle">输入您的技术难题或成果描述，AI 将为您智能匹配最合适的合作伙伴</p>

        <div class="search-container">
          <el-input
            v-model="searchText"
            type="textarea"
            :rows="6"
            placeholder="请输入您的技术难题或成果描述..."
            class="search-textarea"
            :disabled="loading"
          />

          <div class="mode-selector">
            <el-radio-group v-model="matchMode" size="large">
              <el-radio-button label="enterprise">我是企业找成果</el-radio-button>
              <el-radio-button label="researcher">我是专家找需求</el-radio-button>
            </el-radio-group>
          </div>

          <el-button
            type="primary"
            size="large"
            class="match-button"
            :loading="loading"
            @click="startMatch"
          >
            <el-icon v-if="!loading"><Search /></el-icon>
            <span>{{ loading ? '匹配中...' : '开始智能匹配' }}</span>
          </el-button>
        </div>
      </div>
    </div>

    <!-- 匹配结果区域 -->
    <div class="results-section" v-if="showResults">
      <div class="container">
        <div class="results-header">
          <div>
            <h2 class="results-title">匹配结果</h2>
            <p class="results-subtitle">为您找到 {{ filteredResults.length }} 个匹配项</p>
          </div>
          <div class="action-buttons" v-if="selectedPapers.length > 0">
            <el-button 
              type="success" 
              size="large"
              :loading="generatingPath"
              @click="generateImplementationPath"
            >
              <el-icon><Document /></el-icon>
              生成实现路径 (已选 {{ selectedPapers.length }} 篇)
            </el-button>
            <el-button @click="clearSelection" size="large">
              清空选择
            </el-button>
          </div>
        </div>

        <el-row :gutter="24">
          <el-col :span="8" v-for="item in filteredResults" :key="item.id">
            <div class="paper-card" :class="{ 'selected': isPaperSelected(item.paper_id) }">
              <div class="card-checkbox-wrapper">
                <el-checkbox 
                  v-model="selectedPaperIds" 
                  :value="item.paper_id"
                  @change="handlePaperSelection(item.paper_id, $event)"
                  class="paper-checkbox"
                  size="large"
                />
              </div>
              <div class="card-content">
                <div class="card-header">
                  <h3 class="paper-title">{{ item.title }}</h3>
                </div>
                <div class="card-body">
                  <div class="summary-content" v-html="highlightKeywords(item.summary)"></div>
                  
                  <!-- 推荐理由 -->
                  <div class="reason-section" v-if="item.reason">
                    <div class="reason-label">
                      <el-icon><Lightbulb /></el-icon>
                      推荐理由
                    </div>
                    <div class="reason-text">{{ item.reason }}</div>
                  </div>
                  
                  <div class="confidence-section">
                    <div class="score-header">
                      <span class="score-label">匹配度</span>
                      <el-tag v-if="item.match_type" :type="getMatchTypeTagType(item.match_type)" size="small" effect="dark">
                        {{ item.match_type }}
                      </el-tag>
                    </div>
                    <el-progress
                      :percentage="item.matchScore"
                      :color="getScoreColor(item.matchScore)"
                      :stroke-width="8"
                      :status="item.matchScore >= 90 ? 'success' : item.matchScore >= 75 ? 'warning' : ''"
                      :show-text="true"
                      :format="(percentage) => `${percentage}%`"
                    />
                  </div>
                  
                  <div class="card-meta">
                    <el-tag v-if="item.type" :type="item.type === '成果' ? 'success' : 'primary'" size="small" effect="plain">
                      {{ item.type }}
                    </el-tag>
                    <span class="meta-item" v-if="item.field">
                      <el-icon><FolderOpened /></el-icon>
                      {{ item.field }}
                    </span>
                    <span class="meta-item" v-if="item.authors">
                      <el-icon><User /></el-icon>
                      {{ item.authors.split(',').slice(0, 2).join(',') }}{{ item.authors.split(',').length > 2 ? '等' : '' }}
                    </span>
                    <span class="meta-item" v-if="item.published_date">
                      <el-icon><Calendar /></el-icon>
                      {{ formatDate(item.published_date) }}
                    </span>
                  </div>
                </div>
                <div class="card-footer">
                  <el-button type="primary" size="default" @click="viewProposal(item.id)" plain>
                    <el-icon><Document /></el-icon>
                    查看方案
                  </el-button>
                  <el-button v-if="item.pdf_url" @click="openPdf(item.pdf_url)" link type="primary">
                    <el-icon><Document /></el-icon>
                    查看PDF
                  </el-button>
                </div>
              </div>
            </div>
          </el-col>
        </el-row>
      </div>
    </div>

    <!-- 实现路径对话框 -->
    <el-dialog
      v-model="showPathDialog"
      title="科研成果实现路径"
      width="80%"
      :close-on-click-modal="false"
      class="implementation-path-dialog"
    >
      <div v-if="pathLoading" class="path-loading">
        <el-skeleton :rows="10" animated />
      </div>
      <div v-else-if="implementationPath" class="path-content">
        <!-- 整体概述 -->
        <div class="path-section" v-if="implementationPath.overview">
          <h3>📋 整体概述</h3>
          <p>{{ implementationPath.overview }}</p>
        </div>

        <!-- 技术选型 -->
        <div class="path-section" v-if="implementationPath.technology_selection">
          <h3>🔧 技术选型</h3>
          <div class="tech-selection">
            <div v-if="implementationPath.technology_selection.primary_techniques">
              <strong>主要技术：</strong>
              <el-tag 
                v-for="tech in implementationPath.technology_selection.primary_techniques" 
                :key="tech"
                type="success"
                style="margin: 5px"
              >
                {{ tech }}
              </el-tag>
            </div>
            <p v-if="implementationPath.technology_selection.integration_strategy" style="margin-top: 10px">
              <strong>整合策略：</strong>{{ implementationPath.technology_selection.integration_strategy }}
            </p>
          </div>
        </div>

        <!-- 实施阶段 -->
        <div class="path-section" v-if="implementationPath.implementation_phases">
          <h3>📅 实施阶段</h3>
          <el-timeline>
            <el-timeline-item
              v-for="phase in implementationPath.implementation_phases"
              :key="phase.phase"
              :timestamp="phase.estimated_time"
              placement="top"
            >
              <el-card>
                <h4>{{ phase.name }}</h4>
                <div v-if="phase.objectives">
                  <strong>目标：</strong>
                  <ul>
                    <li v-for="obj in phase.objectives" :key="obj">{{ obj }}</li>
                  </ul>
                </div>
                <div v-if="phase.deliverables" style="margin-top: 10px">
                  <strong>交付物：</strong>
                  <ul>
                    <li v-for="del in phase.deliverables" :key="del">{{ del }}</li>
                  </ul>
                </div>
                <div v-if="phase.key_tasks" style="margin-top: 10px">
                  <strong>关键任务：</strong>
                  <el-tag 
                    v-for="task in phase.key_tasks" 
                    :key="task"
                    style="margin: 3px"
                  >
                    {{ task }}
                  </el-tag>
                </div>
              </el-card>
            </el-timeline-item>
          </el-timeline>
        </div>

        <!-- 风险评估 -->
        <div class="path-section" v-if="implementationPath.risk_assessment">
          <h3>⚠️ 风险评估</h3>
          <div class="risk-assessment">
            <div v-if="implementationPath.risk_assessment.technical_risks">
              <strong>技术风险：</strong>
              <ul>
                <li v-for="risk in implementationPath.risk_assessment.technical_risks" :key="risk">{{ risk }}</li>
              </ul>
            </div>
            <div v-if="implementationPath.risk_assessment.mitigation_strategies" style="margin-top: 10px">
              <strong>应对策略：</strong>
              <ul>
                <li v-for="strategy in implementationPath.risk_assessment.mitigation_strategies" :key="strategy">{{ strategy }}</li>
              </ul>
            </div>
          </div>
        </div>

        <!-- 成功标准 -->
        <div class="path-section" v-if="implementationPath.success_criteria">
          <h3>✅ 成功标准</h3>
          <ul>
            <li v-for="criteria in implementationPath.success_criteria" :key="criteria">{{ criteria }}</li>
          </ul>
        </div>

        <!-- 论文分析详情 -->
        <div class="path-section" v-if="papersAnalysis && papersAnalysis.length > 0">
          <h3>📄 论文分析详情</h3>
          <el-collapse>
            <el-collapse-item
              v-for="(paper, index) in papersAnalysis"
              :key="index"
              :title="paper.title"
            >
              <div v-if="paper.status === 'success' && paper.analysis">
                <div v-if="paper.analysis.core_techniques">
                  <strong>核心技术：</strong>
                  <el-tag 
                    v-for="tech in paper.analysis.core_techniques" 
                    :key="tech"
                    style="margin: 3px"
                  >
                    {{ tech }}
                  </el-tag>
                </div>
                <p v-if="paper.analysis.summary" style="margin-top: 10px">
                  <strong>总结：</strong>{{ paper.analysis.summary }}
                </p>
                <p v-if="paper.analysis.key_implementation_details" style="margin-top: 10px">
                  <strong>实现细节：</strong>{{ paper.analysis.key_implementation_details }}
                </p>
                <p v-if="paper.analysis.technical_advantages" style="margin-top: 10px">
                  <strong>技术优势：</strong>{{ paper.analysis.technical_advantages }}
                </p>
                <p v-if="paper.analysis.implementation_challenges" style="margin-top: 10px">
                  <strong>实现难点：</strong>{{ paper.analysis.implementation_challenges }}
                </p>
              </div>
              <div v-else>
                <el-alert :title="paper.error_message || '分析失败'" type="error" />
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
      </div>
      <div v-else-if="pathError" class="path-error">
        <el-alert :title="pathError" type="error" />
      </div>
      <template #footer>
        <el-button @click="showPathDialog = false">关闭</el-button>
        <el-button type="primary" @click="exportPath">导出路径</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '../stores/user'
import { ElMessage } from 'element-plus'
import { Search, FolderOpened, OfficeBuilding, User, Document, Lightbulb, Calendar } from '@element-plus/icons-vue'
import api from '../api'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const searchText = ref('')
const matchMode = ref('enterprise')
const loading = ref(false)
const showResults = ref(false)
const currentMatchMode = ref(null) // 记录当前匹配时的模式
const currentHistoryId = ref(null) // 当前匹配的历史ID

// 论文选择和实现路径相关
const selectedPaperIds = ref([])
const selectedPapers = computed(() => {
  return matchResults.value.filter(item => selectedPaperIds.value.includes(item.paper_id))
})
const generatingPath = ref(false)
const showPathDialog = ref(false)
const pathLoading = ref(false)
const pathError = ref(null)
const implementationPath = ref(null)
const papersAnalysis = ref([])

// 保存匹配状态到 localStorage（只在查看合作方案后保存）
const saveMatchState = () => {
  const state = {
    searchText: searchText.value,
    matchMode: matchMode.value,
    hasResults: showResults.value,
    timestamp: Date.now()
  }
  localStorage.setItem('smartMatchState', JSON.stringify(state))
}

// 恢复匹配状态（从合作方案详情返回时）
const restoreMatchState = () => {
  try {
    // 首先检查 URL 参数
    if (route.query.restore === 'true') {
      const saved = localStorage.getItem('smartMatchState')
      if (saved) {
        const state = JSON.parse(saved)
        // 检查状态是否过期（30分钟内有效）
        const isExpired = Date.now() - state.timestamp > 30 * 60 * 1000
        
        if (!isExpired && state.hasResults) {
          // 恢复搜索内容和匹配模式
          searchText.value = state.searchText || route.query.searchText || ''
          matchMode.value = state.matchMode || route.query.matchMode || 'enterprise'
          
          // 恢复匹配结果
          if (state.results && state.results.length > 0) {
            matchResults.value = state.results
            showResults.value = true
            currentMatchMode.value = state.matchMode || 'enterprise'
          } else {
            showResults.value = false
          }
          
          // 滚动到结果区域
          setTimeout(() => {
            const resultsSection = document.querySelector('.results-section')
            if (resultsSection) {
              resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' })
            }
          }, 100)
          return true
        } else {
          // 状态过期，清除
          localStorage.removeItem('smartMatchState')
        }
      }
    }
    
    // 如果没有 URL 参数，尝试从 localStorage 恢复
    const saved = localStorage.getItem('smartMatchState')
    if (saved) {
      const state = JSON.parse(saved)
      const isExpired = Date.now() - state.timestamp > 30 * 60 * 1000
      
      if (!isExpired && state.hasResults && state.results) {
        searchText.value = state.searchText || ''
        matchMode.value = state.matchMode || 'enterprise'
        matchResults.value = state.results
        showResults.value = true
        currentMatchMode.value = state.matchMode || 'enterprise'
        return true
      }
    }
  } catch (e) {
    console.error('恢复匹配状态失败:', e)
  }
  return false
}

// 清除匹配状态
const clearMatchState = () => {
  localStorage.removeItem('smartMatchState')
}

// 从匹配历史恢复结果
const restoreFromHistory = (historyId) => {
  try {
    const historyKey = 'matchHistory'
    const history = JSON.parse(localStorage.getItem(historyKey) || '[]')
    const historyItem = history.find(item => item.id === parseInt(historyId))
    
    if (historyItem && historyItem.results) {
      // 恢复搜索内容和模式
      searchText.value = historyItem.searchContent
      matchMode.value = historyItem.matchMode
      currentMatchMode.value = historyItem.matchMode
      
      // 恢复匹配结果
      if (historyItem.results && historyItem.results.length > 0) {
        matchResults.value = historyItem.results
        showResults.value = true
      } else {
        showResults.value = false
      }
      
      // 滚动到结果区域
      setTimeout(() => {
        const resultsSection = document.querySelector('.results-section')
        if (resultsSection) {
          resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }
      }, 100)
      
      return true
    }
  } catch (e) {
    console.error('恢复匹配历史失败:', e)
  }
  return false
}

// 根据用户角色自动设置默认模式，并处理路由参数
onMounted(() => {
  // 检查是否从合作方案详情返回（有保存的状态）
  const restored = restoreMatchState()
  
  if (!restored) {
    // 如果从匹配历史跳转过来，恢复历史记录
    if (route.query.historyId) {
      const restoredFromHistory = restoreFromHistory(route.query.historyId)
      if (restoredFromHistory) {
        return // 已恢复，直接返回
      }
    }
    
    // 如果没有保存的状态，处理从匹配历史页面传递的参数（旧版本兼容）
    if (route.query.q) {
      searchText.value = route.query.q.toString()
    }
    if (route.query.type) {
      const type = route.query.type.toString()
      if (type === 'enterprise' || type === 'researcher') {
        matchMode.value = type
      }
    } else if (userStore.userInfo?.role) {
      // 如果没有传递类型参数，则使用用户角色
      matchMode.value = userStore.userInfo.role
    }
    
    // 如果从匹配历史跳转过来，从 sessionStorage 加载结果
    if (route.query.fromHistory === 'true') {
      try {
        const sessionResults = sessionStorage.getItem('matchingResults')
        if (sessionResults) {
          const data = JSON.parse(sessionResults)
          const papers = data.papers || []
          
          if (papers.length > 0) {
            // 恢复搜索内容和模式
            searchText.value = route.query.q || data.searchText || ''
            matchMode.value = route.query.type || data.matchMode || 'enterprise'
            
            // 恢复匹配结果
            matchResults.value = papers
            showResults.value = true
            currentMatchMode.value = matchMode.value
            
            // 清除 sessionStorage（避免重复使用）
            sessionStorage.removeItem('matchingResults')
            
            // 滚动到结果区域
            setTimeout(() => {
              const resultsSection = document.querySelector('.results-section')
              if (resultsSection) {
                resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' })
              }
            }, 100)
          } else {
            showResults.value = false
          }
        } else {
          showResults.value = false
        }
      } catch (e) {
        console.error('从匹配历史恢复失败:', e)
        showResults.value = false
      }
    } else {
      // 新进入页面时，清除之前的状态（但保留匹配结果数据，以便从合作方案返回时使用）
      showResults.value = false
      currentMatchMode.value = null
      // 不清除 matchResults，因为可能从合作方案页面返回
    }
  }
})

// 存储从API获取的真实匹配结果
const matchResults = ref([])

// 根据匹配模式过滤结果（现在使用真实数据）
const filteredResults = computed(() => {
  // 如果没有结果显示，返回空数组
  if (!showResults.value) {
    return []
  }
  
  // 如果切换了模式，不显示结果（需要重新匹配）
  if (currentMatchMode.value && matchMode.value !== currentMatchMode.value) {
    return []
  }
  
  // 直接返回从API获取的真实匹配结果
  // 后端返回的是论文数据，统一作为成果显示
  return matchResults.value
})

// 监听匹配模式变化
watch(matchMode, (newMode, oldMode) => {
  // 如果已经有结果显示，且切换了模式，则隐藏结果
  if (showResults.value && currentMatchMode.value && newMode !== currentMatchMode.value) {
    showResults.value = false
    currentMatchMode.value = null
  }
})

// 保存匹配历史到 localStorage
const saveMatchHistory = () => {
  try {
    const historyKey = 'matchHistory'
    let history = JSON.parse(localStorage.getItem(historyKey) || '[]')
    
    // 获取当前匹配的结果（使用真实数据）
    const currentResults = matchResults.value
    
    const historyItem = {
      id: Date.now(), // 使用时间戳作为ID
      matchTime: new Date().toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      }),
      searchContent: searchText.value,
      matchType: matchMode.value === 'enterprise' ? '找成果' : '找需求',
      matchCount: currentResults.length,
      results: currentResults, // 保存完整的匹配结果
      matchMode: matchMode.value
    }
    
    // 添加到历史记录开头（最新的在前面）
    history.unshift(historyItem)
    
    // 只保留最近50条记录
    if (history.length > 50) {
      history = history.slice(0, 50)
    }
    
    localStorage.setItem(historyKey, JSON.stringify(history))
  } catch (e) {
    console.error('保存匹配历史失败:', e)
  }
}

// 开始匹配
const startMatch = async () => {
  if (!searchText.value.trim()) {
    ElMessage.warning('请输入搜索内容')
    return
  }

  loading.value = true
  showResults.value = false

  // 清除之前保存的状态（新匹配时）
  clearMatchState()

  try {
    // 调用后端匹配API（自动保存匹配历史）
    const response = await api.post('/matching/match', {
      requirement: searchText.value,
      top_k: 50,
      match_mode: matchMode.value,
      save_history: true  // 自动保存匹配历史
    })

    // 将后端返回的论文数据转换为成果格式
    const papers = response.data.papers || []
    const convertedResults = papers.map((paper, index) => {
      // 后端返回的 score 是 0-100 的整数，不需要再乘以100
      const score = paper.score || paper.similarity_score || 0
      // 如果 score 是 0-1 之间的小数，转换为 0-100；如果已经是 0-100，直接使用
      const matchScore = score > 1 ? Math.round(score) : Math.round(score * 100)
      
      return {
        id: paper.paper_id || `paper_${index}`,
        title: paper.title || '无标题',
        summary: paper.abstract || paper.desc || '暂无摘要',
        matchScore: matchScore,
        type: '成果', // 后端返回的是论文，统一作为成果显示
        field: paper.categories || '未分类',
        keywords: paper.categories ? paper.categories.split(',') : [],
        paper_id: paper.paper_id,
        pdf_url: paper.pdf_url,
        authors: paper.authors || '',
        published_date: paper.published_date || '',
        reason: paper.reason || '',
        match_type: paper.match_type || '', // S级-完美适配、A级-技术相关等
        vector_score: paper.vector_score || 0 // 向量相似度分数
      }
    })

    // 更新结果数据（使用真实数据）
    matchResults.value = convertedResults

    loading.value = false
    showResults.value = true
    // 记录当前匹配时的模式
    currentMatchMode.value = matchMode.value

    // 保存匹配历史到 localStorage（作为本地备份）
    saveMatchHistory()
    
    // 后端已经自动保存到数据库，这里显示成功消息
    const historyId = response.data.history_id
    if (historyId) {
      ElMessage.success(`匹配完成！找到 ${convertedResults.length} 个匹配项，已保存到匹配历史`)
    } else {
      ElMessage.success(`匹配完成！找到 ${convertedResults.length} 个匹配项`)
    }

    // 滚动到结果区域
    setTimeout(() => {
      const resultsSection = document.querySelector('.results-section')
      if (resultsSection) {
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }
    }, 100)
  } catch (error) {
    loading.value = false
    ElMessage.error('匹配失败: ' + (error.response?.data?.detail || error.message))
    console.error('匹配失败:', error)
  }
}

// 获取匹配度颜色
const getScoreColor = (score) => {
  if (score >= 90) return '#67c23a' // 绿色
  if (score >= 80) return '#409eff' // 蓝色
  if (score >= 70) return '#e6a23c' // 橙色
  return '#f56c6c' // 红色
}

// 高亮关键词
const highlightKeywords = (text) => {
  if (!text) return ''
  
  // 从搜索结果中提取关键词（这里简化处理，实际应该从匹配结果中获取）
  const keywords = searchText.value.split(/\s+/).filter(k => k.length > 1)
  
  let highlighted = text
  keywords.forEach(keyword => {
    if (keyword.length > 1) {
      const regex = new RegExp(`(${keyword})`, 'gi')
      highlighted = highlighted.replace(regex, '<mark class="highlight">$1</mark>')
    }
  })
  
  return highlighted
}

// 论文选择相关函数
const isPaperSelected = (paperId) => {
  return selectedPaperIds.value.includes(paperId)
}

const handlePaperSelection = (paperId, checked) => {
  if (checked && !selectedPaperIds.value.includes(paperId)) {
    selectedPaperIds.value.push(paperId)
  } else if (!checked) {
    selectedPaperIds.value = selectedPaperIds.value.filter(id => id !== paperId)
  }
  
  // 限制最多选择5篇
  if (selectedPaperIds.value.length > 5) {
    ElMessage.warning('最多只能选择5篇论文进行分析')
    selectedPaperIds.value = selectedPaperIds.value.slice(0, 5)
  }
}

const clearSelection = () => {
  selectedPaperIds.value = []
  ElMessage.info('已清空选择')
}

// 生成实现路径
const generateImplementationPath = async () => {
  if (selectedPaperIds.value.length === 0) {
    ElMessage.warning('请至少选择一篇论文')
    return
  }
  
  if (selectedPaperIds.value.length > 5) {
    ElMessage.warning('最多只能选择5篇论文')
    return
  }
  
  generatingPath.value = true
  showPathDialog.value = true
  pathLoading.value = true
  pathError.value = null
  implementationPath.value = null
  papersAnalysis.value = []
  
  try {
    const requestData = {
      paper_ids: selectedPaperIds.value,
      max_pages_per_paper: 20
    }
    
    // 如果有历史ID，使用历史ID获取需求；否则使用当前搜索文本
    if (currentHistoryId.value) {
      requestData.history_id = currentHistoryId.value
    } else {
      requestData.user_requirement = searchText.value
    }
    
    const response = await api.post('/papers/generate-implementation-path', requestData)
    
    if (response.data.status === 'error') {
      pathError.value = response.data.error_message || '生成实现路径失败'
      ElMessage.error(pathError.value)
    } else {
      implementationPath.value = response.data.implementation_path
      papersAnalysis.value = response.data.papers_analysis || []
      ElMessage.success('实现路径生成成功！')
    }
  } catch (error) {
    pathError.value = error.response?.data?.detail || error.message || '生成实现路径失败'
    ElMessage.error(pathError.value)
    console.error('生成实现路径失败:', error)
  } finally {
    pathLoading.value = false
    generatingPath.value = false
  }
}

// 导出实现路径
const exportPath = () => {
  if (!implementationPath.value) {
    ElMessage.warning('没有可导出的内容')
    return
  }
  
  const content = JSON.stringify(implementationPath.value, null, 2)
  const blob = new Blob([content], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `实现路径_${new Date().getTime()}.json`
  link.click()
  URL.revokeObjectURL(url)
  ElMessage.success('导出成功')
}

// 查看合作方案
const viewProposal = (id) => {
  // 保存当前状态和匹配结果后再跳转
  const state = {
    searchText: searchText.value,
    matchMode: matchMode.value,
    hasResults: showResults.value,
    results: matchResults.value, // 保存完整的匹配结果
    timestamp: Date.now()
  }
  localStorage.setItem('smartMatchState', JSON.stringify(state))
  
  router.push({
    path: `/proposal/${id}`,
    query: {
      from: 'smart-match'
    }
  })
}

// 打开PDF
const openPdf = (url) => {
  if (url) {
    window.open(url, '_blank')
  }
}

// 格式化日期
const formatDate = (dateStr) => {
  if (!dateStr) return ''
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

// 获取匹配类型标签类型
const getMatchTypeTagType = (matchType) => {
  if (matchType && matchType.includes('S级')) return 'success'
  if (matchType && matchType.includes('A级')) return 'warning'
  if (matchType && matchType.includes('B级')) return 'info'
  return ''
}
</script>

<style scoped>
.smart-match {
  min-height: calc(100vh - 60px);
}

/* Hero Section */
.hero-section {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 80px 0;
  text-align: center;
}

.hero-content {
  max-width: 900px;
  margin: 0 auto;
  padding: 0 20px;
}

.hero-title {
  font-size: 3.5rem;
  font-weight: bold;
  margin-bottom: 20px;
  line-height: 1.2;
}

.hero-subtitle {
  font-size: 1.2rem;
  margin-bottom: 40px;
  opacity: 0.9;
  line-height: 1.6;
}

.search-container {
  margin-top: 40px;
  text-align: left;
}

.search-textarea {
  margin-bottom: 24px;
}

.search-textarea :deep(.el-textarea__inner) {
  font-size: 16px;
  line-height: 1.6;
  padding: 16px;
  border-radius: 8px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  background: rgba(255, 255, 255, 0.95);
  color: #333;
  transition: all 0.3s;
}

.search-textarea :deep(.el-textarea__inner):focus {
  border-color: rgba(255, 255, 255, 0.8);
  background: #fff;
  box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.2);
}

.mode-selector {
  margin-bottom: 24px;
  display: flex;
  justify-content: center;
}

.mode-selector :deep(.el-radio-group) {
  background: rgba(255, 255, 255, 0.15);
  border-radius: 8px;
  padding: 4px;
}

.mode-selector :deep(.el-radio-button__inner) {
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.8);
  padding: 12px 24px;
}

.mode-selector :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: #fff;
  color: #667eea;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.match-button {
  width: 100%;
  height: 56px;
  font-size: 18px;
  font-weight: 600;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  transition: all 0.3s;
}

.match-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.3);
}

/* 结果区域 */
.results-section {
  padding: 60px 0;
  background: #f5f5f5;
  min-height: 400px;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

/* 这些样式在.results-header中已重新定义 */

.card {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.06);
  padding: 20px;
  display: flex;
  flex-direction: column;
  min-height: 280px;
  margin-bottom: 20px;
  transition: all 0.3s;
  position: relative;
}

.card.selected {
  border: 2px solid #409eff;
  box-shadow: 0 4px 20px rgba(64, 158, 255, 0.2);
}

.paper-checkbox {
  width: 100%;
}

.paper-checkbox :deep(.el-checkbox__label) {
  width: 100%;
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.action-buttons {
  display: flex;
  gap: 10px;
}

.implementation-path-dialog :deep(.el-dialog__body) {
  max-height: 70vh;
  overflow-y: auto;
}

.path-section {
  margin-bottom: 30px;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
}

.path-section h3 {
  margin-top: 0;
  margin-bottom: 15px;
  color: #303133;
  font-size: 18px;
}

.path-section ul {
  margin: 10px 0;
  padding-left: 20px;
}

.path-section li {
  margin: 5px 0;
  line-height: 1.6;
}

.tech-selection {
  margin-top: 10px;
}

.risk-assessment {
  margin-top: 10px;
}

.path-loading {
  padding: 40px;
}

.path-error {
  padding: 40px;
  text-align: center;
}

.card:hover {
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
  transform: translateY(-2px);
}

.card-header {
  margin-bottom: 16px;
  padding-right: 40px;
}

.paper-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #1f2937;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-body {
  flex: 1;
  margin-bottom: 16px;
}

.summary-content {
  color: #4b5563;
  min-height: 80px;
  font-size: 14px;
  line-height: 1.8;
  margin-bottom: 16px;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}

.summary-content :deep(.highlight) {
  background: linear-gradient(120deg, #fef3c7 0%, #fde68a 100%);
  color: #92400e;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
  box-shadow: 0 1px 2px rgba(146, 64, 14, 0.1);
}

.confidence-section {
  margin: 16px 0;
  padding: 14px;
  background: #f8fafc;
  border-radius: 10px;
}

.score-label {
  font-size: 13px;
  font-weight: 600;
  color: #475569;
}

.card-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: #64748b;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #e2e8f0;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background: #f1f5f9;
  border-radius: 6px;
  transition: all 0.2s;
}

.meta-item:hover {
  background: #e2e8f0;
}

.meta-item .el-icon {
  font-size: 13px;
  color: #64748b;
}

/* 推荐理由样式 */
.reason-section {
  margin: 16px 0;
  padding: 14px 16px;
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border-radius: 10px;
  border-left: 4px solid #3b82f6;
  box-shadow: 0 2px 4px rgba(59, 130, 246, 0.1);
}

.reason-label {
  font-size: 13px;
  font-weight: 600;
  color: #3b82f6;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.reason-text {
  font-size: 13px;
  color: #475569;
  line-height: 1.7;
}

/* 分数头部样式 */
.score-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.score-header span {
  font-size: 13px;
  color: #666;
}

.card-footer {
  margin-top: auto;
  padding-top: 16px;
  border-top: 1px solid #f1f5f9;
  display: flex;
  gap: 8px;
  justify-content: flex-start;
}

.card-footer .el-button {
  flex: 1;
}

@media (max-width: 768px) {
  .hero-title {
    font-size: 2.5rem;
  }

  .hero-subtitle {
    font-size: 1rem;
  }

  .results-title {
    font-size: 2rem;
  }

  .search-textarea :deep(.el-textarea__inner) {
    font-size: 14px;
  }

  .mode-selector :deep(.el-radio-button__inner) {
    padding: 10px 16px;
    font-size: 14px;
  }
}

/* 论文选择和实现路径相关样式 */
.results-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 32px;
  flex-wrap: wrap;
  gap: 20px;
  padding: 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(102, 126, 234, 0.3);
}

.results-header > div:first-child {
  flex: 1;
}

.results-title {
  color: #fff;
  margin-bottom: 8px;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.results-subtitle {
  color: rgba(255, 255, 255, 0.9);
  font-size: 15px;
}

.action-buttons {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.action-buttons .el-button {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  border: none;
  font-weight: 600;
}

.action-buttons .el-button--success {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
}

.action-buttons .el-button--success:hover {
  background: linear-gradient(135deg, #059669 0%, #047857 100%);
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(16, 185, 129, 0.4);
}

.card.selected {
  border: 2px solid #409eff;
  box-shadow: 0 4px 20px rgba(64, 158, 255, 0.2);
}

.paper-checkbox {
  width: 100%;
}

.paper-checkbox :deep(.el-checkbox__label) {
  width: 100%;
}

/* 实现路径对话框样式 */
.implementation-path-dialog :deep(.el-dialog__body) {
  max-height: 70vh;
  overflow-y: auto;
}

.path-section {
  margin-bottom: 30px;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
}

.path-section h3 {
  margin-top: 0;
  margin-bottom: 15px;
  color: #303133;
  font-size: 18px;
}

.path-section ul {
  margin: 10px 0;
  padding-left: 20px;
}

.path-section li {
  margin: 5px 0;
  line-height: 1.6;
}

.tech-selection {
  margin-top: 10px;
}

.risk-assessment {
  margin-top: 10px;
}

.path-loading {
  padding: 40px;
}

.path-error {
  padding: 40px;
  text-align: center;
}
</style>


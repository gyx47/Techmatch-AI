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
        <h2 class="results-title">匹配结果</h2>
        <p class="results-subtitle">为您找到 {{ filteredResults.length }} 个匹配项</p>

        <el-row :gutter="20">
          <el-col :span="8" v-for="item in filteredResults" :key="item.id">
            <div class="card">
              <div class="card-header">
                <h3>{{ item.title }}</h3>
              </div>
              <div class="card-body">
                <div class="summary-content" v-html="highlightKeywords(item.summary)"></div>
                <div class="confidence">
                  <span>匹配度</span>
                  <el-progress
                    :percentage="item.matchScore"
                    :color="getScoreColor(item.matchScore)"
                    :stroke-width="10"
                    :status="item.matchScore >= 90 ? 'success' : ''"
                  />
                </div>
                <div class="card-meta">
                  <el-tag v-if="item.type" :type="item.type === '成果' ? 'success' : 'primary'" size="small">
                    {{ item.type }}
                  </el-tag>
                  <span class="meta-item">
                    <el-icon><FolderOpened /></el-icon>
                    {{ item.field }}
                  </span>
                </div>
              </div>
              <div class="card-footer">
                <el-button type="primary" @click="viewProposal(item.id)">
                  查看合作方案
                </el-button>
              </div>
            </div>
          </el-col>
        </el-row>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '../stores/user'
import { ElMessage } from 'element-plus'
import { Search, FolderOpened, OfficeBuilding } from '@element-plus/icons-vue'
import api from '../api'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const searchText = ref('')
const matchMode = ref('enterprise')
const loading = ref(false)
const showResults = ref(false)
const currentMatchMode = ref(null) // 记录当前匹配时的模式

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
    const saved = localStorage.getItem('smartMatchState')
    if (saved) {
      const state = JSON.parse(saved)
      // 检查状态是否过期（30分钟内有效）
      const isExpired = Date.now() - state.timestamp > 30 * 60 * 1000
      
      if (!isExpired && state.hasResults) {
        // 恢复搜索内容和匹配模式
        searchText.value = state.searchText || ''
        matchMode.value = state.matchMode || 'enterprise'
        showResults.value = true
        // 恢复匹配时的模式
        currentMatchMode.value = state.matchMode || 'enterprise'
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
      
      // 恢复匹配结果（需要更新allMockResults，但这里我们直接使用历史中的结果）
      // 注意：由于我们使用的是computed filteredResults，它会根据matchMode自动过滤
      // 所以我们需要确保历史中的结果能被正确显示
      showResults.value = true
      
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
    
    // 如果从匹配历史跳转过来（旧版本兼容），直接显示结果
    if (route.query.fromHistory === 'true' && route.query.q) {
      showResults.value = true
      currentMatchMode.value = matchMode.value
      // 滚动到结果区域
      setTimeout(() => {
        const resultsSection = document.querySelector('.results-section')
        if (resultsSection) {
          resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }
      }, 100)
    } else {
      // 新进入页面时，清除之前的状态
      showResults.value = false
      currentMatchMode.value = null
    }
  }
})

// Mock 匹配结果数据（包含成果和需求）
const allMockResults = ref([
  {
    id: 101,
    title: '基于深度学习的智能图像识别系统',
    summary: '采用卷积神经网络(CNN)和Transformer架构，实现高精度的图像分类和目标检测。系统支持多场景应用，包括医疗影像分析、工业质检、自动驾驶等领域。准确率达到98.5%，处理速度提升40%。',
    matchScore: 95,
    type: '成果',
    field: '人工智能/计算机视觉',
    keywords: ['深度学习', '图像识别', 'CNN', 'Transformer', '医疗影像', '工业质检']
  },
  {
    id: 102,
    title: '大语言模型驱动的智能对话系统',
    summary: '基于Transformer架构的大语言模型，支持多轮对话、上下文理解和知识检索。模型参数量达到70B，在中文理解、代码生成、逻辑推理等任务上表现优异。已应用于智能客服、教育辅导等多个场景。',
    matchScore: 92,
    type: '成果',
    field: '自然语言处理/大语言模型',
    keywords: ['大语言模型', 'Transformer', '智能对话', '多轮对话', '知识检索']
  },
  {
    id: 103,
    title: '寻求AI驱动的智能客服解决方案',
    summary: '公司需要一套基于自然语言处理的智能客服系统，能够处理多轮对话、情感识别和知识库检索。要求支持中英文，响应时间小于2秒，准确率高于90%。希望与有相关技术积累的科研团队合作。',
    matchScore: 88,
    type: '需求',
    field: '互联网/电商',
    company: '某科技股份有限公司',
    keywords: ['AI', '智能客服', '自然语言处理', '多轮对话']
  },
  {
    id: 104,
    title: '基于强化学习的智能决策优化算法',
    summary: '采用深度强化学习(DRL)方法，解决复杂环境下的决策优化问题。算法在资源调度、路径规划、游戏策略等场景中表现突出，相比传统方法效率提升50%以上。支持在线学习和策略迁移。',
    matchScore: 85,
    type: '成果',
    field: '强化学习/决策优化',
    keywords: ['强化学习', 'DRL', '决策优化', '资源调度', '路径规划']
  },
  {
    id: 105,
    title: 'AI视觉检测系统开发需求',
    summary: '制造企业需要部署基于深度学习的视觉检测系统，用于产品质量自动检测。要求支持多种缺陷类型识别，检测准确率高于99%，处理速度满足生产线实时要求。希望与有工业AI应用经验的团队合作。',
    matchScore: 82,
    type: '需求',
    field: '制造业',
    company: '某智能制造科技公司',
    keywords: ['AI视觉', '深度学习', '质量检测', '工业AI', '缺陷识别']
  },
  {
    id: 106,
    title: '联邦学习隐私保护框架',
    summary: '构建分布式机器学习框架，在保护数据隐私的前提下实现模型协同训练。采用差分隐私、同态加密等技术，确保数据不出本地即可完成模型训练。已在医疗、金融等敏感领域应用。',
    matchScore: 90,
    type: '成果',
    field: '联邦学习/隐私计算',
    keywords: ['联邦学习', '隐私计算', '分布式学习', '数据安全']
  },
  {
    id: 107,
    title: '大语言模型定制化训练服务需求',
    summary: '企业需要针对特定领域（如法律、医疗）定制化训练大语言模型。要求模型具备领域专业知识，支持长文本理解，能够进行专业问答和文档生成。希望与有LLM训练经验的科研院所合作。',
    matchScore: 87,
    type: '需求',
    field: '企业服务',
    company: '某AI技术服务公司',
    keywords: ['大语言模型', '定制化训练', 'LLM', '专业领域']
  }
])

// 根据匹配模式过滤结果
const filteredResults = computed(() => {
  // 如果没有结果显示，返回空数组
  if (!showResults.value) {
    return []
  }
  
  // 如果切换了模式，不显示结果（需要重新匹配）
  if (currentMatchMode.value && matchMode.value !== currentMatchMode.value) {
    return []
  }
  
  // 后端返回的是论文数据，可以作为成果显示
  // 企业找成果：显示所有匹配的论文（作为成果）
  // 专家找需求：也显示所有匹配的论文（因为论文可以转化为需求）
  // 如果以后有专门的需求数据，可以在这里区分
  if (matchMode.value === 'enterprise') {
    // 企业找成果：显示成果类型的结果
    return allMockResults.value.filter(item => item.type === '成果')
  } else if (matchMode.value === 'researcher') {
    // 专家找需求：目前后端只返回论文，暂时也显示成果（论文可以作为需求参考）
    // 如果以后有专门的需求数据，可以改为：return allMockResults.value.filter(item => item.type === '需求')
    return allMockResults.value.filter(item => item.type === '成果')
  }
  return allMockResults.value
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
    
    // 获取当前匹配的结果（根据模式过滤）
    const currentResults = filteredResults.value
    
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
    // 调用后端匹配API
    const response = await api.post('/matching/match', {
      requirement: searchText.value,
      top_k: 50
    })

    // 将后端返回的论文数据转换为成果格式
    const papers = response.data.papers || []
    const convertedResults = papers.map((paper, index) => ({
      id: paper.paper_id || `paper_${index}`,
      title: paper.title || '无标题',
      summary: paper.abstract || paper.desc || '暂无摘要',
      matchScore: Math.round((paper.score || paper.similarity_score || 0) * 100),
      type: '成果', // 后端返回的是论文，统一作为成果显示
      field: paper.categories || '未分类',
      keywords: paper.categories ? paper.categories.split(',') : [],
      paper_id: paper.paper_id,
      pdf_url: paper.pdf_url,
      reason: paper.reason || ''
    }))

    // 更新结果数据
    allMockResults.value = convertedResults

    loading.value = false
    showResults.value = true
    // 记录当前匹配时的模式
    currentMatchMode.value = matchMode.value

    // 保存匹配历史
    saveMatchHistory()

    ElMessage.success(`匹配完成！找到 ${convertedResults.length} 个匹配项`)

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

// 查看合作方案
const viewProposal = (id) => {
  // 保存当前状态后再跳转
  saveMatchState()
  router.push({
    path: `/proposal/${id}`,
    query: {
      from: 'smart-match'
    }
  })
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

.results-title {
  font-size: 2.5rem;
  font-weight: bold;
  color: #1f2937;
  margin-bottom: 8px;
  text-align: center;
}

.results-subtitle {
  font-size: 1rem;
  color: #6b7280;
  margin-bottom: 40px;
  text-align: center;
}

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
}

.card:hover {
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
  transform: translateY(-2px);
}

.card-header {
  margin-bottom: 12px;
}

.card-header h3 {
  margin: 0 0 10px;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.card-body {
  flex: 1;
  margin-bottom: 16px;
}

.summary-content {
  color: #666;
  min-height: 60px;
  font-size: 14px;
  line-height: 1.6;
  margin-bottom: 12px;
}

.summary-content :deep(.highlight) {
  background: #fef3c7;
  color: #92400e;
  padding: 2px 4px;
  border-radius: 3px;
  font-weight: 600;
}

.confidence {
  margin: 12px 0;
}

.confidence span {
  display: block;
  font-size: 13px;
  color: #666;
  margin-bottom: 6px;
}

.card-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  color: #9ca3af;
  margin-top: 12px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.meta-item .el-icon {
  font-size: 14px;
}

.card-footer {
  margin-top: auto;
  padding-top: 12px;
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
</style>


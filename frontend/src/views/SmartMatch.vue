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
                
                <!-- 推荐理由 -->
                <div class="reason-section" v-if="item.reason">
                  <div class="reason-label">推荐理由：</div>
                  <div class="reason-text">{{ item.reason }}</div>
                </div>
                
                <div class="confidence">
                  <div class="score-header">
                    <span>匹配度</span>
                    <el-tag v-if="item.match_type" :type="getMatchTypeTagType(item.match_type)" size="small">
                      {{ item.match_type }}
                    </el-tag>
                  </div>
                  <el-progress
                    :percentage="item.matchScore"
                    :color="getScoreColor(item.matchScore)"
                    :stroke-width="10"
                    :status="item.matchScore >= 90 ? 'success' : item.matchScore >= 75 ? 'warning' : ''"
                  />
                </div>
                
                <div class="card-meta">
                  <el-tag v-if="item.type" :type="item.type === '成果' ? 'success' : 'primary'" size="small">
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
                    {{ formatDate(item.published_date) }}
                  </span>
                </div>
              </div>
              <div class="card-footer">
                <el-button type="primary" @click="viewProposal(item.id)">
                  查看合作方案
                </el-button>
                <el-button v-if="item.pdf_url" @click="openPdf(item.pdf_url)" link>
                  查看PDF
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
import { Search, FolderOpened, OfficeBuilding, User } from '@element-plus/icons-vue'
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

/* 推荐理由样式 */
.reason-section {
  margin: 12px 0;
  padding: 12px;
  background: #f9fafb;
  border-radius: 6px;
  border-left: 3px solid #667eea;
}

.reason-label {
  font-size: 13px;
  font-weight: 600;
  color: #667eea;
  margin-bottom: 6px;
}

.reason-text {
  font-size: 13px;
  color: #666;
  line-height: 1.6;
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


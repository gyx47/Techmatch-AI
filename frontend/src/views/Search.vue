<template>
  <div class="search-page">
    <div class="container">
      <!-- 搜索区域 -->
      <div class="search-section">
        <h1 class="page-title">论文搜索</h1>
        <div class="search-form">
          <el-input
            v-model="searchQuery"
            placeholder="输入关键词搜索论文..."
            size="large"
            class="search-input"
            @keyup.enter="handleSearch"
          >
            <template #append>
              <el-button
                type="primary"
                :loading="searching"
                @click="handleSearch"
              >
                <el-icon><Search /></el-icon>
                搜索
              </el-button>
            </template>
          </el-input>
        </div>
        
        <!-- 搜索选项 -->
        <div class="search-options">
          <el-row :gutter="20">
            <el-col :span="8">
              <el-select
                v-model="searchType"
                placeholder="搜索类型"
                style="width: 100%"
              >
                <el-option label="全部" value="all" />
                <el-option label="标题" value="title" />
                <el-option label="作者" value="author" />
                <el-option label="摘要" value="abstract" />
              </el-select>
            </el-col>
            <el-col :span="8">
              <el-select
                v-model="category"
                placeholder="选择分类"
                style="width: 100%"
              >
                <el-option label="全部分类" value="" />
                <el-option
                  v-for="cat in categories"
                  :key="cat"
                  :label="cat"
                  :value="cat"
                />
              </el-select>
            </el-col>
            <el-col :span="8">
              <el-input-number
                v-model="maxResults"
                :min="1"
                :max="100"
                placeholder="结果数量"
                style="width: 100%"
              />
            </el-col>
          </el-row>
        </div>
      </div>

      <!-- 搜索结果 -->
      <div class="results-section" v-if="papers.length > 0">
        <div class="results-header">
          <h2>搜索结果 ({{ papers.length }} 篇)</h2>
          <el-button @click="searchLocal" :loading="localSearching">
            搜索本地数据库
          </el-button>
        </div>
        
        <div class="papers-list">
          <div
            v-for="paper in papers"
            :key="paper.arxiv_id"
            class="paper-card"
          >
            <div class="paper-header">
              <h3 class="paper-title">{{ paper.title }}</h3>
              <div class="paper-meta">
                <span class="paper-id">arXiv:{{ paper.arxiv_id }}</span>
                <span class="paper-date">{{ paper.published_date }}</span>
              </div>
            </div>
            
            <div class="paper-authors">
              <strong>作者:</strong> {{ paper.authors }}
            </div>
            
            <div class="paper-categories">
              <el-tag
                v-for="cat in paper.categories?.split(',')"
                :key="cat"
                size="small"
                type="info"
                class="category-tag"
              >
                {{ cat.trim() }}
              </el-tag>
            </div>
            
            <div class="paper-abstract">
              <p>{{ paper.abstract }}</p>
            </div>
            
            <div class="paper-actions">
              <el-button
                type="primary"
                size="small"
                @click="openPdf(paper.pdf_url)"
              >
                <el-icon><Document /></el-icon>
                查看PDF
              </el-button>
              <el-button
                size="small"
                @click="summarizePaper(paper)"
                :loading="summarizing === paper.arxiv_id"
              >
                <el-icon><ChatDotRound /></el-icon>
                AI摘要
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div class="empty-state" v-else-if="!searching && searchQuery">
        <el-empty description="未找到相关论文">
          <el-button type="primary" @click="searchQuery = ''">
            重新搜索
          </el-button>
        </el-empty>
      </div>

      <!-- 欢迎状态 -->
      <div class="welcome-state" v-else-if="!searching && !searchQuery">
        <div class="welcome-content">
          <el-icon class="welcome-icon"><Search /></el-icon>
          <h3>开始搜索论文</h3>
          <p>输入关键词，发现最新的学术研究成果</p>
        </div>
      </div>
    </div>

    <!-- AI摘要对话框 -->
    <el-dialog
      v-model="showSummary"
      :title="`AI摘要 - ${selectedPaper?.title}`"
      width="60%"
    >
      <div v-if="paperSummary">
        <h4>摘要</h4>
        <p>{{ paperSummary.summary }}</p>
        
        <h4 v-if="paperSummary.key_points.length > 0">关键要点</h4>
        <ul v-if="paperSummary.key_points.length > 0">
          <li v-for="point in paperSummary.key_points" :key="point">
            {{ point }}
          </li>
        </ul>
        
        <div class="relevance-score">
          <strong>相关性评分:</strong>
          <el-rate
            v-model="paperSummary.relevance_score"
            disabled
            show-score
            text-color="#ff9900"
          />
        </div>
      </div>
      <div v-else>
        <el-skeleton :rows="5" animated />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Document, ChatDotRound } from '@element-plus/icons-vue'
import api from '../api'

// 响应式数据
const searchQuery = ref('')
const searchType = ref('all')
const category = ref('')
const maxResults = ref(20)
const searching = ref(false)
const localSearching = ref(false)
const papers = ref([])
const categories = ref([])
const showSummary = ref(false)
const selectedPaper = ref(null)
const paperSummary = ref(null)
const summarizing = ref('')

// 搜索论文
const handleSearch = async () => {
  if (!searchQuery.value.trim()) {
    ElMessage.warning('请输入搜索关键词')
    return
  }
  
  searching.value = true
  papers.value = []
  
  try {
    const response = await api.get('/papers/search', {
      params: {
        query: searchQuery.value,
        max_results: maxResults.value
      }
    })
    
    papers.value = response.data
    ElMessage.success(`找到 ${papers.value.length} 篇论文`)
  } catch (error) {
    ElMessage.error('搜索失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    searching.value = false
  }
}

// 本地搜索
const searchLocal = async () => {
  if (!searchQuery.value.trim()) {
    ElMessage.warning('请输入搜索关键词')
    return
  }
  
  localSearching.value = true
  
  try {
    const response = await api.get('/papers/local-search', {
      params: {
        query: searchQuery.value,
        limit: maxResults.value
      }
    })
    
    papers.value = response.data
    ElMessage.success(`本地数据库找到 ${papers.value.length} 篇论文`)
  } catch (error) {
    ElMessage.error('本地搜索失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    localSearching.value = false
  }
}

// 打开PDF
const openPdf = (url) => {
  window.open(url, '_blank')
}

// 生成AI摘要
const summarizePaper = async (paper) => {
  selectedPaper.value = paper
  showSummary.value = true
  paperSummary.value = null
  summarizing.value = paper.arxiv_id
  
  try {
    const response = await api.post('/ai/summarize-paper', {
      paper_id: paper.arxiv_id,
      summary_type: 'detailed'
    })
    
    paperSummary.value = response.data
  } catch (error) {
    ElMessage.error('生成摘要失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    summarizing.value = ''
  }
}

// 获取分类列表
const getCategories = async () => {
  try {
    const response = await api.get('/papers/categories')
    categories.value = response.data.categories
  } catch (error) {
    console.error('获取分类失败:', error)
  }
}

onMounted(() => {
  getCategories()
})
</script>

<style scoped>
.search-page {
  min-height: 100vh;
  background: #f5f5f5;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.page-title {
  text-align: center;
  font-size: 2.5rem;
  margin-bottom: 30px;
  color: #333;
}

.search-section {
  background: white;
  padding: 40px;
  border-radius: 12px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  margin-bottom: 30px;
}

.search-form {
  margin-bottom: 30px;
}

.search-input {
  max-width: 600px;
  margin: 0 auto;
}

.search-options {
  max-width: 800px;
  margin: 0 auto;
}

.results-section {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 30px;
  background: #f8f9fa;
  border-bottom: 1px solid #e4e7ed;
}

.results-header h2 {
  margin: 0;
  color: #333;
}

.papers-list {
  padding: 20px;
}

.paper-card {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
  transition: box-shadow 0.3s ease;
}

.paper-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.paper-header {
  margin-bottom: 15px;
}

.paper-title {
  font-size: 1.2rem;
  font-weight: bold;
  color: #333;
  margin: 0 0 10px 0;
  line-height: 1.4;
}

.paper-meta {
  display: flex;
  gap: 20px;
  color: #666;
  font-size: 0.9rem;
}

.paper-authors {
  margin-bottom: 10px;
  color: #555;
}

.paper-categories {
  margin-bottom: 15px;
}

.category-tag {
  margin-right: 8px;
  margin-bottom: 5px;
}

.paper-abstract {
  margin-bottom: 15px;
  color: #666;
  line-height: 1.6;
}

.paper-abstract p {
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.paper-actions {
  display: flex;
  gap: 10px;
}

.empty-state,
.welcome-state {
  text-align: center;
  padding: 60px 20px;
}

.welcome-content {
  max-width: 400px;
  margin: 0 auto;
}

.welcome-icon {
  font-size: 4rem;
  color: #ccc;
  margin-bottom: 20px;
}

.welcome-content h3 {
  color: #666;
  margin-bottom: 10px;
}

.welcome-content p {
  color: #999;
}

.relevance-score {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #e4e7ed;
}

@media (max-width: 768px) {
  .search-section {
    padding: 20px;
  }
  
  .results-header {
    flex-direction: column;
    gap: 15px;
    align-items: stretch;
  }
  
  .paper-actions {
    flex-direction: column;
  }
}
</style>

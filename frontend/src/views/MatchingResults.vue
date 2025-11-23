<template>
  <div class="matches">
    <div class="container">
      <h1 class="title">AI Matching Results</h1>
      <p class="subtitle">基于你的需求，展示可能匹配的研究成果与解决方案</p>

      <div v-if="loading" class="loading">
        <el-skeleton :rows="5" animated />
      </div>

      <div v-else-if="results.length === 0" class="empty">
        <el-empty description="暂无匹配结果" />
      </div>

      <div v-else>
        <el-row :gutter="20">
          <el-col :span="8" v-for="item in paginatedResults" :key="item.paper_id || item.id">
            <div class="card">
              <div class="card-header">
                <h3>{{ item.title }}</h3>
                <div class="paper-meta" v-if="item.paper_id">
                  <span class="paper-id">arXiv: {{ item.paper_id }}</span>
                </div>
              </div>
              <div class="card-body">
                <p class="desc">{{ item.abstract || item.desc || '暂无摘要' }}</p>
                <div class="confidence" v-if="item.score !== undefined">
                  <span>Match Score: {{ (item.score * 100).toFixed(1) }}%</span>
                  <el-progress 
                    :percentage="item.score * 100" 
                    :stroke-width="10" 
                    :status="item.score > 0.8 ? 'success' : item.score > 0.6 ? 'warning' : 'exception'" 
                  />
                </div>
                <div class="confidence" v-else-if="item.confidence !== undefined">
                  <span>Match Confidence</span>
                  <el-progress :percentage="item.confidence" :stroke-width="10" status="success" />
                </div>
                <div class="reason" v-if="item.reason">
                  <strong>推荐理由:</strong>
                  <p>{{ item.reason }}</p>
                </div>
              </div>
              <div class="card-footer">
                <el-button type="primary" @click="$router.push('/solution/' + (item.paper_id || item.id))">
                  View Solution
                </el-button>
                <el-button v-if="item.pdf_url" @click="openPdf(item.pdf_url)" link>
                  查看PDF
                </el-button>
              </div>
            </div>
          </el-col>
        </el-row>

        <div class="pagination" v-if="total > pageSize">
          <el-pagination
            v-model:current-page="currentPage"
            :page-size="pageSize"
            :total="total"
            layout="prev, pager, next, jumper, total"
            @current-change="handlePageChange"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api'

const route = useRoute()
const results = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(9) // 每页显示9个（3列x3行）

// 计算分页后的结果
const paginatedResults = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return results.value.slice(start, end)
})

// 总数量
const total = computed(() => results.value.length)

// 处理页码变化
const handlePageChange = (page) => {
  currentPage.value = page
  // 滚动到顶部
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

// 打开PDF
const openPdf = (url) => {
  if (url) {
    window.open(url, '_blank')
  }
}

// 加载匹配结果
const loadResults = async () => {
  loading.value = true
  
  try {
    // 首先检查sessionStorage中是否有结果（从提交页面跳转过来的）
    const storedResults = sessionStorage.getItem('matchingResults')
    if (storedResults) {
      const data = JSON.parse(storedResults)
      results.value = data.papers || []
      sessionStorage.removeItem('matchingResults') // 清除存储
      return
    }
    
    // 如果有查询参数，尝试从URL参数获取需求并调用API
    const q = (route.query.q || '').toString()
    if (q) {
      const response = await api.post('/matching/match', {
        requirement: q,
        top_k: 50
      })
      results.value = response.data.papers || []
    } else {
      // 没有查询参数，显示空结果
      results.value = []
    }
  } catch (error) {
    ElMessage.error('加载匹配结果失败: ' + (error.response?.data?.detail || error.message))
    results.value = []
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadResults()
})
</script>

<style scoped>
.container { max-width: 1200px; margin: 0 auto; padding: 20px; }
.title { font-size: 32px; margin: 10px 0; }
.subtitle { color: #666; margin-bottom: 20px; }
.loading { margin: 20px 0; }
.empty { margin: 40px 0; }
.card { 
  background: #fff; 
  border-radius: 12px; 
  box-shadow: 0 2px 10px rgba(0,0,0,.06); 
  padding: 20px; 
  display: flex; 
  flex-direction: column; 
  height: 100%; 
  margin-bottom: 20px;
}
.card-header h3 { 
  margin: 0 0 10px; 
  font-size: 18px;
  line-height: 1.4;
}
.paper-meta { 
  margin-top: 5px; 
  font-size: 12px; 
  color: #999; 
}
.paper-id { 
  font-family: monospace; 
}
.desc { 
  color: #666; 
  min-height: 60px; 
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.confidence { 
  margin: 15px 0; 
}
.confidence span {
  display: block;
  margin-bottom: 5px;
  font-size: 14px;
  color: #666;
}
.reason {
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px solid #eee;
}
.reason strong {
  display: block;
  margin-bottom: 5px;
  color: #333;
  font-size: 14px;
}
.reason p {
  color: #666;
  font-size: 13px;
  line-height: 1.5;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.card-footer { 
  margin-top: auto; 
  padding-top: 15px;
  display: flex;
  gap: 10px;
}
.pagination { 
  margin-top: 30px; 
  text-align: center; 
  display: flex;
  justify-content: center;
}
</style>



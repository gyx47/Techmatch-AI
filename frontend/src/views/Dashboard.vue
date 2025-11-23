<template>
  <div class="dashboard">
    <div class="container">
      <h1 class="title">Your Dashboard</h1>
      <p class="subtitle">概览：活跃需求、匹配结果与系统功能</p>

      <el-row :gutter="20" class="stats">
        <el-col :span="8">
          <div class="card">
            <div class="card-title">Total Requests</div>
            <div class="card-value">{{ stats.totalRequests }}</div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="card">
            <div class="card-title">Active Matches</div>
            <div class="card-value">{{ stats.activeMatches }}</div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="card">
            <div class="card-title">Completed Matches</div>
            <div class="card-value">{{ stats.completedMatches }}</div>
          </div>
        </el-col>
      </el-row>

      <div class="actions">
        <el-button type="primary" @click="$router.push('/new-request')">Submit New Request</el-button>
        <el-button @click="$router.push('/matches')">View All Matches</el-button>
        <el-button type="success" @click="showCrawlerDialog = true" :loading="crawling">
          <el-icon><Refresh /></el-icon>
          更新数据
        </el-button>
      </div>

      <div class="section">
        <h3>Recent Activity</h3>
        <el-table :data="recent" stripe>
          <el-table-column prop="title" label="REQUEST TITLE" />
          <el-table-column prop="status" label="STATUS" />
          <el-table-column prop="date" label="SUBMITTED DATE" />
          <el-table-column label=""> 
            <template #default="scope">
              <el-link type="primary" @click="$router.push('/solution/' + scope.row.id)">View</el-link>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 数据统计卡片 -->
      <div class="section" v-if="vectorStats">
        <h3>数据统计</h3>
        <el-row :gutter="20">
          <el-col :span="8">
            <div class="stat-card">
              <div class="stat-label">向量数据库</div>
              <div class="stat-value">{{ vectorStats.vector_db_count || 0 }}</div>
              <div class="stat-desc">已索引论文数</div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="stat-card">
              <div class="stat-label">数据库</div>
              <div class="stat-value">{{ vectorStats.database_count || 0 }}</div>
              <div class="stat-desc">总论文数</div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="stat-card">
              <div class="stat-label">索引进度</div>
              <div class="stat-value">{{ vectorStats.indexed_percentage || 0 }}%</div>
              <div class="stat-desc">已完成索引</div>
            </div>
          </el-col>
        </el-row>
      </div>
    </div>

    <!-- 爬虫对话框 -->
    <el-dialog v-model="showCrawlerDialog" title="更新数据" width="500px">
      <el-form :model="crawlerForm" label-width="100px">
        <el-form-item label="关键词">
          <el-select
            v-model="crawlerForm.keywords"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="输入关键词，如：machine learning, deep learning"
            style="width: 100%"
          >
            <el-option label="machine learning" value="machine learning" />
            <el-option label="deep learning" value="deep learning" />
            <el-option label="AI" value="AI" />
            <el-option label="neural networks" value="neural networks" />
            <el-option label="computer vision" value="computer vision" />
            <el-option label="NLP" value="NLP" />
          </el-select>
          <div class="form-tip">爬虫将爬取最近30天包含这些关键词的论文</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCrawlerDialog = false">取消</el-button>
        <el-button type="primary" @click="startCrawler" :loading="crawling">
          开始爬取
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import api from '../api'

const stats = reactive({ totalRequests: 5, activeMatches: 2, completedMatches: 3 })
const recent = reactive([
  { id: 1, title: 'AI-Powered Image Recognition for Manufacturing', status: 'In Progress', date: '2023-11-15' },
  { id: 2, title: 'Predictive Maintenance using Machine Learning', status: 'Completed', date: '2023-10-20' },
  { id: 3, title: 'Natural Language Processing for Customer Service', status: 'Completed', date: '2023-09-05' }
])

const showCrawlerDialog = ref(false)
const crawling = ref(false)
const crawlerForm = reactive({
  keywords: ['machine learning', 'deep learning', 'AI']
})
const vectorStats = ref(null)

// 加载向量数据库统计
const loadVectorStats = async () => {
  try {
    const response = await api.get('/matching/vector-stats')
    vectorStats.value = response.data
  } catch (error) {
    console.error('加载统计信息失败:', error)
  }
}

// 启动爬虫
const startCrawler = async () => {
  if (!crawlerForm.keywords || crawlerForm.keywords.length === 0) {
    ElMessage.warning('请至少输入一个关键词')
    return
  }
  
  crawling.value = true
  try {
    await api.post('/crawler/run', {
      keywords: crawlerForm.keywords
    })
    
    ElMessage.success('爬虫任务已启动，正在后台运行。请查看后端日志了解进度。')
    showCrawlerDialog.value = false
    
    // 延迟刷新统计信息
    setTimeout(() => {
      loadVectorStats()
    }, 5000)
  } catch (error) {
    ElMessage.error('启动爬虫失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    crawling.value = false
  }
}

onMounted(() => {
  loadVectorStats()
})
</script>

<style scoped>
.container { max-width: 1200px; margin: 0 auto; padding: 20px; }
.title { font-size: 32px; margin: 10px 0; }
.subtitle { color: #666; margin-bottom: 20px; }
.stats .card { background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,.06); }
.card-title { color: #666; }
.card-value { font-size: 28px; font-weight: 700; margin-top: 6px; }
.actions { margin: 20px 0; display: flex; gap: 12px; }
.section { 
  background: #fff; 
  border-radius: 12px; 
  padding: 20px; 
  box-shadow: 0 2px 10px rgba(0,0,0,.06); 
  margin-top: 20px;
}
.section h3 {
  margin-top: 0;
  margin-bottom: 20px;
  font-size: 20px;
}
.stat-card {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 20px;
  text-align: center;
}
.stat-label {
  color: #666;
  font-size: 14px;
  margin-bottom: 8px;
}
.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: #409eff;
  margin-bottom: 4px;
}
.stat-desc {
  color: #999;
  font-size: 12px;
}
.form-tip {
  color: #999;
  font-size: 12px;
  margin-top: 5px;
}
</style>

 
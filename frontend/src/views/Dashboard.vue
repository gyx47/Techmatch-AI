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
        <el-button 
          type="success" 
          @click="showCrawlerDialog = true" 
          :loading="crawling"
          :disabled="crawlerStatus === 'running'"
        >
          <el-icon><Refresh /></el-icon>
          更新数据
        </el-button>
        <el-button 
          type="danger" 
          @click="stopCrawler" 
          :loading="stopping"
          :disabled="crawlerStatus !== 'running'"
        >
          <el-icon><Close /></el-icon>
          停止爬虫
        </el-button>
        <el-button 
          type="warning" 
          @click="startIndexing" 
          :loading="indexing"
          :disabled="indexerStatus === 'running' || (vectorStats && vectorStats.unindexed_count === 0)"
        >
          <el-icon><DocumentAdd /></el-icon>
          向量化论文
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
        <!-- 未向量化论文提示 -->
        <el-alert
          v-if="vectorStats && vectorStats.unindexed_count > 0"
          :title="`还有 ${vectorStats.unindexed_count} 篇论文未向量化`"
          type="warning"
          :closable="false"
          show-icon
          style="margin-top: 15px;"
        >
          <template #default>
            <span>点击"向量化论文"按钮将这些论文添加到向量数据库，以便进行匹配搜索。</span>
          </template>
        </el-alert>
        <!-- 索引任务进度 -->
        <el-card v-if="indexerStatus && indexerStatus.status === 'running'" style="margin-top: 15px;">
          <template #header>
            <span>向量化任务进行中...</span>
          </template>
          <div>
            <el-progress 
              :percentage="indexerStatus.total > 0 ? Math.round((indexerStatus.processed + indexerStatus.skipped + indexerStatus.error) / indexerStatus.total * 100) : 0"
              :status="indexerStatus.error > 0 ? 'exception' : 'success'"
            />
            <div style="margin-top: 10px; font-size: 14px; color: #666;">
              {{ indexerStatus.message }}
            </div>
            <div style="margin-top: 8px; font-size: 12px; color: #999;">
              已处理: {{ indexerStatus.processed }} | 
              跳过: {{ indexerStatus.skipped }} | 
              失败: {{ indexerStatus.error }} | 
              总计: {{ indexerStatus.total }}
            </div>
          </div>
        </el-card>
        <!-- 索引任务完成提示 -->
        <el-alert
          v-if="indexerStatus && indexerStatus.status === 'completed'"
          :title="indexerStatus.message"
          type="success"
          :closable="true"
          @close="indexerStatus = null"
          style="margin-top: 15px;"
        />
      </div>
    </div>

    <!-- 爬虫对话框 -->
    <el-dialog v-model="showCrawlerDialog" title="更新数据" width="500px">
      <el-form :model="crawlerForm" label-width="120px">
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
        </el-form-item>
        <el-form-item label="时间范围">
          <el-slider
            v-model="crawlerForm.days"
            :min="1"
            :max="365"
            :step="1"
            show-stops
            :show-tooltip="true"
            :format-tooltip="(val) => `${val} 天`"
            style="width: 100%"
          />
          <div class="form-tip">
            爬取最近 <strong>{{ crawlerForm.days }}</strong> 天包含这些关键词的论文
            <br>
            <span style="color: #999; font-size: 12px;">
              建议：首次使用选择30-90天，定期更新选择7-14天
            </span>
          </div>
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
import { reactive, ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Close, DocumentAdd } from '@element-plus/icons-vue'
import api from '../api'

const stats = reactive({ totalRequests: 5, activeMatches: 2, completedMatches: 3 })
const recent = reactive([
  { id: 1, title: 'AI-Powered Image Recognition for Manufacturing', status: 'In Progress', date: '2023-11-15' },
  { id: 2, title: 'Predictive Maintenance using Machine Learning', status: 'Completed', date: '2023-10-20' },
  { id: 3, title: 'Natural Language Processing for Customer Service', status: 'Completed', date: '2023-09-05' }
])

const showCrawlerDialog = ref(false)
const crawling = ref(false)
const stopping = ref(false)
const crawlerStatus = ref('ready') // ready, running, stopping
const crawlerForm = reactive({
  keywords: ['machine learning', 'deep learning', 'AI'],
  days: 30  // 默认30天
})
const vectorStats = ref(null)
const indexing = ref(false)
const indexerStatus = ref(null)
let statusCheckInterval = null

// 加载向量数据库统计
const loadVectorStats = async () => {
  try {
    const response = await api.get('/matching/vector-stats')
    vectorStats.value = response.data
    // 更新索引任务状态
    if (response.data.indexer_status) {
      indexerStatus.value = response.data.indexer_status
      // 如果任务已完成，5秒后清除状态
      if (response.data.indexer_status.status === 'completed') {
        setTimeout(() => {
          if (indexerStatus.value && indexerStatus.value.status === 'completed') {
            indexerStatus.value = null
          }
        }, 5000)
      }
    }
  } catch (error) {
    console.error('加载统计信息失败:', error)
  }
}

// 检查爬虫状态
const checkCrawlerStatus = async () => {
  try {
    const response = await api.get('/crawler/status')
    crawlerStatus.value = response.data.status
  } catch (error) {
    console.error('检查爬虫状态失败:', error)
  }
}

// 停止爬虫
const stopCrawler = async () => {
  stopping.value = true
  try {
    const response = await api.post('/crawler/stop')
    ElMessage.success(response.data.message || '已发送停止请求')
    // 立即检查状态
    await checkCrawlerStatus()
  } catch (error) {
    ElMessage.error('停止爬虫失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    stopping.value = false
  }
}

// 启动爬虫
const startCrawler = async () => {
  if (!crawlerForm.keywords || crawlerForm.keywords.length === 0) {
    ElMessage.warning('请至少输入一个关键词')
    return
  }
  
  if (!crawlerForm.days || crawlerForm.days < 1 || crawlerForm.days > 365) {
    ElMessage.warning('天数范围应在1-365天之间')
    return
  }
  
  crawling.value = true
  try {
    const response = await api.post('/crawler/run', {
      keywords: crawlerForm.keywords,
      days: crawlerForm.days
    })
    
    ElMessage.success(
      `爬虫任务已启动！将爬取最近${crawlerForm.days}天的论文。请查看后端日志了解进度。`
    )
    showCrawlerDialog.value = false
    
    // 立即检查状态
    await checkCrawlerStatus()
    
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

// 启动向量化任务
const startIndexing = async () => {
  if (indexerStatus.value && indexerStatus.value.status === 'running') {
    ElMessage.warning('向量化任务正在运行中，请稍候...')
    return
  }
  
  if (vectorStats.value && vectorStats.value.unindexed_count === 0) {
    ElMessage.info('所有论文已向量化，无需重复操作')
    return
  }
  
  indexing.value = true
  try {
    const response = await api.post('/matching/index-papers')
    ElMessage.success(response.data.message || '向量化任务已启动')
    
    // 立即刷新状态
    await loadVectorStats()
    
    // 定期检查进度（每2秒）
    const progressInterval = setInterval(async () => {
      try {
        const statusResponse = await api.get('/matching/index-status')
        indexerStatus.value = statusResponse.data
        
        if (statusResponse.data.status !== 'running') {
          clearInterval(progressInterval)
          indexing.value = false
          // 刷新统计信息
          await loadVectorStats()
        }
      } catch (error) {
        console.error('检查索引状态失败:', error)
        clearInterval(progressInterval)
        indexing.value = false
      }
    }, 2000)
    
  } catch (error) {
    ElMessage.error('启动向量化任务失败: ' + (error.response?.data?.detail || error.message))
    indexing.value = false
  }
}

onMounted(() => {
  loadVectorStats()
  checkCrawlerStatus()
  
  // 定期检查爬虫状态和索引状态（每5秒）
  statusCheckInterval = setInterval(() => {
    if (crawlerStatus.value === 'running' || crawlerStatus.value === 'stopping') {
      checkCrawlerStatus()
    }
    // 如果索引任务正在运行，也刷新状态
    if (indexerStatus.value && indexerStatus.value.status === 'running') {
      loadVectorStats()
    } else {
      // 否则只定期刷新统计信息（每30秒）
      if (Date.now() % 30000 < 5000) {
        loadVectorStats()
      }
    }
  }, 5000)
})

onUnmounted(() => {
  if (statusCheckInterval) {
    clearInterval(statusCheckInterval)
  }
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

 
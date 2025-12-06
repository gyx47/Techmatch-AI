<template>
  <div class="dashboard">
    <div class="container">
      <h1 class="title">资源大厅</h1>
      <p class="subtitle">浏览全网最新科研成果与企业需求</p>

      <!-- 操作按钮区域 -->
      <div class="actions">
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

      <el-tabs v-model="activeTab" class="resource-tabs">
        <el-tab-pane label="找成果" name="achievements">
          <!-- 搜索框 -->
          <div class="search-section">
            <el-input
              v-model="achievementSearchQuery"
              placeholder="搜索成果标题、描述..."
              clearable
              @clear="handleAchievementSearch"
              @keyup.enter="handleAchievementSearch"
              style="max-width: 500px; margin-bottom: 20px;"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
              <template #append>
                <el-button @click="handleAchievementSearch" :loading="loadingAchievements">
                  搜索
                </el-button>
              </template>
            </el-input>
          </div>
          
          <div v-loading="loadingAchievements" class="card-list">
            <el-card
              v-for="item in paginatedAchievements"
              :key="item.id"
              class="resource-card"
              shadow="hover"
            >
              <div class="card-content">
                <div class="card-main">
                  <div class="card-header">
                    <h3 class="card-title">{{ item.display_title }}</h3>
                    <el-tag
                      :type="item.data_source === '用户发布' ? 'primary' : 'info'"
                      size="small"
                    >
                      {{ item.data_source }}
                    </el-tag>
                  </div>
                  <p class="card-description">{{ item.display_description }}</p>
                  <div class="card-meta">
                    <span class="meta-item">
                      <el-icon><FolderOpened /></el-icon>
                      {{ item.display_field }}
                    </span>
                    <span class="meta-item">
                      <el-icon><Clock /></el-icon>
                      {{ item.display_time ? item.display_time.split('T')[0] : '' }}
                    </span>
                  </div>
                </div>
                <div class="card-action">
                  <el-button type="primary" @click="openDrawer(item, 'achievement')">
                    查看详情
                  </el-button>
                </div>
              </div>
            </el-card>
            <el-empty v-if="!loadingAchievements && paginatedAchievements.length === 0" description="暂无成果数据" />
            
            <!-- 分页组件 -->
            <div v-if="achievementTotal > 0" class="pagination-container">
              <el-pagination
                v-model:current-page="achievementPage"
                :page-size="achievementPageSize"
                :total="achievementTotal"
                layout="total, prev, pager, next, jumper"
                @current-change="handleAchievementPageChange"
              />
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="找需求" name="needs">
          <!-- 搜索框 -->
          <div class="search-section">
            <el-input
              v-model="needSearchQuery"
              placeholder="搜索需求标题、描述..."
              clearable
              @clear="handleNeedSearch"
              @keyup.enter="handleNeedSearch"
              style="max-width: 500px; margin-bottom: 20px;"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
              <template #append>
                <el-button @click="handleNeedSearch" :loading="loadingNeeds">
                  搜索
                </el-button>
              </template>
            </el-input>
          </div>
          
          <div v-loading="loadingNeeds" class="card-list">
            <el-card
              v-for="item in paginatedNeeds"
              :key="item.id"
              class="resource-card"
              shadow="hover"
            >
              <div class="card-content">
                <div class="card-main">
                  <div class="card-header">
                    <h3 class="card-title">{{ item.title }}</h3>
                    <el-tag
                      :type="item.data_source === '用户发布' ? 'primary' : 'info'"
                      size="small"
                    >
                      {{ item.data_source }}
                    </el-tag>
                  </div>
                  <p class="card-description">{{ item.description }}</p>
                  <div class="card-meta">
                    <span class="meta-item">
                      <el-icon><OfficeBuilding /></el-icon>
                      {{ item.company_name }}
                    </span>
                    <span class="meta-item">
                      <el-icon><Collection /></el-icon>
                      {{ item.industry }}
                    </span>
                    <span class="meta-item">
                      <el-icon><Clock /></el-icon>
                      {{ item.publish_time ? item.publish_time.split('T')[0] : '' }}
                    </span>
                  </div>
                </div>
                <div class="card-action">
                  <el-button type="primary" @click="openDrawer(item, 'need')">
                    查看详情
                  </el-button>
                </div>
              </div>
            </el-card>
            <el-empty v-if="!loadingNeeds && paginatedNeeds.length === 0" description="暂无需求数据" />
            
            <!-- 分页组件 -->
            <div v-if="needTotal > 0" class="pagination-container">
              <el-pagination
                v-model:current-page="needPage"
                :page-size="needPageSize"
                :total="needTotal"
                layout="total, prev, pager, next, jumper"
                @current-change="handleNeedPageChange"
              />
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>

      <!-- 详情抽屉 -->
      <el-drawer
        v-model="drawerVisible"
        :title="drawerTitle"
        size="500px"
        direction="rtl"
      >
        <div class="drawer-content" v-if="currentItem">
          <!-- 论文详情 -->
          <template v-if="drawerType === 'achievement' && currentItem.type === 'paper'">
            <div class="detail-section">
              <h3 class="detail-title">{{ currentItem.raw_data.title }}</h3>
              <div class="detail-tag">
                <el-tag type="info" size="small">系统采集</el-tag>
              </div>
            </div>
            <div class="detail-section">
              <h4 class="section-title">作者</h4>
              <p class="section-content">{{ currentItem.raw_data.authors }}</p>
            </div>
            <div class="detail-section">
              <h4 class="section-title">摘要</h4>
              <p class="section-content">{{ currentItem.raw_data.abstract }}</p>
            </div>
            <div class="detail-section">
              <h4 class="section-title">分类</h4>
              <p class="section-content">{{ currentItem.raw_data.categories }}</p>
            </div>
            <div class="detail-section">
              <h4 class="section-title">发布日期</h4>
              <p class="section-content">{{ currentItem.raw_data.published_date }}</p>
            </div>
            <div class="detail-section">
              <h4 class="section-title">PDF链接</h4>
              <p class="section-content">
                <a :href="currentItem.raw_data.pdf_url" target="_blank" style="color: #409eff;">
                  {{ currentItem.raw_data.pdf_url }}
                </a>
              </p>
            </div>
          </template>

          <!-- 成果详情 -->
          <template v-else-if="drawerType === 'achievement' && currentItem.type === 'achievement'">
            <div class="detail-section">
              <h3 class="detail-title">{{ currentItem.raw_data.name }}</h3>
              <div class="detail-tag">
                <el-tag type="primary" size="small">用户发布</el-tag>
              </div>
            </div>
            <div class="detail-section">
              <h4 class="section-title">成果简介</h4>
              <p class="section-content">{{ currentItem.raw_data.description }}</p>
            </div>
            <div class="detail-section">
              <h4 class="section-title">技术领域</h4>
              <p class="section-content">{{ currentItem.raw_data.field }}</p>
            </div>
            <div class="detail-section" v-if="currentItem.raw_data.application">
              <h4 class="section-title">应用场景</h4>
              <p class="section-content">{{ currentItem.raw_data.application }}</p>
            </div>
            <div class="detail-section" v-if="currentItem.raw_data.cooperation_mode && currentItem.raw_data.cooperation_mode.length > 0">
              <h4 class="section-title">合作方式</h4>
              <p class="section-content">
                <el-tag v-for="mode in currentItem.raw_data.cooperation_mode" :key="mode" style="margin-right: 8px;">
                  {{ mode }}
                </el-tag>
              </p>
            </div>
            <div class="detail-section">
              <h4 class="section-title">发布时间</h4>
              <p class="section-content">{{ currentItem.raw_data.created_at ? currentItem.raw_data.created_at.split('T')[0] : '' }}</p>
            </div>
            <div class="detail-section">
              <el-divider />
              <h4 class="section-title">联系方式</h4>
              <div class="contact-info">
                <p><strong>联系人：</strong>{{ currentItem.raw_data.contact_name }}</p>
                <p><strong>联系电话：</strong>{{ currentItem.raw_data.contact_phone }}</p>
                <p v-if="currentItem.raw_data.contact_email"><strong>联系邮箱：</strong>{{ currentItem.raw_data.contact_email }}</p>
              </div>
            </div>
          </template>

          <!-- 需求详情 -->
          <template v-else-if="drawerType === 'need'">
            <div class="detail-section">
              <h3 class="detail-title">{{ currentItem.title }}</h3>
              <div class="detail-tag">
                <el-tag type="primary" size="small">用户发布</el-tag>
              </div>
            </div>
            <div class="detail-section">
              <h4 class="section-title">需求描述</h4>
              <p class="section-content">{{ currentItem.description }}</p>
            </div>
            <div class="detail-section">
              <h4 class="section-title">企业信息</h4>
              <p class="section-content">
                <strong>公司名称：</strong>{{ currentItem.company_name }}<br />
                <strong>所属行业：</strong>{{ currentItem.industry }}
              </p>
            </div>
            <div class="detail-section" v-if="currentItem.urgency_level">
              <h4 class="section-title">紧急程度</h4>
              <p class="section-content">{{ currentItem.urgency_level }}</p>
            </div>
            <div class="detail-section" v-if="currentItem.cooperation_preference && currentItem.cooperation_preference.length > 0">
              <h4 class="section-title">合作方式偏好</h4>
              <p class="section-content">
                <el-tag v-for="pref in currentItem.cooperation_preference" :key="pref" style="margin-right: 8px;">
                  {{ pref }}
                </el-tag>
              </p>
            </div>
            <div class="detail-section" v-if="currentItem.budget_range">
              <h4 class="section-title">预算范围</h4>
              <p class="section-content">{{ currentItem.budget_range }}</p>
            </div>
            <div class="detail-section">
              <h4 class="section-title">发布时间</h4>
              <p class="section-content">{{ currentItem.publish_time ? currentItem.publish_time.split('T')[0] : '' }}</p>
            </div>
            <div class="detail-section">
              <el-divider />
              <h4 class="section-title">联系方式</h4>
              <div class="contact-info">
                <p><strong>联系人：</strong>{{ currentItem.contact_name }}</p>
                <p><strong>联系电话：</strong>{{ currentItem.contact_phone }}</p>
                <p v-if="currentItem.contact_email"><strong>联系邮箱：</strong>{{ currentItem.contact_email }}</p>
              </div>
            </div>
          </template>

        </div>
      </el-drawer>
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
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh, Close, DocumentAdd, FolderOpened, Clock, OfficeBuilding, Collection, Search } from '@element-plus/icons-vue'
import api from '../api'

const router = useRouter()
const route = useRoute()

const activeTab = ref('achievements')

// 根据路由参数恢复标签页状态
onMounted(() => {
  if (route.query.tab) {
    const tab = route.query.tab.toString()
    if (tab === 'achievements' || tab === 'needs') {
      activeTab.value = tab
    }
  }
})

const drawerVisible = ref(false)
const drawerTitle = ref('')
const drawerType = ref('')
const currentItem = ref(null)

// 成果数据（合并论文和发布的成果）
const achievements = ref([])
const needs = ref([])
const loadingAchievements = ref(false)
const loadingNeeds = ref(false)

// 分页相关
const achievementPage = ref(1)
const achievementPageSize = ref(10)
const achievementTotal = ref(0)
const paginatedAchievements = ref([])

// 论文和成果的分页数据
const paperPage = ref(1)
const paperPageSize = ref(10)
const paperTotal = ref(0)
const publishedAchievementPage = ref(1)
const publishedAchievementPageSize = ref(10)
const publishedAchievementTotal = ref(0)

const needPage = ref(1)
const needPageSize = ref(10)
const needTotal = ref(0)
const paginatedNeeds = ref([])

// 搜索关键词
const achievementSearchQuery = ref('')
const needSearchQuery = ref('')

// 加载成果数据（合并论文和发布的成果）
const loadAchievements = async () => {
  loadingAchievements.value = true
  try {
    const allAchievements = []
    
    // 1. 获取论文数据（系统采集）- 使用分页
    try {
      const papersResponse = await api.get('/papers/local-search', {
        params: { 
          query: achievementSearchQuery.value || '', 
          page: paperPage.value, 
          page_size: paperPageSize.value 
        }
      })
      
      // 处理分页格式返回
      if (papersResponse.data && papersResponse.data.items) {
        paperTotal.value = papersResponse.data.total || 0
        papersResponse.data.items.forEach(paper => {
          allAchievements.push({
            id: `paper_${paper.id || paper.arxiv_id}`,
            type: 'paper',
            data_source: '系统采集',
            display_title: paper.title,
            display_description: paper.abstract || '',
            display_field: paper.categories || '',
            display_time: paper.published_date || paper.created_at,
            raw_data: paper
          })
        })
      } else if (Array.isArray(papersResponse.data)) {
        // 向后兼容：如果返回的是数组
        papersResponse.data.forEach(paper => {
          allAchievements.push({
            id: `paper_${paper.id || paper.arxiv_id}`,
            type: 'paper',
            data_source: '系统采集',
            display_title: paper.title,
            display_description: paper.abstract || '',
            display_field: paper.categories || '',
            display_time: paper.published_date || paper.created_at,
            raw_data: paper
          })
        })
      }
    } catch (error) {
      console.error('加载论文数据失败:', error)
    }
    
    // 2. 获取发布的成果 - 使用分页
    try {
      const achievementsResponse = await api.get('/publish/achievements', {
        params: { 
          page: publishedAchievementPage.value, 
          page_size: publishedAchievementPageSize.value,
          keyword: achievementSearchQuery.value || undefined
        }
      })
      if (achievementsResponse.data && achievementsResponse.data.items) {
        publishedAchievementTotal.value = achievementsResponse.data.total || 0
        achievementsResponse.data.items.forEach(achievement => {
          allAchievements.push({
            id: `achievement_${achievement.id}`,
            type: 'achievement',
            data_source: '用户发布',
            display_title: achievement.name,
            display_description: achievement.description || '',
            display_field: achievement.field || '',
            display_time: achievement.created_at,
            raw_data: achievement
          })
        })
      }
    } catch (error) {
      console.error('加载发布成果失败:', error)
    }
    
    // 3. 按时间排序
    allAchievements.sort((a, b) => {
      const timeA = new Date(a.display_time || 0).getTime()
      const timeB = new Date(b.display_time || 0).getTime()
      return timeB - timeA
    })
    
    // 4. 计算总数和分页
    achievementTotal.value = paperTotal.value + publishedAchievementTotal.value
    paginatedAchievements.value = allAchievements
  } catch (error) {
    ElMessage.error('加载成果数据失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loadingAchievements.value = false
  }
}

// 成果搜索
const handleAchievementSearch = () => {
  achievementPage.value = 1
  paperPage.value = 1
  publishedAchievementPage.value = 1
  loadAchievements()
}

// 成果分页改变
const handleAchievementPageChange = async (page) => {
  achievementPage.value = page
  
  // 根据总数比例计算论文和成果应该在第几页
  // 简单策略：如果论文数量远大于成果，主要显示论文
  if (paperTotal.value > 0 && publishedAchievementTotal.value > 0) {
    const totalItems = paperTotal.value + publishedAchievementTotal.value
    const paperRatio = paperTotal.value / totalItems
    
    // 如果论文占比很大（>90%），主要翻论文的页
    if (paperRatio > 0.9) {
      paperPage.value = page
      publishedAchievementPage.value = Math.max(1, Math.floor(page * (publishedAchievementTotal.value / paperTotal.value)))
    } else {
      // 否则按比例分配
      const currentPosition = (page - 1) * achievementPageSize.value
      const paperPosition = Math.floor(currentPosition * paperRatio)
      const achievementPosition = Math.floor(currentPosition * (1 - paperRatio))
      
      paperPage.value = Math.max(1, Math.floor(paperPosition / paperPageSize.value) + 1)
      publishedAchievementPage.value = Math.max(1, Math.floor(achievementPosition / publishedAchievementPageSize.value) + 1)
    }
  } else if (paperTotal.value > 0) {
    // 只有论文
    paperPage.value = page
  } else if (publishedAchievementTotal.value > 0) {
    // 只有成果
    publishedAchievementPage.value = page
  }
  
  // 重新加载数据
  await loadAchievements()
  // 滚动到顶部
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

// 需求搜索
const handleNeedSearch = () => {
  needPage.value = 1
  loadNeeds()
}

// 加载需求数据
const loadNeeds = async () => {
  loadingNeeds.value = true
  try {
    const response = await api.get('/publish/needs', {
      params: { 
        page: needPage.value, 
        page_size: needPageSize.value,
        keyword: needSearchQuery.value || undefined
      }
    })
    if (response.data) {
      needTotal.value = response.data.total || 0
      if (response.data.items) {
        paginatedNeeds.value = response.data.items.map(need => ({
          ...need,
          data_source: '用户发布',
          publish_time: need.created_at
        }))
      }
    }
  } catch (error) {
    ElMessage.error('加载需求数据失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loadingNeeds.value = false
  }
}

// 需求分页改变
const handleNeedPageChange = (page) => {
  needPage.value = page
  loadNeeds()
  // 滚动到顶部
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

// Mock 成果数据（已废弃，保留用于参考）
const mockAchievements = ref([
  {
    id: 1,
    title: '基于深度学习的智能图像识别系统',
    description: '采用卷积神经网络(CNN)和Transformer架构，实现高精度的图像分类和目标检测。系统支持多场景应用，包括医疗影像分析、工业质检、自动驾驶等领域。准确率达到98.5%，处理速度提升40%。',
    field: '人工智能/计算机视觉',
    publish_time: '2024-01-15',
    data_source: '用户发布'
  },
  {
    id: 2,
    title: '大语言模型驱动的智能对话系统',
    description: '基于Transformer架构的大语言模型，支持多轮对话、上下文理解和知识检索。模型参数量达到70B，在中文理解、代码生成、逻辑推理等任务上表现优异。已应用于智能客服、教育辅导、代码助手等多个场景。',
    field: '自然语言处理/大语言模型',
    publish_time: '2024-01-12',
    data_source: '系统采集'
  },
  {
    id: 3,
    title: '基于强化学习的智能决策优化算法',
    description: '采用深度强化学习(DRL)方法，解决复杂环境下的决策优化问题。算法在资源调度、路径规划、游戏策略等场景中表现突出，相比传统方法效率提升50%以上。支持在线学习和策略迁移。',
    field: '强化学习/决策优化',
    publish_time: '2024-01-10',
    data_source: '用户发布'
  },
  {
    id: 4,
    title: '联邦学习隐私保护框架',
    description: '构建分布式机器学习框架，在保护数据隐私的前提下实现模型协同训练。采用差分隐私、同态加密等技术，确保数据不出本地即可完成模型训练。已在医疗、金融等敏感领域应用。',
    field: '联邦学习/隐私计算',
    publish_time: '2024-01-08',
    data_source: '系统采集'
  },
  {
    id: 5,
    title: 'AI驱动的智能推荐系统',
    description: '基于深度学习的个性化推荐算法，融合协同过滤、内容推荐和深度学习技术。支持多模态内容理解，推荐准确率提升35%，用户点击率提升28%。已应用于电商、视频、新闻等多个平台。',
    field: '推荐系统/深度学习',
    publish_time: '2024-01-05',
    data_source: '用户发布'
  },
  {
    id: 6,
    title: '生成式AI内容创作平台',
    description: '集成文本生成、图像生成、视频生成等多种生成式AI能力，支持多模态内容创作。采用扩散模型和GAN技术，生成内容质量达到商业应用标准。已申请多项技术专利。',
    field: '生成式AI/多模态学习',
    publish_time: '2024-01-03',
    data_source: '系统采集'
  }
])

// Mock 需求数据
const mockNeeds = ref([
  {
    id: 101,
    title: '寻求AI驱动的智能客服解决方案',
    description: '公司需要一套基于自然语言处理的智能客服系统，能够处理多轮对话、情感识别和知识库检索。要求支持中英文，响应时间小于2秒，准确率高于90%。希望与有相关技术积累的科研团队合作。',
    industry: '互联网/电商',
    company_name: '某科技股份有限公司',
    publish_time: '2024-01-14',
    data_source: '用户发布'
  },
  {
    id: 102,
    title: 'AI视觉检测系统开发需求',
    description: '制造企业需要部署基于深度学习的视觉检测系统，用于产品质量自动检测。要求支持多种缺陷类型识别，检测准确率高于99%，处理速度满足生产线实时要求。希望与有工业AI应用经验的团队合作。',
    industry: '制造业',
    company_name: '某智能制造科技公司',
    publish_time: '2024-01-11',
    data_source: '系统采集'
  },
  {
    id: 103,
    title: '大语言模型定制化训练服务',
    description: '企业需要针对特定领域（如法律、医疗）定制化训练大语言模型。要求模型具备领域专业知识，支持长文本理解，能够进行专业问答和文档生成。希望与有LLM训练经验的科研院所合作。',
    industry: '企业服务',
    company_name: '某AI技术服务公司',
    publish_time: '2024-01-09',
    data_source: '用户发布'
  },
  {
    id: 104,
    title: 'AI驱动的智能推荐算法优化',
    description: '电商平台需要优化现有的推荐系统，提升推荐准确性和多样性。要求算法支持冷启动、实时推荐、多目标优化等功能。希望与推荐算法领域的专家团队合作，提供技术方案和算法优化服务。',
    industry: '互联网/电商',
    company_name: '某电商平台',
    publish_time: '2024-01-07',
    data_source: '用户发布'
  },
  {
    id: 105,
    title: '联邦学习隐私计算平台',
    description: '金融机构需要构建联邦学习平台，在保护数据隐私的前提下实现跨机构模型训练。要求支持多种联邦学习算法，具备完善的隐私保护机制，符合金融行业监管要求。',
    industry: '金融科技',
    company_name: '某金融科技公司',
    publish_time: '2024-01-04',
    data_source: '系统采集'
  },
  {
    id: 106,
    title: '医疗影像AI辅助诊断系统',
    description: '医疗机构寻求医疗影像AI辅助诊断技术，支持CT、MRI、X光等多种影像类型的自动分析和病灶识别。要求诊断准确率高，符合医疗器械相关标准，能够辅助医生提高诊断效率。',
    industry: '医疗健康',
    company_name: '某医疗科技公司',
    publish_time: '2024-01-02',
    data_source: '用户发布'
  }
])

// Mock 联系人信息
const mockContactInfo = {
  contact_name: '张教授',
  phone: '138-0000-1234',
  email: 'zhang.prof@ai-lab.edu.cn'
}

// 打开抽屉
const openDrawer = (item, type) => {
  currentItem.value = item
  drawerType.value = type
  if (type === 'achievement') {
    // 根据数据类型设置标题
    if (item.type === 'paper') {
      drawerTitle.value = '论文详情'
    } else {
      drawerTitle.value = '成果详情'
    }
  } else {
    drawerTitle.value = '需求详情'
  }
  drawerVisible.value = true
}

// 爬虫相关状态
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
  // 根据路由参数恢复标签页状态
  if (route.query.tab) {
    const tab = route.query.tab.toString()
    if (tab === 'achievements' || tab === 'needs') {
      activeTab.value = tab
    }
  }
  
  // 加载资源大厅数据
  loadAchievements()
  loadNeeds()
  
  // 加载统计信息和爬虫状态
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
.dashboard {
  min-height: calc(100vh - 60px);
  background: #f5f5f5;
  padding: 20px 0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.title {
  font-size: 32px;
  margin: 10px 0;
  color: #1f2937;
}

.subtitle {
  color: #6b7280;
  margin-bottom: 24px;
  font-size: 14px;
}

.actions {
  margin: 20px 0;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.section {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.06);
  margin-top: 20px;
  margin-bottom: 20px;
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

.resource-tabs {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.06);
}

.card-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 20px;
}

.resource-card {
  transition: all 0.3s;
}

.resource-card:hover {
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
  transform: translateY(-2px);
}

.card-content {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 20px;
}

.card-main {
  flex: 1;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
  gap: 12px;
}

.card-title {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
  flex: 1;
}

.card-description {
  color: #6b7280;
  font-size: 14px;
  line-height: 1.6;
  margin: 0 0 12px 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  font-size: 13px;
  color: #9ca3af;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.meta-item .el-icon {
  font-size: 14px;
}

.card-action {
  flex-shrink: 0;
}

.drawer-content {
  padding: 0 10px;
}

.detail-section {
  margin-bottom: 24px;
}

.detail-title {
  font-size: 20px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 12px 0;
}

.detail-tag {
  margin-bottom: 16px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #374151;
  margin: 0 0 8px 0;
}

.section-content {
  font-size: 14px;
  color: #6b7280;
  line-height: 1.6;
  margin: 0;
}

.contact-info {
  background: #f9fafb;
  padding: 16px;
  border-radius: 8px;
}

.contact-info p {
  margin: 8px 0;
  font-size: 14px;
  color: #374151;
}

.contact-info strong {
  color: #1f2937;
}

.pagination-container {
  margin-top: 24px;
  display: flex;
  justify-content: center;
  padding: 20px 0;
}

.search-section {
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 12px;
}
</style>

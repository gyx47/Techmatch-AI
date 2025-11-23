<template>
  <div class="dashboard">
    <div class="container">
      <h1 class="title">资源大厅</h1>
      <p class="subtitle">浏览全网最新科研成果与企业需求</p>

      <el-tabs v-model="activeTab" class="resource-tabs">
        <el-tab-pane label="找成果" name="achievements">
          <div class="card-list">
            <el-card
              v-for="item in mockAchievements"
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
                      <el-icon><FolderOpened /></el-icon>
                      {{ item.field }}
                    </span>
                    <span class="meta-item">
                      <el-icon><Clock /></el-icon>
                      {{ item.publish_time }}
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
          </div>
        </el-tab-pane>

        <el-tab-pane label="找需求" name="needs">
          <div class="card-list">
            <el-card
              v-for="item in mockNeeds"
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
                      {{ item.publish_time }}
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
          <div class="detail-section">
            <h3 class="detail-title">{{ currentItem.title }}</h3>
            <div class="detail-tag">
              <el-tag
                :type="currentItem.data_source === '用户发布' ? 'primary' : 'info'"
                size="small"
              >
                {{ currentItem.data_source }}
              </el-tag>
            </div>
          </div>

          <div class="detail-section">
            <h4 class="section-title">简介</h4>
            <p class="section-content">{{ currentItem.description }}</p>
          </div>

          <div class="detail-section" v-if="drawerType === 'achievement'">
            <h4 class="section-title">技术领域</h4>
            <p class="section-content">{{ currentItem.field }}</p>
          </div>

          <div class="detail-section" v-if="drawerType === 'need'">
            <h4 class="section-title">企业信息</h4>
            <p class="section-content">
              <strong>公司名称：</strong>{{ currentItem.company_name }}<br />
              <strong>所属行业：</strong>{{ currentItem.industry }}
            </p>
          </div>

          <div class="detail-section">
            <h4 class="section-title">发布时间</h4>
            <p class="section-content">{{ currentItem.publish_time }}</p>
          </div>

          <!-- 用户发布的数据显示联系人信息 -->
          <div class="detail-section" v-if="currentItem.data_source === '用户发布'">
            <el-divider />
            <h4 class="section-title">联系方式</h4>
            <div class="contact-info">
              <p><strong>联系人：</strong>{{ mockContactInfo.contact_name }}</p>
              <p><strong>联系电话：</strong>{{ mockContactInfo.phone }}</p>
              <p><strong>联系邮箱：</strong>{{ mockContactInfo.email }}</p>
            </div>
          </div>

        </div>
      </el-drawer>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { FolderOpened, Clock, OfficeBuilding, Collection } from '@element-plus/icons-vue'

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

// Mock 成果数据
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
  drawerTitle.value = type === 'achievement' ? '成果详情' : '需求详情'
  drawerVisible.value = true
}

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
</style>

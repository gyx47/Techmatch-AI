<template>
  <div class="publish-center">
    <div class="container">
      <el-row :gutter="20">
        <!-- 左侧介绍区域 -->
        <el-col :span="10">
          <div class="panel hero">
            <h2>Share Your Vision</h2>
            <p v-if="userStore.userInfo?.role === 'researcher'">
              发布您的科研成果，让更多企业发现您的技术价值，开启合作之旅。
            </p>
            <p v-else-if="userStore.userInfo?.role === 'enterprise'">
              发布您的技术需求，让AI为您匹配最合适的科研成果和专家团队。
            </p>
            <p v-else>
              描述你的技术需求或研究兴趣，我们将为你匹配合适的研究成果。
            </p>
          </div>
        </el-col>

        <!-- 右侧表单区域 -->
        <el-col :span="14">
          <div class="panel form">
            <h2 class="page-title">发布中心</h2>
            <p class="page-subtitle">发布您的科研成果或企业需求，让更多人看到</p>

            <!-- 未登录或无角色提示 -->
            <div v-if="!userStore.isLoggedIn || !userStore.userInfo?.role" class="no-role-tip">
              <el-alert
                title="请先登录并选择角色"
                type="warning"
                :closable="false"
                show-icon
              >
                <template #default>
                  <p>您需要登录并选择角色（科研人员或企业用户）后才能发布内容。</p>
                  <el-button type="primary" @click="$router.push('/login')" style="margin-top: 12px;">
                    前往登录
                  </el-button>
                </template>
              </el-alert>
            </div>

            <!-- 成果发布表单（科研人员） -->
            <div v-else-if="userStore.userInfo.role === 'researcher'" class="form-container">
              <h3 class="form-title">成果发布</h3>
              <el-form
                :model="achievementForm"
                :rules="achievementRules"
                ref="achievementFormRef"
                label-position="top"
              >
                <el-form-item label="成果名称" prop="name">
                  <el-input
                    v-model="achievementForm.name"
                    placeholder="请输入成果名称"
                    :disabled="submitting"
                  />
                </el-form-item>

                <el-form-item label="技术领域" prop="field">
                  <el-select
                    v-model="achievementForm.field"
                    placeholder="请选择技术领域"
                    style="width: 100%"
                    :disabled="submitting"
                  >
                    <el-option label="人工智能/机器学习" value="人工智能/机器学习" />
                    <el-option label="计算机视觉" value="计算机视觉" />
                    <el-option label="自然语言处理" value="自然语言处理" />
                    <el-option label="区块链技术" value="区块链技术" />
                    <el-option label="新能源材料" value="新能源材料" />
                    <el-option label="生物医药" value="生物医药" />
                    <el-option label="通信工程" value="通信工程" />
                    <el-option label="大数据/云计算" value="大数据/云计算" />
                    <el-option label="物联网" value="物联网" />
                    <el-option label="其他" value="其他" />
                  </el-select>
                </el-form-item>

                <el-form-item label="成果简介" prop="description">
                  <el-input
                    v-model="achievementForm.description"
                    type="textarea"
                    :rows="6"
                    placeholder="请详细描述您的科研成果，包括技术特点、创新点、应用价值等..."
                    :disabled="submitting"
                  />
                </el-form-item>

                <el-form-item label="应用场景" prop="application">
                  <el-input
                    v-model="achievementForm.application"
                    type="textarea"
                    :rows="3"
                    placeholder="请描述该成果的应用场景和适用领域..."
                    :disabled="submitting"
                  />
                </el-form-item>

                <el-form-item label="合作方式">
                  <el-select
                    v-model="achievementForm.cooperation_mode"
                    multiple
                    placeholder="请选择合作方式（可多选）"
                    style="width: 100%"
                    :disabled="submitting"
                  >
                    <el-option label="技术转让" value="技术转让" />
                    <el-option label="联合开发" value="联合开发" />
                    <el-option label="授权许可" value="授权许可" />
                    <el-option label="技术咨询" value="技术咨询" />
                    <el-option label="其他" value="其他" />
                  </el-select>
                </el-form-item>

                <el-form-item label="联系人" prop="contact_name">
                  <el-input
                    v-model="achievementForm.contact_name"
                    placeholder="请输入联系人姓名"
                    :disabled="submitting"
                  />
                </el-form-item>

                <el-form-item label="电话" prop="contact_phone">
                  <el-input
                    v-model="achievementForm.contact_phone"
                    placeholder="请输入联系电话"
                    :disabled="submitting"
                  />
                </el-form-item>

                <el-form-item label="联系邮箱">
                  <el-input
                    v-model="achievementForm.contact_email"
                    type="email"
                    placeholder="请输入联系邮箱（可选）"
                    :disabled="submitting"
                  />
                </el-form-item>

                <el-form-item>
                  <el-button
                    type="primary"
                    size="large"
                    :loading="submitting"
                    @click="submitAchievement"
                    style="width: 100%"
                  >
                    发布成果
                  </el-button>
                </el-form-item>
              </el-form>
            </div>

            <!-- 需求发布表单（企业用户） -->
            <div v-else-if="userStore.userInfo.role === 'enterprise'" class="form-container">
              <h3 class="form-title">需求发布</h3>
              <el-form
                :model="needForm"
                :rules="needRules"
                ref="needFormRef"
                label-position="top"
              >
                <el-form-item label="需求标题" prop="title">
                  <el-input
                    v-model="needForm.title"
                    placeholder="请输入需求标题"
                    :disabled="submitting"
                  />
                </el-form-item>

                <el-form-item label="行业领域" prop="industry">
                  <el-select
                    v-model="needForm.industry"
                    placeholder="请选择行业领域"
                    style="width: 100%"
                    :disabled="submitting"
                  >
                    <el-option label="互联网/电商" value="互联网/电商" />
                    <el-option label="制造业" value="制造业" />
                    <el-option label="金融科技" value="金融科技" />
                    <el-option label="医疗健康" value="医疗健康" />
                    <el-option label="新能源汽车" value="新能源汽车" />
                    <el-option label="智慧农业" value="智慧农业" />
                    <el-option label="教育科技" value="教育科技" />
                    <el-option label="能源环保" value="能源环保" />
                    <el-option label="物流运输" value="物流运输" />
                    <el-option label="其他" value="其他" />
                  </el-select>
                </el-form-item>

                <el-form-item label="需求详细描述" prop="description">
                  <el-input
                    v-model="needForm.description"
                    type="textarea"
                    :rows="6"
                    placeholder="请详细描述您的技术需求，包括具体需求、技术要求、预期目标等..."
                    :disabled="submitting"
                  />
                </el-form-item>

                <el-form-item label="紧急程度">
                  <el-select
                    v-model="needForm.urgency_level"
                    placeholder="请选择紧急程度"
                    style="width: 100%"
                    :disabled="submitting"
                  >
                    <el-option label="一般" value="一般" />
                    <el-option label="较急" value="较急" />
                    <el-option label="紧急" value="紧急" />
                  </el-select>
                </el-form-item>

                <el-form-item label="合作方式偏好">
                  <el-select
                    v-model="needForm.cooperation_preference"
                    multiple
                    placeholder="请选择合作方式偏好（可多选）"
                    style="width: 100%"
                    :disabled="submitting"
                  >
                    <el-option label="技术转让" value="技术转让" />
                    <el-option label="联合开发" value="联合开发" />
                    <el-option label="授权许可" value="授权许可" />
                    <el-option label="技术咨询" value="技术咨询" />
                    <el-option label="其他" value="其他" />
                  </el-select>
                </el-form-item>

                <el-form-item label="预算范围">
                  <el-select
                    v-model="needForm.budget_range"
                    placeholder="请选择预算范围"
                    style="width: 100%"
                    :disabled="submitting"
                  >
                    <el-option label="10万以下" value="10万以下" />
                    <el-option label="10-50万" value="10-50万" />
                    <el-option label="50-100万" value="50-100万" />
                    <el-option label="100-500万" value="100-500万" />
                    <el-option label="500万以上" value="500万以上" />
                    <el-option label="面议" value="面议" />
                  </el-select>
                </el-form-item>

                <el-form-item label="企业名称" prop="company_name">
                  <el-input
                    v-model="needForm.company_name"
                    placeholder="请输入企业名称"
                    :disabled="submitting"
                  />
                </el-form-item>

                <el-form-item label="联系人" prop="contact_name">
                  <el-input
                    v-model="needForm.contact_name"
                    placeholder="请输入联系人姓名"
                    :disabled="submitting"
                  />
                </el-form-item>

                <el-form-item label="电话" prop="contact_phone">
                  <el-input
                    v-model="needForm.contact_phone"
                    placeholder="请输入联系电话"
                    :disabled="submitting"
                  />
                </el-form-item>

                <el-form-item label="联系邮箱">
                  <el-input
                    v-model="needForm.contact_email"
                    type="email"
                    placeholder="请输入联系邮箱（可选）"
                    :disabled="submitting"
                  />
                </el-form-item>

                <el-form-item>
                  <el-button
                    type="primary"
                    size="large"
                    :loading="submitting"
                    @click="submitNeed"
                    style="width: 100%"
                  >
                    发布需求
                  </el-button>
                </el-form-item>
              </el-form>
            </div>
          </div>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { ElMessage } from 'element-plus'
import api from '../api'

const router = useRouter()
const userStore = useUserStore()

const submitting = ref(false)
const achievementFormRef = ref()
const needFormRef = ref()

// 成果发布表单
const achievementForm = reactive({
  name: '',
  field: '',
  description: '',
  application: '',
  cooperation_mode: [],
  contact_name: '',
  contact_phone: '',
  contact_email: ''
})

// 需求发布表单
const needForm = reactive({
  title: '',
  industry: '',
  description: '',
  urgency_level: '',
  cooperation_preference: [],
  budget_range: '',
  company_name: '',
  contact_name: '',
  contact_phone: '',
  contact_email: ''
})

// 成果表单验证规则
const achievementRules = {
  name: [{ required: true, message: '请输入成果名称', trigger: 'blur' }],
  field: [{ required: true, message: '请选择技术领域', trigger: 'change' }],
  description: [
    { required: true, message: '请输入成果简介', trigger: 'blur' },
    { min: 20, message: '成果简介至少需要20个字符', trigger: 'blur' }
  ],
  application: [{ required: true, message: '请输入应用场景', trigger: 'blur' }],
  contact_name: [{ required: true, message: '请输入联系人', trigger: 'blur' }],
  contact_phone: [
    { required: true, message: '请输入联系电话', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$|^0\d{2,3}-?\d{7,8}$/, message: '请输入正确的电话号码', trigger: 'blur' }
  ]
}

// 需求表单验证规则
const needRules = {
  title: [{ required: true, message: '请输入需求标题', trigger: 'blur' }],
  industry: [{ required: true, message: '请选择行业领域', trigger: 'change' }],
  description: [
    { required: true, message: '请输入需求详细描述', trigger: 'blur' },
    { min: 20, message: '需求描述至少需要20个字符', trigger: 'blur' }
  ],
  company_name: [{ required: true, message: '请输入企业名称', trigger: 'blur' }],
  contact_name: [{ required: true, message: '请输入联系人', trigger: 'blur' }],
  contact_phone: [
    { required: true, message: '请输入联系电话', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$|^0\d{2,3}-?\d{7,8}$/, message: '请输入正确的电话号码', trigger: 'blur' }
  ]
}

// 提交成果
const submitAchievement = async () => {
  if (!achievementFormRef.value) return

  await achievementFormRef.value.validate(async (valid) => {
    if (!valid) return

    submitting.value = true

    try {
      const response = await api.post('/publish/achievement', achievementForm)
      ElMessage.success('成果发布成功！')
      
      // 清空表单
      Object.assign(achievementForm, {
        name: '',
        field: '',
        description: '',
        application: '',
        cooperation_mode: [],
        contact_name: '',
        contact_phone: '',
        contact_email: ''
      })

      // 清除表单验证状态
      achievementFormRef.value.clearValidate()
    } catch (error) {
      ElMessage.error('发布失败: ' + (error.response?.data?.detail || error.message || '未知错误'))
    } finally {
      submitting.value = false
    }
  })
}

// 提交需求
const submitNeed = async () => {
  if (!needFormRef.value) return

  await needFormRef.value.validate(async (valid) => {
    if (!valid) return

    submitting.value = true

    try {
      const response = await api.post('/publish/need', needForm)
      ElMessage.success('需求发布成功！')
      
      // 清空表单
      Object.assign(needForm, {
        title: '',
        industry: '',
        description: '',
        urgency_level: '',
        cooperation_preference: [],
        budget_range: '',
        company_name: '',
        contact_name: '',
        contact_phone: '',
        contact_email: ''
      })

      // 清除表单验证状态
      needFormRef.value.clearValidate()
    } catch (error) {
      ElMessage.error('发布失败: ' + (error.response?.data?.detail || error.message || '未知错误'))
    } finally {
      submitting.value = false
    }
  })
}
</script>

<style scoped>
.publish-center {
  min-height: calc(100vh - 60px);
  background: #f5f5f5;
  padding: 20px 0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.panel {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.06);
}

.hero {
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.hero h2 {
  font-size: 24px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 16px 0;
}

.hero p {
  color: #6b7280;
  line-height: 1.7;
  font-size: 15px;
  margin: 0;
}

.form h2 {
  margin-bottom: 10px;
}

.page-title {
  font-size: 28px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 8px 0;
}

.page-subtitle {
  font-size: 14px;
  color: #6b7280;
  margin: 0 0 32px 0;
}

.no-role-tip {
  margin-top: 20px;
}

.no-role-tip :deep(.el-alert__content) {
  width: 100%;
}

.form-container {
  margin-top: 24px;
}

.form-title {
  font-size: 20px;
  font-weight: 600;
  color: #374151;
  margin: 0 0 24px 0;
  padding-bottom: 12px;
  border-bottom: 2px solid #e5e7eb;
}

:deep(.el-form-item__label) {
  font-weight: 500;
  color: #374151;
  margin-bottom: 8px;
}

:deep(.el-input__inner),
:deep(.el-textarea__inner) {
  border-radius: 6px;
}

:deep(.el-select) {
  width: 100%;
}
</style>


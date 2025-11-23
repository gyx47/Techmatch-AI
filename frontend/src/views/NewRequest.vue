<template>
  <div class="new-request">
    <div class="container">
      <el-row :gutter="20">
        <el-col :span="10">
          <div class="panel hero">
            <h2>Share Your Vision</h2>
            <p>描述你的技术需求或研究兴趣，我们将为你匹配合适的研究成果。</p>
          </div>
        </el-col>
        <el-col :span="14">
          <div class="panel form">
            <h2>Submit a New Request</h2>
            <el-form :model="form" label-width="120px">
              <el-form-item label="Request Title">
                <el-input v-model="form.title" placeholder="e.g., AI-powered logistics optimization" />
              </el-form-item>
              <el-form-item label="Detailed Description">
                <el-input v-model="form.description" type="textarea" :rows="5" placeholder="Describe your requirements, challenges, and desired outcomes..." />
              </el-form-item>
              <el-form-item label="Keywords / Phrases">
                <el-select v-model="form.keywords" multiple filterable allow-create default-first-option placeholder="e.g., machine learning, supply chain">
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="submit" :loading="submitting">
                  {{ submitting ? '提交中...' : 'Submit Request' }}
                </el-button>
              </el-form-item>
            </el-form>
          </div>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import api from '../api'

const router = useRouter()
const form = reactive({ title: '', description: '', keywords: [] })
const submitting = ref(false)

const submit = async () => {
  if (!form.description || !form.description.trim()) {
    return ElMessage.warning('请填写详细描述')
  }
  
  submitting.value = true
  try {
    // 构建需求文本：标题 + 描述 + 关键词
    const requirement = [
      form.title && `标题: ${form.title}`,
      `需求描述: ${form.description}`,
      form.keywords.length > 0 && `关键词: ${form.keywords.join(', ')}`
    ].filter(Boolean).join('\n\n')
    
    // 调用匹配API
    const response = await api.post('/matching/match', {
      requirement: requirement,
      top_k: 50
    })
    
    ElMessage.success(`匹配完成！找到 ${response.data.total || 0} 篇相关论文，正在跳转到结果页面...`)
    
    // 将匹配结果存储到sessionStorage，然后跳转
    sessionStorage.setItem('matchingResults', JSON.stringify(response.data))
    router.push({ name: 'MatchingResults' })
  } catch (error) {
    ElMessage.error('提交失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.container { max-width: 1200px; margin: 0 auto; padding: 20px; }
.panel { background: #fff; border-radius: 12px; padding: 24px; box-shadow: 0 2px 10px rgba(0,0,0,.06); }
.hero { height: 100%; display: flex; flex-direction: column; justify-content: center; }
.form h2 { margin-bottom: 10px; }
</style>

 
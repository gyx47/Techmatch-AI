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
                <el-button type="primary" @click="submit">Submit Request</el-button>
              </el-form-item>
            </el-form>
          </div>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import { reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'

const router = useRouter()
const form = reactive({ title: '', description: '', keywords: [] })

const submit = () => {
  if (!form.title) return ElMessage.warning('请填写标题')
  router.push({ name: 'MatchingResults', query: { q: form.keywords.join(',') } })
}
</script>

<style scoped>
.container { max-width: 1200px; margin: 0 auto; padding: 20px; }
.panel { background: #fff; border-radius: 12px; padding: 24px; box-shadow: 0 2px 10px rgba(0,0,0,.06); }
.hero { height: 100%; display: flex; flex-direction: column; justify-content: center; }
.form h2 { margin-bottom: 10px; }
</style>

 
<template>
  <div class="matches">
    <div class="container">
      <h1 class="title">AI Matching Results</h1>
      <p class="subtitle">基于你的需求关键词，展示可能匹配的研究成果与解决方案</p>

      <el-row :gutter="20">
        <el-col :span="8" v-for="item in results" :key="item.id">
          <div class="card">
            <div class="card-header">
              <h3>{{ item.title }}</h3>
            </div>
            <div class="card-body">
              <p class="desc">{{ item.desc }}</p>
              <div class="confidence">
                <span>Match Confidence</span>
                <el-progress :percentage="item.confidence" :stroke-width="10" status="success" />
              </div>
            </div>
            <div class="card-footer">
              <el-button type="primary" @click="$router.push('/solution/' + item.id)">View Solution</el-button>
            </div>
          </div>
        </el-col>
      </el-row>

      <div class="pagination">
        <el-pagination layout="prev, pager, next" :total="100" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const results = ref([])

onMounted(() => {
  const q = (route.query.q || '').toString()
  results.value = [
    { id: 101, title: 'Deep Learning for Image Recognition', desc: 'Advanced ML techniques for image recognition', confidence: 95 },
    { id: 102, title: 'NLP for Sentiment Analysis', desc: 'Large-language-model-based sentiment analysis', confidence: 88 },
    { id: 103, title: 'Reinforcement Learning for Cloud', desc: 'Optimize resource allocation using RL', confidence: 75 }
  ]
})
</script>

<style scoped>
.container { max-width: 1200px; margin: 0 auto; padding: 20px; }
.title { font-size: 32px; margin: 10px 0; }
.subtitle { color: #666; margin-bottom: 20px; }
.card { background: #fff; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,.06); padding: 20px; display: flex; flex-direction: column; height: 100%; }
.card-header h3 { margin: 0 0 10px; }
.desc { color: #666; min-height: 60px; }
.confidence { margin: 10px 0; }
.card-footer { margin-top: auto; }
.pagination { margin-top: 20px; text-align: center; }
</style>



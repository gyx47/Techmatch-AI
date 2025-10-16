<template>
  <div class="solution">
    <div class="container">
      <h1 class="title">AI-Powered Image Recognition</h1>
      <p class="subtitle">Generated solution proposal with linked patents and documentation</p>

      <el-row :gutter="20">
        <el-col :span="16">
          <div class="panel">
            <h3>Solution Summary</h3>
            <p>
              This solution leverages cutting-edge AI techniques to improve image recognition capabilities,
              ideal for applications such as object detection and classification.
            </p>
          </div>

          <div class="panel">
            <h3>Related Academic Papers</h3>
            <el-timeline>
              <el-timeline-item v-for="p in papers" :key="p.id" :timestamp="p.date">
                <div class="paper-item">
                  <div class="paper-title">{{ p.title }}</div>
                  <div class="paper-meta">Authors: {{ p.authors }}</div>
                  <el-link type="primary" :href="p.url" target="_blank">View on arXiv</el-link>
                </div>
              </el-timeline-item>
            </el-timeline>
          </div>
        </el-col>

        <el-col :span="8">
          <div class="panel">
            <h3>Key Concepts</h3>
            <div class="tags">
              <el-tag v-for="t in tags" :key="t" type="info" class="tag">{{ t }}</el-tag>
            </div>
          </div>

          <div class="panel">
            <h3>Linked Patents</h3>
            <el-list>
              <el-list-item v-for="pt in patents" :key="pt.id">
                <div class="patent">
                  <div class="patent-title">{{ pt.title }}</div>
                  <el-tag :type="pt.status === 'Granted' ? 'success' : 'warning'">{{ pt.status }}</el-tag>
                </div>
              </el-list-item>
            </el-list>
          </div>

          <div class="panel">
            <h3>Contact Team</h3>
            <el-button type="primary">Contact</el-button>
          </div>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const tags = ref(['Image Recognition', 'Deep Learning', 'CNN', 'Object Detection'])
const papers = ref([
  { id: 1, title: 'Advancements in CNNs for Image Recognition', authors: 'Li, Zhang, Wang', date: '2023-03-01', url: 'https://arxiv.org' },
  { id: 2, title: 'A Novel Approach to Object Detection Using Deep Learning', authors: 'Chen, Liu, Xu', date: '2022-11-15', url: 'https://arxiv.org' }
])
const patents = ref([
  { id: 11, title: 'Method for Enhanced Image Recognition', status: 'Granted' },
  { id: 12, title: 'System for Real-Time Object Detection', status: 'Pending' }
])
</script>

<style scoped>
.container { max-width: 1200px; margin: 0 auto; padding: 20px; }
.title { font-size: 28px; margin: 8px 0; }
.subtitle { color: #666; margin-bottom: 16px; }
.panel { background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,.06); margin-bottom: 16px; }
.tags .tag { margin: 4px; }
.paper-item .paper-title { font-weight: 600; }
.patent { display:flex; align-items:center; justify-content:space-between; }
</style>



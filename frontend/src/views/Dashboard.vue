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
    </div>
  </div>
</template>

<script setup>
import { reactive } from 'vue'

const stats = reactive({ totalRequests: 5, activeMatches: 2, completedMatches: 3 })
const recent = reactive([
  { id: 1, title: 'AI-Powered Image Recognition for Manufacturing', status: 'In Progress', date: '2023-11-15' },
  { id: 2, title: 'Predictive Maintenance using Machine Learning', status: 'Completed', date: '2023-10-20' },
  { id: 3, title: 'Natural Language Processing for Customer Service', status: 'Completed', date: '2023-09-05' }
])
</script>

<style scoped>
.container { max-width: 1200px; margin: 0 auto; padding: 20px; }
.title { font-size: 32px; margin: 10px 0; }
.subtitle { color: #666; margin-bottom: 20px; }
.stats .card { background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,.06); }
.card-title { color: #666; }
.card-value { font-size: 28px; font-weight: 700; margin-top: 6px; }
.actions { margin: 20px 0; display: flex; gap: 12px; }
.section { background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,.06); }
</style>

 
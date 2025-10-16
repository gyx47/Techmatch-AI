<template>
  <div class="home">
    <!-- 英雄区域 -->
    <div class="hero-section">
      <div class="hero-content">
        <h1 class="hero-title">AI论文搜索系统</h1>
        <p class="hero-subtitle">
          基于人工智能的智能论文搜索平台，让学术研究更高效
        </p>
        <div class="hero-actions">
          <el-button
            v-if="!userStore.isLoggedIn"
            type="primary"
            size="large"
            @click="$router.push('/search')"
          >
            开始搜索
          </el-button>
          <el-button
            v-else
            type="primary"
            size="large"
            @click="$router.push('/search')"
          >
            进入搜索
          </el-button>
        </div>
      </div>
    </div>

    <!-- 功能特性 -->
    <div class="features-section">
      <div class="container">
        <h2 class="section-title">核心功能</h2>
        <div class="features-grid">
          <div class="feature-card">
            <div class="feature-icon">
              <el-icon><Search /></el-icon>
            </div>
            <h3>智能搜索</h3>
            <p>基于arXiv API的智能论文搜索，支持关键词、作者、分类等多种搜索方式</p>
          </div>
          <div class="feature-card">
            <div class="feature-icon">
              <el-icon><ChatDotRound /></el-icon>
            </div>
            <h3>AI助手</h3>
            <p>集成OpenAI GPT模型，提供论文摘要、问答和学术讨论功能</p>
          </div>
          <div class="feature-card">
            <div class="feature-icon">
              <el-icon><Document /></el-icon>
            </div>
            <h3>论文管理</h3>
            <p>本地数据库存储，支持搜索历史记录和个性化推荐</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 技术栈 -->
    <div class="tech-section">
      <div class="container">
        <h2 class="section-title">技术栈</h2>
        <div class="tech-grid">
          <div class="tech-item">
            <h4>前端</h4>
            <ul>
              <li>Vue 3 + Composition API</li>
              <li>Vite 构建工具</li>
              <li>Element Plus UI组件</li>
              <li>Pinia 状态管理</li>
              <li>Axios HTTP客户端</li>
            </ul>
          </div>
          <div class="tech-item">
            <h4>后端</h4>
            <ul>
              <li>FastAPI 高性能框架</li>
              <li>Uvicorn ASGI服务器</li>
              <li>SQLite 轻量级数据库</li>
              <li>JWT 身份认证</li>
              <li>OpenAI API 集成</li>
            </ul>
          </div>
          <div class="tech-item">
            <h4>数据源</h4>
            <ul>
              <li>arXiv API 论文数据</li>
              <li>OpenAI GPT 智能对话</li>
              <li>本地SQLite存储</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useUserStore } from '../stores/user'
import { Search, ChatDotRound, Document } from '@element-plus/icons-vue'

const userStore = useUserStore()
</script>

<style scoped>
.home {
  min-height: 100vh;
}

.hero-section {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 80px 0;
  text-align: center;
}

.hero-content {
  max-width: 800px;
  margin: 0 auto;
  padding: 0 20px;
}

.hero-title {
  font-size: 3.5rem;
  font-weight: bold;
  margin-bottom: 20px;
  line-height: 1.2;
}

.hero-subtitle {
  font-size: 1.2rem;
  margin-bottom: 40px;
  opacity: 0.9;
  line-height: 1.6;
}

.hero-actions {
  margin-top: 30px;
}

.features-section,
.tech-section {
  padding: 80px 0;
  background: white;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.section-title {
  text-align: center;
  font-size: 2.5rem;
  margin-bottom: 60px;
  color: #333;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 40px;
  margin-top: 40px;
}

.feature-card {
  text-align: center;
  padding: 40px 20px;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  transition: transform 0.3s ease;
}

.feature-card:hover {
  transform: translateY(-5px);
}

.feature-icon {
  width: 80px;
  height: 80px;
  margin: 0 auto 20px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 2rem;
}

.feature-card h3 {
  font-size: 1.5rem;
  margin-bottom: 15px;
  color: #333;
}

.feature-card p {
  color: #666;
  line-height: 1.6;
}

.tech-section {
  background: #f8f9fa;
}

.tech-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 40px;
  margin-top: 40px;
}

.tech-item {
  background: white;
  padding: 30px;
  border-radius: 12px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.tech-item h4 {
  font-size: 1.3rem;
  margin-bottom: 20px;
  color: #333;
  border-bottom: 2px solid #667eea;
  padding-bottom: 10px;
}

.tech-item ul {
  list-style: none;
  padding: 0;
}

.tech-item li {
  padding: 8px 0;
  color: #666;
  border-bottom: 1px solid #f0f0f0;
}

.tech-item li:last-child {
  border-bottom: none;
}

@media (max-width: 768px) {
  .hero-title {
    font-size: 2.5rem;
  }
  
  .section-title {
    font-size: 2rem;
  }
  
  .features-grid,
  .tech-grid {
    grid-template-columns: 1fr;
  }
}
</style>

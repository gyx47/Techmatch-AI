<template>
  <div class="home">
    <!-- 英雄区域 -->
    <div class="hero-section">
      <div class="hero-content">
        <h1 class="hero-title">成果需求智能匹配平台</h1>
        <p class="hero-subtitle">
          智能连接科研成果与企业需求，加速科技成果转化与产业升级
        </p>
        <div class="hero-actions">
          <el-button
            v-if="!userStore.isLoggedIn"
            type="primary"
            size="large"
            @click="$router.push('/register')"
          >
            立即注册
          </el-button>
          <el-button
            v-else
            type="primary"
            size="large"
            @click="$router.push('/smart-match')"
          >
            开始智能匹配
          </el-button>
          <el-button
            v-if="!userStore.isLoggedIn"
            size="large"
            @click="$router.push('/login')"
            style="margin-left: 12px"
          >
            登录
          </el-button>
        </div>
      </div>
    </div>

    <!-- 功能特性 -->
    <div class="features-section">
      <div class="container">
        <h2 class="section-title">核心功能</h2>
        <div class="features-grid">
          <div class="feature-card" @click="$router.push('/dashboard')">
            <div class="feature-icon">
              <el-icon><Box /></el-icon>
            </div>
            <h3>资源大厅</h3>
            <p>浏览全网最新科研成果与企业需求，快速发现匹配机会</p>
          </div>
          <div class="feature-card" @click="$router.push('/smart-match')">
            <div class="feature-icon">
              <el-icon><Connection /></el-icon>
            </div>
            <h3>AI智能匹配</h3>
            <p>基于大语言模型的智能匹配算法，精准连接供需双方</p>
          </div>
          <div class="feature-card" @click="$router.push('/publish')">
            <div class="feature-icon">
              <el-icon><Upload /></el-icon>
            </div>
            <h3>发布中心</h3>
            <p>科研人员发布成果，企业发布需求，让更多人看到</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 平台优势 -->
    <div class="advantages-section">
      <div class="container">
        <h2 class="section-title">平台优势</h2>
        <div class="advantages-grid">
          <div class="advantage-item">
            <div class="advantage-icon">
              <el-icon><MagicStick /></el-icon>
            </div>
            <h4>AI驱动</h4>
            <p>采用先进的大语言模型和深度学习技术，实现精准智能匹配</p>
          </div>
          <div class="advantage-item">
            <div class="advantage-icon">
              <el-icon><Lock /></el-icon>
            </div>
            <h4>安全可靠</h4>
            <p>完善的隐私保护机制，确保用户信息和数据安全</p>
          </div>
          <div class="advantage-item">
            <div class="advantage-icon">
              <el-icon><Lightning /></el-icon>
            </div>
            <h4>高效便捷</h4>
            <p>一站式服务平台，简化合作流程，提升对接效率</p>
          </div>
          <div class="advantage-item">
            <div class="advantage-icon">
              <el-icon><UserFilled /></el-icon>
            </div>
            <h4>专业服务</h4>
            <p>覆盖AI、机器学习、计算机视觉等多个前沿技术领域</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 使用流程 -->
    <div class="workflow-section">
      <div class="container">
        <h2 class="section-title">使用流程</h2>
        <div class="workflow-steps">
          <div class="step-item">
            <div class="step-number">1</div>
            <h4>注册登录</h4>
            <p>选择身份（科研人员/企业用户）完成注册</p>
          </div>
          <div class="step-arrow">→</div>
          <div class="step-item">
            <div class="step-number">2</div>
            <h4>发布内容</h4>
            <p>发布科研成果或企业需求，让平台为您匹配</p>
          </div>
          <div class="step-arrow">→</div>
          <div class="step-item">
            <div class="step-number">3</div>
            <h4>智能匹配</h4>
            <p>AI算法自动分析，为您推荐最合适的合作伙伴</p>
          </div>
          <div class="step-arrow">→</div>
          <div class="step-item">
            <div class="step-number">4</div>
            <h4>达成合作</h4>
            <p>查看合作方案，联系对接，开启合作之旅</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useUserStore } from '../stores/user'
import { Box, Connection, Upload, MagicStick, Lock, Lightning, UserFilled } from '@element-plus/icons-vue'

const userStore = useUserStore()
</script>

<style scoped>
.home {
  min-height: 100vh;
}

.hero-section {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 100px 0;
  text-align: center;
}

.hero-content {
  max-width: 900px;
  margin: 0 auto;
  padding: 0 20px;
}

.hero-title {
  font-size: 4rem;
  font-weight: bold;
  margin-bottom: 24px;
  line-height: 1.2;
}

.hero-subtitle {
  font-size: 1.4rem;
  margin-bottom: 48px;
  opacity: 0.95;
  line-height: 1.6;
}

.hero-actions {
  margin-top: 40px;
}

.features-section,
.advantages-section,
.workflow-section {
  padding: 80px 0;
  background: white;
}

.advantages-section {
  background: #f8f9fa;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.section-title {
  text-align: center;
  font-size: 2.5rem;
  font-weight: 600;
  margin-bottom: 60px;
  color: #1f2937;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 40px;
  margin-top: 40px;
}

.feature-card {
  text-align: center;
  padding: 40px 24px;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  transition: all 0.3s ease;
  cursor: pointer;
  background: white;
}

.feature-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
}

.feature-icon {
  width: 80px;
  height: 80px;
  margin: 0 auto 24px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 2.5rem;
}

.feature-card h3 {
  font-size: 1.5rem;
  font-weight: 600;
  margin-bottom: 16px;
  color: #1f2937;
}

.feature-card p {
  color: #6b7280;
  line-height: 1.7;
  font-size: 15px;
}

.advantages-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 32px;
  margin-top: 40px;
}

.advantage-item {
  text-align: center;
  padding: 32px 20px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.advantage-icon {
  width: 60px;
  height: 60px;
  margin: 0 auto 20px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 1.8rem;
}

.advantage-item h4 {
  font-size: 1.2rem;
  font-weight: 600;
  margin-bottom: 12px;
  color: #1f2937;
}

.advantage-item p {
  color: #6b7280;
  line-height: 1.6;
  font-size: 14px;
}

.workflow-steps {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 24px;
  margin-top: 40px;
}

.step-item {
  flex: 1;
  min-width: 200px;
  max-width: 250px;
  text-align: center;
  padding: 32px 20px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}

.step-number {
  width: 60px;
  height: 60px;
  margin: 0 auto 20px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 1.8rem;
  font-weight: bold;
}

.step-item h4 {
  font-size: 1.2rem;
  font-weight: 600;
  margin-bottom: 12px;
  color: #1f2937;
}

.step-item p {
  color: #6b7280;
  line-height: 1.6;
  font-size: 14px;
}

.step-arrow {
  font-size: 2rem;
  color: #667eea;
  font-weight: bold;
}

@media (max-width: 768px) {
  .hero-title {
    font-size: 2.5rem;
  }

  .hero-subtitle {
    font-size: 1.1rem;
  }

  .section-title {
    font-size: 2rem;
  }

  .features-grid,
  .advantages-grid {
    grid-template-columns: 1fr;
  }

  .workflow-steps {
    flex-direction: column;
  }

  .step-arrow {
    transform: rotate(90deg);
  }

  .step-item {
    max-width: 100%;
  }
}
</style>

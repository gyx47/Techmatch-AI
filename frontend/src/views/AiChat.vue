<template>
  <div class="ai-chat-page">
    <div class="container">
      <h1 class="page-title">AI学术助手</h1>
      
      <div class="chat-container">
        <!-- 聊天区域 -->
        <div class="chat-area">
          <div class="chat-messages" ref="chatMessages">
            <div
              v-for="message in messages"
              :key="message.id"
              :class="['message', message.type]"
            >
              <div class="message-avatar">
                <el-icon v-if="message.type === 'user'">
                  <User />
                </el-icon>
                <el-icon v-else>
                  <Robot />
                </el-icon>
              </div>
              <div class="message-content">
                <div class="message-text" v-html="formatMessage(message.text)"></div>
                <div class="message-time">{{ formatTime(message.timestamp) }}</div>
              </div>
            </div>
            
            <!-- 加载状态 -->
            <div v-if="isLoading" class="message ai">
              <div class="message-avatar">
                <el-icon><Robot /></el-icon>
              </div>
              <div class="message-content">
                <div class="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          </div>
          
          <!-- 输入区域 -->
          <div class="chat-input">
            <el-input
              v-model="inputMessage"
              type="textarea"
              :rows="3"
              placeholder="输入您的问题，AI助手将为您提供帮助..."
              @keyup.ctrl.enter="sendMessage"
              :disabled="isLoading"
            />
            <div class="input-actions">
              <div class="input-tips">
                <span>按 Ctrl+Enter 发送</span>
              </div>
              <el-button
                type="primary"
                @click="sendMessage"
                :loading="isLoading"
                :disabled="!inputMessage.trim()"
              >
                发送
              </el-button>
            </div>
          </div>
        </div>
        
        <!-- 侧边栏 -->
        <div class="sidebar">
          <div class="sidebar-section">
            <h3>会话管理</h3>
            <el-button @click="newSession" type="primary" size="small">
              新建会话
            </el-button>
            <el-button @click="loadHistory" size="small">
              加载历史
            </el-button>
          </div>
          
          <div class="sidebar-section">
            <h3>快捷功能</h3>
            <div class="quick-actions">
              <el-button
                v-for="action in quickActions"
                :key="action.label"
                @click="useQuickAction(action)"
                size="small"
                class="quick-action-btn"
              >
                {{ action.label }}
              </el-button>
            </div>
          </div>
          
          <div class="sidebar-section">
            <h3>使用提示</h3>
            <div class="tips">
              <p>• 可以询问论文相关问题</p>
              <p>• 请求论文摘要和解释</p>
              <p>• 讨论学术概念</p>
              <p>• 获取研究建议</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { User, Robot } from '@element-plus/icons-vue'
import api from '../api'

// 响应式数据
const inputMessage = ref('')
const isLoading = ref(false)
const messages = ref([])
const chatMessages = ref(null)
const currentSessionId = ref(`session_${Date.now()}`)

// 快捷操作
const quickActions = ref([
  { label: '解释论文摘要', action: '请帮我解释一下这篇论文的摘要内容' },
  { label: '研究方法建议', action: '请给我一些关于机器学习的研究方法建议' },
  { label: '学术写作帮助', action: '请帮我改进这段学术写作' },
  { label: '概念解释', action: '请解释一下深度学习的基本概念' }
])

// 发送消息
const sendMessage = async () => {
  if (!inputMessage.value.trim() || isLoading.value) return
  
  const userMessage = {
    id: Date.now(),
    type: 'user',
    text: inputMessage.value,
    timestamp: new Date()
  }
  
  messages.value.push(userMessage)
  const messageText = inputMessage.value
  inputMessage.value = ''
  isLoading.value = true
  
  // 滚动到底部
  await nextTick()
  scrollToBottom()
  
  try {
    const response = await api.post('/ai/chat', {
      message: messageText,
      session_id: currentSessionId.value
    })
    
    const aiMessage = {
      id: Date.now() + 1,
      type: 'ai',
      text: response.data.response,
      timestamp: new Date()
    }
    
    messages.value.push(aiMessage)
    
  } catch (error) {
    const errorMessage = {
      id: Date.now() + 1,
      type: 'ai',
      text: '抱歉，我暂时无法回答您的问题。请稍后再试。',
      timestamp: new Date()
    }
    messages.value.push(errorMessage)
    if (!error._handled) {
      ElMessage.error('发送消息失败: ' + (error.response?.data?.detail || error.message))
    }
  } finally {
    isLoading.value = false
    await nextTick()
    scrollToBottom()
  }
}

// 使用快捷操作
const useQuickAction = (action) => {
  inputMessage.value = action.action
}

// 新建会话
const newSession = () => {
  currentSessionId.value = `session_${Date.now()}`
  messages.value = []
  ElMessage.success('已创建新会话')
}

// 加载历史记录
const loadHistory = async () => {
  try {
    const response = await api.get('/ai/conversation-history', {
      params: {
        session_id: currentSessionId.value,
        limit: 50
      }
    })
    
    const history = response.data.conversations.reverse()
    messages.value = history.map((item, index) => ({
      id: index,
      type: 'user',
      text: item.user_message,
      timestamp: new Date(item.created_at)
    })).concat(history.map((item, index) => ({
      id: index + 1000,
      type: 'ai',
      text: item.ai_response,
      timestamp: new Date(item.created_at)
    }))).sort((a, b) => a.timestamp - b.timestamp)
    
    ElMessage.success('历史记录加载完成')
    await nextTick()
    scrollToBottom()
  } catch (error) {
    if (!error._handled) {
      ElMessage.error('加载历史记录失败: ' + (error.response?.data?.detail || error.message))
    }
  }
}

// 滚动到底部
const scrollToBottom = () => {
  if (chatMessages.value) {
    chatMessages.value.scrollTop = chatMessages.value.scrollHeight
  }
}

// 格式化消息
const formatMessage = (text) => {
  // 简单的Markdown格式化
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br>')
}

// 格式化时间
const formatTime = (timestamp) => {
  return new Date(timestamp).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

onMounted(() => {
  // 添加欢迎消息
  messages.value.push({
    id: 0,
    type: 'ai',
    text: '您好！我是AI学术助手，可以帮您解答论文相关问题、提供学术建议和解释概念。请问有什么可以帮助您的吗？',
    timestamp: new Date()
  })
})
</script>

<style scoped>
.ai-chat-page {
  min-height: 100vh;
  background: #f5f5f5;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.page-title {
  text-align: center;
  font-size: 2.5rem;
  margin-bottom: 30px;
  color: #333;
}

.chat-container {
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 20px;
  height: calc(100vh - 200px);
}

.chat-area {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
}

.chat-messages {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.message {
  display: flex;
  gap: 12px;
  max-width: 80%;
}

.message.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message.ai {
  align-self: flex-start;
}

.message-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.message.user .message-avatar {
  background: #409eff;
  color: white;
}

.message.ai .message-avatar {
  background: #f0f0f0;
  color: #666;
}

.message-content {
  flex: 1;
  min-width: 0;
}

.message.user .message-content {
  text-align: right;
}

.message-text {
  background: #f0f0f0;
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.5;
  word-wrap: break-word;
}

.message.user .message-text {
  background: #409eff;
  color: white;
}

.message-time {
  font-size: 0.8rem;
  color: #999;
  margin-top: 5px;
}

.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 12px 16px;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #999;
  animation: typing 1.4s infinite ease-in-out;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
    opacity: 0.5;
  }
  30% {
    transform: translateY(-10px);
    opacity: 1;
  }
}

.chat-input {
  padding: 20px;
  border-top: 1px solid #e4e7ed;
}

.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
}

.input-tips {
  color: #999;
  font-size: 0.9rem;
}

.sidebar {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  padding: 20px;
  height: fit-content;
}

.sidebar-section {
  margin-bottom: 30px;
}

.sidebar-section h3 {
  margin: 0 0 15px 0;
  color: #333;
  font-size: 1.1rem;
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.quick-action-btn {
  width: 100%;
  text-align: left;
  justify-content: flex-start;
}

.tips {
  color: #666;
  font-size: 0.9rem;
  line-height: 1.6;
}

.tips p {
  margin: 8px 0;
}

@media (max-width: 768px) {
  .chat-container {
    grid-template-columns: 1fr;
    height: auto;
  }
  
  .sidebar {
    order: -1;
  }
  
  .message {
    max-width: 95%;
  }
}
</style>

<template>
  <div class="register">
    <div class="auth-card">
      <div class="brand">
        <el-icon class="brand-icon"><UserFilled /></el-icon>
        <div class="brand-name">成果需求智能匹配平台</div>
      </div>
      <h2 class="title">注册账户</h2>
      <p class="subtitle">选择您的身份，开始使用智能匹配服务</p>

      <el-form :model="form" :rules="rules" ref="formRef" label-position="top">
        <!-- 角色选择区域 -->
        <el-form-item label="选择身份" prop="role" class="role-selector">
          <el-radio-group v-model="form.role" class="role-radio-group">
            <el-radio-button label="researcher" class="role-option">
              <div class="role-content">
                <div class="role-title">我是科研人员</div>
                <div class="role-desc">发布成果、找需求</div>
              </div>
            </el-radio-button>
            <el-radio-button label="enterprise" class="role-option">
              <div class="role-content">
                <div class="role-title">我是企业用户</div>
                <div class="role-desc">发布需求、找成果</div>
              </div>
            </el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" show-password />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input v-model="form.confirmPassword" type="password" placeholder="请再次输入密码" show-password />
        </el-form-item>
        <el-button type="primary" class="submit" :loading="loading" @click="onSubmit">注册</el-button>
      </el-form>

      <div class="tips">
        已有账号？
        <el-link type="primary" @click="$router.push('/login')">立即登录</el-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { UserFilled } from '@element-plus/icons-vue'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const formRef = ref()
const form = reactive({
  role: '',
  username: '',
  email: '',
  password: '',
  confirmPassword: ''
})

const validateConfirmPassword = (rule, value, callback) => {
  if (value !== form.password) {
    callback(new Error('两次输入密码不一致'))
  } else {
    callback()
  }
}

const rules = {
  role: [{ required: true, message: '请选择您的身份', trigger: 'change' }],
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { 
      min: 5, 
      max: 150, 
      message: '邮箱长度应在 5-150 个字符之间', 
      trigger: 'blur' 
    },
    { 
      type: 'email', 
      message: '请输入正确的邮箱格式（例如：user@example.com）', 
      trigger: 'blur' 
    },
    {
      pattern: /^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/,
      message: '邮箱格式不正确，请使用标准邮箱格式（例如：user@example.com）',
      trigger: 'blur'
    }
  ],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

const onSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    try {
      loading.value = true
      // 调用后端注册API（包含角色信息）
      await userStore.register({
        username: form.username,
        email: form.email,
        password: form.password,
        role: form.role
      })
      
      ElMessage.success('注册成功')
      // 注册成功后跳转到首页或之前访问的页面
      const redirect = router.currentRoute.value.query.redirect || '/'
      router.replace(redirect)
    } catch (e) {
      if (!e._handled) {
        ElMessage.error(e?.message || '注册失败，请检查后端服务是否运行')
      }
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.register {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #eef2ff, #f8fafc);
  padding: 24px;
}

.auth-card {
  width: 420px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(28, 37, 64, 0.16);
  padding: 28px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}

.brand-icon {
  font-size: 20px;
  color: #3b82f6;
}

.brand-name {
  font-weight: 700;
  color: #1f2937;
}

.title {
  margin: 8px 0;
  font-size: 22px;
  color: #111827;
}

.subtitle {
  color: #6b7280;
  margin-bottom: 18px;
}

.role-selector {
  margin-bottom: 20px;
}

.role-radio-group {
  width: 100%;
  display: flex;
  gap: 12px;
}

.role-option {
  flex: 1;
  height: auto;
  padding: 0;
}

.role-option :deep(.el-radio-button__inner) {
  width: 100%;
  padding: 16px;
  border-radius: 8px;
  border: 2px solid #e5e7eb;
  background: #fff;
  transition: all 0.3s;
}

.role-option :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  border-color: #3b82f6;
  background: #eff6ff;
  color: #1e40af;
}

.role-content {
  text-align: center;
}

.role-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 4px;
  color: #111827;
}

.role-desc {
  font-size: 12px;
  color: #6b7280;
}

.submit {
  width: 100%;
  margin-top: 6px;
}

.tips {
  color: #9ca3af;
  font-size: 12px;
  text-align: center;
  margin-top: 10px;
}
</style>


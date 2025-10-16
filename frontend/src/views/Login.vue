<template>
  <div class="login">
    <div class="auth-card">
      <div class="brand">
        <el-icon class="brand-icon"><Lock /></el-icon>
        <div class="brand-name">AI Research Match</div>
      </div>
      <h2 class="title">登录账户</h2>
      <p class="subtitle">登录后访问仪表盘、提交需求与查看匹配结果</p>

      <el-form :model="form" :rules="rules" ref="formRef" label-position="top">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" show-password />
        </el-form-item>
        <el-button type="primary" class="submit" :loading="loading" @click="onSubmit">登录</el-button>
      </el-form>

      <div class="tips">没有账号？可先用任意用户名注册于右上角弹窗，或使用临时账号。</div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock } from '@element-plus/icons-vue'
import { useUserStore } from '../stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const formRef = ref()
const form = reactive({ username: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const onSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    try {
      loading.value = true
      await userStore.login(form)
      ElMessage.success('登录成功')
      const redirect = (route.query.redirect || '/').toString()
      router.replace(redirect)
    } catch (e) {
      ElMessage.error(e?.message || '登录失败')
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.login { min-height: 100vh; display:flex; align-items:center; justify-content:center; background: linear-gradient(135deg,#eef2ff,#f8fafc); padding: 24px; }
.auth-card { width: 420px; background:#fff; border-radius: 16px; box-shadow: 0 20px 60px rgba(28,37,64,.16); padding: 28px; }
.brand { display:flex; align-items:center; gap:10px; margin-bottom: 6px; }
.brand-icon { font-size: 20px; color:#3b82f6; }
.brand-name { font-weight: 700; color:#1f2937; }
.title { margin: 8px 0; font-size: 22px; color:#111827; }
.subtitle { color:#6b7280; margin-bottom: 18px; }
.submit { width: 100%; margin-top: 6px; }
.tips { color:#9ca3af; font-size: 12px; text-align:center; margin-top: 10px; }
</style>



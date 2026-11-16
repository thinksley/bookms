<template>
  <div class="login-wrap">
    <div class="login-panel">
      <div class="brand">
        <div class="brand-mark">📚</div>
        <h1 class="brand-title">图书管理系统</h1>
        <p class="brand-sub">Library Management System</p>
      </div>
      <el-card class="login-card" shadow="never">
        <div class="card-title">账号登录</div>
        <el-form :model="form" label-position="top" @submit.prevent="handleLogin">
          <el-form-item label="用户名">
            <el-input v-model="form.username" size="large" placeholder="请输入用户名" :prefix-icon="User" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input
              v-model="form.password"
              type="password"
              size="large"
              show-password
              placeholder="请输入密码"
              :prefix-icon="Lock"
              @keyup.enter="handleLogin"
            />
          </el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            class="submit-btn"
            @click="handleLogin"
          >
            登 录
          </el-button>
        </el-form>
      </el-card>
      <p class="copyright">图书管理系统 · 仅限授权管理员使用</p>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import request from '@/api/request'

const router = useRouter()
const loading = ref(false)
const form = reactive({ username: '', password: '' })

const handleLogin = async () => {
  if (!form.username || !form.password) {
    return ElMessage.warning('请输入用户名和密码')
  }
  loading.value = true
  try {
    // 后端 OAuth2 登录接口要求 form-urlencoded 格式
    const params = new URLSearchParams()
    params.append('username', form.username)
    params.append('password', form.password)

    const res = await request.post('/auth/login', params)
    localStorage.setItem('token', res.access_token)
    localStorage.setItem('username', form.username)
    ElMessage.success('登录成功')
    router.push('/')
  } catch (e) {
    // 错误提示已在 request 拦截器中统一弹出
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  min-height: 100vh;
  background: radial-gradient(circle at 20% 20%, #3a4a63 0%, #2b3547 45%, #232b3a 100%);
}

.login-panel {
  width: 380px;
}

.brand {
  text-align: center;
  margin-bottom: 22px;
  color: #fff;
}

.brand-mark {
  font-size: 34px;
  line-height: 1;
}

.brand-title {
  margin: 12px 0 4px;
  font-size: 21px;
  font-weight: 600;
  letter-spacing: 2px;
}

.brand-sub {
  margin: 0;
  font-size: 12px;
  letter-spacing: 1px;
  color: #97a4b8;
  text-transform: uppercase;
}

.login-card {
  border: none;
  border-radius: 4px;
  padding: 6px 4px 10px;
  box-shadow: 0 12px 32px rgba(12, 18, 28, 0.28);
}

.login-card :deep(.el-card__body) {
  padding: 22px 24px 18px;
}

.card-title {
  margin-bottom: 16px;
  font-size: 15px;
  font-weight: 600;
  color: #2c3444;
}

.submit-btn {
  width: 100%;
  margin-top: 6px;
  letter-spacing: 4px;
  height: 38px;
}

.copyright {
  margin-top: 18px;
  text-align: center;
  font-size: 12px;
  color: #8593a8;
}
</style>

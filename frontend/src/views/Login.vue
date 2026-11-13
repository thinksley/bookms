<template>
  <div class="login-wrap">
    <el-card class="login-card" header="管理员登录">
      <el-form :model="form" label-position="top" @submit.prevent="handleLogin">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            placeholder="请输入密码"
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-button type="primary" :loading="loading" style="width: 100%" @click="handleLogin">
          登录
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
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
  height: 100vh;
  background: #f0f2f5;
}
.login-card {
  width: 360px;
}
</style>

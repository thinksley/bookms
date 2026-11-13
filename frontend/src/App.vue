<template>
  <el-container style="min-height: 100vh">
    <el-aside v-if="showSide" width="200px" class="aside">
      <div class="logo">📚 图书管理系统</div>
      <el-menu :default-active="activeMenu" router class="menu">
        <el-menu-item index="/dashboard">📊 数据看板</el-menu-item>
        <el-menu-item index="/books">📖 图书管理</el-menu-item>
        <el-menu-item index="/borrows">🔄 借阅管理</el-menu-item>
        <el-menu-item index="/readers">👥 读者管理</el-menu-item>
        <el-menu-item index="/categories">🏷️ 分类管理</el-menu-item>
        <el-menu-item index="/users">👤 用户管理</el-menu-item>
        <el-menu-item index="/settings">⚙️ 系统设置</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header v-if="showHeader" class="header">
        <span class="title">{{ pageTitle }}</span>
        <div>
          <el-dropdown @command="onUserCommand">
            <span class="user">{{ username }} ▾</span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="password">修改密码</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>

    <el-dialog v-model="pwdVisible" title="修改密码" width="420px">
      <el-form label-width="90px">
        <el-form-item label="原密码" required>
          <el-input v-model="pwd.old_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码" required>
          <el-input v-model="pwd.new_password" type="password" show-password placeholder="至少 6 位" />
        </el-form-item>
        <el-form-item label="确认密码" required>
          <el-input v-model="pwd.confirm" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pwdVisible = false">取消</el-button>
        <el-button type="primary" :loading="pwdSaving" @click="changePassword">保存</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '@/api/request'

const route = useRoute()
const router = useRouter()

const showSide = computed(() => route.path !== '/login')
const showHeader = computed(() => route.path !== '/login')
const activeMenu = computed(() => route.path)
const pageTitle = computed(() => {
  const titles = {
    '/dashboard': '数据看板',
    '/borrows': '借阅管理',
    '/readers': '读者管理',
    '/categories': '分类管理',
    '/users': '用户管理',
    '/settings': '系统设置',
  }
  return titles[route.path] || '图书管理系统'
})
const username = computed(() => localStorage.getItem('username') || 'admin')

const onUserCommand = (cmd) => {
  if (cmd === 'logout') {
    logout()
  } else if (cmd === 'password') {
    Object.assign(pwd, { old_password: '', new_password: '', confirm: '' })
    pwdVisible.value = true
  }
}

const logout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('username')
  router.push('/login')
}

// ---------- 修改密码 ----------
const pwdVisible = ref(false)
const pwdSaving = ref(false)
const pwd = reactive({ old_password: '', new_password: '', confirm: '' })

const changePassword = async () => {
  if (!pwd.old_password) {
    return ElMessage.warning('请输入原密码')
  }
  if (pwd.new_password.length < 6) {
    return ElMessage.warning('新密码至少 6 位')
  }
  if (pwd.new_password !== pwd.confirm) {
    return ElMessage.warning('两次输入的新密码不一致')
  }
  pwdSaving.value = true
  try {
    await request.post('/auth/change-password', {
      old_password: pwd.old_password,
      new_password: pwd.new_password,
    })
    ElMessage.success('密码修改成功')
    pwdVisible.value = false
  } finally {
    pwdSaving.value = false
  }
}
</script>

<style scoped>
.aside {
  background: #fff;
  border-right: 1px solid #e6e6e6;
}
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: bold;
  color: #409eff;
}
.menu {
  border-right: none;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #409eff;
  color: #fff;
}
.title {
  font-size: 18px;
  font-weight: bold;
}
.user {
  margin-right: 4px;
  color: #fff;
  cursor: pointer;
  outline: none;
}
</style>

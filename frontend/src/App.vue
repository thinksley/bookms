<template>
  <router-view v-if="!showSide" />

  <el-container v-else class="layout">
    <el-aside :width="collapsed ? '64px' : '210px'" class="aside">
      <div class="brand">
        <span class="brand-mark">📚</span>
        <span v-show="!collapsed" class="brand-text">图书管理系统</span>
      </div>
      <el-scrollbar class="nav-scroll">
        <el-menu
          :default-active="activeMenu"
          :default-openeds="['stock', 'circulation', 'system']"
          :collapse="collapsed"
          :collapse-transition="false"
          router
          class="side-menu"
        >
          <el-menu-item index="/dashboard">
            <el-icon><DataLine /></el-icon>
            <template #title>数据看板</template>
          </el-menu-item>

          <el-sub-menu index="stock">
            <template #title>
              <el-icon><Reading /></el-icon>
              <span>馆藏管理</span>
            </template>
            <el-menu-item index="/books">图书管理</el-menu-item>
            <el-menu-item index="/categories">分类管理</el-menu-item>
            <el-menu-item index="/recycle">回收站</el-menu-item>
          </el-sub-menu>

          <el-sub-menu index="circulation">
            <template #title>
              <el-icon><Tickets /></el-icon>
              <span>流通管理</span>
            </template>
            <el-menu-item index="/borrows">借阅管理</el-menu-item>
            <el-menu-item index="/readers">读者管理</el-menu-item>
          </el-sub-menu>

          <el-sub-menu index="system">
            <template #title>
              <el-icon><Setting /></el-icon>
              <span>系统管理</span>
            </template>
            <el-menu-item index="/users">用户管理</el-menu-item>
            <el-menu-item index="/settings">系统设置</el-menu-item>
          </el-sub-menu>
        </el-menu>
      </el-scrollbar>
    </el-aside>

    <el-container class="main-wrap">
      <el-header class="topbar" height="50px">
        <div class="topbar-left">
          <el-icon class="collapse-btn" @click="collapsed = !collapsed">
            <Expand v-if="collapsed" />
            <Fold v-else />
          </el-icon>
        </div>
        <div class="topbar-right">
          <el-dropdown trigger="click" @command="onUserCommand">
            <span class="user">
              <el-avatar :size="26" class="user-avatar">{{ avatarText }}</el-avatar>
              <span class="user-name">{{ username }}</span>
              <el-icon class="user-arrow"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="password">修改密码</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <div class="crumb-bar">
        <el-breadcrumb separator="/">
          <el-breadcrumb-item :to="{ path: '/dashboard' }">首页</el-breadcrumb-item>
          <el-breadcrumb-item v-if="current.group">{{ current.group }}</el-breadcrumb-item>
          <el-breadcrumb-item>{{ current.title }}</el-breadcrumb-item>
        </el-breadcrumb>

        <div class="tabs">
          <span
            v-for="t in tabs"
            :key="t.path"
            class="page-tab"
            :class="{ 'is-active': t.path === route.path }"
            @click="router.push(t.path)"
          >
            {{ t.title }}
            <el-icon v-if="tabs.length > 1" class="tab-close" @click.stop="closeTab(t.path)">
              <Close />
            </el-icon>
          </span>
        </div>
      </div>

      <el-main class="content">
        <router-view />
      </el-main>
    </el-container>
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
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Fold,
  Expand,
  DataLine,
  Reading,
  Tickets,
  Setting,
  ArrowDown,
  Close,
} from '@element-plus/icons-vue'
import request from '@/api/request'

const route = useRoute()
const router = useRouter()

const showSide = computed(() => route.path !== '/login')
const activeMenu = computed(() => route.path)
const collapsed = ref(false)

const PAGE_META = {
  '/dashboard': { group: '', title: '数据看板' },
  '/books': { group: '馆藏管理', title: '图书管理' },
  '/categories': { group: '馆藏管理', title: '分类管理' },
  '/recycle': { group: '馆藏管理', title: '回收站' },
  '/borrows': { group: '流通管理', title: '借阅管理' },
  '/readers': { group: '流通管理', title: '读者管理' },
  '/users': { group: '系统管理', title: '用户管理' },
  '/settings': { group: '系统管理', title: '系统设置' },
}

const current = computed(
  () => PAGE_META[route.path] || { group: '', title: '图书管理系统' }
)

const username = computed(() => localStorage.getItem('username') || 'admin')
const avatarText = computed(() => (username.value || 'A').slice(0, 1).toUpperCase())

// ---------- 页签 ----------
const tabs = ref([])
watch(
  () => route.path,
  (path) => {
    if (path === '/login') return
    const meta = PAGE_META[path]
    if (!meta) return
    if (!tabs.value.some((t) => t.path === path)) {
      tabs.value.push({ path, title: meta.title })
    }
  },
  { immediate: true }
)

const closeTab = (path) => {
  const idx = tabs.value.findIndex((t) => t.path === path)
  if (idx === -1) return
  tabs.value.splice(idx, 1)
  if (route.path === path) {
    const next = tabs.value[tabs.value.length - 1]
    router.push(next ? next.path : '/dashboard')
  }
}

// ---------- 用户菜单 ----------
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
  tabs.value = []
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
.layout {
  min-height: 100vh;
  background: var(--app-content-bg);
}

/* ---------- 侧边栏 ---------- */
.aside {
  background: var(--app-sidebar-bg);
  transition: width 0.2s;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.brand {
  height: 50px;
  flex: 0 0 50px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 18px;
  background: var(--app-sidebar-deep);
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.5px;
  white-space: nowrap;
  overflow: hidden;
}

.brand-mark {
  font-size: 16px;
  line-height: 1;
}

.nav-scroll {
  flex: 1;
  padding: 6px 0;
}

.side-menu {
  border-right: none;
  background: transparent;
  --el-menu-bg-color: transparent;
  --el-menu-text-color: var(--app-nav-text);
  --el-menu-hover-bg-color: var(--app-nav-hover-bg);
  --el-menu-active-color: var(--app-nav-active-text);
  --el-menu-item-height: 44px;
  --el-menu-sub-item-height: 40px;
}

.side-menu :deep(.el-menu-item),
.side-menu :deep(.el-sub-menu__title) {
  color: var(--app-nav-text);
  font-size: 13.5px;
  border-radius: 0;
}

.side-menu :deep(.el-menu-item:hover),
.side-menu :deep(.el-sub-menu__title:hover) {
  background: var(--app-nav-hover-bg);
  color: #fff;
}

.side-menu :deep(.el-menu-item.is-active) {
  background: var(--app-nav-active-bg);
  color: var(--app-nav-active-text);
  font-weight: 600;
  position: relative;
}

.side-menu :deep(.el-menu-item.is-active::before) {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 3px;
  background: var(--app-nav-active-text);
}

.side-menu :deep(.el-sub-menu .el-menu) {
  background: transparent;
}

.side-menu :deep(.el-sub-menu .el-menu-item) {
  padding-left: 50px !important;
  font-size: 13px;
}

.side-menu :deep(.el-icon) {
  font-size: 16px;
}

/* ---------- 顶栏 ---------- */
.main-wrap {
  min-width: 0;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--app-sidebar-bg);
  color: #fff;
  padding: 0 16px;
}

.topbar-left {
  display: flex;
  align-items: center;
}

.collapse-btn {
  font-size: 18px;
  cursor: pointer;
  color: #d7dee9;
}

.collapse-btn:hover {
  color: #fff;
}

.user {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #fff;
  cursor: pointer;
  outline: none;
}

.user-avatar {
  background: #3d8bfd;
  font-size: 13px;
}

.user-name {
  font-size: 13px;
}

.user-arrow {
  font-size: 12px;
  color: #c3ccda;
}

/* ---------- 面包屑 + 页签 ---------- */
.crumb-bar {
  height: 42px;
  flex: 0 0 42px;
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 0 16px;
  background: #fff;
  border-bottom: 1px solid var(--app-border);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
  overflow-x: auto;
}

.crumb-bar :deep(.el-breadcrumb) {
  font-size: 13px;
  white-space: nowrap;
}

.crumb-bar :deep(.el-breadcrumb__inner) {
  color: #7b8598;
  font-weight: 400;
}

.crumb-bar :deep(.el-breadcrumb__item:last-child .el-breadcrumb__inner) {
  color: #2c3444;
  font-weight: 500;
}

.tabs {
  display: flex;
  gap: 8px;
  align-items: center;
}

/* ---------- 内容区 ---------- */
.content {
  padding: 12px;
  background: var(--app-content-bg);
  overflow-y: auto;
}

@media (max-width: 900px) {
  .content {
    padding: 8px;
  }
}
</style>

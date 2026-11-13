<template>
  <div class="page">
    <div class="toolbar">
      <el-input
        v-model="keyword"
        placeholder="按用户名搜索"
        clearable
        style="width: 300px"
        @keyup.enter="search"
        @clear="search"
      />
      <el-button type="primary" @click="search">搜索</el-button>
      <el-button type="success" @click="openAdd">新增用户</el-button>
    </div>

    <el-table v-loading="loading" :data="users" stripe border>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="username" label="用户名" min-width="140" />
      <el-table-column label="角色" width="120">
        <template #default="{ row }">
          <el-tag v-if="row.is_admin" type="warning">管理员</el-tag>
          <el-tag v-else type="info">普通用户</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="180" :formatter="formatTime" />
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="page"
      v-model:page-size="size"
      :total="total"
      :page-sizes="[10, 20, 50]"
      layout="total, sizes, prev, pager, next"
      class="pagination"
      @current-change="load"
      @size-change="search"
    />

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑用户' : '新增用户'" width="480px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="用户名" required>
          <el-input v-model="form.username" maxlength="50" />
        </el-form-item>
        <el-form-item label="密码" :required="!isEdit">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            maxlength="72"
            :placeholder="isEdit ? '留空则不修改密码' : '至少 6 位'"
          />
        </el-form-item>
        <el-form-item label="管理员">
          <el-switch v-model="form.is_admin" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/api/request'

// ---------- 列表 ----------
const users = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const keyword = ref('')
const loading = ref(false)

const formatTime = (row) => (row.created_at ? row.created_at.replace('T', ' ').slice(0, 19) : '')

const load = async () => {
  loading.value = true
  try {
    const res = await request.get('/users', {
      params: {
        page: page.value,
        size: size.value,
        keyword: keyword.value || undefined,
      },
    })
    users.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

const search = () => {
  page.value = 1
  load()
}

// ---------- 新增 / 编辑 ----------
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref(null)
const saving = ref(false)

const emptyForm = () => ({ username: '', password: '', is_admin: false })
const form = reactive(emptyForm())

const openAdd = () => {
  Object.assign(form, emptyForm())
  isEdit.value = false
  editingId.value = null
  dialogVisible.value = true
}

const openEdit = (row) => {
  Object.assign(form, {
    username: row.username,
    password: '',
    is_admin: row.is_admin,
  })
  isEdit.value = true
  editingId.value = row.id
  dialogVisible.value = true
}

const submit = async () => {
  if (!form.username.trim()) {
    return ElMessage.warning('用户名不能为空')
  }
  if (!isEdit.value && form.password.length < 6) {
    return ElMessage.warning('密码至少 6 位')
  }
  if (isEdit.value && form.password && form.password.length < 6) {
    return ElMessage.warning('密码至少 6 位')
  }

  // 编辑时密码留空表示不修改
  const payload = isEdit.value
    ? { username: form.username.trim(), is_admin: form.is_admin }
    : { username: form.username.trim(), password: form.password, is_admin: form.is_admin }
  if (isEdit.value && form.password) {
    payload.password = form.password
  }

  saving.value = true
  try {
    if (isEdit.value) {
      await request.put(`/users/${editingId.value}`, payload)
    } else {
      await request.post('/users', payload)
    }
    ElMessage.success('保存成功')
    dialogVisible.value = false
    load()
  } finally {
    saving.value = false
  }
}

// ---------- 删除 ----------
const remove = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除用户「${row.username}」吗？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  await request.delete(`/users/${row.id}`)
  ElMessage.success('删除成功')
  load()
}

onMounted(load)
</script>

<style scoped>
.page {
  width: 100%;
}
.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
.pagination {
  margin-top: 16px;
  justify-content: flex-end;
}
</style>

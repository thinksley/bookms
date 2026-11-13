<template>
  <div class="page">
    <div class="toolbar">
      <el-button type="success" @click="openAdd">新增分类</el-button>
    </div>

    <el-table v-loading="loading" :data="categories" stripe border>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="name" label="分类名称" min-width="180" />
      <el-table-column label="图书数量" width="110">
        <template #default="{ row }">
          <el-tag :type="row.book_count ? 'primary' : 'info'" size="small">{{ row.book_count }} 本</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="180" :formatter="formatTime" />
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openRename(row)">编辑</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '重命名分类' : '新增分类'" width="420px">
      <el-input
        v-model="name"
        maxlength="50"
        placeholder="分类名称，如：计算机 / 历史 / 艺术"
        @keyup.enter="submit"
      />
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/api/request'

const categories = ref([])
const loading = ref(false)

const formatTime = (row) => (row.created_at ? row.created_at.replace('T', ' ').slice(0, 19) : '')

const load = async () => {
  loading.value = true
  try {
    categories.value = await request.get('/categories')
  } finally {
    loading.value = false
  }
}

// ---------- 新增 / 重命名 ----------
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref(null)
const name = ref('')
const saving = ref(false)

const openAdd = () => {
  name.value = ''
  isEdit.value = false
  editingId.value = null
  dialogVisible.value = true
}

const openRename = (row) => {
  name.value = row.name
  isEdit.value = true
  editingId.value = row.id
  dialogVisible.value = true
}

const submit = async () => {
  const value = name.value.trim()
  if (!value) {
    return ElMessage.warning('分类名称不能为空')
  }
  saving.value = true
  try {
    if (isEdit.value) {
      await request.put(`/categories/${editingId.value}`, { name: value })
      ElMessage.success('重命名成功，相关图书已同步更新')
    } else {
      await request.post('/categories', { name: value })
      ElMessage.success('分类已创建')
    }
    dialogVisible.value = false
    load()
  } finally {
    saving.value = false
  }
}

// ---------- 删除 ----------
const remove = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除分类「${row.name}」吗？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  await request.delete(`/categories/${row.id}`)
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
</style>

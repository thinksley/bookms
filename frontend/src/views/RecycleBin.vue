<template>
  <div class="page">
    <div class="toolbar actions">
      <el-button type="primary" plain :icon="RefreshLeft" :loading="loading" @click="load">
        刷新
      </el-button>
      <el-button
        type="success"
        plain
        :icon="RefreshRight"
        :disabled="!selection.length"
        :loading="batchLoading"
        @click="batchRestore"
      >
        恢复选中{{ selection.length ? `（${selection.length}）` : '' }}
      </el-button>
      <el-button
        type="danger"
        plain
        :icon="Delete"
        :disabled="!selection.length"
        :loading="batchLoading"
        @click="batchPurge"
      >
        彻底删除{{ selection.length ? `（${selection.length}）` : '' }}
      </el-button>
      <div class="flex-1"></div>
      <span class="recycle-count" v-if="!loading">共 {{ deletedBooks.length }} 本在回收站</span>
    </div>

    <el-table
      ref="tableRef"
      v-loading="loading"
      :data="deletedBooks"
      border
      stripe
      @selection-change="onSelectionChange"
    >
      <el-table-column type="selection" width="42" />
      <el-table-column prop="title" label="书名" min-width="160">
        <template #default="{ row }">
          <div class="title-cell">
            <el-image
              v-if="row.cover_url"
              :src="row.cover_url"
              fit="cover"
              class="mini-cover"
              :preview-src-list="[row.cover_url]"
              preview-teleported
            />
            <span>{{ row.title }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="author" label="作者" width="120" show-overflow-tooltip />
      <el-table-column prop="isbn" label="ISBN" width="160" />
      <el-table-column prop="category" label="分类" width="110" />
      <el-table-column prop="stock" label="库存" width="70" align="center" />
      <el-table-column label="删除时间" width="170">
        <template #default="{ row }">
          {{ (row.deleted_at || '').replace('T', ' ').slice(0, 19) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" :icon="RefreshRight" @click="restoreOne(row)">恢复</el-button>
          <el-button link type="danger" :icon="Delete" @click="purgeOne(row)">彻底删除</el-button>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="回收站是空的" :image-size="90" />
      </template>
    </el-table>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { RefreshLeft, RefreshRight, Delete } from '@element-plus/icons-vue'
import request from '@/api/request'

const tableRef = ref()
const loading = ref(false)
const batchLoading = ref(false)
const deletedBooks = ref([])
const selection = ref([])

const onSelectionChange = (rows) => {
  selection.value = rows
}

const load = async () => {
  loading.value = true
  try {
    deletedBooks.value = await request.get('/books/recycle-bin')
  } finally {
    loading.value = false
  }
}

const restoreIds = async (rows) => {
  batchLoading.value = true
  try {
    for (const row of rows) {
      await request.post(`/books/${row.id}/restore`)
    }
    ElMessage.success(rows.length === 1 ? `《${rows[0].title}》已恢复` : `已恢复 ${rows.length} 本`)
    await load()
  } finally {
    batchLoading.value = false
  }
}

const purgeIds = async (rows) => {
  const names = rows.length === 1 ? `《${rows[0].title}》` : `选中的 ${rows.length} 本图书`
  try {
    await ElMessageBox.confirm(`彻底删除${names}后不可恢复，确定吗？`, '彻底删除', {
      type: 'error',
      confirmButtonText: '彻底删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  batchLoading.value = true
  try {
    for (const row of rows) {
      await request.delete(`/books/${row.id}/purge`)
    }
    ElMessage.success('已彻底删除')
    await load()
  } finally {
    batchLoading.value = false
  }
}

const restoreOne = (row) => restoreIds([row])
const purgeOne = (row) => purgeIds([row])
const batchRestore = () => restoreIds(selection.value)
const batchPurge = () => purgeIds(selection.value)

onMounted(load)
</script>

<style scoped>
.recycle-count {
  color: #909399;
  font-size: 13px;
}

.title-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mini-cover {
  width: 28px;
  height: 38px;
  border-radius: 3px;
  flex: 0 0 auto;
  background: #f0f2f5;
}
</style>

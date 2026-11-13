<template>
  <div class="page">
    <div class="toolbar">
      <el-input
        v-model="keyword"
        placeholder="按姓名 / 证号 / 电话搜索"
        clearable
        style="width: 300px"
        @keyup.enter="search"
        @clear="search"
      />
      <el-button type="primary" @click="search">搜索</el-button>
      <el-button type="success" @click="openAdd">新增读者</el-button>
    </div>

    <el-table v-loading="loading" :data="readers" stripe border>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="card_no" label="读者证号" width="110" />
      <el-table-column prop="name" label="姓名" min-width="110" />
      <el-table-column prop="phone" label="电话" width="130" />
      <el-table-column prop="email" label="邮箱" min-width="140" show-overflow-tooltip />
      <el-table-column label="在借 / 上限" width="110">
        <template #default="{ row }">
          <el-tag
            :type="row.active_borrows >= row.max_borrow ? 'danger' : 'success'"
            size="small"
          >
            {{ row.active_borrows }} / {{ row.max_borrow }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="remark" label="备注" min-width="110" show-overflow-tooltip />
      <el-table-column label="操作" width="140" fixed="right">
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

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑读者' : '新增读者'" width="460px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="姓名" required>
          <el-input v-model="form.name" maxlength="50" />
        </el-form-item>
        <el-form-item label="读者证号">
          <el-input v-model="form.card_no" maxlength="20" placeholder="留空自动生成" />
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="form.phone" maxlength="20" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="form.email" maxlength="100" />
        </el-form-item>
        <el-form-item label="可借上限">
          <el-input-number v-model="form.max_borrow" :min="1" :max="20" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" maxlength="200" />
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
const readers = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const keyword = ref('')
const loading = ref(false)

const load = async () => {
  loading.value = true
  try {
    const res = await request.get('/readers', {
      params: {
        page: page.value,
        size: size.value,
        keyword: keyword.value || undefined,
      },
    })
    readers.value = res.items
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

const emptyForm = () => ({
  name: '', card_no: '', phone: '', email: '', max_borrow: defaultMax.value, remark: '',
})
const defaultMax = ref(5) // 从系统设置读到的默认可借上限
const form = reactive(emptyForm())

const openAdd = () => {
  Object.assign(form, emptyForm())
  isEdit.value = false
  editingId.value = null
  dialogVisible.value = true
}

const openEdit = (row) => {
  Object.assign(form, {
    name: row.name,
    card_no: row.card_no || '',
    phone: row.phone || '',
    email: row.email || '',
    max_borrow: row.max_borrow,
    remark: row.remark || '',
  })
  isEdit.value = true
  editingId.value = row.id
  dialogVisible.value = true
}

const submit = async () => {
  if (!form.name.trim()) {
    return ElMessage.warning('姓名不能为空')
  }
  const payload = {
    name: form.name.trim(),
    card_no: form.card_no.trim() || null,
    phone: form.phone.trim() || null,
    email: form.email.trim() || null,
    max_borrow: form.max_borrow,
    remark: form.remark.trim() || null,
  }
  saving.value = true
  try {
    if (isEdit.value) {
      await request.put(`/readers/${editingId.value}`, payload)
    } else {
      await request.post('/readers', payload)
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
    await ElMessageBox.confirm(
      `确定删除读者「${row.name}」吗？历史借阅记录会保留。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  await request.delete(`/readers/${row.id}`)
  ElMessage.success('删除成功')
  load()
}

onMounted(async () => {
  load()
  // 新读者默认可借上限从系统设置取
  try {
    const rules = await request.get('/settings')
    defaultMax.value = rules.max_borrow
  } catch {
    /* 拿不到就沿用代码里的默认值 */
  }
})
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

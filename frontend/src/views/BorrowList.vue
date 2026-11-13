<template>
  <div class="page">
    <div class="toolbar">
      <el-radio-group v-model="status" @change="search">
        <el-radio-button label="">全部</el-radio-button>
        <el-radio-button label="在借" />
        <el-radio-button label="逾期" />
        <el-radio-button label="已还" />
      </el-radio-group>
      <el-input
        v-model="keyword"
        placeholder="按书名 / 借阅人搜索"
        clearable
        style="width: 260px"
        @keyup.enter="search"
        @clear="search"
      />
      <el-button type="primary" @click="search">搜索</el-button>
      <el-button type="success" @click="openBorrow">新增借阅</el-button>
    </div>

    <el-table v-loading="loading" :data="records" stripe border>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="book_title" label="书名" min-width="160" />
      <el-table-column prop="borrower_name" label="借阅人" width="110" />
      <el-table-column prop="borrow_date" label="借出日期" width="110" />
      <el-table-column prop="due_date" label="应还日期" width="110" />
      <el-table-column prop="return_date" label="归还日期" width="110" />
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ row.status }}</el-tag>
          <el-tag v-if="row.renewed_count > 0" size="small" type="warning" effect="plain" style="margin-left: 4px">已续借</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="operator" label="经手人" width="100" />
      <el-table-column prop="remark" label="备注" min-width="110" show-overflow-tooltip />
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button v-if="row.status !== '已还' && row.renewed_count < 1" link type="warning" @click="renew(row)">续借</el-button>
          <el-button v-if="row.status !== '已还'" link type="success" @click="giveBack(row)">归还</el-button>
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

    <el-dialog v-model="dialogVisible" title="新增借阅" width="460px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="图书" required>
          <el-select
            v-model="form.book_id"
            filterable
            placeholder="输入书名搜索"
            style="width: 100%"
          >
            <el-option
              v-for="b in bookOptions"
              :key="b.id"
              :label="`${b.title}（库存 ${b.stock}）`"
              :value="b.id"
              :disabled="b.stock <= 0"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="读者" required>
          <el-select
            v-model="form.reader_id"
            filterable
            placeholder="输入姓名 / 证号搜索"
            style="width: 100%"
          >
            <el-option
              v-for="r in readerOptions"
              :key="r.id"
              :label="`${r.name}（${r.card_no}，在借 ${r.active_borrows}/${r.max_borrow}）`"
              :value="r.id"
              :disabled="r.active_borrows >= r.max_borrow"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="借期（天）">
          <el-input-number v-model="form.days" :min="1" :max="365" style="width: 100%" />
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
const records = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const status = ref('')
const keyword = ref('')
const loading = ref(false)

const load = async () => {
  loading.value = true
  try {
    const res = await request.get('/borrows', {
      params: {
        page: page.value,
        size: size.value,
        status: status.value || undefined,
        keyword: keyword.value || undefined,
      },
    })
    records.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

const search = () => {
  page.value = 1
  load()
}

const statusType = (s) => (s === '逾期' ? 'danger' : s === '已还' ? 'success' : 'primary')

// ---------- 新增借阅 ----------
const dialogVisible = ref(false)
const saving = ref(false)
const bookOptions = ref([])
const readerOptions = ref([])
const defaultDays = ref(31) // 从系统设置读到的默认借期
const renewDays = ref(30) // 从系统设置读到的续借顺延天数
const form = reactive({ book_id: null, reader_id: null, days: 31, remark: '' })

const openBorrow = async () => {
  Object.assign(form, { book_id: null, reader_id: null, days: defaultDays.value, remark: '' })
  const res = await request.get('/books', { params: { page: 1, size: 100 } })
  bookOptions.value = res.items
  const readers = await request.get('/readers', { params: { page: 1, size: 200 } })
  readerOptions.value = readers.items
  dialogVisible.value = true
}

const submit = async () => {
  if (!form.book_id || !form.reader_id) {
    return ElMessage.warning('请选择图书和读者')
  }
  saving.value = true
  try {
    await request.post('/borrows', {
      book_id: form.book_id,
      reader_id: form.reader_id,
      days: form.days,
      remark: form.remark.trim() || null,
    })
    ElMessage.success('借出成功')
    dialogVisible.value = false
    load()
  } finally {
    saving.value = false
  }
}

// ---------- 续借 / 归还 / 删除 ----------
const renew = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定续借《${row.book_title}》吗？应还日期将顺延 ${renewDays.value} 天。`,
      '续借确认',
      { type: 'warning', confirmButtonText: '续借', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  await request.post(`/borrows/${row.id}/renew`)
  ElMessage.success('续借成功')
  load()
}
const giveBack = async (row) => {
  try {
    await ElMessageBox.confirm(`确定《${row.book_title}》已归还吗？`, '归还确认', {
      type: 'success',
      confirmButtonText: '归还',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  await request.post(`/borrows/${row.id}/return`)
  ElMessage.success('已归还')
  load()
}

const remove = async (row) => {
  try {
    await ElMessageBox.confirm(
      row.status === '已还'
        ? `确定删除「${row.borrower_name}」借阅《${row.book_title}》的记录吗？`
        : `该记录仍在借，删除将取消借阅并恢复库存，确定吗？`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  await request.delete(`/borrows/${row.id}`)
  ElMessage.success('删除成功')
  load()
}

onMounted(async () => {
  load()
  // 默认借期/续借天数从系统设置取，管理员改设置后这里自动跟着变
  try {
    const rules = await request.get('/settings')
    defaultDays.value = rules.borrow_days
    renewDays.value = rules.renew_days
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

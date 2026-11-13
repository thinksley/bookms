<template>
  <div class="page">
    <div class="toolbar">
      <el-input
        v-model="keyword"
        placeholder="按书名 / 作者 / ISBN / 分类 / 标签等搜索"
        clearable
        style="width: 320px"
        @keyup.enter="search"
        @clear="search"
      />
      <el-button type="primary" @click="search">搜索</el-button>
      <el-button type="success" @click="openAdd">新增图书</el-button>
      <el-button @click="exportBooks" :loading="exporting">导出 Excel</el-button>
      <el-button @click="importVisible = true">批量导入</el-button>
      <el-button type="danger" plain :disabled="!selection.length" @click="batchRemove">
        批量删除{{ selection.length ? `（${selection.length}）` : '' }}
      </el-button>
      <el-button plain :disabled="!selection.length" @click="openBatchCategory">批量改分类</el-button>
      <el-button @click="openRecycleBin">回收站</el-button>
    </div>

    <el-table
      ref="tableRef"
      v-loading="loading"
      :data="books"
      stripe
      border
      @selection-change="onSelectionChange"
    >
      <el-table-column type="expand">
        <template #default="{ row }">
          <div class="detail">
            <el-descriptions :column="3" border>
              <el-descriptions-item
                v-for="[key, label] in detailFields"
                :key="key"
                :label="label"
              >
                {{ fmt(row[key]) }}
              </el-descriptions-item>
            </el-descriptions>
            <el-descriptions
              v-if="row.summary || row.author_intro || row.catalog"
              :column="1"
              border
              class="detail-text"
            >
              <el-descriptions-item v-if="row.summary" label="内容简介">{{ row.summary }}</el-descriptions-item>
              <el-descriptions-item v-if="row.author_intro" label="作者简介">{{ row.author_intro }}</el-descriptions-item>
              <el-descriptions-item v-if="row.catalog" label="目录">{{ row.catalog }}</el-descriptions-item>
            </el-descriptions>
          </div>
        </template>
      </el-table-column>
      <el-table-column type="selection" width="42" />
      <el-table-column label="封面" width="80">
        <template #default="{ row }">
          <el-image
            v-if="row.cover_url"
            :src="row.cover_url"
            :preview-src-list="[row.cover_url]"
            preview-teleported
            fit="cover"
            style="width: 48px; height: 64px; border-radius: 4px"
          />
          <span v-else class="no-cover">无封面</span>
        </template>
      </el-table-column>
      <el-table-column prop="title" label="书名" min-width="180" />
      <el-table-column prop="author" label="作者" width="130" />
      <el-table-column prop="category" label="分类" width="100" />
      <el-table-column prop="publisher" label="出版社" width="140" />
      <el-table-column prop="isbn" label="ISBN" width="150" />
      <el-table-column prop="price" label="定价" width="90" />
      <el-table-column prop="stock" label="库存" width="80" />
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

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑图书' : '新增图书'" width="720px" top="5vh">
      <el-form :model="form" label-width="90px">
        <el-divider content-position="left">基本信息</el-divider>
        <el-row :gutter="12">
          <el-col :span="24">
            <el-form-item label="书名" required>
              <el-input v-model="form.title" maxlength="200" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="副标题">
              <el-input v-model="form.subtitle" maxlength="200" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="原作名">
              <el-input v-model="form.original_title" maxlength="200" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="作者" required>
              <el-input v-model="form.author" maxlength="100" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="译者">
              <el-input v-model="form.translator" maxlength="100" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="ISBN">
              <div class="isbn-row">
                <el-input v-model="form.isbn" maxlength="20" placeholder="输入后可点查询自动获取信息" />
                <el-button :loading="lookingUp" :disabled="!form.isbn.trim()" @click="lookupIsbn">查询</el-button>
              </div>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="丛书系列">
              <el-input v-model="form.series" maxlength="100" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="分类">
              <el-select
                v-model="form.category"
                filterable
                allow-create
                default-first-option
                clearable
                placeholder="选择或输入新分类"
                style="width: 100%"
              >
                <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.name" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="标签">
              <el-input v-model="form.tags" maxlength="200" placeholder="多个用逗号分隔" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="语种">
              <el-input v-model="form.language" maxlength="50" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">出版信息</el-divider>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="出版社">
              <el-input v-model="form.publisher" maxlength="100" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="出版地">
              <el-input v-model="form.publish_place" maxlength="100" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="出版日期">
              <el-date-picker
                v-model="form.publish_date"
                type="date"
                value-format="YYYY-MM-DD"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="版次">
              <el-input v-model="form.edition" maxlength="50" placeholder="如：第2版" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="装帧">
              <el-input v-model="form.binding" maxlength="20" placeholder="平装 / 精装" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="开本">
              <el-input v-model="form.book_format" maxlength="20" placeholder="如：16开" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="页数">
              <el-input-number v-model="form.page_count" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="定价">
              <el-input-number v-model="form.price" :min="0" :precision="2" :step="1" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">馆藏信息</el-divider>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="条形码">
              <el-input v-model="form.barcode" maxlength="50" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="索书号">
              <el-input v-model="form.call_number" maxlength="100" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="馆藏位置">
              <el-input v-model="form.location" maxlength="100" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="来源">
              <el-input v-model="form.source" maxlength="50" placeholder="购买 / 捐赠 / 调拨" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="库存">
              <el-input-number v-model="form.stock" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="封面">
              <div class="cover-input">
                <el-input v-model="form.cover_url" maxlength="500" placeholder="上传或粘贴图片链接" />
                <el-upload :show-file-list="false" accept=".jpg,.jpeg,.png,.webp" :http-request="uploadCover">
                  <el-button :loading="uploading">上传</el-button>
                </el-upload>
              </div>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item v-if="form.cover_url" label="预览">
          <el-image :src="form.cover_url" fit="cover" style="width: 96px; height: 128px; border-radius: 4px" />
        </el-form-item>

        <el-divider content-position="left">内容介绍</el-divider>
        <el-form-item label="内容简介">
          <el-input v-model="form.summary" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="作者简介">
          <el-input v-model="form.author_intro" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="目录">
          <el-input v-model="form.catalog" type="textarea" :rows="4" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="importVisible" title="批量导入图书" width="480px">
      <el-upload
        drag
        action="/api/books/import"
        :headers="authHeaders"
        accept=".xlsx"
        :show-file-list="false"
        :on-success="onImportOk"
        :on-error="onImportErr"
      >
        <div class="upload-tip">拖拽 .xlsx 文件到此处，或<em>点击选择文件</em></div>
      </el-upload>
      <div class="import-tip">
        表头需包含「书名」「作者」列，建议先导出 Excel 作为模板填写；ISBN 重复的行会自动跳过。
      </div>
    </el-dialog>

    <el-dialog v-model="recycleVisible" title="回收站" width="720px">
      <el-table v-loading="recycleLoading" :data="deletedBooks" size="small" border>
        <el-table-column prop="title" label="书名" min-width="140" />
        <el-table-column prop="author" label="作者" width="100" />
        <el-table-column prop="isbn" label="ISBN" width="160" />
        <el-table-column label="删除时间" width="160">
          <template #default="{ row }">{{ (row.deleted_at || '').replace('T', ' ').slice(0, 19) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="restoreBook(row)">恢复</el-button>
            <el-button link type="danger" @click="purgeBook(row)">彻底删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <el-dialog v-model="batchCategoryVisible" title="批量改分类" width="420px">
      <el-select
        v-model="batchCategory"
        filterable
        allow-create
        default-first-option
        placeholder="选择或输入新分类"
        style="width: 100%"
      >
        <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.name" />
      </el-select>
      <template #footer>
        <el-button @click="batchCategoryVisible = false">取消</el-button>
        <el-button type="primary" :loading="batchSaving" @click="submitBatchCategory">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/api/request'

// 展开行详情字段：[字段名, 显示名]
const fmt = (v) => (v === null || v === undefined || v === '' ? '—' : v)

const detailFields = [
  ['subtitle', '副标题'],
  ['original_title', '原作名'],
  ['translator', '译者'],
  ['series', '丛书系列'],
  ['category', '分类'],
  ['tags', '标签'],
  ['language', '语种'],
  ['publisher', '出版社'],
  ['publish_place', '出版地'],
  ['publish_date', '出版日期'],
  ['edition', '版次'],
  ['binding', '装帧'],
  ['book_format', '开本'],
  ['page_count', '页数'],
  ['isbn', 'ISBN'],
  ['barcode', '条形码'],
  ['call_number', '索书号'],
  ['location', '馆藏位置'],
  ['source', '来源'],
  ['price', '定价'],
]

// ---------- 列表 ----------
const tableRef = ref()
const books = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const keyword = ref('')
const loading = ref(false)
const categories = ref([])

const load = async () => {
  loading.value = true
  try {
    const res = await request.get('/books', {
      params: {
        page: page.value,
        size: size.value,
        keyword: keyword.value || undefined,
      },
    })
    books.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

const loadCategories = async () => {
  categories.value = await request.get('/categories')
}

const search = () => {
  page.value = 1
  load()
}

// ---------- 导入导出 ----------
const exporting = ref(false)
const importVisible = ref(false)
const authHeaders = computed(() => ({
  Authorization: `Bearer ${localStorage.getItem('token') || ''}`,
}))

const exportBooks = async () => {
  exporting.value = true
  try {
    const blob = await request.get('/books/export', { responseType: 'blob' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `图书数据_${new Date().toISOString().slice(0, 10)}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  } finally {
    exporting.value = false
  }
}

const onImportOk = async (res) => {
  importVisible.value = false
  const msg = `成功导入 ${res.created} 本，跳过 ${res.skipped} 本，失败 ${res.failed} 本`
  if (res.errors?.length) {
    await ElMessageBox.alert(res.errors.join('\n'), msg, {
      confirmButtonText: '知道了',
      customStyle: { whiteSpace: 'pre-line' },
    })
  } else {
    ElMessage.success(msg)
  }
  load()
  loadCategories()
}

const onImportErr = () => {
  ElMessage.error('导入失败，请确认文件为 .xlsx 格式')
}

// ---------- ISBN 在线查询 ----------
const lookingUp = ref(false)

const lookupIsbn = async () => {
  const isbn = form.isbn.trim()
  if (!isbn) {
    return
  }
  lookingUp.value = true
  try {
    const res = await request.get('/books/lookup', { params: { isbn } })
    const fillFields = [
      'title', 'subtitle', 'original_title', 'author', 'translator', 'publisher',
      'publish_date', 'edition', 'binding', 'series', 'page_count', 'price',
      'summary', 'author_intro', 'cover_url',
    ]
    fillFields.forEach((k) => {
      if (res[k] !== null && res[k] !== undefined && res[k] !== '') {
        form[k] = res[k]
      }
    })
    ElMessage.success(`已从${res.source || '网络'}获取图书信息，请核对后保存`)
  } catch {
    // 错误提示由 axios 拦截器统一弹出
  } finally {
    lookingUp.value = false
  }
}

// ---------- 回收站 ----------
const recycleVisible = ref(false)
const recycleLoading = ref(false)
const deletedBooks = ref([])

const openRecycleBin = async () => {
  recycleVisible.value = true
  recycleLoading.value = true
  try {
    deletedBooks.value = await request.get('/books/recycle-bin')
  } finally {
    recycleLoading.value = false
  }
}

const restoreBook = async (row) => {
  await request.post(`/books/${row.id}/restore`)
  ElMessage.success(`《${row.title}》已恢复`)
  openRecycleBin()
  load()
}

const purgeBook = async (row) => {
  try {
    await ElMessageBox.confirm(
      `彻底删除《${row.title}》后不可恢复，确定吗？`,
      '彻底删除',
      { type: 'error', confirmButtonText: '彻底删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  await request.delete(`/books/${row.id}/purge`)
  ElMessage.success('已彻底删除')
  openRecycleBin()
}

// ---------- 批量操作 ----------
const selection = ref([])
const batchCategoryVisible = ref(false)
const batchCategory = ref('')
const batchSaving = ref(false)

const onSelectionChange = (rows) => {
  selection.value = rows
}

const batchRemove = async () => {
  const ids = selection.value.map((r) => r.id)
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${ids.length} 本图书吗？`, '批量删除', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  const res = await request.post('/books/batch-delete', { ids })
  ElMessage.success(`已移入回收站 ${res.deleted} 本`)
  load()
}

const openBatchCategory = () => {
  batchCategory.value = ''
  batchCategoryVisible.value = true
}

const submitBatchCategory = async () => {
  if (!batchCategory.value) {
    return ElMessage.warning('请选择或输入分类')
  }
  batchSaving.value = true
  try {
    const ids = selection.value.map((r) => r.id)
    await request.post('/books/batch-category', { ids, category: batchCategory.value })
    ElMessage.success(`已把 ${ids.length} 本图书分类改为「${batchCategory.value}」`)
    batchCategoryVisible.value = false
    tableRef.value?.clearSelection()
    load()
    loadCategories()
  } finally {
    batchSaving.value = false
  }
}

// ---------- 新增 / 编辑 ----------
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref(null)
const saving = ref(false)
const uploading = ref(false)

const emptyForm = () => ({
  title: '', subtitle: '', original_title: '', author: '', translator: '',
  isbn: '', series: '', language: '中文', category: '', tags: '',
  publisher: '', publish_place: '', publish_date: '', edition: '',
  binding: '', book_format: '', page_count: null,
  barcode: '', call_number: '', location: '', source: '', cover_url: '',
  price: 0, stock: 0,
  summary: '', author_intro: '', catalog: '',
})
const form = reactive(emptyForm())

const openAdd = () => {
  Object.assign(form, emptyForm())
  isEdit.value = false
  editingId.value = null
  dialogVisible.value = true
}

const openEdit = (row) => {
  Object.keys(form).forEach((k) => {
    form[k] = row[k] ?? (k === 'price' || k === 'stock' ? 0 : '')
  })
  isEdit.value = true
  editingId.value = row.id
  dialogVisible.value = true
}

const uploadCover = async ({ file }) => {
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    const res = await request.post('/uploads/cover', fd)
    form.cover_url = res.url
    ElMessage.success('封面上传成功')
  } finally {
    uploading.value = false
  }
}

const submit = async () => {
  if (!form.title.trim() || !form.author.trim()) {
    return ElMessage.warning('书名和作者不能为空')
  }
  // 必填字段 + 其余字段去掉首尾空格、空串转 null（日期/页数等才能正常入库）
  const payload = {}
  for (const [k, v] of Object.entries(form)) {
    if (k === 'title' || k === 'author') {
      payload[k] = v.trim()
    } else if (typeof v === 'string') {
      payload[k] = v.trim() || null
    } else {
      payload[k] = v
    }
  }

  saving.value = true
  try {
    if (isEdit.value) {
      await request.put(`/books/${editingId.value}`, payload)
    } else {
      await request.post('/books', payload)
    }
    ElMessage.success('保存成功')
    dialogVisible.value = false
    load()
    loadCategories()
  } finally {
    saving.value = false
  }
}

// ---------- 删除 ----------
const remove = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定删除《${row.title}》吗？删除后可在回收站恢复。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  await request.delete(`/books/${row.id}`)
  ElMessage.success('已移入回收站')
  load()
}

onMounted(() => {
  load()
  loadCategories()
})
</script>

<style scoped>
.page {
  width: 100%;
}
.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}
.pagination {
  margin-top: 16px;
  justify-content: flex-end;
}
.detail {
  padding: 12px 24px;
}
.detail-text {
  margin-top: 12px;
}
.detail-text :deep(.el-descriptions__label) {
  width: 90px;
}
.detail :deep(.el-descriptions__body .el-descriptions__cell) {
  word-break: break-all;
}
.no-cover {
  font-size: 12px;
  color: #c0c4cc;
}
.isbn-row {
  display: flex;
  gap: 8px;
  width: 100%;
}
.cover-input {
  display: flex;
  gap: 8px;
  width: 100%;
}
.upload-tip {
  padding: 24px 0;
  color: #606266;
}
.upload-tip em {
  color: #409eff;
  font-style: normal;
}
.import-tip {
  margin-top: 12px;
  color: #909399;
  font-size: 13px;
  line-height: 1.6;
}
</style>

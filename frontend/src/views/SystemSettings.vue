<template>
  <div class="page">
    <el-card shadow="never" class="card">
      <template #header>借阅规则</template>
      <el-form label-width="140px" :disabled="!isAdmin">
        <el-form-item label="默认借期（天）">
          <el-input-number v-model="form.borrow_days" :min="1" :max="365" />
          <span class="tip">办借书登记时不填借期，就按这个天数算应还日期</span>
        </el-form-item>
        <el-form-item label="续借顺延（天）">
          <el-input-number v-model="form.renew_days" :min="1" :max="365" />
          <span class="tip">点「续借」后应还日期往后推多少天</span>
        </el-form-item>
        <el-form-item label="逾期日罚金（元）">
          <el-input-number v-model="form.fine_per_day" :min="0" :max="100" :step="0.1" :precision="2" />
          <span class="tip">逾期一天收多少元，罚款功能预留</span>
        </el-form-item>
        <el-form-item label="新读者可借上限">
          <el-input-number v-model="form.max_borrow" :min="1" :max="20" />
          <span class="tip">新建读者档案时默认的可同时借阅本数</span>
        </el-form-item>
        <el-form-item v-if="isAdmin">
          <el-button type="primary" :loading="saving" @click="save">保存设置</el-button>
        </el-form-item>
      </el-form>
      <el-alert v-if="!isAdmin" title="仅管理员可修改设置" type="info" :closable="false" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/api/request'

const isAdmin = ref(false)
const saving = ref(false)
const form = reactive({ borrow_days: 31, renew_days: 30, fine_per_day: 0.5, max_borrow: 5 })

onMounted(async () => {
  // 规则和当前用户身份并行取，互不依赖
  const [rules, me] = await Promise.all([request.get('/settings'), request.get('/auth/me')])
  Object.assign(form, rules)
  isAdmin.value = !!me.is_admin
})

const save = async () => {
  saving.value = true
  try {
    const rules = await request.put('/settings', { ...form })
    Object.assign(form, rules)
    ElMessage.success('设置已保存，立即生效')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.page {
  width: 100%;
}
.card {
  max-width: 680px;
}
.tip {
  margin-left: 12px;
  color: #909399;
  font-size: 12px;
}
</style>

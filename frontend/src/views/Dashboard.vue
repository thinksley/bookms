<template>
  <div class="page">
    <el-row :gutter="16">
      <el-col :span="5"><div class="stat"><div class="num">{{ s.titles ?? 0 }}</div><div class="label">藏书品种</div></div></el-col>
      <el-col :span="5"><div class="stat"><div class="num">{{ s.stock ?? 0 }}</div><div class="label">总库存（本）</div></div></el-col>
      <el-col :span="5"><div class="stat"><div class="num">{{ s.active_borrows ?? 0 }}</div><div class="label">在借（笔）</div></div></el-col>
      <el-col :span="5"><div class="stat"><div class="num" :class="{ danger: s.overdue }">{{ s.overdue ?? 0 }}</div><div class="label">逾期（笔）</div></div></el-col>
      <el-col :span="4"><div class="stat"><div class="num" :class="{ danger: lowCount }">{{ lowCount }}</div><div class="label">库存告警（种）</div></div></el-col>
    </el-row>

    <el-row :gutter="16" class="mt">
      <el-col :span="14">
        <el-card shadow="never">
          <template #header>分类分布</template>
          <div v-if="s.categories?.length" class="bars">
            <div v-for="c in s.categories" :key="c.name" class="bar-row">
              <span class="bar-name">{{ c.name }}</span>
              <div class="bar-track"><div class="bar-fill" :style="{ width: pct(c.count) }"></div></div>
              <span class="bar-num">{{ c.count }} 种</span>
            </div>
          </div>
          <el-empty v-else description="暂无数据" :image-size="60" />
        </el-card>

        <el-card shadow="never" class="mt">
          <template #header>最近入库</template>
          <div v-if="s.recent?.length" class="list">
            <div v-for="b in s.recent" :key="b.id" class="list-row">
              <span class="list-title">《{{ b.title }}》</span>
              <span class="list-sub">{{ b.publisher || '—' }} · {{ (b.created_at || '').slice(0, 10) }}</span>
            </div>
          </div>
          <el-empty v-else description="暂无数据" :image-size="60" />
        </el-card>
      </el-col>

      <el-col :span="10">
        <el-card shadow="never">
          <template #header>借阅排行 TOP5</template>
          <div v-if="s.top_borrowed?.length" class="list">
            <div v-for="(t, i) in s.top_borrowed" :key="t.title" class="list-row">
              <span class="rank" :class="'r' + (i + 1)">{{ i + 1 }}</span>
              <span class="list-title">{{ t.title }}</span>
              <span class="list-sub">{{ t.count }} 次</span>
            </div>
          </div>
          <el-empty v-else description="暂无借阅记录" :image-size="60" />
        </el-card>

        <el-card shadow="never" class="mt">
          <template #header>库存告警（库存 ≤ 3）</template>
          <div v-if="s.low_stock?.length" class="list">
            <div v-for="b in s.low_stock" :key="b.id" class="list-row">
              <span class="list-title">《{{ b.title }}》</span>
              <el-tag :type="b.stock === 0 ? 'danger' : 'warning'" size="small">剩 {{ b.stock }} 本</el-tag>
            </div>
          </div>
          <el-empty v-else description="库存充足" :image-size="60" />
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" class="mt">
      <template #header>借阅热力图（星期 × 近 12 个月，颜色越深借得越多）</template>
      <div v-if="s.heatmap?.length" class="heatmap">
        <div class="heat-row">
          <span class="heat-label"></span>
          <span v-for="m in s.monthly_borrows" :key="m.month" class="heat-month">
            {{ Number(m.month.slice(5)) }}月
          </span>
        </div>
        <div v-for="(row, w) in s.heatmap" :key="w" class="heat-row">
          <span class="heat-label">{{ weekNames[w] }}</span>
          <span
            v-for="(v, i) in row"
            :key="i"
            class="heat-cell"
            :style="{ backgroundColor: heatColor(v), color: v / maxHeat > 0.55 ? '#fff' : '#909399' }"
            :title="`${s.monthly_borrows[i]?.month} ${weekNames[w]}：借出 ${v} 次`"
          >{{ v || '' }}</span>
        </div>
      </div>
      <el-empty v-else description="暂无借阅数据" :image-size="60" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import request from '@/api/request'

const s = ref({})

const lowCount = computed(() => s.value.low_stock?.length || 0)
const maxCount = computed(() => Math.max(1, ...(s.value.categories || []).map((c) => c.count)))
const pct = (count) => `${Math.round((count / maxCount.value) * 100)}%`

// ---------- 借阅热力图 ----------
const weekNames = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

const maxHeat = computed(() => {
  let max = 0
  for (const row of s.value.heatmap || []) {
    for (const v of row) max = Math.max(max, v)
  }
  return max || 1
})

const heatColor = (v) => {
  if (!v) return '#f5f7fa'
  const alpha = 0.15 + 0.85 * (v / maxHeat.value)
  return `rgba(64, 158, 255, ${alpha.toFixed(2)})`
}

onMounted(async () => {
  s.value = await request.get('/stats')
})
</script>

<style scoped>
.page {
  width: 100%;
}
.stat {
  background: #fff;
  border: 1px solid #e6e6e6;
  border-radius: 8px;
  padding: 20px;
  text-align: center;
}
.num {
  font-size: 32px;
  font-weight: bold;
  color: #303133;
}
.num.danger {
  color: #f56c6c;
}
.label {
  margin-top: 6px;
  color: #909399;
  font-size: 13px;
}
.mt {
  margin-top: 16px;
}
.bars {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 6px 0;
}
.bar-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.bar-name {
  width: 90px;
  text-align: right;
  color: #606266;
  font-size: 13px;
}
.bar-track {
  flex: 1;
  height: 14px;
  background: #f0f2f5;
  border-radius: 7px;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #409eff, #79bbff);
  border-radius: 7px;
}
.bar-num {
  width: 50px;
  color: #909399;
  font-size: 13px;
}
.list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 2px 0;
}
.list-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.list-title {
  color: #303133;
}
.list-sub {
  margin-left: auto;
  color: #909399;
  font-size: 13px;
}
.rank {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #c0c4cc;
  color: #fff;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.rank.r1 { background: #f56c6c; }
.rank.r2 { background: #e6a23c; }
.rank.r3 { background: #409eff; }
.heatmap {
  padding: 4px 0;
}
.heat-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
}
.heat-label {
  width: 44px;
  text-align: right;
  color: #606266;
  font-size: 12px;
  flex-shrink: 0;
}
.heat-month {
  flex: 1;
  max-width: 64px;
  text-align: center;
  color: #909399;
  font-size: 12px;
}
.heat-cell {
  flex: 1;
  max-width: 64px;
  height: 34px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}
</style>

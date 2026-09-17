<script setup>
import { onMounted, ref } from 'vue'
import { getJSON } from '../api'
const items = ref([])
onMounted(async () => { items.value = (await getJSON('/api/history')).items })

const parsed = (row) => {
  try { return JSON.parse(row.result_json) } catch { return null }
}
const summary = (row) => {
  const r = parsed(row)
  if (!r) return '—'
  if (r.total != null) return `¥${r.total}`
  return `平${r.plain_total}/尖${r.peak_total}`
}
// 历史 bill 运行：钉选写入当时的命中时段与系数，不受后续配置变更影响
const peakPin = (row) => {
  if (row.kind !== 'bill') return null
  const r = parsed(row)
  const snap = r?.peak_snapshot
  if (!snap) return null
  if (snap.hit) return { hit: true, text: `${snap.window_code} ×${snap.factor}` }
  return { hit: false, text: `未命中 ×${snap.factor}` }
}
</script>
<template>
  <div class="page">
    <h1>测算记录</h1>
    <table>
      <thead>
        <tr><th>#</th><th>类型</th><th>户号</th><th>结果摘要</th><th>尖峰钉选（快照）</th><th>时间</th></tr></thead>
      <tbody>
        <tr v-for="h in items" :key="h.id">
          <td>{{ h.id }}</td><td>{{ h.kind }}</td><td>{{ h.account_id ?? '—' }}</td>
          <td>{{ summary(h) }}</td>
          <td>
            <span v-if="peakPin(h)" :class="peakPin(h).hit ? 'tag on' : 'tag off'">
              {{ peakPin(h).text }}
            </span>
            <span v-else class="muted">—</span>
          </td>
          <td class="muted">{{ h.created_at }}</td>
        </tr>
      </tbody>
    </table>
    <p class="muted hint">“钉选”列为运行写入时快照的命中时段与系数；之后在维护页停用/调整时段不会改写历史。</p>
  </div>
</template>
<style scoped>
.tag { padding: 0.1rem 0.5rem; border-radius: 999px; font-size: 0.78rem; }
.tag.on { background: color-mix(in srgb, var(--accent) 22%, transparent); color: var(--accent); }
.tag.off { background: color-mix(in srgb, var(--muted) 20%, transparent); color: var(--muted); }
.hint { font-size: 0.85rem; }
</style>

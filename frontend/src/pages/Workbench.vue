<script setup>
import { ref } from 'vue'
import { postJSON, errMsg } from '../api'
import TierLadder from '../components/TierLadder.vue'
import SegmentTable from '../components/SegmentTable.vue'

const nowLocal = () => {
  const d = new Date()
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset())
  return d.toISOString().slice(0, 16)
}

const MISS_REASONS = {
  PEAK_NOT_REQUESTED: '未勾选尖峰',
  NO_ENABLED_WINDOW: '当前没有启用的尖峰时段',
  OUTSIDE_ALL_WINDOWS: '账期锚定时刻不在任何启用时段内',
}

const kwh = ref(220)
const peak = ref(false)
const anchor = ref(nowLocal())
const result = ref(null)
const error = ref('')

const run = async (persist) => {
  error.value = ''
  try {
    result.value = await postJSON('/api/bill', {
      kwh: kwh.value,
      peak: peak.value,
      persist,
      anchor_at: anchor.value || null,
    })
  } catch (e) {
    error.value = errMsg(e)
  }
}

const missText = (r) => MISS_REASONS[r.peak?.miss_reason] ?? r.peak?.miss_reason
</script>
<template>
  <div class="page work">
    <h1>测算工作台</h1>
    <div class="panel form-row">
      <label>电量(kWh) <input type="number" v-model.number="kwh" min="0" step="1" /></label>
      <label>账期锚定时刻 <input type="datetime-local" v-model="anchor" /></label>
      <label><input type="checkbox" v-model="peak" /> 尖峰系数</label>
      <button @click="run(false)">试算(不入库)</button>
      <button @click="run(true)">计算并入库</button>
    </div>
    <div v-if="error" class="panel error">{{ error }}</div>
    <div v-if="result" class="panel">
      <p>
        合计 ¥{{ result.total }}
        <span v-if="result.run_id" class="muted">记录#{{ result.run_id }}</span>
        <span v-else class="muted">试算结果，未入库</span>
      </p>
      <p class="peak-line">
        <template v-if="result.peak?.matched">
          命中时段「{{ result.peak.window_code }}」
          <span class="muted">
            {{ result.peak.window.start }}–{{ result.peak.window.end }}<template v-if="result.peak.window.cross_day">(跨日)</template>
          </span>
          · 系数 ×{{ result.peak.factor }}
          <span class="muted">（来源 {{ result.peak.factor_source }}）</span>
        </template>
        <template v-else>
          未套用尖峰系数（{{ missText(result) }}），按系数 ×1.0 计算
        </template>
      </p>
      <TierLadder :segments="result.segments" />
      <SegmentTable :rows="result.segments" />
    </div>
  </div>
</template>
<style scoped>
.form-row { display: flex; flex-wrap: wrap; gap: 1rem; align-items: end; }
.form-row label { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.85rem; }
.form-row label:has(input[type=checkbox]) { flex-direction: row; align-items: center; }
input[type=number] { width: 6rem; }
.peak-line { margin-top: 0.25rem; }
.error { border: 1px solid #d6455b; color: #f2b8c1; }
</style>

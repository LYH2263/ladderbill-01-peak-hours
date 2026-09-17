<script setup>
import { ref } from 'vue'
import { postJSON } from '../api'
import { defaultAnchor, missReasonText, FACTOR_SOURCE_LABELS } from '../peak'
import TierLadder from '../components/TierLadder.vue'
import SegmentTable from '../components/SegmentTable.vue'

const kwh = ref(220)
const peak = ref(true)
const anchor = ref(defaultAnchor())
const result = ref(null)
const error = ref('')
const busy = ref(false)

const run = async (persist) => {
  error.value = ''
  busy.value = true
  try {
    result.value = await postJSON('/api/bill', {
      kwh: kwh.value,
      peak: peak.value,
      anchor_date: peak.value ? anchor.value : null,
      persist,
    })
  } catch (e) {
    result.value = null
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="page work">
    <h1>测算工作台</h1>
    <div class="panel form-row">
      <label>电量(kWh) <input type="number" v-model.number="kwh" min="0" step="1" /></label>
      <label><input type="checkbox" v-model="peak" /> 尖峰系数</label>
      <label v-if="peak">
        账期锚定时刻
        <input type="datetime-local" v-model="anchor" />
      </label>
      <button :disabled="busy" @click="run(false)">只读试算</button>
      <button class="solid" :disabled="busy" @click="run(true)">计算并入库</button>
    </div>

    <div v-if="error" class="panel error-box">⚠ {{ error }}</div>

    <div v-if="result" class="panel hit-panel" :class="result.peak_hit ? 'hit' : 'miss'">
      <template v-if="peak">
        <div v-if="result.peak_hit" class="hit-line">
          <span class="hit-badge">命中尖峰</span>
          <div>
            命中时段 <code>{{ result.window_code }}</code>
            （优先级 {{ result.window_priority }}），
            锚定 {{ result.anchor_label }}
          </div>
        </div>
        <div v-else class="hit-line">
          <span class="miss-badge">未命中</span>
          <div>{{ missReasonText(result.miss_reason) }} · 锚定 {{ result.anchor_label ?? '—' }}</div>
        </div>
        <div class="factor-line">
          所用系数 <strong>{{ result.factor }}</strong>
          <span class="muted">来源：{{ FACTOR_SOURCE_LABELS[result.factor_source] ?? result.factor_source }}</span>
          <span class="muted">（settings.peak_factor = {{ result.settings_peak_factor }}）</span>
        </div>
      </template>
      <div v-else class="factor-line muted">未勾选尖峰，按平段系数 1.0 计费（与改造前一致）</div>
    </div>

    <div v-if="result" class="panel">
      <p>
        合计 ¥{{ result.total }}
        <span class="muted" v-if="result.run_id">记录 #{{ result.run_id }} · 已钉选当时系数</span>
        <span class="muted" v-else>试算结果（不产生运行记录）</span>
      </p>
      <TierLadder :segments="result.segments" />
      <SegmentTable :rows="result.segments" />
    </div>

    <p class="muted hint">
      提示：在“尖峰时段”页调整启用窗或优先级后，同户同电量再次试算会立即反映新的命中关系；
      已入库的历史运行保留写入时钉选的系数，可在“记录”页对照查阅。
    </p>
  </div>
</template>

<style scoped>
.form-row { display: flex; flex-wrap: wrap; gap: 1rem; align-items: end; }
input[type=number] { width: 6rem; margin-left: 0.35rem; }
button.solid { box-shadow: 0 0 0 2px color-mix(in srgb, var(--accent) 40%, transparent); }
.error-box { border: 1px solid #d97070; color: #f3b3b3; }
.hit-panel { border-left: 4px solid var(--muted); }
.hit-panel.hit { border-left-color: var(--accent); }
.hit-line { display: flex; align-items: center; gap: 0.75rem; font-size: 1.02rem; }
.hit-badge, .miss-badge { padding: 0.15rem 0.6rem; border-radius: 999px; font-size: 0.82rem; font-weight: 600; }
.hit-badge { background: color-mix(in srgb, var(--accent) 22%, transparent); color: var(--accent); }
.miss-badge { background: color-mix(in srgb, var(--muted) 22%, transparent); color: var(--muted); }
.factor-line { margin-top: 0.5rem; font-size: 0.95rem; display: flex; gap: 0.6rem; flex-wrap: wrap; align-items: baseline; }
.hint { font-size: 0.85rem; }
</style>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getJSON, postJSON } from '../api'
import { defaultAnchor, FACTOR_SOURCE_LABELS, missReasonText } from '../peak'
import SegmentTable from '../components/SegmentTable.vue'
const route = useRoute()
const data = ref(null)
const bill = ref(null)
const peak = ref(false)
const anchor = ref(defaultAnchor())
const load = async () => {
  data.value = await getJSON(`/api/accounts/${route.params.id}`)
  const r = data.value.readings[0]
  if (r) {
    peak.value = !!r.peak
    bill.value = await postJSON('/api/bill', {
      account_id: +route.params.id,
      kwh: r.kwh,
      peak: !!r.peak,
      anchor_date: r.peak ? anchor.value : null,
      persist: false,
    })
  }
}
onMounted(load)
watch(() => route.params.id, load)
const account = computed(() => data.value?.account)
</script>
<template>
  <div class="page" v-if="account">
    <h1>{{ account.name }}</h1>
    <p class="muted">表号 {{ account.meter_no }} · {{ account.note }}</p>
    <div class="panel">
      <h3>最近抄表试算（只读，不落库）</h3>
      <label><input type="checkbox" v-model="peak" @change="bill = null" /> 尖峰</label>
      <label v-if="peak" style="margin-left:0.75rem">
        锚定时刻 <input type="datetime-local" v-model="anchor" />
      </label>
      <button @click="load">刷新</button>
      <p v-if="bill">合计 <strong class="hero-num" style="font-size:1.5rem">¥{{ bill.total }}</strong></p>
      <p v-if="bill && peak" class="muted">
        <template v-if="bill.peak_hit">
          命中 <code>{{ bill.window_code }}</code>，系数 {{ bill.factor }}
          （{{ FACTOR_SOURCE_LABELS[bill.factor_source] ?? bill.factor_source }}）
        </template>
        <template v-else>未命中：{{ missReasonText(bill.miss_reason) }}，系数 {{ bill.factor }}</template>
      </p>
      <SegmentTable :rows="bill?.segments || []" />
    </div>
  </div>
</template>

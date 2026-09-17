<script setup>
import { onMounted, ref } from 'vue'
import { getJSON, postJSON, putJSON, errMsg } from '../api'

const items = ref([])
const error = ref('')
const editingId = ref(null)
const form = ref(blank())

function blank() {
  return { code: '', start: '18:00', end: '22:00', cross_day: false, priority: 0, enabled: true, note: '' }
}

async function reload() {
  items.value = (await getJSON('/api/peak-windows')).items
}

async function submit() {
  error.value = ''
  const body = { ...form.value, note: form.value.note || null }
  try {
    if (editingId.value) {
      await putJSON(`/api/peak-windows/${editingId.value}`, body)
    } else {
      await postJSON('/api/peak-windows', body)
    }
    form.value = blank()
    editingId.value = null
    await reload()
  } catch (e) {
    error.value = errMsg(e)
  }
}

function edit(w) {
  error.value = ''
  editingId.value = w.id
  form.value = { code: w.code, start: w.start, end: w.end, cross_day: w.cross_day, priority: w.priority, enabled: w.enabled, note: w.note ?? '' }
}

function cancelEdit() {
  editingId.value = null
  form.value = blank()
  error.value = ''
}

async function disable(w) {
  error.value = ''
  try {
    await postJSON(`/api/peak-windows/${w.id}/disable`, {})
    await reload()
  } catch (e) {
    error.value = errMsg(e)
  }
}

async function enable(w) {
  error.value = ''
  try {
    await putJSON(`/api/peak-windows/${w.id}`, { enabled: true })
    await reload()
  } catch (e) {
    error.value = errMsg(e)
  }
}

onMounted(reload)
</script>

<template>
  <div class="page">
    <h1>尖峰时段维护</h1>
    <p class="muted">测算勾选尖峰时，账期锚定时刻落入任一启用时段即套用 settings.peak_factor；同优先级时段不得重叠。</p>

    <div v-if="error" class="panel error">{{ error }}</div>

    <div class="panel">
      <h3>{{ editingId ? `编辑时段 #${editingId}` : '新建时段' }}</h3>
      <div class="form-row">
        <label>标识 <input v-model.trim="form.code" placeholder="如：晚高峰" /></label>
        <label>开始 <input type="time" v-model="form.start" /></label>
        <label>结束 <input type="time" v-model="form.end" /></label>
        <label>优先级 <input type="number" v-model.number="form.priority" step="1" /></label>
        <label><input type="checkbox" v-model="form.cross_day" /> 跨日</label>
        <label v-if="editingId"><input type="checkbox" v-model="form.enabled" /> 启用</label>
        <label>备注 <input v-model="form.note" placeholder="可选" /></label>
        <button @click="submit">{{ editingId ? '保存' : '创建' }}</button>
        <button v-if="editingId" class="ghost" @click="cancelEdit">取消</button>
      </div>
    </div>

    <table>
      <thead>
        <tr><th>标识</th><th>时段</th><th>优先级</th><th>状态</th><th>备注</th><th>操作</th></tr>
      </thead>
      <tbody>
        <tr v-for="w in items" :key="w.id" :class="{ off: !w.enabled }">
          <td>{{ w.code }}</td>
          <td>
            {{ w.start }} – {{ w.end }}
            <span v-if="w.cross_day" class="badge">跨日</span>
          </td>
          <td>{{ w.priority }}</td>
          <td>{{ w.enabled ? '启用' : '停用' }}</td>
          <td class="muted">{{ w.note ?? '—' }}</td>
          <td class="ops">
            <button class="ghost" @click="edit(w)">编辑</button>
            <button v-if="w.enabled" class="ghost" @click="disable(w)">停用</button>
            <button v-else class="ghost" @click="enable(w)">启用</button>
          </td>
        </tr>
        <tr v-if="!items.length"><td colspan="6" class="muted">暂无时段，请先创建</td></tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.form-row { display: flex; flex-wrap: wrap; gap: 0.9rem; align-items: end; }
.form-row label { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.85rem; }
.form-row label:has(input[type=checkbox]) { flex-direction: row; align-items: center; }
input[type=number] { width: 5rem; }
.error { border: 1px solid #d6455b; color: #f2b8c1; }
.badge { border: 1px solid var(--accent); border-radius: 6px; padding: 0 0.3rem; font-size: 0.75rem; color: var(--accent); }
tr.off td { opacity: 0.55; }
.ops { white-space: nowrap; }
button.ghost { background: transparent; border: 1px solid var(--muted); color: var(--text); padding: 0.25rem 0.6rem; margin-right: 0.35rem; }
</style>

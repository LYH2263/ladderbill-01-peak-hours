<script setup>
import { onMounted, reactive, ref } from 'vue'
import { getJSON, postJSON, putJSON } from '../api'

const items = ref([])
const error = ref('')
const loading = ref(false)

const blank = () => ({
  code: '', start_time: '18:00', end_time: '22:00',
  cross_day: false, priority: 100, enabled: true, note: '',
})
const form = reactive(blank())
const editingId = ref(null)
const editForm = reactive(blank())

const load = async () => {
  items.value = (await getJSON('/api/peak-windows')).items
}
onMounted(load)

const withError = async (fn) => {
  error.value = ''
  loading.value = true
  try { await fn() } catch (e) { error.value = e.message } finally { loading.value = false }
}

const create = async () => {
  await withError(async () => {
    await postJSON('/api/peak-windows', payload(form))
    Object.assign(form, blank())
    await load()
  })
}

const startEdit = (w) => {
  editingId.value = w.id
  Object.assign(editForm, {
    code: w.code, start_time: w.start_time, end_time: w.end_time,
    cross_day: w.cross_day, priority: w.priority, enabled: w.enabled, note: w.note ?? '',
  })
}
const cancelEdit = () => { editingId.value = null }
const saveEdit = async () => {
  await withError(async () => {
    await putJSON(`/api/peak-windows/${editingId.value}`, payload(editForm))
    editingId.value = null
    await load()
  })
}

const disable = async (w) => {
  await withError(async () => {
    await postJSON(`/api/peak-windows/${w.id}/disable`)
    await load()
  })
}
const toggleEnabled = async (w) => {
  await withError(async () => {
    await putJSON(`/api/peak-windows/${w.id}`, { enabled: !w.enabled })
    await load()
  })
}

const payload = (f) => ({
  code: f.code.trim(),
  start_time: f.start_time,
  end_time: f.end_time,
  cross_day: f.cross_day,
  priority: Number(f.priority),
  enabled: f.enabled,
  note: f.note?.trim() || null,
})

const span = (w) => `${w.start_time} – ${w.end_time}${w.cross_day ? '（次日）' : ''}`
</script>

<template>
  <div class="page">
    <h1>尖峰时段维护</h1>
    <p class="muted">
      维护可启用的尖峰时段；账期锚定时刻落入启用时段时按 settings 的 peak_factor 计费。
      同优先级时段时间重叠会被拒绝，跨夜时段请勾选“跨日”。
    </p>

    <div v-if="error" class="panel error-box">⚠ {{ error }}</div>

    <table>
      <thead>
        <tr><th>标识</th><th>时间窗</th><th>跨日</th><th>优先级</th><th>状态</th><th>备注</th><th>操作</th></tr>
      </thead>
      <tbody>
        <tr v-for="w in items" :key="w.id" :class="{ disabled: !w.enabled }">
          <template v-if="editingId === w.id">
            <td><input v-model="editForm.code" size="14" /></td>
            <td>
              <input type="time" v-model="editForm.start_time" />
              –<input type="time" v-model="editForm.end_time" />
            </td>
            <td><input type="checkbox" v-model="editForm.cross_day" /></td>
            <td><input type="number" v-model.number="editForm.priority" min="0" style="width:5rem" /></td>
            <td><input type="checkbox" v-model="editForm.enabled" /> 启用</td>
            <td><input v-model="editForm.note" size="12" placeholder="备注" /></td>
            <td>
              <button :disabled="loading" @click="saveEdit">保存</button>
              <button class="ghost" @click="cancelEdit">取消</button>
            </td>
          </template>
          <template v-else>
            <td><code>{{ w.code }}</code></td>
            <td>{{ span(w) }}</td>
            <td>{{ w.cross_day ? '是' : '否' }}</td>
            <td>{{ w.priority }}</td>
            <td>
              <span :class="w.enabled ? 'tag on' : 'tag off'">
                {{ w.enabled ? '启用中' : '已停用' }}
              </span>
            </td>
            <td class="muted">{{ w.note ?? '—' }}</td>
            <td>
              <button class="ghost" @click="startEdit(w)">编辑</button>
              <button v-if="w.enabled" class="ghost danger" @click="disable(w)">停用</button>
              <button v-else class="ghost" @click="toggleEnabled(w)">重新启用</button>
            </td>
          </template>
        </tr>
      </tbody>
    </table>

    <div class="panel">
      <h3>新增时段</h3>
      <div class="form-grid">
        <label>标识
          <input v-model="form.code" placeholder="如 EVENING_PEAK" />
        </label>
        <label>开始
          <input type="time" v-model="form.start_time" />
        </label>
        <label>结束
          <input type="time" v-model="form.end_time" />
        </label>
        <label class="inline"><input type="checkbox" v-model="form.cross_day" /> 跨日</label>
        <label>优先级
          <input type="number" v-model.number="form.priority" min="0" />
        </label>
        <label class="inline"><input type="checkbox" v-model="form.enabled" /> 立即启用</label>
        <label class="wide">备注
          <input v-model="form.note" placeholder="可选" />
        </label>
      </div>
      <button :disabled="loading" @click="create">创建时段</button>
    </div>
  </div>
</template>

<style scoped>
.form-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 0.75rem; margin-bottom: 0.9rem; }
.form-grid label { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.85rem; color: var(--muted); }
.form-grid .inline { flex-direction: row; align-items: center; justify-content: flex-start; gap: 0.4rem; color: var(--text); }
.form-grid .wide { grid-column: span 3; }
tr.disabled { opacity: 0.55; }
.tag { padding: 0.1rem 0.5rem; border-radius: 999px; font-size: 0.78rem; }
.tag.on { background: color-mix(in srgb, var(--accent) 22%, transparent); color: var(--accent); }
.tag.off { background: color-mix(in srgb, var(--muted) 20%, transparent); color: var(--muted); }
button.ghost { background: transparent; border: 1px solid var(--muted); color: var(--text); margin-left: 0.35rem; }
button.danger { border-color: #d97070; color: #e89595; }
.error-box { border: 1px solid #d97070; color: #f3b3b3; }
input[type=time] { width: 7.2rem; }
</style>

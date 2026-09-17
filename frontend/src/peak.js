// 尖峰命中相关的前端展示工具

export const MISS_REASON_LABELS = {
  peak_not_requested: '未勾选尖峰',
  missing_anchor: '缺少账期锚定日',
  outside_windows: '锚定时刻不在任何启用时段内',
  disabled: '当前没有启用的尖峰时段',
}

export const FACTOR_SOURCE_LABELS = {
  'settings.peak_factor': 'settings.peak_factor（尖峰系数设置）',
  default_1_0: '未命中，按平段系数 1.0',
  not_applied: '未套用尖峰系数',
}

export const missReasonText = (reason) => MISS_REASON_LABELS[reason] ?? reason

// datetime-local 的默认值：今天 19:00（落在种子晚高峰内）
export const defaultAnchor = () => {
  const d = new Date()
  d.setHours(19, 0, 0, 0)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

import dayjs from 'dayjs'

/**
 * 生成月视图网格所需的日期数组（6行7列 = 42 天）。
 * 包含上月尾部 + 当月 + 下月头部的补位日期。
 */
export function generateMonthGrid(year, month) {
  const firstDay = dayjs(`${year}-${String(month).padStart(2, '0')}-01`)
  const startOfWeek = firstDay.day() // 0=周日

  const days = []

  // 上月补位
  for (let i = startOfWeek - 1; i >= 0; i--) {
    days.push({
      date: firstDay.subtract(i + 1, 'day'),
      isCurrentMonth: false,
    })
  }

  // 当月
  const daysInMonth = firstDay.daysInMonth()
  for (let d = 1; d <= daysInMonth; d++) {
    days.push({
      date: firstDay.date(d),
      isCurrentMonth: true,
    })
  }

  // 下月补位（补到 42 格 = 6 行）
  const remaining = 42 - days.length
  const lastDay = firstDay.date(daysInMonth)
  for (let i = 1; i <= remaining; i++) {
    days.push({
      date: lastDay.add(i, 'day'),
      isCurrentMonth: false,
    })
  }

  return days
}

/**
 * 按日期分组：{ "2026-04-24": [item, item, ...], ... }
 */
export function groupByDate(items) {
  const map = {}
  for (const item of items) {
    const key = item.item_date
    if (!map[key]) map[key] = []
    map[key].push(item)
  }
  return map
}

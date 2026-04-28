<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  stats: { type: Object, required: true },
})

const priorityBars = [
  { key: 3, label: '高', color: '#ef4444' },
  { key: 2, label: '中', color: '#f59e0b' },
  { key: 1, label: '低', color: '#3b82f6' },
  { key: 0, label: '无', color: '#d4d4d4' },
]

function getBarColor(idx) {
  const colors = ['#6b7280', '#8b5cf6', '#f59e0b', '#10b981', '#ef4444', '#3b82f6', '#ec4899', '#14b8a6', '#f97316', '#64748b']
  return colors[idx % colors.length]
}

// 数字过渡动画
const animatedTotal = ref(0)
let rafId = null

watch(() => props.stats.total, (newVal, oldVal) => {
  if (rafId) cancelAnimationFrame(rafId)
  const from = oldVal || 0
  const to = newVal || 0
  const duration = 300
  const start = performance.now()
  function step(now) {
    const t = Math.min((now - start) / duration, 1)
    const ease = 1 - Math.pow(1 - t, 3) // ease-out-cubic
    animatedTotal.value = Math.round(from + (to - from) * ease)
    if (t < 1) rafId = requestAnimationFrame(step)
  }
  rafId = requestAnimationFrame(step)
}, { immediate: true })
</script>

<template>
  <div>
    <!-- 标题 -->
    <div class="mb-4" style="color: #111; font-weight: 600; font-size: 0.9375rem; line-height: 1.3">
      {{ title }}：<span style="font-variant-numeric: tabular-nums">{{ animatedTotal }}</span> 条
      <span v-if="subtitle" style="color: #999; font-size: 0.6875rem; margin-left: 6px; font-weight: 400">{{ subtitle }}</span>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-x-6 md:gap-x-10 gap-y-5 md:gap-y-6">
      <!-- 优先级（独占一行） -->
      <div class="md:col-span-2 pb-2" style="border-bottom: 1px solid #f0f0f0">
        <div style="font-size: 0.6875rem; color: #999; margin-bottom: 8px; font-weight: 500; letter-spacing: 0.02em">优先级分布</div>
        <div v-for="(p, pi) in priorityBars" :key="p.key" :style="{ marginBottom: pi < priorityBars.length - 1 ? '8px' : '0' }">
          <div class="flex items-center justify-between" style="margin-bottom: 3px">
            <span style="font-size: 0.6875rem; color: #555">{{ p.label }}</span>
            <span style="font-size: 0.6875rem; color: #999; font-variant-numeric: tabular-nums">{{ stats.priority[p.key] || 0 }}</span>
          </div>
          <div style="background: #f0f0f0; border-radius: 3px; height: 8px; overflow: hidden">
            <div
              style="height: 100%; border-radius: 3px; transition: width 150ms ease"
              :style="{
                width: stats.total ? (stats.priority[p.key] / stats.total * 100) + '%' : '0%',
                backgroundColor: p.color,
              }"
              role="progressbar"
              :aria-valuenow="stats.priority[p.key] || 0"
              :aria-valuemax="stats.total"
            ></div>
          </div>
        </div>
      </div>

      <!-- 资源位 -->
      <div>
        <div style="font-size: 0.6875rem; color: #999; margin-bottom: 8px; font-weight: 500; letter-spacing: 0.02em">资源位</div>
        <div style="margin-bottom: 8px">
          <div class="flex items-center justify-between" style="margin-bottom: 3px">
            <span style="font-size: 0.6875rem; color: #555">已配置</span>
            <span style="font-size: 0.6875rem; color: #999; font-variant-numeric: tabular-nums">{{ stats.configuredCount }}</span>
          </div>
          <div style="background: #f0f0f0; border-radius: 3px; height: 8px; overflow: hidden">
            <div
              style="height: 100%; border-radius: 3px; background-color: #34c759; transition: width 150ms ease"
              :style="{ width: stats.total ? (stats.configuredCount / stats.total * 100) + '%' : '0%' }"
              role="progressbar"
            ></div>
          </div>
        </div>
        <div style="margin-bottom: 8px">
          <div class="flex items-center justify-between" style="margin-bottom: 3px">
            <span style="font-size: 0.6875rem; color: #555">未配置</span>
            <span style="font-size: 0.6875rem; color: #999; font-variant-numeric: tabular-nums">{{ stats.unconfiguredCount }}</span>
          </div>
          <div style="background: #f0f0f0; border-radius: 3px; height: 8px; overflow: hidden">
            <div
              style="height: 100%; border-radius: 3px; background-color: #d4d4d4; transition: width 150ms ease"
              :style="{ width: stats.total ? (stats.unconfiguredCount / stats.total * 100) + '%' : '0%' }"
              role="progressbar"
            ></div>
          </div>
        </div>
      </div>

      <!-- 数据来源 -->
      <div>
        <div style="font-size: 0.6875rem; color: #999; margin-bottom: 8px; font-weight: 500; letter-spacing: 0.02em">数据来源</div>
        <div style="margin-bottom: 8px">
          <div class="flex items-center justify-between" style="margin-bottom: 3px">
            <span style="font-size: 0.6875rem; color: #555">抓取</span>
            <span style="font-size: 0.6875rem; color: #999; font-variant-numeric: tabular-nums">{{ stats.newsCount }}</span>
          </div>
          <div style="background: #f0f0f0; border-radius: 3px; height: 8px; overflow: hidden">
            <div
              style="height: 100%; border-radius: 3px; background-color: #6b7280; transition: width 150ms ease"
              :style="{ width: stats.total ? (stats.newsCount / stats.total * 100) + '%' : '0%' }"
            ></div>
          </div>
        </div>
        <div style="margin-bottom: 8px">
          <div class="flex items-center justify-between" style="margin-bottom: 3px">
            <span style="font-size: 0.6875rem; color: #555">手动</span>
            <span style="font-size: 0.6875rem; color: #999; font-variant-numeric: tabular-nums">{{ stats.eventCount }}</span>
          </div>
          <div style="background: #f0f0f0; border-radius: 3px; height: 8px; overflow: hidden">
            <div
              style="height: 100%; border-radius: 3px; background-color: #a3a3a3; transition: width 150ms ease"
              :style="{ width: stats.total ? (stats.eventCount / stats.total * 100) + '%' : '0%' }"
            ></div>
          </div>
        </div>
      </div>

      <!-- 游戏分布 -->
      <div>
        <div style="font-size: 0.6875rem; color: #999; margin-bottom: 8px; font-weight: 500; letter-spacing: 0.02em">游戏分布</div>
        <template v-if="stats.gameDist.length">
          <div v-for="([game, count], idx) in stats.gameDist" :key="game" style="margin-bottom: 8px">
            <div class="flex items-center justify-between" style="margin-bottom: 3px">
              <span style="font-size: 0.6875rem; color: #555">{{ game }}</span>
              <span style="font-size: 0.6875rem; color: #999; font-variant-numeric: tabular-nums">{{ count }}</span>
            </div>
            <div style="background: #f0f0f0; border-radius: 3px; height: 6px; overflow: hidden">
              <div
                style="height: 100%; border-radius: 3px; transition: width 150ms ease"
                :style="{ width: (count / stats.total * 100) + '%', backgroundColor: getBarColor(idx) }"
              ></div>
            </div>
          </div>
        </template>
        <div v-else style="font-size: 0.6875rem; color: #ccc">暂无数据</div>
      </div>

      <!-- 负责人分布 -->
      <div>
        <div style="font-size: 0.6875rem; color: #999; margin-bottom: 8px; font-weight: 500; letter-spacing: 0.02em">负责人分布</div>
        <template v-if="stats.ownerDist.length">
          <div v-for="([owner, count], idx) in stats.ownerDist" :key="owner" style="margin-bottom: 8px">
            <div class="flex items-center justify-between" style="margin-bottom: 3px">
              <span style="font-size: 0.6875rem; color: #555">{{ owner }}</span>
              <span style="font-size: 0.6875rem; color: #999; font-variant-numeric: tabular-nums">{{ count }}</span>
            </div>
            <div style="background: #f0f0f0; border-radius: 3px; height: 6px; overflow: hidden">
              <div
                style="height: 100%; border-radius: 3px; transition: width 150ms ease"
                :style="{ width: (count / stats.total * 100) + '%', backgroundColor: getBarColor(idx) }"
              ></div>
            </div>
          </div>
        </template>
        <div v-else style="font-size: 0.6875rem; color: #ccc">暂无数据</div>
      </div>
    </div>
  </div>
</template>

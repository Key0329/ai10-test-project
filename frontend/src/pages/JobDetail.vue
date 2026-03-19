<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { getJob, cancelJob, streamLogs } from '../api'
import StatusBadge from '../components/StatusBadge.vue'

const router = useRouter()
const route = useRoute()

const FILTER_OPTIONS = [
  { key: 'all', label: 'All' },
  { key: 'assistant', label: 'Assistant' },
  { key: 'tool', label: 'Tools' },
  { key: 'system', label: 'System' },
]

const props = defineProps({
  id: String,
})

const job = ref(null)
const logs = ref([])
const error = ref('')
const filter = ref('all')
const logEl = ref(null)
let stopStream = null
let pollInterval = null

const isActive = computed(() =>
  job.value && ['queued', 'cloning', 'running', 'pushing'].includes(job.value.status)
)

const filteredLogs = computed(() => logs.value.filter(matchesFilter))

function matchesFilter(entry) {
  if (filter.value === 'all') return true
  if (filter.value === 'assistant') return entry.event_type === 'assistant'
  if (filter.value === 'tool') return entry.event_type === 'tool_use' || entry.event_type === 'tool_result'
  if (filter.value === 'system') return entry.stream === 'system' || entry.stream === 'error'
  return true
}

function lineClass(entry) {
  if (entry.stream === 'error') return 'log-line log-line-error'
  if (entry.stream === 'stderr') return 'log-line log-line-stderr'
  if (entry.stream === 'system') return 'log-line log-line-system'
  if (entry.event_type === 'assistant') return 'log-line log-line-assistant'
  if (entry.event_type === 'user') return 'log-line log-line-tool-result'
  if (entry.event_type === 'result') return 'log-line log-line-result'
  return 'log-line'
}

function tagLabel(entry) {
  if (entry.stream === 'system') return 'SYS'
  if (entry.stream === 'error') return 'ERR'
  if (entry.event_type === 'assistant') return 'AI'
  if (entry.event_type === 'user') return 'TOOL'
  if (entry.event_type === 'system') return 'INIT'
  if (entry.event_type === 'result') return 'DONE'
  return entry.event_type || entry.stream
}

function tagColor(entry) {
  if (entry.stream === 'error') return '#c4736d'
  if (entry.stream === 'system') return '#75736e'
  if (entry.event_type === 'assistant') return '#7ba3c9'
  if (entry.event_type === 'user') return '#9b8dbd'
  if (entry.event_type === 'system') return '#75736e'
  if (entry.event_type === 'result') return '#6aab87'
  return '#75736e'
}

function elapsed() {
  if (!job.value) return '-'
  const start = new Date(job.value.created_at)
  const end = job.value.finished_at ? new Date(job.value.finished_at) : new Date()
  const s = Math.round((end - start) / 1000)
  if (s < 60) return `${s}s`
  return `${Math.floor(s / 60)}m ${s % 60}s`
}

async function loadJob() {
  try {
    job.value = await getJob(props.id)
  } catch (e) {
    error.value = e.message
  }
}

async function handleCancel() {
  if (!confirm('Cancel this job?')) return
  try {
    await cancelJob(props.id)
    job.value = await getJob(props.id)
  } catch (e) {
    error.value = e.message
  }
}

watch(isActive, (active, prevActive) => {
  if (active && !stopStream) {
    stopStream = streamLogs(
      props.id,
      (entry) => {
        logs.value.push(entry)
        if (logEl.value) {
          requestAnimationFrame(() => {
            logEl.value.scrollTop = logEl.value.scrollHeight
          })
        }
      },
      () => { stopStream = null }
    )
  }
  if (!active && stopStream) {
    stopStream()
    stopStream = null
  }
})

onMounted(() => {
  loadJob()
  pollInterval = setInterval(loadJob, 3000)
})

onUnmounted(() => {
  clearInterval(pollInterval)
  if (stopStream) {
    stopStream()
    stopStream = null
  }
})
</script>

<template>
  <div v-if="!job && !error" class="empty">Loading...</div>
  <div v-else-if="error" class="alert alert-error">{{ error }}</div>
  <div v-else-if="job">
    <button class="back-btn" @click="router.push('/')">← Back to Dashboard</button>

    <div class="detail-header" style="margin-top: 12px">
      <div style="display: flex; align-items: center; gap: 12px">
        <span class="detail-ticket">{{ job.jira_ticket }}</span>
        <StatusBadge :status="job.status" />
      </div>
      <div style="font-size: 12px; color: var(--text-dim)">{{ elapsed() }}</div>
    </div>

    <div class="detail-meta">
      <div class="meta-item">
        <div class="meta-label">Repository</div>
        <div class="meta-value">{{ job.repo_url }}</div>
      </div>
      <div class="meta-item">
        <div class="meta-label">Branch</div>
        <div class="meta-value">{{ job.branch || 'default' }}</div>
      </div>
      <div class="meta-item">
        <div class="meta-label">Requested by</div>
        <div class="meta-value">{{ job.requested_by || '-' }}</div>
      </div>
      <div class="meta-item">
        <div class="meta-label">Priority</div>
        <div class="meta-value">{{ job.priority }}</div>
      </div>
      <div class="meta-item">
        <div class="meta-label">Created</div>
        <div class="meta-value">{{ new Date(job.created_at).toLocaleString('zh-TW') }}</div>
      </div>
      <div class="meta-item">
        <div class="meta-label">Job ID</div>
        <div class="meta-value">{{ job.job_id }}</div>
      </div>
    </div>

    <div v-if="job.pr_url" class="alert alert-success">
      PR created: <a :href="job.pr_url" target="_blank" rel="noopener" style="color: inherit">{{ job.pr_url }}</a>
    </div>
    <div v-if="job.error_message" class="alert alert-error">{{ job.error_message }}</div>
    <div v-if="job.extra_prompt" style="margin-bottom: 14px">
      <div class="section-title">Extra Prompt</div>
      <div style="font-size: 12px; color: var(--text-dim); padding: 10px 14px; background: var(--surface); border-radius: 8px; border: 1px solid var(--border)">
        {{ job.extra_prompt }}
      </div>
    </div>

    <div style="display: flex; align-items: center; justify-content: space-between; margin-top: 16px">
      <div class="section-title" style="margin: 0">
        Logs <span v-if="isActive" style="color: var(--blue)">(live)</span>
      </div>
      <div style="display: flex; gap: 4px">
        <button
          v-for="opt in FILTER_OPTIONS"
          :key="opt.key"
          :style="{
            fontSize: '11px', padding: '2px 8px', borderRadius: '4px',
            border: '1px solid var(--border)',
            background: filter === opt.key ? 'var(--blue)' : 'var(--surface)',
            color: filter === opt.key ? '#fff' : 'var(--text-dim)',
            cursor: 'pointer',
          }"
          @click="filter = opt.key"
        >
          {{ opt.label }}
        </button>
      </div>
    </div>
    <div class="log-viewer" ref="logEl">
      <div v-if="filteredLogs.length === 0" style="color: var(--text-hint)">
        {{ isActive ? 'Waiting for output...' : 'No logs available.' }}
      </div>
      <div v-for="(entry, i) in filteredLogs" :key="i" :class="lineClass(entry)">
        <span class="log-tag" :style="{ background: tagColor(entry) }">{{ tagLabel(entry) }}</span>
        <span class="log-msg" v-html="entry.message.replace(/\n/g, '<br>')"></span>
      </div>
    </div>

    <button
      v-if="isActive"
      class="btn btn-danger"
      style="margin-top: 14px"
      @click="handleCancel"
    >
      Cancel Job
    </button>
  </div>
</template>

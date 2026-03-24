<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { listJobs } from '../api'
import StatusBadge from '../components/StatusBadge.vue'
import { useCredentials } from '../composables/useCredentials'

const { credentials, rememberEmail, save: saveCredentials } = useCredentials()
const showTokens = ref({ github: false, jira: false })

function onCredentialInput() {
  saveCredentials()
}

const router = useRouter()

const FILTERS = [
  { label: 'All', value: null },
  { label: 'Running', value: 'running' },
  { label: 'Queued', value: 'queued' },
  { label: 'Completed', value: 'completed' },
  { label: 'Failed', value: 'failed' },
]

const data = ref({ jobs: [], total: 0, running: 0, queued: 0 })
const filter = ref(null)
const error = ref('')
let interval = null

async function refresh() {
  try {
    data.value = await listJobs(filter.value)
    error.value = ''
  } catch (e) {
    error.value = e.message
  }
}

const completed = computed(() => data.value.jobs.filter(j => j.status === 'completed').length)
const failed = computed(() => data.value.jobs.filter(j => j.status === 'failed').length)
const successRate = computed(() => {
  const total = completed.value + failed.value
  return total > 0 ? Math.round((completed.value / total) * 100) : 0
})

function elapsed(job) {
  const start = new Date(job.created_at)
  const end = job.finished_at ? new Date(job.finished_at) : new Date()
  return Math.round((end - start) / 1000)
}

function timeAgo(iso) {
  if (!iso) return '-'
  const s = Math.round((Date.now() - new Date(iso)) / 1000)
  if (s < 60) return `${s}s ago`
  if (s < 3600) return `${Math.round(s / 60)}m ago`
  if (s < 86400) return `${Math.round(s / 3600)}h ago`
  return `${Math.round(s / 86400)}d ago`
}

watch(filter, () => refresh())

onMounted(() => {
  refresh()
  interval = setInterval(refresh, 4000)
})

onUnmounted(() => {
  clearInterval(interval)
})
</script>

<template>
  <div>
    <div v-if="error" class="alert alert-error">{{ error }}</div>

    <!-- Credentials 設定區 -->
    <div style="border: 1px solid var(--border); border-radius: 10px; background: var(--surface); padding: 16px; margin-bottom: 16px">
      <div style="font-size: 11px; font-weight: 600; color: var(--text-hint); letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 12px">
        🔑 API Credentials <span style="font-weight: 400; color: var(--text-dim)">(Token 關分頁即清除)</span>
      </div>
      <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px">
        <div>
          <div style="font-size: 11px; color: var(--text-dim); margin-bottom: 4px">GitHub Token</div>
          <div style="position: relative">
            <input
              :type="showTokens.github ? 'text' : 'password'"
              class="form-input"
              style="padding-right: 32px; font-size: 12px"
              v-model="credentials.github_token"
              placeholder="ghp_xxxxxxxxxxxx"
              @input="onCredentialInput"
            />
            <span
              style="position: absolute; right: 8px; top: 50%; transform: translateY(-50%); cursor: pointer; color: var(--text-hint); font-size: 13px; user-select: none"
              @click="showTokens.github = !showTokens.github"
            >{{ showTokens.github ? '🙈' : '👁' }}</span>
          </div>
        </div>
        <div>
          <div style="font-size: 11px; color: var(--text-dim); margin-bottom: 4px">Jira API Token</div>
          <div style="position: relative">
            <input
              :type="showTokens.jira ? 'text' : 'password'"
              class="form-input"
              style="padding-right: 32px; font-size: 12px"
              v-model="credentials.jira_api_token"
              placeholder="ATATT3xxxxxxxxxxx"
              @input="onCredentialInput"
            />
            <span
              style="position: absolute; right: 8px; top: 50%; transform: translateY(-50%); cursor: pointer; color: var(--text-hint); font-size: 13px; user-select: none"
              @click="showTokens.jira = !showTokens.jira"
            >{{ showTokens.jira ? '🙈' : '👁' }}</span>
          </div>
        </div>
        <div>
          <div style="font-size: 11px; color: var(--text-dim); margin-bottom: 4px">Jira Email</div>
          <input
            type="email"
            class="form-input"
            style="font-size: 12px"
            v-model="credentials.jira_email"
            placeholder="you@company.com"
            @input="onCredentialInput"
          />
          <label style="display: flex; align-items: center; gap: 4px; margin-top: 4px; font-size: 11px; color: var(--text-hint); cursor: pointer; user-select: none">
            <input type="checkbox" v-model="rememberEmail" @change="onCredentialInput" />
            記住 Email
          </label>
        </div>
      </div>
    </div>

    <div class="stats">
      <div class="stat-card">
        <div class="stat-value" style="color: var(--blue)">{{ data.running }}</div>
        <div class="stat-label">Running</div>
      </div>
      <div class="stat-card">
        <div class="stat-value" style="color: var(--amber)">{{ data.queued }}</div>
        <div class="stat-label">Queued</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ data.total }}</div>
        <div class="stat-label">Total</div>
      </div>
      <div class="stat-card">
        <div class="stat-value" style="color: var(--green)">{{ successRate }}%</div>
        <div class="stat-label">Success Rate</div>
      </div>
    </div>

    <div class="filters">
      <button
        v-for="f in FILTERS"
        :key="f.label"
        :class="['filter-btn', { active: filter === f.value }]"
        @click="filter = f.value"
      >
        {{ f.label }}
      </button>
    </div>

    <div v-if="data.jobs.length === 0" class="empty">
      No jobs yet.
      <span style="color: var(--blue); cursor: pointer" @click="router.push('/new')">Create one</span>
    </div>

    <div
      v-for="job in data.jobs"
      :key="job.job_id"
      class="card"
      @click="router.push(`/jobs/${job.job_id}`)"
    >
      <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 12px">
        <div style="min-width: 0">
          <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px">
            <span style="font-weight: 600; font-size: 14px">{{ job.jira_ticket }}</span>
            <StatusBadge :status="job.status" />
            <span style="font-size: 10px; padding: 1px 6px; border-radius: 4px; background: var(--surface-alt, #2a2a2a); color: var(--text-hint)">
              {{ job.agent_mode === 'copilot' ? '⚡ Copilot' : '🤖 Claude' }}
            </span>
          </div>
          <div style="font-size: 11px; color: var(--text-dim); overflow: hidden; text-overflow: ellipsis; white-space: nowrap">
            {{ job.repo_url.replace('https://github.com/', '') }}
          </div>
          <div v-if="job.requested_by" style="font-size: 11px; color: var(--text-hint); margin-top: 2px">
            by {{ job.requested_by }}
          </div>
        </div>
        <div style="text-align: right; flex-shrink: 0">
          <div style="font-size: 11px; color: var(--text-dim)">{{ timeAgo(job.created_at) }}</div>
          <div style="font-size: 11px; color: var(--text-hint); margin-top: 2px">{{ elapsed(job) }}s</div>
        </div>
      </div>
      <div v-if="job.pr_url" style="margin-top: 8px; font-size: 11px; color: var(--green)">
        PR: {{ job.pr_url }}
      </div>
      <div v-if="job.error_message" style="margin-top: 8px; font-size: 11px; color: var(--red); overflow: hidden; text-overflow: ellipsis; white-space: nowrap">
        {{ job.error_message }}
      </div>
    </div>
  </div>
</template>

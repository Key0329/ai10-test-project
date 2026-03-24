<script setup>
import { ref, reactive, watch } from 'vue'
import { useRouter } from 'vue-router'
import { createJob, scanRepoMcp } from '../api'
import { useCredentials } from '../composables/useCredentials'

const router = useRouter()
const { credentials, validate: validateCredentials } = useCredentials()

const DEFAULT_REPOS = [
  // Add your team's repos here
  // 'https://github.com/your-org/repo-a.git',
  // 'https://github.com/your-org/repo-b.git',
]

const form = reactive({
  repo_url: '',
  jira_ticket: '',
  branch: '',
  extra_prompt: '',
  requested_by: localStorage.getItem('cra_user') || '',
  agent_mode: 'claude_code',
})
const submitting = ref(false)
const error = ref('')

// Repo MCP scan 狀態
const scanMissingVars = ref([])
const scanServers = ref([])
const envOverrides = ref({})
const scanLoading = ref(false)
let scanDebounceTimer = null

// Repo MCP scan：repo_url 或 branch 變化後 debounce 掃描
watch([() => form.repo_url, () => form.branch], () => {
  clearTimeout(scanDebounceTimer)
  scanMissingVars.value = []
  scanServers.value = []
  envOverrides.value = {}
  if (!form.repo_url) return
  scanDebounceTimer = setTimeout(async () => {
    const token = credentials.value?.github_token
    if (!token) return
    scanLoading.value = true
    try {
      const res = await scanRepoMcp(form.repo_url, form.branch || null, token)
      scanMissingVars.value = res.missing_vars || []
      scanServers.value = res.servers || []
    } catch {
      // scan 失敗不阻擋送 job
    } finally {
      scanLoading.value = false
    }
  }, 800)
})

async function handleSubmit() {
  if (!form.repo_url || !form.jira_ticket) {
    error.value = 'Repo URL and Jira Ticket are required'
    return
  }
  const credError = validateCredentials()
  if (credError) {
    error.value = credError
    return
  }
  error.value = ''
  submitting.value = true

  if (form.requested_by) {
    localStorage.setItem('cra_user', form.requested_by)
  }

  try {
    const res = await createJob({
      repo_url: form.repo_url,
      jira_ticket: form.jira_ticket.replace(/.*\/browse\//, '').replace(/.*\//, '').toUpperCase(),
      branch: form.branch || undefined,
      extra_prompt: form.extra_prompt || undefined,
      requested_by: form.requested_by || undefined,
      agent_mode: form.agent_mode,
      env_overrides: envOverrides.value,
      github_token: credentials.github_token,
      jira_api_token: credentials.jira_api_token,
      jira_email: credentials.jira_email,
    })
    router.push(`/jobs/${res.job_id}`)
  } catch (e) {
    error.value = e.message
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div>
    <button class="back-btn" @click="router.push('/')">← Back to Dashboard</button>

    <div style="border: 1px solid var(--border); border-radius: 10px; background: var(--surface); padding: 20px; margin-top: 12px">
      <div class="section-title">New Job</div>

      <div v-if="error" class="alert alert-error">{{ error }}</div>

      <form @submit.prevent="handleSubmit">
        <div class="form-group">
          <label class="form-label">Execution Engine</label>
          <div style="display: flex; gap: 10px; margin-top: 4px">
            <label style="display: flex; align-items: center; gap: 6px; cursor: pointer; padding: 8px 14px; border-radius: 6px; border: 1px solid var(--border)" :style="form.agent_mode === 'claude_code' ? 'border-color: var(--accent); background: color-mix(in srgb, var(--accent) 12%, transparent)' : ''">
              <input type="radio" v-model="form.agent_mode" value="claude_code" style="accent-color: var(--accent)" />
              <span>Claude Code</span>
            </label>
            <label style="display: flex; align-items: center; gap: 6px; cursor: pointer; padding: 8px 14px; border-radius: 6px; border: 1px solid var(--border)" :style="form.agent_mode === 'copilot' ? 'border-color: var(--accent); background: color-mix(in srgb, var(--accent) 12%, transparent)' : ''">
              <input type="radio" v-model="form.agent_mode" value="copilot" style="accent-color: var(--accent)" />
              <span>Copilot</span>
            </label>
          </div>
        </div>

        <!-- MCP 偵測摘要 -->
        <div v-if="scanServers.length > 0" style="margin-bottom: 16px; padding: 10px 14px; background: color-mix(in srgb, #34d399 8%, transparent); border: 1px solid var(--border); border-radius: 8px; font-size: 12px; color: var(--text-hint)">
          偵測到 {{ scanServers.length }} 個 MCP servers：{{ scanServers.join(', ') }}
        </div>

        <!-- Repo MCP Token 動態輸入 -->
        <div v-if="scanMissingVars.length > 0" style="margin-bottom: 16px; border: 1px solid var(--border); border-radius: 8px; padding: 12px 14px">
          <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 8px; color: #f59e0b">
            🔑 Repo MCP 需要的環境變數
          </div>
          <div style="font-size: 12px; color: var(--text-hint); margin-bottom: 10px">
            偵測到 <code>.mcp.json</code> 引用了以下未定義的環境變數，請填入對應的 token：
          </div>
          <div v-for="varName in scanMissingVars" :key="varName" style="margin-bottom: 6px">
            <label style="font-size: 12px; font-weight: 600; display: block; margin-bottom: 2px">{{ varName }}</label>
            <input
              class="form-input"
              type="password"
              :placeholder="varName"
              :value="envOverrides[varName] || ''"
              @input="envOverrides[varName] = $event.target.value"
            />
          </div>
        </div>
        <div v-if="scanLoading" style="margin-bottom: 16px; font-size: 12px; color: var(--text-hint)">
          掃描 repo MCP 設定中...
        </div>

        <div class="form-group">
          <label class="form-label">Repository URL *</label>
          <template v-if="DEFAULT_REPOS.length > 0">
            <select class="form-select" v-model="form.repo_url">
              <option value="">Select a repo or type below</option>
              <option v-for="r in DEFAULT_REPOS" :key="r" :value="r">
                {{ r.replace('https://github.com/', '') }}
              </option>
            </select>
            <input
              class="form-input"
              style="margin-top: 6px"
              v-model="form.repo_url"
              placeholder="or enter URL manually"
            />
          </template>
          <input
            v-else
            class="form-input"
            v-model="form.repo_url"
            placeholder="https://github.com/org/repo.git"
          />
        </div>

        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Jira Ticket *</label>
            <input class="form-input" v-model="form.jira_ticket" placeholder="JRA-123" />
          </div>
          <div class="form-group">
            <label class="form-label">Branch <span style="color: var(--text-hint)">(optional)</span></label>
            <input class="form-input" v-model="form.branch" placeholder="main" />
          </div>
        </div>

        <!-- Your Name, Extra Prompt 暫時隱藏
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Your Name <span style="color: var(--text-hint)">(optional)</span></label>
            <input class="form-input" v-model="form.requested_by" placeholder="Your name" />
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">Extra Prompt <span style="color: var(--text-hint)">(optional, max 2000 chars)</span></label>
          <textarea
            class="form-textarea"
            v-model="form.extra_prompt"
            placeholder="Additional instructions for Claude..."
            maxlength="2000"
            rows="3"
          />
        </div>
        -->

        <button class="btn" type="submit" :disabled="submitting">
          {{ submitting ? 'Submitting...' : '→ Submit Job' }}
        </button>
      </form>
    </div>
  </div>
</template>


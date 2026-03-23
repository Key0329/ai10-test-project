<script setup>
import { ref, reactive, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { createJob, getMcpList, testMcpServers } from '../api'
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
  priority: 3,
  requested_by: localStorage.getItem('cra_user') || '',
  agent_mode: 'claude_code',
})
const submitting = ref(false)
const error = ref('')

// MCP 狀態
const mcpList = ref([])
const mcpPresets = ref({})
const selectedMcps = ref(['context7'])
const mcpTokens = ref({})
const mcpExpanded = ref(false)
const mcpTestResults = ref({})
const mcpInitTested = ref(false)

// 載入 MCP 清單
onMounted(async () => {
  try {
    const data = await getMcpList()
    mcpList.value = data.mcps || []
    mcpPresets.value = data.presets || {}
  } catch {
    // 後端未啟動時靜默忽略
  }
})

// 切換到 copilot 模式時自動測試預設 MCP
watch(() => form.agent_mode, async (mode) => {
  if (mode === 'copilot' && mcpList.value.length > 0 && !mcpInitTested.value) {
    mcpInitTested.value = true
    await doTestMcps(selectedMcps.value.filter(id => {
      const mcp = mcpList.value.find(m => m.id === id)
      return !(mcp?.token_required && mcp?.token_source === 'user_input')
    }))
  }
})

async function doTestMcps(ids) {
  if (!ids.length) return
  const updates = Object.fromEntries(ids.map(id => [id, { testing: true }]))
  mcpTestResults.value = { ...mcpTestResults.value, ...updates }
  try {
    const data = await testMcpServers(ids, mcpTokens.value)
    mcpTestResults.value = { ...mcpTestResults.value, ...data.results }
  } catch {
    const errResults = Object.fromEntries(ids.map(id => [id, { ok: false, error: '無法連線後端' }]))
    mcpTestResults.value = { ...mcpTestResults.value, ...errResults }
  }
}

async function testSingleMcp(id, tokens) {
  mcpTestResults.value = { ...mcpTestResults.value, [id]: { testing: true } }
  try {
    const data = await testMcpServers([id], tokens)
    mcpTestResults.value = { ...mcpTestResults.value, ...data.results }
  } catch {
    mcpTestResults.value = { ...mcpTestResults.value, [id]: { ok: false, error: '無法連線後端' } }
  }
}

function toggleMcp(id) {
  const isAdding = !selectedMcps.value.includes(id)
  if (isAdding) {
    selectedMcps.value = [...selectedMcps.value, id]
    const mcp = mcpList.value.find(m => m.id === id)
    const needsToken = mcp?.token_required && mcp?.token_source === 'user_input'
    if (needsToken && !mcpTokens.value[id]?.trim()) {
      mcpTestResults.value = { ...mcpTestResults.value, [id]: { ok: false, error: '未提供 Token' } }
    } else {
      testSingleMcp(id, mcpTokens.value)
    }
  } else {
    selectedMcps.value = selectedMcps.value.filter(x => x !== id)
    const next = { ...mcpTestResults.value }
    delete next[id]
    mcpTestResults.value = next
  }
}

const tokenTimers = {}
function setMcpToken(id, value) {
  mcpTokens.value = { ...mcpTokens.value, [id]: value }
  if (tokenTimers[id]) clearTimeout(tokenTimers[id])
  if (value.trim()) {
    tokenTimers[id] = setTimeout(() => {
      testSingleMcp(id, { ...mcpTokens.value, [id]: value })
    }, 800)
  } else {
    mcpTestResults.value = { ...mcpTestResults.value, [id]: { ok: false, error: '未提供 Token' } }
  }
}

const hasMissingMcpTokens = () => selectedMcps.value.some(id => {
  const mcp = mcpList.value.find(m => m.id === id)
  return mcp?.token_required && mcp?.token_source === 'user_input' && !mcpTokens.value[id]?.trim()
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
  if (form.agent_mode === 'copilot' && hasMissingMcpTokens()) {
    error.value = '請為需要 Token 的 MCP 提供 Token'
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
      priority: form.priority,
      requested_by: form.requested_by || undefined,
      agent_mode: form.agent_mode,
      selected_mcps: form.agent_mode === 'copilot' ? selectedMcps.value : [],
      mcp_tokens: form.agent_mode === 'copilot' ? mcpTokens.value : {},
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
          <div v-if="form.agent_mode === 'copilot'" style="margin-top: 6px; font-size: 12px; color: var(--text-hint)">
            需要 target repo 有 .github/skills/jirara/ 與 GitHub Copilot 已登入
          </div>
        </div>

        <!-- MCP 設定（僅 Copilot 模式顯示） -->
        <div v-if="form.agent_mode === 'copilot'" style="margin-bottom: 16px; border: 1px solid var(--border); border-radius: 8px; overflow: hidden">
          <div
            style="padding: 10px 14px; display: flex; align-items: center; gap: 8px; cursor: pointer; background: color-mix(in srgb, #a78bfa 8%, transparent)"
            @click="mcpExpanded = !mcpExpanded"
          >
            <span style="width: 8px; height: 8px; border-radius: 50%; background: #a78bfa; flex-shrink: 0; display: inline-block"></span>
            <span style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em">
              MCP 設定 · {{ selectedMcps.length }} 個已啟用
            </span>
            <span style="margin-left: auto; font-size: 12px; color: var(--text-hint); transition: transform 0.2s" :style="mcpExpanded ? 'transform: rotate(180deg)' : ''">▾</span>
          </div>

          <div v-if="mcpExpanded" style="padding: 12px 14px; display: flex; flex-direction: column; gap: 8px">
            <div
              v-for="mcp in mcpList"
              :key="mcp.id"
              style="background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 8px 10px"
            >
              <div style="display: flex; align-items: center; justify-content: space-between">
                <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; flex: 1">
                  <input
                    type="checkbox"
                    :checked="selectedMcps.includes(mcp.id)"
                    @change="toggleMcp(mcp.id)"
                    style="accent-color: #a78bfa; width: 14px; height: 14px; cursor: pointer"
                  />
                  <span style="font-size: 12px; font-weight: 600">{{ mcp.name }}</span>
                  <span style="font-size: 11px; color: var(--text-hint)">{{ mcp.description }}</span>
                </label>
                <span
                  v-if="mcpTestResults[mcp.id]"
                  style="font-size: 12px; flex-shrink: 0; margin-left: 8px"
                  :style="{
                    color: mcpTestResults[mcp.id].testing ? '#f59e0b' : mcpTestResults[mcp.id].ok ? '#34d399' : '#f87171'
                  }"
                >
                  <span v-if="mcpTestResults[mcp.id].testing" style="display: inline-block; width: 10px; height: 10px; border: 2px solid #1e293b; border-top-color: #f59e0b; border-radius: 50%; animation: spin 0.8s linear infinite"></span>
                  <span v-else>{{ mcpTestResults[mcp.id].ok ? '✓' : '✗' }}</span>
                </span>
              </div>
              <!-- Token 輸入（需要 token 且已勾選） -->
              <div v-if="selectedMcps.includes(mcp.id) && mcp.token_required && mcp.token_source === 'user_input'" style="margin-top: 8px; padding-left: 22px">
                <input
                  class="form-input"
                  type="password"
                  :placeholder="`${mcp.name} Token`"
                  :value="mcpTokens[mcp.id] || ''"
                  @input="setMcpToken(mcp.id, $event.target.value)"
                />
              </div>
            </div>
            <div v-if="mcpList.length === 0" style="font-size: 12px; color: var(--text-hint); text-align: center; padding: 8px 0">
              載入中...
            </div>
          </div>
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

        <!-- Priority, Your Name, Extra Prompt 暫時隱藏
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Priority</label>
            <select class="form-select" v-model.number="form.priority">
              <option :value="1">1 — Urgent</option>
              <option :value="2">2 — High</option>
              <option :value="3">3 — Normal</option>
              <option :value="4">4 — Low</option>
              <option :value="5">5 — Background</option>
            </select>
          </div>
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

<style scoped>
@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>

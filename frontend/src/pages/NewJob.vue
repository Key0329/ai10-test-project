<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { createJob } from '../api'

const router = useRouter()

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
})
const submitting = ref(false)
const error = ref('')

async function handleSubmit() {
  if (!form.repo_url || !form.jira_ticket) {
    error.value = 'Repo URL and Jira Ticket are required'
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

        <button class="btn" type="submit" :disabled="submitting">
          {{ submitting ? 'Submitting...' : '→ Submit Job' }}
        </button>
      </form>
    </div>
  </div>
</template>

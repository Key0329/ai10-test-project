<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { setToken, healthCheck } from '../api'

const router = useRouter()
const value = ref('')
const error = ref('')
const checking = ref(false)

async function handleSubmit() {
  if (!value.value.trim()) return
  checking.value = true
  error.value = ''
  setToken(value.value.trim())
  try {
    await healthCheck()
    router.push('/')
  } catch {
    error.value = 'Unable to connect. Check the token and server URL.'
    setToken('')
  } finally {
    checking.value = false
  }
}
</script>

<template>
  <div class="token-gate">
    <div class="token-card">
      <h2>Claude Remote Agent</h2>
      <p>Enter the API token to connect to the server.</p>
      <div v-if="error" class="alert alert-error">{{ error }}</div>
      <form @submit.prevent="handleSubmit">
        <div class="form-group">
          <label class="form-label">API Token</label>
          <input
            type="password"
            class="form-input"
            v-model="value"
            placeholder="your-secret-token"
            autofocus
          />
        </div>
        <button class="btn" type="submit" :disabled="checking">
          {{ checking ? 'Connecting...' : 'Connect' }}
        </button>
      </form>
    </div>
  </div>
</template>

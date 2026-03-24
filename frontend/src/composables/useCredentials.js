/**
 * 共用憑證狀態
 * - github_token / jira_api_token → sessionStorage（關分頁即清除）
 * - jira_email → 依 rememberEmail 決定存 localStorage 或 sessionStorage
 * 提供 credentials reactive 物件、save()、validate()
 */
import { reactive, ref } from 'vue'

const KEYS = {
  githubToken:    'cra_github_token',
  jiraToken:      'cra_jira_token',
  jiraEmail:      'cra_jira_email',
  rememberEmail:  'cra_remember_email',
}

const rememberEmail = ref(localStorage.getItem(KEYS.rememberEmail) === 'true')

// 單例：所有頁面共享同一個 reactive 物件
const credentials = reactive({
  github_token:   sessionStorage.getItem(KEYS.githubToken) || '',
  jira_api_token: sessionStorage.getItem(KEYS.jiraToken)   || '',
  jira_email:     (rememberEmail.value
    ? localStorage.getItem(KEYS.jiraEmail)
    : sessionStorage.getItem(KEYS.jiraEmail)) || '',
})

function save() {
  sessionStorage.setItem(KEYS.githubToken, credentials.github_token)
  sessionStorage.setItem(KEYS.jiraToken,   credentials.jira_api_token)

  localStorage.setItem(KEYS.rememberEmail, rememberEmail.value)
  if (rememberEmail.value) {
    localStorage.setItem(KEYS.jiraEmail, credentials.jira_email)
    sessionStorage.removeItem(KEYS.jiraEmail)
  } else {
    sessionStorage.setItem(KEYS.jiraEmail, credentials.jira_email)
    localStorage.removeItem(KEYS.jiraEmail)
  }
}

/** 回傳第一個錯誤訊息，全部填寫則回 null */
function validate() {
  if (!credentials.github_token)   return 'GitHub Token 未填寫，請至 Dashboard 設定'
  if (!credentials.jira_api_token) return 'Jira API Token 未填寫，請至 Dashboard 設定'
  if (!credentials.jira_email)     return 'Jira Email 未填寫，請至 Dashboard 設定'
  return null
}

export function useCredentials() {
  return { credentials, rememberEmail, save, validate }
}

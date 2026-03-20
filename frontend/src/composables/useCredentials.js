/**
 * 共用憑證狀態 — 使用 sessionStorage（關分頁即清除）
 * 提供 credentials reactive 物件、save()、validate()
 */
import { reactive } from 'vue'

const KEYS = {
  githubToken: 'cra_github_token',
  jiraToken:   'cra_jira_token',
  jiraEmail:   'cra_jira_email',
}

// 單例：所有頁面共享同一個 reactive 物件
const credentials = reactive({
  github_token:   sessionStorage.getItem(KEYS.githubToken) || '',
  jira_api_token: sessionStorage.getItem(KEYS.jiraToken)   || '',
  jira_email:     sessionStorage.getItem(KEYS.jiraEmail)    || '',
})

function save() {
  sessionStorage.setItem(KEYS.githubToken, credentials.github_token)
  sessionStorage.setItem(KEYS.jiraToken,   credentials.jira_api_token)
  sessionStorage.setItem(KEYS.jiraEmail,   credentials.jira_email)
}

/** 回傳第一個錯誤訊息，全部填寫則回 null */
function validate() {
  if (!credentials.github_token)   return 'GitHub Token 未填寫，請至 Dashboard 設定'
  if (!credentials.jira_api_token) return 'Jira API Token 未填寫，請至 Dashboard 設定'
  if (!credentials.jira_email)     return 'Jira Email 未填寫，請至 Dashboard 設定'
  return null
}

export function useCredentials() {
  return { credentials, save, validate }
}

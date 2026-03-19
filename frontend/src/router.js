import { createRouter, createWebHashHistory } from 'vue-router'
import { getStoredToken } from './api'

import Dashboard from './pages/Dashboard.vue'
import NewJob from './pages/NewJob.vue'
import JobDetail from './pages/JobDetail.vue'
import TokenGate from './components/TokenGate.vue'

const routes = [
  { path: '/', component: Dashboard },
  { path: '/new', component: NewJob },
  { path: '/jobs/:id', component: JobDetail, props: true },
  { path: '/login', component: TokenGate },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

router.beforeEach((to) => {
  if (to.path !== '/login' && !getStoredToken()) {
    return '/login'
  }
})

export default router

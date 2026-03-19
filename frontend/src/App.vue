<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <div class="app">
    <header class="header">
      <div class="header-left" style="cursor: pointer" @click="router.push('/')">
        <span class="pulse-dot" />
        <span class="header-title">claude-remote-agent</span>
      </div>
      <nav class="header-nav">
        <button class="nav-btn" @click="router.push('/')">Dashboard</button>
        <button class="nav-btn primary" @click="router.push('/new')">+ New Job</button>
      </nav>
    </header>
    <main class="main">
      <router-view />
    </main>
  </div>
</template>

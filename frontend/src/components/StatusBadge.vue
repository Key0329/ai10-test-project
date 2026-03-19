<script setup>
defineProps({
  status: String,
})
</script>

<template>
  <span :class="`badge badge-${status}`">
    <span class="badge-dot" />
    {{ status }}
  </span>
</template>

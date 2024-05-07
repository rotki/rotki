<script setup lang="ts">
function noop() {}
</script>

<template>
  <form @submit.prevent="noop()">
    <slot />
  </form>
</template>

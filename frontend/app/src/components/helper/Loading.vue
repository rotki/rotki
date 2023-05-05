<script setup lang="ts">
const char = '.';
</script>

<template>
  <div class="loading">
    <span v-for="i in 3" :key="i" v-text="char" />
  </div>
</template>

<style scoped lang="scss">
@import '~@/scss/loading';
</style>

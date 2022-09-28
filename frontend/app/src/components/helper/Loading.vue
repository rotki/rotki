<template>
  <div class="loading">
    <span v-for="i in 3" :key="i" v-text="char" />
  </div>
</template>

<script setup lang="ts">
const char = '.';
</script>

<style scoped lang="scss">
@import '~@/scss/loading.scss';
</style>

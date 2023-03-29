<script setup lang="ts">
const reportStore = useReportsStore();
onUnmounted(() => {
  reportStore.$reset();
});
</script>
<template>
  <router-view />
</template>

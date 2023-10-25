<script setup lang="ts">
const reportStore = useReportsStore();
onUnmounted(() => {
  reportStore.reset();
});
</script>

<template>
  <RouterView />
</template>

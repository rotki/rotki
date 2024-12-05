<script setup lang="ts">
import { useReportsStore } from '@/store/reports';

const reportStore = useReportsStore();
onUnmounted(() => {
  reportStore.reset();
});
</script>

<template>
  <RouterView />
</template>

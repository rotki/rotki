<script setup lang="ts">
import { useReportsStore } from '@/modules/reports/use-reports-store';

const reportStore = useReportsStore();
onUnmounted(() => {
  reportStore.reset();
});
</script>

<template>
  <RouterView />
</template>

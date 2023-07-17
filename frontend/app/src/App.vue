<script setup lang="ts">
import '@/utils/chartjs-adapter-dayjs';

useSessionStateCleaner();

const { setupBackend } = useBackendManagement();
startPromise(setupBackend());
</script>

<template>
  <RouterView />
</template>

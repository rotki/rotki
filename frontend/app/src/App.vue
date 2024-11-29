<script setup lang="ts">
import '@/utils/chartjs-adapter-dayjs';
import { startPromise } from '@shared/utils';

useSessionStateCleaner();

const { setupBackend } = useBackendManagement();
startPromise(setupBackend());
</script>

<template>
  <RouterView />
</template>

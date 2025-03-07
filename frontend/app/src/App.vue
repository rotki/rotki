<script setup lang="ts">
import { useBackendManagement } from '@/composables/backend';
import { useSessionStateCleaner } from '@/composables/session/logout';
import { startPromise } from '@shared/utils';
import '@/utils/chartjs-adapter-dayjs';

useSessionStateCleaner();

const { setupBackend } = useBackendManagement();
startPromise(setupBackend());
</script>

<template>
  <RouterView />
</template>

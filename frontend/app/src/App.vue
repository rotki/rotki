<script setup lang="ts">
import { startPromise } from '@shared/utils';
import { useBackendManagement } from '@/composables/backend';
import { useSessionStateCleaner } from '@/composables/session/logout';
import '@/utils/chartjs-adapter-dayjs';

useSessionStateCleaner();

const { setupBackend } = useBackendManagement();
startPromise(setupBackend());
</script>

<template>
  <RouterView />
</template>

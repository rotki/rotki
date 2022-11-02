<template>
  <router-view />
</template>

<script setup lang="ts">
import { useBackendManagement } from '@/composables/backend';
import { useSessionStateCleaner } from '@/composables/logout';
import { startPromise } from '@/utils';
import '@/utils/chartjs-adapter-dayjs';

useSessionStateCleaner();

const { setupBackend } = useBackendManagement();
startPromise(setupBackend());
</script>

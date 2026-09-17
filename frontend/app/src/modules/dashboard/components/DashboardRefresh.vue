<script setup lang="ts">
import { startPromise } from '@shared/utils';
import DashboardRefreshButton from '@/modules/dashboard/components/DashboardRefreshButton.vue';
import { useDashboardRefresh } from '@/modules/dashboard/use-dashboard-refresh';

const { busy, refresh, sources } = useDashboardRefresh();
</script>

<template>
  <DashboardRefreshButton
    :busy="busy"
    :sources="sources"
    @refresh="startPromise(refresh($event))"
  />
</template>

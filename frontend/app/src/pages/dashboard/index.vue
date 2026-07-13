<script setup lang="ts">
import { msg } from '@/message-key';
import { NoteLocation } from '@/modules/core/common/notes';
import Dashboard from '@/modules/dashboard/Dashboard.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.dashboard'), icon: 'lu-layout-dashboard', section: 1, order: 10, drawer: 'dashboard' },
    noteLocation: NoteLocation.DASHBOARD,
  },
});
</script>

<template>
  <Dashboard />
</template>

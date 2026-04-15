<script setup lang="ts">
import { NoteLocation } from '@/modules/common/notes';
import Dashboard from '@/modules/dashboard/Dashboard.vue';

definePage({
  meta: {
    noteLocation: NoteLocation.DASHBOARD,
  },
  name: 'dashboard',
});
</script>

<template>
  <Dashboard />
</template>

<script setup lang="ts">
import Dashboard from '@/modules/dashboard/Dashboard.vue';
import { NoteLocation } from '@/types/notes';

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

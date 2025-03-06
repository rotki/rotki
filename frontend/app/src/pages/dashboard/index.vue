<script setup lang="ts">
import { NoteLocation } from '@/types/notes';
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

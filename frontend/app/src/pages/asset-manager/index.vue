<script setup lang="ts">
import { NoteLocation } from '@/modules/common/notes';

definePage({
  meta: {
    noteLocation: NoteLocation.ASSETS,
  },
  redirect: '/asset-manager/managed',
});
</script>

<template>
  <RouterView />
</template>

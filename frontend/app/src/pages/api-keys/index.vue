<script setup lang="ts">
import { NoteLocation } from '@/modules/core/common/notes';

definePage({
  meta: {
    noteLocation: NoteLocation.API_KEYS,
  },
  redirect: '/api-keys/premium',
});
</script>

<template>
  <RouterView />
</template>

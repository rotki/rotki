<script setup lang="ts">
import { NoteLocation } from '@/types/notes';

definePage({
  meta: {
    noteLocation: NoteLocation.TAG_MANAGER,
  },
  name: 'tag_manager',
});
</script>

<template>
  <TagManager />
</template>

<script setup lang="ts">
import { NoteLocation } from '@/types/notes.ts';

definePage({
  name: 'tag_manager',
  meta: {
    noteLocation: NoteLocation.TAG_MANAGER,
  },
});
</script>

<template>
  <TagManager />
</template>

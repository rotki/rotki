<script setup lang="ts">
import { NoteLocation } from '@/modules/core/common/notes';
import TagManager from '@/modules/tags/TagManager.vue';

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

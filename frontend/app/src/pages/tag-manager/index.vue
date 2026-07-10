<script setup lang="ts">
import { NoteLocation } from '@/modules/core/common/notes';
import TagManager from '@/modules/tags/TagManager.vue';

definePage({
  meta: {
    nav: { labelKey: 'navigation_menu.tag_manager', icon: 'lu-tag-manager', section: 2, order: 10, drawer: 'tag-manager', addAction: { labelKey: 'tag_manager.create_tag.title' } },
    noteLocation: NoteLocation.TAG_MANAGER,
  },
});
</script>

<template>
  <TagManager />
</template>

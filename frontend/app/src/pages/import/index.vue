<script setup lang="ts">
import { msg } from '@/message-key';
import { NoteLocation } from '@/modules/core/common/notes';
import GroupedImport from '@/modules/user-data/GroupedImport.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.import_data'), icon: 'lu-folder-input', section: 3, order: 20, drawer: 'import' },
    noteLocation: NoteLocation.IMPORT,
  },
});
</script>

<template>
  <GroupedImport />
</template>

<script setup lang="ts">
import { msg } from '@/message-key';
import { NoteLocation } from '@/modules/core/common/notes';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.api_keys'), icon: 'lu-key', section: 3, order: 10, drawer: 'api-keys' },
    noteLocation: NoteLocation.API_KEYS,
  },
  redirect: '/api-keys/premium',
});
</script>

<template>
  <RouterView />
</template>

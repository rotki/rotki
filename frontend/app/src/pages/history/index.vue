<script setup lang="ts">
import { msg } from '@/message-key';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.history'), icon: 'lu-history', section: 1, order: 40, drawer: 'history' },
  },
  redirect: { name: '/history/events/' },
});
</script>

<template>
  <div />
</template>

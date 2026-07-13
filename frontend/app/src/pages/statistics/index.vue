<script setup lang="ts">
import { msg } from '@/message-key';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.statistics'), icon: 'lu-file-chart-column', section: 1, order: 70, drawer: 'statistics' },
  },
  redirect: '/statistics/graphs',
});
</script>

<template>
  <RouterView />
</template>

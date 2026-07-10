<script setup lang="ts">
definePage({
  meta: {
    nav: { labelKey: 'navigation_menu.statistics', icon: 'lu-file-chart-column', section: 1, order: 70, drawer: 'statistics' },
  },
  redirect: '/statistics/graphs',
});
</script>

<template>
  <RouterView />
</template>

<script setup lang="ts">
import { msg } from '@/message-key';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.manage_assets_sub.more'), icon: 'lu-more-assets', parent: '/asset-manager/', order: 30, drawer: 'asset-manager-more' },
  },
});
</script>

<template>
  <div class="container">
    <RouterView />
  </div>
</template>

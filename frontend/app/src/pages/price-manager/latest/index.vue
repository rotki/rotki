<script setup lang="ts">
import LatestPriceContent from '@/modules/assets/prices/latest/LatestPriceContent.vue';

definePage({
  meta: {
    nav: { labelKey: 'navigation_menu.manage_prices_sub.latest_prices', icon: 'lu-latest-prices', parent: '/price-manager/', order: 10, drawer: 'price-manager-latest', addAction: { labelKey: 'price_management.latest.add_title' } },
  },
});
</script>

<template>
  <LatestPriceContent />
</template>

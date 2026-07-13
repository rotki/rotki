<script setup lang="ts">
import { msg } from '@/message-key';
import LatestPriceContent from '@/modules/assets/prices/latest/LatestPriceContent.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.manage_prices_sub.latest_prices'), icon: 'lu-latest-prices', parent: '/price-manager/', order: 10, drawer: 'price-manager-latest', addAction: { labelKey: msg.$t('price_management.latest.add_title') } },
  },
});
</script>

<template>
  <LatestPriceContent />
</template>

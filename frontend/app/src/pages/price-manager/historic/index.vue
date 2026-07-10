<script setup lang="ts">
import HistoricPriceContent from '@/modules/assets/prices/historic/HistoricPriceContent.vue';

definePage({
  meta: {
    nav: { labelKey: 'navigation_menu.manage_prices_sub.historic_prices', icon: 'lu-historic-prices', parent: '/price-manager/', order: 20, drawer: 'price-manager-historic', addAction: { labelKey: 'price_management.historic.add_title' } },
  },
});
</script>

<template>
  <HistoricPriceContent />
</template>

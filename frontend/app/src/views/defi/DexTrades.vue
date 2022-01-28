<template>
  <dex-trade-history />
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import DexTradeHistory from '@/components/defi/dex-trades/DexTradeHistory.vue';

export default defineComponent({
  name: 'DexTrades',
  components: { DexTradeHistory }
});
</script>

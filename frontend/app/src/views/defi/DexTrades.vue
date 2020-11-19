<template>
  <dex-trade-history />
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import DexTradeHistory from '@/components/defi/dex-trades/DexTradeHistory.vue';

@Component({
  components: { DexTradeHistory }
})
export default class DexTrades extends Vue {}
</script>

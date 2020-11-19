<template>
  <v-container>
    <no-premium-placeholder v-if="!premium" :text="$t('dex_trade.title')" />
    <progress-screen v-else-if="loading">
      <template #message>{{ $t('dex_trades.loading') }}</template>
    </progress-screen>
    <dex-trades-table v-else :refreshing="refreshing" />
  </v-container>
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import { mapActions } from 'vuex';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import NoPremiumPlaceholder from '@/components/premium/NoPremiumPlaceholder.vue';
import PremiumMixin from '@/mixins/premium-mixin';
import StatusMixin from '@/mixins/status-mixin';
import { Section } from '@/store/const';
import { DexTradesTable } from '@/utils/premium';

@Component({
  components: { NoPremiumPlaceholder, ProgressScreen, DexTradesTable },
  methods: {
    ...mapActions('defi', ['fetchUniswapTrades'])
  }
})
export default class DexTradeHistory extends Mixins(StatusMixin, PremiumMixin) {
  section = Section.DEFI_UNISWAP_TRADES;
  fetchUniswapTrades!: (refresh: boolean) => Promise<void>;

  async mounted() {
    await this.fetchUniswapTrades(false);
  }
}
</script>

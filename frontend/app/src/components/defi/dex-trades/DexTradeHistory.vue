<template>
  <v-container>
    <module-not-active
      v-if="!isUniswapEnabled && !isBalancerEnabled"
      :modules="[MODULE_UNISWAP, balancerModule]"
    />
    <no-premium-placeholder
      v-else-if="!premium"
      :text="$t('dex_trade.title')"
    />
    <progress-screen v-else-if="dexLoading">
      <template #message>{{ $t('dex_trades.loading') }}</template>
    </progress-screen>
    <dex-trades-table v-else :refreshing="anyRefreshing" />
  </v-container>
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import { mapActions } from 'vuex';
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import NoPremiumPlaceholder from '@/components/premium/NoPremiumPlaceholder.vue';
import DefiModuleMixin from '@/mixins/defi-module-mixin';
import PremiumMixin from '@/mixins/premium-mixin';
import StatusMixin from '@/mixins/status-mixin';
import { DexTradesTable } from '@/premium/premium';
import { Section } from '@/store/const';

@Component({
  components: {
    ModuleNotActive,
    NoPremiumPlaceholder,
    ProgressScreen,
    DexTradesTable
  },
  methods: {
    ...mapActions('defi', ['fetchUniswapTrades', 'fetchBalancerTrades'])
  }
})
export default class DexTradeHistory extends Mixins(
  StatusMixin,
  PremiumMixin,
  DefiModuleMixin
) {
  section = Section.DEFI_UNISWAP_TRADES;
  secondSection = Section.DEFI_BALANCER_TRADES;

  fetchUniswapTrades!: (refresh: boolean) => Promise<void>;
  fetchBalancerTrades!: (refresh: boolean) => Promise<void>;

  get dexLoading(): boolean {
    return (
      (this.isUniswapEnabled && this.loading) ||
      (this.isBalancerEnabled && this.secondaryLoading)
    );
  }

  async mounted() {
    await Promise.all([
      this.fetchUniswapTrades(false),
      this.fetchBalancerTrades(false)
    ]);
  }
}
</script>

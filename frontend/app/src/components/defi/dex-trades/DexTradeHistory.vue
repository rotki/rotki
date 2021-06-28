<template>
  <v-container>
    <module-not-active v-if="!isEnabled" :modules="modules" />
    <no-premium-placeholder
      v-else-if="!premium"
      :text="$t('dex_trade.title')"
    />
    <progress-screen v-else-if="dexLoading">
      <template #message>{{ $t('dex_trades.loading') }}</template>
    </progress-screen>
    <div v-else>
      <active-modules :modules="modules" class="dex-trade-history__modules" />
      <dex-trades-table :refreshing="anyRefreshing" />
    </div>
  </v-container>
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import { mapActions } from 'vuex';
import ActiveModules from '@/components/defi/ActiveModules.vue';
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import NoPremiumPlaceholder from '@/components/premium/NoPremiumPlaceholder.vue';
import ModuleMixin from '@/mixins/module-mixin';
import PremiumMixin from '@/mixins/premium-mixin';
import StatusMixin from '@/mixins/status-mixin';
import { DexTradesTable } from '@/premium/premium';
import { MODULE_BALANCER, MODULE_UNISWAP } from '@/services/session/consts';
import { SupportedModules } from '@/services/session/types';
import { Section } from '@/store/const';

@Component({
  components: {
    ActiveModules,
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
  ModuleMixin
) {
  section = Section.DEFI_UNISWAP_TRADES;
  secondSection = Section.DEFI_BALANCER_TRADES;

  fetchUniswapTrades!: (refresh: boolean) => Promise<void>;
  fetchBalancerTrades!: (refresh: boolean) => Promise<void>;

  readonly modules: SupportedModules[] = [MODULE_UNISWAP, MODULE_BALANCER];

  get isEnabled(): boolean {
    return this.isAnyModuleEnabled(this.modules);
  }

  get dexLoading(): boolean {
    return (
      (this.isModuleEnabled(MODULE_UNISWAP) && this.loading) ||
      (this.isModuleEnabled(MODULE_BALANCER) && this.secondaryLoading)
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

<style scoped lang="scss">
.dex-trade-history {
  &__modules {
    display: inline-flex;
    position: absolute;
    right: 65px;
    top: 43px;
  }
}
</style>

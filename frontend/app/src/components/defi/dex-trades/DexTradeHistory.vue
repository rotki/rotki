<template>
  <div>
    <module-not-active v-if="!isEnabled" :modules="modules" />
    <no-premium-placeholder
      v-else-if="!premium"
      :text="tc('dex_trade.title')"
    />
    <progress-screen v-else-if="loading">
      <template #message>{{ $t('dex_trades.loading') }}</template>
    </progress-screen>
    <div v-else>
      <dex-trades-table :refreshing="refreshing">
        <template #modules>
          <active-modules :modules="modules" />
        </template>
      </dex-trades-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from '@vue/composition-api';
import { get } from '@vueuse/core';
import { useI18n } from 'vue-i18n-composable';
import ActiveModules from '@/components/defi/ActiveModules.vue';
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import NoPremiumPlaceholder from '@/components/premium/NoPremiumPlaceholder.vue';
import { setupStatusChecking } from '@/composables/common';
import { getPremium, useModules } from '@/composables/session';
import { DexTradesTable } from '@/premium/premium';
import { Section } from '@/store/const';
import { useBalancerStore } from '@/store/defi/balancer';
import { useSushiswapStore } from '@/store/defi/sushiswap';
import { useUniswapStore } from '@/store/defi/uniswap';
import { Module } from '@/types/modules';

const modules: Module[] = [Module.UNISWAP, Module.BALANCER, Module.SUSHISWAP];

const { fetchTrades: fetchBalancerTrades } = useBalancerStore();
const { fetchTrades: fetchUniswapTrades } = useUniswapStore();
const { fetchTrades: fetchSushiswapTrades } = useSushiswapStore();
const { isAnyModuleEnabled, isModuleEnabled } = useModules();
const {
  shouldShowLoadingScreen: showLoading,
  isSectionRefreshing: showRefreshing
} = setupStatusChecking();
const premium = getPremium();

const loading = computed(() => {
  const isLoading = (module: Module, section: Section) =>
    get(isModuleEnabled(module)) && get(showLoading(section));
  return (
    isLoading(Module.UNISWAP, Section.DEFI_UNISWAP_TRADES) &&
    isLoading(Module.BALANCER, Section.DEFI_BALANCER_TRADES) &&
    isLoading(Module.SUSHISWAP, Section.DEFI_SUSHISWAP_TRADES)
  );
});

const refreshing = computed(() => {
  const isRefreshing = (module: Module, section: Section) =>
    get(isModuleEnabled(module)) && get(showRefreshing(section));
  return (
    isRefreshing(Module.UNISWAP, Section.DEFI_UNISWAP_TRADES) ||
    isRefreshing(Module.BALANCER, Section.DEFI_BALANCER_TRADES) ||
    isRefreshing(Module.SUSHISWAP, Section.DEFI_SUSHISWAP_TRADES)
  );
});

const isEnabled = isAnyModuleEnabled(modules);

const { tc } = useI18n();

onMounted(async () => {
  await Promise.allSettled([
    fetchUniswapTrades(false),
    fetchBalancerTrades(false),
    fetchSushiswapTrades(false)
  ]);
});
</script>

<script setup lang="ts">
import DashboardAssetTable from '@/components/dashboard/DashboardAssetTable.vue';
import DynamicMessageDisplay from '@/components/dashboard/DynamicMessageDisplay.vue';
import NftBalanceTable from '@/components/dashboard/NftBalanceTable.vue';
import OverallBalances from '@/components/dashboard/OverallBalances.vue';
import PriceRefresh from '@/components/helper/PriceRefresh.vue';
import { useBalancesLoading } from '@/composables/balances/loading';
import { useAggregatedBalances } from '@/composables/balances/use-aggregated-balances';
import { useDynamicMessages } from '@/composables/dynamic-messages';
import { useModules } from '@/composables/session/modules';
import HistoryQueryIndicator from '@/modules/dashboard/history-progress/HistoryQueryIndicator.vue';
import { Module } from '@/types/modules';
import { DashboardTableType } from '@/types/settings/frontend-settings';
import PoolTable from './liquidity-pools/PoolTable.vue';
import Summary from './summary/Summary.vue';

const Type = DashboardTableType;

const { t } = useI18n({ useScope: 'global' });
const { isModuleEnabled } = useModules();
const { balances, liabilities } = useAggregatedBalances();
const { activeDashboardMessages } = useDynamicMessages();

const aggregatedBalances = balances();
const aggregatedLiabilities = liabilities();

const nftEnabled = isModuleEnabled(Module.NFTS);

const { loadingBalancesAndDetection: isAnyLoading } = useBalancesLoading();
const dismissedMessage = useSessionStorage('rotki.messages.dash.dismissed', false);

const dashboardRef = ref<HTMLElement>();
const floatingRef = ref<HTMLElement>();
const dashboardWidth = ref(0);

const { width } = useElementSize(dashboardRef);
watch(width, (newWidth) => {
  set(dashboardWidth, newWidth);
});

const showDynamicMessage = computed(() => get(activeDashboardMessages).length > 0 && !get(dismissedMessage));

const { height: floatingHeight } = useElementSize(floatingRef);

watch(floatingHeight, (newHeight, oldHeight) => {
  const diff = newHeight - oldHeight;
  if (diff !== 0) {
    const scrollElement = document.documentElement.scrollTop > 0 ? document.documentElement : document.body;
    const currentScroll = scrollElement.scrollTop;

    // Temporarily disable smooth scrolling
    const originalBehavior = scrollElement.style.scrollBehavior;
    scrollElement.style.scrollBehavior = 'auto';

    scrollElement.scrollTop = currentScroll + diff;

    // Restore original scroll behavior after a frame
    requestAnimationFrame(() => {
      scrollElement.style.scrollBehavior = originalBehavior;
    });
  }
});

const paddingTop = computed(() => get(floatingHeight) || 0);
</script>

<template>
  <div
    ref="dashboardRef"
    class="pb-6"
    data-cy="dashboard"
  >
    <div
      ref="floatingRef"
      class="fixed z-[7] top-14 md:top-16 shadow-sm"
      :style="{ width: `${dashboardWidth}px` }"
    >
      <DynamicMessageDisplay
        v-if="showDynamicMessage"
        :messages="activeDashboardMessages"
        @dismiss="dismissedMessage = true"
      />
      <HistoryQueryIndicator />
    </div>
    <div
      class="container"
      :style="{ paddingTop: `${paddingTop}px` }"
    >
      <div class="flex flex-wrap gap-6">
        <div class="w-full">
          <OverallBalances />
        </div>
        <Summary />
      </div>
      <div class="flex justify-end my-4">
        <PriceRefresh />
      </div>
      <DashboardAssetTable
        :title="t('common.assets')"
        :table-type="Type.ASSETS"
        :loading="isAnyLoading"
        :balances="aggregatedBalances"
      />
      <PoolTable class="mt-8" />
      <DashboardAssetTable
        v-if="aggregatedLiabilities.length > 0"
        class="mt-8"
        :table-type="Type.LIABILITIES"
        :title="t('dashboard.liabilities.title')"
        :loading="isAnyLoading"
        :balances="aggregatedLiabilities"
      />
      <NftBalanceTable
        v-if="nftEnabled"
        id="nft-balance-table-section"
        data-cy="nft-balance-table"
        class="mt-8"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import PriceRefresh from '@/modules/assets/prices/PriceRefresh.vue';
import { useAggregatedBalances } from '@/modules/balances/use-aggregated-balances';
import { useBalancesLoading } from '@/modules/balances/use-balance-loading';
import { useDynamicMessages } from '@/modules/core/messaging/use-dynamic-messages';
import DashboardAssetTable from '@/modules/dashboard/DashboardAssetTable.vue';
import DynamicMessageDisplay from '@/modules/dashboard/DynamicMessageDisplay.vue';
import NftBalanceTable from '@/modules/dashboard/NftBalanceTable.vue';
import OverallBalances from '@/modules/dashboard/OverallBalances.vue';
import DashboardProgressIndicator from '@/modules/dashboard/progress/DashboardProgressIndicator.vue';
import { Module, useModuleEnabled } from '@/modules/session/use-module-enabled';
import { DashboardTableType } from '@/modules/settings/types/frontend-settings';
import PoolTable from './liquidity-pools/PoolTable.vue';
import Summary from './summary/Summary.vue';

const Type = DashboardTableType;

const dashboardWidth = ref<number>(0);
const dashboardRef = useTemplateRef<HTMLElement>('dashboardRef');
const floatingRef = useTemplateRef<HTMLElement>('floatingRef');

const { t } = useI18n({ useScope: 'global' });
const { useBalances, useLiabilities } = useAggregatedBalances();
const { activeDashboardMessages } = useDynamicMessages();

const aggregatedBalances = useBalances();
const aggregatedLiabilities = useLiabilities();

const { enabled: nftEnabled } = useModuleEnabled(Module.NFTS);

const { width } = useElementSize(dashboardRef);
const { height: floatingHeight } = useElementBounding(floatingRef);

const { loadingBalancesAndDetection: isAnyLoading } = useBalancesLoading();
const dismissedMessage = useSessionStorage('rotki.messages.dash.dismissed', false);

const paddingTop = computed<number>(() => get(floatingHeight) || 0);
const showDynamicMessage = computed<boolean>(() => get(activeDashboardMessages).length > 0 && !get(dismissedMessage));

watch(floatingHeight, (newHeight, oldHeight) => {
  const diff = newHeight - oldHeight;
  if (diff === 0) {
    return;
  }

  const scrollElement = document.documentElement.scrollTop > 0 ? document.documentElement : document.body;
  const currentScroll = scrollElement.scrollTop;
  const originalBehavior = scrollElement.style.scrollBehavior;

  scrollElement.style.scrollBehavior = 'auto';
  scrollElement.scrollTop = currentScroll + diff;

  requestAnimationFrame(() => {
    scrollElement.style.scrollBehavior = originalBehavior;
  });
});

watch(width, (newWidth) => {
  set(dashboardWidth, newWidth);
});
</script>

<template>
  <div
    ref="dashboardRef"
    class="pb-6"
    data-cy="dashboard"
  >
    <div
      ref="floatingRef"
      class="fixed z-[7] top-14 md:top-16 shadow-sm overflow-hidden"
      :style="{ width: `${dashboardWidth}px` }"
    >
      <DynamicMessageDisplay
        v-if="showDynamicMessage"
        :messages="activeDashboardMessages"
        @dismiss="dismissedMessage = true"
      />
      <DashboardProgressIndicator />
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

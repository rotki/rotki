<script setup lang="ts">
import type { SourceKind } from '@/modules/dashboard/holdings/core/holdings-types';
import { useAggregatedBalances } from '@/modules/balances/use-aggregated-balances';
import { useBalanceStatus } from '@/modules/balances/use-balance-status';
import { useDynamicMessages } from '@/modules/core/messaging/use-dynamic-messages';
import DashboardAssetTable from '@/modules/dashboard/DashboardAssetTable.vue';
import DynamicMessageDisplay from '@/modules/dashboard/DynamicMessageDisplay.vue';
import DashboardLocations from '@/modules/dashboard/holdings/components/DashboardLocations.vue';
import NftBalanceTable from '@/modules/dashboard/NftBalanceTable.vue';
import OverallBalances from '@/modules/dashboard/OverallBalances.vue';
import DashboardProgressIndicator from '@/modules/dashboard/progress/DashboardProgressIndicator.vue';
import { Module, useModuleEnabled } from '@/modules/session/use-module-enabled';
import { DashboardTableType } from '@/modules/settings/types/frontend-settings';
import PoolTable from './liquidity-pools/PoolTable.vue';

const Type = DashboardTableType;

/** A source kind picked in the legend, which narrows the location tiles. */
const selectedKind = ref<SourceKind>();

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

const { isInitialLoading: isAnyLoading } = useBalanceStatus();
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
    data-testid="dashboard"
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
          <OverallBalances v-model:selected-kind="selectedKind" />
        </div>
        <DashboardLocations
          v-model:selected-kind="selectedKind"
          class="w-full"
        />
      </div>
      <DashboardAssetTable
        class="mt-8"
        :title="t('common.assets')"
        :table-type="Type.ASSETS"
        :loading="isAnyLoading"
        :balances="aggregatedBalances"
      />
      <PoolTable class="mt-8" />
      <DashboardAssetTable
        v-if="aggregatedLiabilities.length > 0"
        id="dashboard-liabilities"
        class="mt-8"
        :table-type="Type.LIABILITIES"
        :title="t('dashboard.liabilities.title')"
        :loading="isAnyLoading"
        :balances="aggregatedLiabilities"
      />
      <NftBalanceTable
        v-if="nftEnabled"
        id="nft-balance-table-section"
        data-testid="nft-balance-table"
        class="mt-8"
      />
    </div>
  </div>
</template>

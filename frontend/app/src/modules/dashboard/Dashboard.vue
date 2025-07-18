<script setup lang="ts">
import DashboardAssetTable from '@/components/dashboard/DashboardAssetTable.vue';
import DynamicMessageDisplay from '@/components/dashboard/DynamicMessageDisplay.vue';
import EvmQueryIndicator from '@/components/dashboard/EvmQueryIndicator.vue';
import NftBalanceTable from '@/components/dashboard/NftBalanceTable.vue';
import OverallBalances from '@/components/dashboard/OverallBalances.vue';
import PriceRefresh from '@/components/helper/PriceRefresh.vue';
import { useBalancesLoading } from '@/composables/balances/loading';
import { useAggregatedBalances } from '@/composables/balances/use-aggregated-balances';
import { useDynamicMessages } from '@/composables/dynamic-messages';
import { useModules } from '@/composables/session/modules';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
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

const { showEvmQueryIndicator } = storeToRefs(useFrontendSettingsStore());

const { height: floatingHeight } = useElementSize(floatingRef);

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
      <EvmQueryIndicator v-if="showEvmQueryIndicator" />
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

<script setup lang="ts">
import { startPromise } from '@shared/utils';
import { msg } from '@/message-key';
import { createNewBlockchainAccount } from '@/modules/accounts/blockchain/new-account-state';
import AssetBalances from '@/modules/balances/AssetBalances.vue';
import BlockchainBalanceFilter from '@/modules/balances/BlockchainBalanceFilter.vue';
import BlockchainBalancesRefreshButton from '@/modules/balances/BlockchainBalancesRefreshButton.vue';
import BlockchainBalanceStalenessIndicator from '@/modules/balances/BlockchainBalanceStalenessIndicator.vue';
import { useAggregatedBalances } from '@/modules/balances/use-aggregated-balances';
import { useBalanceStatus } from '@/modules/balances/use-balance-status';
import { NoteLocation } from '@/modules/core/common/notes';
import { useAddQuery } from '@/modules/core/common/use-add-query';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import VisibleColumnsSelector from '@/modules/dashboard/VisibleColumnsSelector.vue';
import HideSmallBalances from '@/modules/settings/HideSmallBalances.vue';
import { BalanceSource, DashboardTableType } from '@/modules/settings/types/frontend-settings';
import { useSetting } from '@/modules/settings/use-setting';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.balances_sub.blockchain_balances'), icon: 'lu-blockchain', parent: '/balances/', order: 10, drawer: 'balances-blockchain' },
    canNavigateBack: true,
    noteLocation: NoteLocation.BALANCES_BLOCKCHAIN,
  },
  props: true,
});

const account = ref<ReturnType<typeof createNewBlockchainAccount>>();
const search = ref<string>('');
const chainsFilter = ref<string[]>([]);

const { t } = useI18n({ useScope: 'global' });

const tableType = DashboardTableType.BLOCKCHAIN_ASSET_BALANCES;

const { useBlockchainBalances } = useAggregatedBalances();
const { isInitialLoading } = useBalanceStatus();
const dashboardTablesVisibleColumns = useSetting('dashboardTablesVisibleColumns');

const aggregatedBalances = useBlockchainBalances(chainsFilter);

const { consumeAddQuery } = useAddQuery(() => {
  startPromise(nextTick(() => {
    set(account, createNewBlockchainAccount());
  }));
});

onMounted(async () => {
  await consumeAddQuery();
});
</script>

<template>
  <TablePageLayout
    :title="[
      t('navigation_menu.balances'),
      t('navigation_menu.balances_sub.blockchain_balances'),
    ]"
  >
    <template #buttons>
      <BlockchainBalanceStalenessIndicator class="self-center" />
      <BlockchainBalancesRefreshButton />
      <HideSmallBalances :source="BalanceSource.BLOCKCHAIN" />
    </template>

    <!-- a frame rather than a card: the card's scrolling content would hold the sticky pagination bar -->
    <TableFrame>
      <template #toolbar>
        <BlockchainBalanceFilter
          v-model:chains="chainsFilter"
          v-model:search="search"
          class="flex-1 min-w-48 md:min-w-96"
        />
        <VisibleColumnsSelector
          :group="tableType"
          :group-label="t('blockchain_balances.group_label')"
          size="sm"
        />
      </template>

      <AssetBalances
        data-testid="blockchain-asset-balances"
        :loading="isInitialLoading"
        :balances="aggregatedBalances"
        :search="search"
        :breakdown="{
          scope: { chains: chainsFilter },
        }"
        :visible-columns="dashboardTablesVisibleColumns[tableType]"
        show-per-protocol
        sticky-header
      />
    </TableFrame>
  </TablePageLayout>
</template>

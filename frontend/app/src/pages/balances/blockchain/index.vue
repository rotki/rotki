<script setup lang="ts">
import { startPromise } from '@shared/utils';
import {
  type AccountManageState,
  createNewBlockchainAccount,
} from '@/composables/accounts/blockchain/use-account-manage';
import { NoteLocation } from '@/types/notes';
import { BalanceSource, DashboardTableType } from '@/types/settings/frontend-settings';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useAccountLoading } from '@/composables/accounts/loading';
import { useBlockchainAggregatedBalances } from '@/composables/blockchain/balances/aggregated';
import AssetBalances from '@/components/AssetBalances.vue';
import VisibleColumnsSelector from '@/components/dashboard/VisibleColumnsSelector.vue';
import ChainSelect from '@/components/accounts/blockchain/ChainSelect.vue';
import CardTitle from '@/components/typography/CardTitle.vue';
import HideSmallBalances from '@/components/settings/HideSmallBalances.vue';
import PriceRefresh from '@/components/helper/PriceRefresh.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import BlockchainBalanceRefreshBehaviourMenu
  from '@/components/dashboard/blockchain-balance/BlockchainBalanceRefreshBehaviourMenu.vue';
import { useBlockchainAccountLoading } from '@/composables/accounts/blockchain/use-account-loading';
import { useRefresh } from '@/composables/balances/refresh';
import SummaryCardRefreshMenu from '@/modules/dashboard/summary/SummaryCardRefreshMenu.vue';

definePage({
  meta: {
    canNavigateBack: true,
    noteLocation: NoteLocation.BALANCES_BLOCKCHAIN,
  },
  name: 'balances-blockchain',
  props: true,
});

const account = ref<AccountManageState>();
const search = ref('');
const chainsFilter = ref<string[]>([]);

const { t } = useI18n();
const route = useRoute('balances-blockchain');

const { blockchainAssets } = useBlockchainAggregatedBalances();
const { isBlockchainLoading } = useAccountLoading();
const { dashboardTablesVisibleColumns } = storeToRefs(useFrontendSettingsStore());

const { isDetectingTokens, refreshDisabled } = useBlockchainAccountLoading();

const tableType = DashboardTableType.BLOCKCHAIN_ASSET_BALANCES;

const aggregatedBalances = blockchainAssets(chainsFilter);

onMounted(() => {
  const { query } = get(route);

  if (query.add) {
    startPromise(nextTick(() => {
      set(account, createNewBlockchainAccount());
    }));
  }
});

const { handleBlockchainRefresh } = useRefresh();
</script>

<template>
  <TablePageLayout
    :title="[
      t('navigation_menu.balances'),
      t('navigation_menu.balances_sub.blockchain_balances'),
    ]"
  >
    <template #buttons>
      <PriceRefresh />
      <HideSmallBalances :source="BalanceSource.BLOCKCHAIN" />
    </template>

    <div class="flex flex-col gap-8">
      <RuiCard>
        <div class="pb-6 flex flex-wrap xl:flex-nowrap justify-between gap-2 items-center">
          <div class="flex flex-row items-center gap-2">
            <SummaryCardRefreshMenu
              data-cy="blockchain-balances-refresh-menu"
              :disabled="refreshDisabled"
              :loading="isDetectingTokens"
              :tooltip="t('account_balances.refresh_tooltip')"
              @refresh="handleBlockchainRefresh()"
            >
              <template #refreshMenu>
                <BlockchainBalanceRefreshBehaviourMenu />
              </template>
            </SummaryCardRefreshMenu>
            <CardTitle class="ml-2">
              {{ t('blockchain_balances.title') }}
            </CardTitle>
          </div>
          <CardTitle class="order-0 whitespace-nowrap" />
          <div class="order-3 xl:order-1 flex flex-wrap md:flex-nowrap grow justify-end w-full xl:w-auto items-center gap-2 overflow-hidden pt-1.5 -mt-1 xl:pl-6">
            <ChainSelect
              v-model="chainsFilter"
              class="w-full xl:w-[30rem]"
              dense
              hide-details
              clearable
              chips
            />
            <RuiTextField
              v-model="search"
              variant="outlined"
              color="primary"
              dense
              prepend-icon="lu-search"
              :label="t('common.actions.search')"
              hide-details
              clearable
              class="w-full xl:w-[16rem]"
              @click:clear="search = ''"
            />
          </div>
          <VisibleColumnsSelector
            class="order-2"
            :group="tableType"
            :group-label="t('blockchain_balances.group_label')"
          />
        </div>

        <AssetBalances
          data-cy="blockchain-asset-balances"
          :loading="isBlockchainLoading"
          :balances="aggregatedBalances"
          :search="search"
          :details="{
            chains: chainsFilter,
          }"
          :visible-columns="dashboardTablesVisibleColumns[tableType]"
          sticky-header
        />
      </RuiCard>
    </div>
  </TablePageLayout>
</template>

<script setup lang="ts">
import { startPromise } from '@shared/utils';
import ChainSelect from '@/components/accounts/blockchain/ChainSelect.vue';
import AssetBalances from '@/components/AssetBalances.vue';
import BlockchainBalanceRefreshBehaviourMenu
  from '@/components/dashboard/blockchain-balance/BlockchainBalanceRefreshBehaviourMenu.vue';
import VisibleColumnsSelector from '@/components/dashboard/VisibleColumnsSelector.vue';
import BlockchainBalanceStalenessIndicator from '@/components/helper/BlockchainBalanceStalenessIndicator.vue';
import PriceRefresh from '@/components/helper/PriceRefresh.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import HideSmallBalances from '@/components/settings/HideSmallBalances.vue';
import CardTitle from '@/components/typography/CardTitle.vue';
import {
  type AccountManageState,
  createNewBlockchainAccount,
} from '@/composables/accounts/blockchain/use-account-manage';
import { useAccountLoading } from '@/composables/accounts/loading';
import { useAggregatedBalances } from '@/composables/balances/use-aggregated-balances';
import { useBlockchainAccountLoading } from '@/modules/accounts/use-account-loading';
import { useBalanceRefresh } from '@/modules/balances/use-balance-refresh';
import SummaryCardRefreshMenu from '@/modules/dashboard/summary/SummaryCardRefreshMenu.vue';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { NoteLocation } from '@/types/notes';
import { BalanceSource, DashboardTableType } from '@/types/settings/frontend-settings';

definePage({
  meta: {
    canNavigateBack: true,
    noteLocation: NoteLocation.BALANCES_BLOCKCHAIN,
  },
  name: 'balances-blockchain',
  props: true,
});

const account = ref<AccountManageState>();
const search = ref<string>('');
const chainsFilter = ref<string[]>([]);

const { t } = useI18n({ useScope: 'global' });

const route = useRoute('balances-blockchain');

const tableType = DashboardTableType.BLOCKCHAIN_ASSET_BALANCES;

const { useBlockchainBalances } = useAggregatedBalances();
const { isBlockchainLoading } = useAccountLoading();
const { dashboardTablesVisibleColumns } = storeToRefs(useFrontendSettingsStore());
const { isDetectingTokens, refreshDisabled } = useBlockchainAccountLoading();
const { handleBlockchainRefresh } = useBalanceRefresh();

const aggregatedBalances = useBlockchainBalances(chainsFilter);

onMounted(() => {
  const { query } = get(route);

  if (!query.add) {
    return;
  }

  startPromise(nextTick(() => {
    set(account, createNewBlockchainAccount());
  }));
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
            <div class="flex flex-col ml-2">
              <CardTitle>
                {{ t('blockchain_balances.title') }}
              </CardTitle>
              <BlockchainBalanceStalenessIndicator />
            </div>
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
          show-per-protocol
          sticky-header
        />
      </RuiCard>
    </div>
  </TablePageLayout>
</template>

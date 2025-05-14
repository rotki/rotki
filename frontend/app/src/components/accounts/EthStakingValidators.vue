<script setup lang="ts">
import type { StakingValidatorManage } from '@/composables/accounts/blockchain/use-account-manage';
import type { EthereumValidator, EthereumValidatorRequestPayload } from '@/types/blockchain/accounts';
import type { ContextColorsType, DataTableColumn } from '@rotki/ui-library';
import Eth2ValidatorLimitRow from '@/components/accounts/blockchain/eth2/Eth2ValidatorLimitRow.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import PercentageDisplay from '@/components/display/PercentageDisplay.vue';
import RowActions from '@/components/helper/RowActions.vue';
import RowAppend from '@/components/helper/RowAppend.vue';
import TableFilter from '@/components/table-filter/TableFilter.vue';
import { useAccountDelete } from '@/composables/accounts/blockchain/use-account-delete';
import { useEthStaking } from '@/composables/blockchain/accounts/staking';
import { type Filters, type Matcher, useEthValidatorAccountFilter } from '@/composables/filters/eth-validator';
import { usePaginationFilters } from '@/composables/use-pagination-filter';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import HashLink from '@/modules/common/links/HashLink.vue';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { TableId, useRememberTableSorting } from '@/modules/table/use-remember-table-sorting';
import { useBlockchainValidatorsStore } from '@/store/blockchain/validators';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useStatusStore } from '@/store/status';
import { useTaskStore } from '@/store/tasks';
import { SavedFilterLocation } from '@/types/filtering';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { Blockchain, One, Zero } from '@rotki/common';

const emit = defineEmits<{
  (e: 'edit', value: StakingValidatorManage): void;
}>();

const { t } = useI18n({ useScope: 'global' });

const selected = ref<number[]>([]);

const blockchainValidatorsStore = useBlockchainValidatorsStore();
const { fetchValidators } = blockchainValidatorsStore;
const { ethStakingValidators } = storeToRefs(blockchainValidatorsStore);
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { showConfirmation } = useAccountDelete();
const { fetchEthStakingValidators } = useEthStaking();
const { useExchangeRate } = usePriceUtils();
const { fetchBlockchainBalances } = useBlockchainBalances();

const {
  fetchData,
  filters,
  matchers,
  pagination,
  sort,
  state: rows,
} = usePaginationFilters<
  EthereumValidator,
  EthereumValidatorRequestPayload,
  Filters,
  Matcher
>(fetchValidators, {
  defaultSortBy: {
    column: 'index',
    direction: 'desc',
  },
  filterSchema: () => useEthValidatorAccountFilter(t),
  history: 'router',
});

const cols = computed<DataTableColumn<EthereumValidator>[]>(() => {
  const currency = { symbol: get(currencySymbol) };
  return [
    {
      cellClass: 'py-0',
      key: 'index',
      label: t('common.validator_index'),
      sortable: true,
    },
    {
      cellClass: 'py-0',
      key: 'publicKey',
      label: t('eth2_input.public_key'),
      sortable: true,
    },
    {
      cellClass: 'py-0',
      key: 'status',
      label: t('common.status'),
      sortable: true,
    },
    {
      align: 'end',
      cellClass: 'py-0',
      key: 'amount',
      label: t('common.amount'),
      sortable: true,
    },
    {
      align: 'end',
      cellClass: 'py-0',
      key: 'usdValue',
      label: t('account_balances.headers.usd_value', currency),
      sortable: true,
    },
    {
      align: 'end',
      cellClass: 'py-0',
      key: 'ownershipPercentage',
      label: t('common.ownership'),
      sortable: false,
    },
    {
      align: 'end',
      cellClass: '!p-0',
      key: 'actions',
      label: t('common.actions_text'),
    },
  ];
});

useRememberTableSorting<EthereumValidator>(TableId.ETH_STAKING_VALIDATORS, sort, cols);

const { useIsTaskRunning } = useTaskStore();
const { isLoading } = useStatusStore();

const loading = isLoading(Section.BLOCKCHAIN, Blockchain.ETH2);

const accountOperation = logicOr(
  useIsTaskRunning(TaskType.ADD_ACCOUNT),
  useIsTaskRunning(TaskType.REMOVE_ACCOUNT),
  loading,
);

function edit(account: EthereumValidator) {
  const { index, ownershipPercentage, publicKey } = account;
  const state: StakingValidatorManage = {
    chain: Blockchain.ETH2,
    data: {
      ownershipPercentage: ownershipPercentage ?? '100',
      publicKey,
      validatorIndex: index.toString(),
    },
    mode: 'edit',
    type: 'validator',
  };
  emit('edit', state);
}

const colorMap: Record<string, ContextColorsType | undefined> = {
  active: 'success',
  consolidated: 'secondary',
  exited: 'error',
  exiting: 'warning',
  pending: 'info',
};

function getColor(status: string): ContextColorsType | undefined {
  return colorMap[status] ?? undefined;
}

function getOwnershipPercentage(row: EthereumValidator): string {
  return row.ownershipPercentage || '100';
}

async function refresh() {
  await fetchEthStakingValidators();
  await fetchBlockchainBalances({
    blockchain: Blockchain.ETH2,
    ignoreCache: true,
  });
}

function confirmDelete(item: EthereumValidator) {
  showConfirmation({
    data: [item],
    type: 'validator',
  });
}

function deleteSelectedValidators() {
  const items = get(rows).data.filter(item => get(selected).includes(item.index));
  showConfirmation({
    data: items,
    type: 'validator',
  });
}

const total = computed(() => {
  const mainCurrency = get(currencySymbol);
  return (get(rows).totalUsdValue || Zero).multipliedBy(get(useExchangeRate(mainCurrency)) ?? One);
});

watchImmediate(ethStakingValidators, async () => {
  await fetchData();
});

defineExpose({
  refresh,
});
</script>

<template>
  <RuiCard>
    <template #header>
      {{ t('blockchain_balances.validators.title') }}
    </template>
    <div class="flex flex-row flex-wrap items-center gap-2">
      <div class="flex flex-row gap-3">
        <RuiButton
          :disabled="selected.length === 0"
          class="h-10"
          variant="outlined"
          color="error"
          :loading="accountOperation"
          @click="deleteSelectedValidators()"
        >
          <template #prepend>
            <RuiIcon
              name="lu-trash-2"
              size="16"
            />
          </template>
          {{ t('common.actions.delete') }}
        </RuiButton>
        <div
          v-if="selected.length > 0"
          class="flex gap-2 items-center text-sm"
        >
          {{ t('blockchain_balances.validators.selected', { count: selected.length }) }}
          <RuiButton
            size="sm"
            class="!py-0 !px-1.5 !gap-0.5 dark:!bg-opacity-30 dark:!text-white"
            @click="selected = []"
          >
            <template #prepend>
              <RuiIcon
                name="lu-x"
                size="14"
              />
            </template>
            {{ t('common.actions.clear_selection') }}
          </RuiButton>
        </div>
      </div>
      <div class="grow" />

      <TableFilter
        v-model:matches="filters"
        :matchers="matchers"
        class="max-w-[calc(100vw-11rem)] w-[25rem] lg:max-w-[30rem]"
        :location="SavedFilterLocation.ETH_VALIDATORS"
      />
    </div>
    <RuiDataTable
      v-model="selected"
      v-model:sort.external="sort"
      v-model:pagination.external="pagination"
      class="mt-4"
      dense
      row-attr="index"
      outlined
      :cols="cols"
      :rows="rows.data"
      sticky-header
      show-select
      return-object
      :empty="{ description: t('data_table.no_data') }"
    >
      <template #item.index="{ row }">
        <HashLink
          class="my-2"
          location="eth2"
          :text="row.index.toString()"
        />
      </template>
      <template #item.publicKey="{ row }">
        <HashLink
          class="my-2"
          location="eth2"
          :show-icon="false"
          :text="row.publicKey.toString()"
        />
      </template>
      <template #item.status="{ row }">
        <RuiChip
          size="sm"
          :color="getColor(row.status)"
          class="uppercase [&_span]:text-xs [&_span]:inline-flex [&_span]:gap-1 [&_span]:items-center font-semibold"
        >
          {{ row.status }}

          <template v-if="row.consolidatedInto">
            <RuiTooltip
              persist-on-tooltip-hover
              :open-delay="300"
            >
              <template #activator>
                <RuiIcon
                  name="lu-merge"
                  size="16"
                  class="bg-rui-grey-200 text-rui-grey-800 rounded-full p-0.5 -mr-1.5 cursor-pointer"
                />
              </template>
              <div>{{ t('blockchain_balances.validators.consolidated') }}</div>
              <HashLink
                location="eth2"
                :text="row.consolidatedInto.toString()"
              />
            </RuiTooltip>
          </template>
        </RuiChip>
      </template>
      <template #item.amount="{ row }">
        <AmountDisplay
          :value="row.amount"
          asset="ETH"
          :asset-padding="0.1"
        />
      </template>
      <template #item.usdValue="{ row }">
        <AmountDisplay
          fiat-currency="USD"
          :value="row.usdValue"
          show-currency="symbol"
        />
      </template>
      <template #item.ownershipPercentage="{ row }">
        <PercentageDisplay
          :value="getOwnershipPercentage(row)"
          :asset-padding="0.1"
        />
      </template>
      <template #item.actions="{ row }">
        <div class="flex justify-end mr-2">
          <RowActions
            :edit-tooltip="t('account_balances.edit_tooltip')"
            :disabled="accountOperation"
            @edit-click="edit(row)"
            @delete-click="confirmDelete(row)"
          />
        </div>
      </template>
      <template #body.prepend="{ colspan }">
        <Eth2ValidatorLimitRow :colspan="colspan" />
      </template>
      <template
        v-if="ethStakingValidators.length > 0"
        #body.append
      >
        <RowAppend
          label-colspan="4"
          :label="t('common.total')"
          :right-patch-colspan="cols.length - 2"
          class-name="[&>td]:p-4 text-sm"
        >
          <AmountDisplay
            :fiat-currency="currencySymbol"
            :value="total"
            show-currency="symbol"
          />
        </RowAppend>
      </template>
    </RuiDataTable>
  </RuiCard>
</template>

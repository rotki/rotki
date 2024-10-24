<script setup lang="ts" generic="T extends BlockchainAccountWithBalance | BlockchainAccountGroupWithBalance">
import { isEmpty, some } from 'lodash-es';
import { TaskType } from '@/types/task-type';
import { Section } from '@/types/status';
import type { TableRowKey } from '@/composables/use-pagination-filter/types';
import type { AccountManageState } from '@/composables/accounts/blockchain/use-account-manage';
import type { Collection } from '@/types/collection';
import type { DataTableColumn, DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { BigNumber } from '@rotki/common';
import type { BlockchainAccountGroupWithBalance, BlockchainAccountWithBalance } from '@/types/blockchain/accounts';

type DataRow = T & { id: string };

defineOptions({
  inheritAttrs: false,
});

const chainFilter = defineModel<Record<string, string[]>>('chainFilter', { required: false, default: {} });

const pagination = defineModel<TablePaginationData>('pagination', { required: true });

const sort = defineModel<DataTableSortData<T>>('sort', { required: true });

const expandedIds = defineModel<string[]>('expandedIds', { required: true });

const props = withDefaults(defineProps<{
  accounts: Collection<T>;
  group?: boolean;
  loading?: boolean;
  showGroupLabel?: boolean;
  isEvm?: boolean;
}>(), {
  loading: false,
  group: false,
  showGroupLabel: false,
  isEvm: false,
});

const emit = defineEmits<{
  (e: 'edit', account: AccountManageState): void;
  (e: 'refresh'): void;
}>();

const { t } = useI18n();

const collapsed = ref<DataRow[]>([]) as Ref<DataRow[]>;

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const { isTaskRunning } = useTaskStore();
const { isLoading } = useStatusStore();
const { supportsTransactions } = useSupportedChains();
const { showConfirmation } = useAccountDelete();

const loading = isLoading(Section.BLOCKCHAIN);

const totalValue = computed<BigNumber | undefined>(() => {
  const totalUsdValue = props.accounts.totalUsdValue;
  if (!totalUsdValue)
    return undefined;

  return totalUsdValue.minus(sum(get(collapsed)));
});

const rows = computed<DataRow[]>(() => {
  const data = props.accounts.data;
  return data.map(account => ({
    ...account,
    id: 'chain' in account ? getAccountId(account) : getGroupId(account),
  }));
});

const anyExpansion = computed(() => get(rows).some(item => item.expansion));

const expanded = computed<DataRow[]>(({
  get() {
    return get(rows).filter(row => get(expandedIds).includes(row.id));
  },
  set(value: DataRow[]) {
    set(expandedIds, get(value).map(row => row.id));
  },
}));

const cols = computed<DataTableColumn<DataRow>[]>(() => {
  const currency = { symbol: get(currencySymbol) };
  const isEvm = props.isEvm;
  const headers: DataTableColumn<T>[] = [
    ...(get(anyExpansion)
      ? [{
          label: '',
          key: 'expand',
          sortable: false,
          class: '!py-0 !pr-0 !pl-3',
          cellClass: '!py-0 !pr-0 !pl-3',
        }]
      : []),
    ...(isEvm
      ? []
      : [{
          label: t('common.account'),
          key: 'label',
          class: '!px-3',
          cellClass: 'py-0 !px-3',
          sortable: true,
        }]),
    {
      label: t('common.chain'),
      key: 'chain',
      cellClass: 'py-0 !pr-0',
      class: '!pr-0',
      sortable: false,
    },
    ...(isEvm
      ? []
      : [{
          label: t('common.tags'),
          key: 'tags',
          cellClass: 'py-0',
          sortable: false,
        }]),
    {
      label: t('common.assets'),
      key: 'assets',
      cellClass: 'py-0 !pr-0 !pl-2',
      class: '!pr-0 !pl-2',
      align: 'end',
    },
    {
      label: t('account_balances.headers.usd_value', currency),
      key: 'usdValue',
      sortable: true,
      cellClass: 'py-0',
      align: 'end',
    },
    {
      label: t('common.actions_text'),
      key: 'actions',
      cellClass: '!p-0',
      align: 'end',
    },
  ];

  return headers;
});

const groupBy = computed<TableRowKey<T>[] | undefined>(() => {
  if (!props.group || !props.showGroupLabel)
    return undefined;

  return ['category' as TableRowKey<T>];
});

const accountOperation = logicOr(
  isTaskRunning(TaskType.ADD_ACCOUNT),
  isTaskRunning(TaskType.REMOVE_ACCOUNT),
  loading,
);

const isAnyLoading = logicOr(accountOperation, loading);

function isRowLoading(row: DataRow) {
  if (row.type === 'account')
    return get(isLoading(Section.BLOCKCHAIN, row.chain));
  else
    return row.chains.some(chain => get(isLoading(Section.BLOCKCHAIN, chain)));
}

function getId(row: DataRow) {
  return row.type === 'group' ? getGroupId(row) : getAccountId(row);
}

function isExpanded(row: DataRow) {
  return some(get(expanded), { id: getId(row) });
}

function expand(item: DataRow) {
  set(expanded, isExpanded(item) ? [] : [item]);
}

function showTokenDetection(row: DataRow): boolean {
  if (row.type === 'group')
    return row.chains.length === 1 && supportsTransactions(row.chains[0]);

  return supportsTransactions(row.chain);
}

function confirmDelete(item: DataRow) {
  showConfirmation({
    type: 'account',
    data: item,
  }, () => {
    emit('refresh');
  });
}

function edit(row: DataRow) {
  emit('edit', editBlockchainAccount(row));
}

function getCategoryTotal(category: string): BigNumber {
  return sum(get(rows).filter(row => row.category === category));
}

function getChains(row: DataRow): string[] {
  if (row.type === 'account')
    return [row.chain];

  const groupId = getGroupId(row);
  const excluded = get(chainFilter)[groupId] ?? [];

  return isEmpty(excluded)
    ? row.chains
    : row.chains.filter(chain => !excluded.includes(chain));
}

defineExpose({
  confirmDelete,
});
</script>

<template>
  <RuiDataTable
    v-bind="$attrs"
    v-model:expanded="expanded"
    v-model:sort.external="sort"
    v-model:pagination.external="pagination"
    v-model:collapsed="collapsed"
    :cols="cols"
    :rows="rows"
    :loading="group && isAnyLoading"
    row-attr="id"
    :empty="{ description: t('data_table.no_data') }"
    :loading-text="t('account_balances.data_table.loading')"
    data-cy="account-table"
    single-expand
    outlined
    :group="groupBy"
    sticky-header
    dense
  >
    <template #item.label="{ row }">
      <LabeledAddressDisplay
        :account="row"
        class="my-2 account-balance-table__account"
      />
    </template>
    <template #item.chain="{ row }">
      <AccountChains
        v-model:chain-filter="chainFilter"
        :row="row"
      />
    </template>
    <template #item.tags="{ row }">
      <TagDisplay
        :tags="row.tags"
        class="!mt-0"
        small
      />
    </template>
    <template #item.assets="{ row }">
      <AccountTopTokens
        :chains="getChains(row)"
        :address="getAccountAddress(row)"
        :loading="isRowLoading(row)"
      />
    </template>
    <template #item.value="{ row }">
      <div class="flex flex-col items-end justify-end">
        <div
          v-if="row.includedValue && !isRowLoading(row)"
          class="text-xs"
        >
          <AmountDisplay
            v-if="row.includedValue"
            :fiat-currency="currencySymbol"
            :value="row.includedValue"
            show-currency="symbol"
          />
          /
        </div>
        <AmountDisplay
          class="font-medium"
          :fiat-currency="currencySymbol"
          :value="row.value"
          show-currency="symbol"
          :loading="isRowLoading(row)"
        />
      </div>
    </template>
    <template #item.actions="{ row }">
      <div class="flex justify-end mr-2">
        <TokenDetection
          v-if="showTokenDetection(row)"
          class="ms-2"
          :address="getAccountAddress(row)"
          :loading="loading"
          :chain="row.type === 'group' ? row.chains[0] : row.chain"
        />
        <RowActions
          v-if="!('virtual' in row) || !row.virtual"
          class="account-balance-table__actions"
          :edit-tooltip="t('account_balances.edit_tooltip')"
          :disabled="accountOperation"
          :no-edit="isEvm"
          @edit-click="edit(row)"
          @delete-click="confirmDelete(row)"
        />
      </div>
    </template>
    <template
      v-if="totalValue"
      #body.append
    >
      <RowAppend
        :label="t('common.total')"
        :left-patch-colspan="anyExpansion ? 1 : 0"
        :label-colspan="isEvm ? 2 : 4"
        :is-mobile="false"
        class-name="[&>td]:p-4 text-sm"
      >
        <template #custom-columns>
          <td class="text-end">
            <AmountDisplay
              :loading="loading"
              :fiat-currency="currencySymbol"
              show-currency="symbol"
              :value="totalValue"
            />
          </td>
        </template>
      </RowAppend>
    </template>
    <template
      v-if="anyExpansion"
      #expanded-item="{ row }"
    >
      <slot
        name="details"
        :row="row"
      />
    </template>
    <template #item.expand="{ row }">
      <RuiTableRowExpander
        v-if="row.expansion"
        :expanded="isExpanded(row)"
        @click="expand(row)"
      />
    </template>
    <template #group.header="{ header, isOpen, toggle, colspan }">
      <td
        :id="header.group.category"
        class="py-2 px-2"
        :colspan="colspan - 2"
      >
        <div class="flex font-medium gap-2 items-center">
          <RuiButton
            icon
            variant="text"
            size="sm"
            @click="toggle()"
          >
            <RuiIcon :name="isOpen ? 'arrow-up-s-line' : 'arrow-down-s-line' " />
          </RuiButton>
          <template
            v-if="header.group.category"
          >
            {{ t('account_balances.data_table.group', { type: header.group.category === 'evm' ? 'EVM' : toSentenceCase(header.group.category) }) }}
          </template>
        </div>
      </td>
      <td class="text-end text-body-2 px-4 py-0">
        <AmountDisplay
          v-if="header.group.category"
          :fiat-currency="currencySymbol"
          :value="getCategoryTotal(header.group.category)"
          show-currency="symbol"
          :loading="loading"
        />
      </td>
      <td />
    </template>
  </RuiDataTable>
</template>

<script setup lang="ts" generic="T extends BlockchainAccountWithBalance | BlockchainAccountGroupWithBalance">
import { some } from 'lodash-es';
import { TaskType } from '@/types/task-type';
import { Section } from '@/types/status';
import { getAccountAddress } from '@/utils/blockchain/accounts';
import type { TableRowKey } from '@/composables/filter-paginate';
import type { AccountManageState } from '@/composables/accounts/blockchain/use-account-manage';
import type { Collection } from '@/types/collection';
import type { DataTableColumn, DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { BlockchainAccountGroupWithBalance, BlockchainAccountWithBalance } from '@/types/blockchain/accounts';

type DataRow = T & { id: string };

const props = withDefaults(
  defineProps<{
    accounts: Collection<T>;
    selection?: boolean;
    group?: boolean;
    loading?: boolean;
    showGroupLabel?: boolean;
    availableChains?: string[];
  }>(),
  {
    loading: false,
    group: false,
    selection: false,
    showGroupLabel: false,
    availableChains: () => [],
  },
);

const emit = defineEmits<{
  (e: 'update:selection', enabled: boolean): void;
  (e: 'edit', account: AccountManageState): void;
  (e: 'refresh'): void;
}>();

const chainFilter = defineModel<string[]>('chainFilter', { required: false, default: [] });

const { t } = useI18n();

const pagination = defineModel<TablePaginationData>('pagination', { required: true });
const sort = defineModel<DataTableSortData<T>>('sort', { required: true });

const selection = ref<string[]>([]);
const expanded = ref<DataRow[]>([]) as Ref<DataRow[]>;

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const { isTaskRunning } = useTaskStore();
const { isLoading } = useStatusStore();
const { supportsTransactions } = useSupportedChains();
const { showConfirmation, showAgnosticConfirmation } = useAccountDelete();

const loading = isLoading(Section.BLOCKCHAIN);

// Keeping it as it is, will allow us to enable it easily later
const selectedIds = computed<undefined>({
  get() {
    return undefined;
  },
  set(value?: string[]) {
    set(selection, value);
    emit('update:selection', !!value && value.length > 0);
  },
});

const rows = computed<DataRow[]>(() => {
  const data = props.accounts.data;
  return data.map(account => ({
    ...account,
    id: 'chain' in account ? getAccountId(account) : getGroupId(account),
  }));
});

const selectedRows = computed<DataRow[]>(() => get(rows).filter(row => get(selection).includes(row.id)));

const anyExpansion = computed(() => get(rows).some(item => item.expansion));

const cols = computed<DataTableColumn<DataRow>[]>(() => {
  const currency = { symbol: get(currencySymbol) };
  const headers: DataTableColumn<T>[] = [
    ...(get(anyExpansion)
      ? [{
          label: '',
          key: 'expand',
          sortable: false,
          class: '!py-0 !pr-0',
          cellClass: '!py-0 !pr-0',
        }]
      : []),
    {
      label: t('common.account'),
      key: 'label',
      cellClass: 'py-0',
      sortable: true,
    },
    {
      label: t('common.chain'),
      key: 'chain',
      cellClass: 'py-0',
      sortable: false,
    },
    {
      label: t('common.tags'),
      key: 'tags',
      cellClass: 'py-0',
      sortable: false,
    },
    {
      label: t('common.assets'),
      key: 'assets',
      cellClass: 'py-0',
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

function isEditable(row: T): boolean {
  return row.data.type === 'xpub' || (row.type === 'group' && row.chains.length === 1);
}

function showTokenDetection(row: DataRow): boolean {
  if (row.type === 'group')
    return row.chains.length === 1 && supportsTransactions(row.chains[0]);

  return supportsTransactions(row.chain);
}

function confirmDelete(item?: DataRow) {
  showConfirmation({
    type: 'accounts',
    data: item ? [item] : get(selectedRows),
  }, () => {
    set(selection, []);
    emit('refresh');
  });
}

function confirmAgnosticDelete(item: DataRow) {
  showAgnosticConfirmation(item, () => {
    set(selection, []);
    emit('refresh');
  });
}

function edit(row: DataRow) {
  emit('edit', editBlockchainAccount(row));
}

defineExpose({
  confirmDelete,
});
</script>

<template>
  <RuiDataTable
    v-model="selectedIds"
    v-bind="$attrs"
    v-model:expanded="expanded"
    v-model:sort.external="sort"
    v-model:pagination.external="pagination"
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
        :group="group"
        :available-chains="availableChains"
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
        :row="row"
        :loading="isRowLoading(row)"
      />
    </template>
    <template #item.usdValue="{ row }">
      <AmountDisplay
        fiat-currency="USD"
        :value="row.usdValue"
        show-currency="symbol"
        :loading="isRowLoading(row)"
      />
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
          @edit-click="edit(row)"
          @delete-click="group && !isEditable(row) ? confirmAgnosticDelete(row) : confirmDelete(row)"
        />
      </div>
    </template>
    <template
      v-if="accounts.totalUsdValue"
      #body.append
    >
      <RowAppend
        :label="t('common.total')"
        :left-patch-colspan="anyExpansion ? 1 : 0"
        :label-colspan="4"
        :is-mobile="false"
        class-name="[&>td]:p-4 text-sm"
      >
        <template #custom-columns>
          <td class="text-end">
            <AmountDisplay
              :loading="loading"
              fiat-currency="USD"
              show-currency="symbol"
              :value="accounts.totalUsdValue"
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
        class="py-2 px-2"
        :colspan="colspan"
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
    </template>
  </RuiDataTable>
</template>

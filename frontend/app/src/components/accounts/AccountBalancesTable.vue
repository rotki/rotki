<script setup lang="ts">
import { some } from 'lodash-es';
import { TaskType } from '@/types/task-type';
import { Section } from '@/types/status';
import { getAccountAddress, getAccountId, getGroupId } from '@/utils/blockchain/accounts';
import type { TablePagination } from '@/types/pagination';
import type { Collection } from '@/types/collection';
import type { DataTableColumn, DataTableOptions, DataTableSortData } from '@rotki/ui-library-compat';
import type { BlockchainAccountGroupWithBalance, BlockchainAccountWithBalance } from '@/types/blockchain/accounts';

type Data = BlockchainAccountGroupWithBalance | BlockchainAccountWithBalance;

type DataRow = Data & { id: string };

type Options = TablePagination<BlockchainAccountWithBalance> | TablePagination<BlockchainAccountGroupWithBalance>;

const props = withDefaults(
  defineProps<{
    accounts: Collection<Data>;
    options: Options;
    selection?: boolean;
    group?: boolean;
    loading?: boolean;
  }>(),
  {
    loading: false,
    group: false,
    selection: false,
  },
);

const emit = defineEmits<{
  (e: 'update:options', options: DataTableOptions): void;
  (e: 'update:selection', enabled: boolean): void;
}>();

const { t } = useI18n();

const selection = ref<string[]>([]);
const expanded = ref<DataRow[]>([]);

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const { isTaskRunning } = useTaskStore();
const { isLoading } = useStatusStore();
const { supportsTransactions } = useSupportedChains();
const { editAccount } = useAccountDialog();
const { showConfirmation } = useAccountDelete();

const loading = isLoading(Section.BLOCKCHAIN);

// Keeping it as it is, will allow us to enable it easily later
const selectedIds = computed<string[] | undefined>({
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

const sort = ref<DataTableSortData>({
  column: 'usdValue',
  direction: 'desc' as const,
});

const cols = computed<DataTableColumn[]>(() => {
  const currency = { symbol: get(currencySymbol) };
  const expand: DataTableColumn = {
    label: '',
    key: 'expand',
    sortable: false,
    class: 'w-16',
    cellClass: '!py-0 w-16',
  };
  const headers: DataTableColumn[] = [
    ...(props.group ? [expand] : []),
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
      sortable: true,
    },
    {
      label: t('common.tags'),
      key: 'tags',
      cellClass: 'py-0',
      sortable: false,
    },
    {
      label: t('common.amount'),
      key: 'amount',
      sortable: true,
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

const accountOperation = logicOr(
  isTaskRunning(TaskType.ADD_ACCOUNT),
  isTaskRunning(TaskType.REMOVE_ACCOUNT),
  loading,
);

const isAnyLoading = logicOr(accountOperation, loading);

function isRowLoading(row: DataRow) {
  if ('chain' in row)
    return get(isLoading(Section.BLOCKCHAIN, row.chain));
  else
    return row.chains.some(chain => get(isLoading(Section.BLOCKCHAIN, chain)));
}

function getId(row: DataRow) {
  return 'chains' in row ? getGroupId(row) : getAccountId(row);
}

function getChains(row: DataRow) {
  return 'chains' in row ? row.chains : [row.chain];
}

function isExpanded(row: DataRow) {
  return some(get(expanded), { id: getId(row) });
}

function expand(item: DataRow) {
  set(expanded, isExpanded(item) ? [] : [item]);
}

function isXpub(row: DataRow): boolean {
  return 'xpub' in row.data;
}

function confirmDelete(item?: DataRow) {
  showConfirmation(item ? [item] : get(selectedRows), () => {
    set(selection, []);
  });
}

defineExpose({
  confirmDelete,
});
</script>

<template>
  <RuiDataTable
    v-model="selectedIds"
    v-bind="$attrs"
    :cols="cols"
    :rows="rows"
    :loading="group && isAnyLoading"
    row-attr="id"
    :expanded.sync="expanded"
    :sort.sync="sort"
    :sort-modifiers="{ external: true }"
    :empty="{ description: t('data_table.no_data') }"
    :loading-text="t('account_balances.data_table.loading')"
    :options="options"
    :pagination="{
      limit: options.itemsPerPage,
      page: options.page,
      total: accounts.found,
    }"
    :pagination-modifiers="{ external: true }"
    data-cy="account-table"
    single-expand
    outlined
    sticky-header
    @update:options="emit('update:options', $event)"
    v-on="
      // eslint-disable-next-line vue/no-deprecated-dollar-listeners-api
      $listeners
    "
  >
    <template #item.label="{ row }">
      <LabeledAddressDisplay
        :account="row"
        class="my-2 account-balance-table__account"
      />
    </template>
    <template #item.chain="{ row }">
      <div class="flex">
        <template v-for="chain in getChains(row)">
          <ChainIcon
            :key="chain"
            :chain="chain"
          />
        </template>
      </div>
    </template>
    <template #item.tags="{ row }">
      <TagDisplay
        :tags="row.tags"
        small
      />
    </template>
    <template #item.amount="{ row }">
      <AmountDisplay
        v-if="row.nativeAsset"
        :value="row.amount"
        :loading="isRowLoading(row)"
        :asset="row.nativeAsset"
        :asset-padding="0.1"
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
          v-if="row.chain && supportsTransactions(row.chain)"
          class="ms-2"
          :address="getAccountAddress(row)"
          :loading="loading"
          :chain="row.chain"
        />
        <RowActions
          v-if="!row.virtual"
          class="account-balance-table__actions"
          :no-edit="group && !isXpub(row)"
          :edit-tooltip="t('account_balances.edit_tooltip')"
          :disabled="accountOperation || row.virtual"
          @edit-click="editAccount(row)"
          @delete-click="confirmDelete(row)"
        />
      </div>
    </template>
    <template
      v-if="accounts.totalUsdValue"
      #body.append
    >
      <RowAppend
        :label="t('common.total')"
        :left-patch-colspan="1"
        :label-colspan="3"
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
    <template #expanded-item="{ row }">
      <slot
        name="details"
        :row="row"
      />
    </template>
    <template #item.expand="{ row }">
      <RuiTableRowExpander
        v-if="row.expandable"
        :expanded="isExpanded(row)"
        @click="expand(row)"
      />
    </template>
    <template #body.prepend="{ colspan }">
      <Eth2ValidatorLimitRow :colspan="colspan" />
    </template>
  </RuiDataTable>
</template>

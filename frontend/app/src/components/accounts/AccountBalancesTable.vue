<script setup lang="ts" generic="T extends BlockchainAccountWithBalance | BlockchainAccountGroupWithBalance">
import type { DataTableColumn, DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { BlockchainAccountGroupWithBalance, BlockchainAccountWithBalance } from '@/types/blockchain/accounts';
import type { Collection } from '@/types/collection';
import { type BigNumber, toSentenceCase } from '@rotki/common';
import { isEmpty } from 'es-toolkit/compat';
import AccountChains from '@/components/accounts/AccountChains.vue';
import AccountTopTokens from '@/components/accounts/AccountTopTokens.vue';
import TokenDetection from '@/components/accounts/blockchain/TokenDetection.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import LabeledAddressDisplay from '@/components/display/LabeledAddressDisplay.vue';
import RowActions from '@/components/helper/RowActions.vue';
import RowAppend from '@/components/helper/RowAppend.vue';
import TagDisplay from '@/components/tags/TagDisplay.vue';
import { useAccountDelete } from '@/composables/accounts/blockchain/use-account-delete';
import { useBlockchainAccountLoading } from '@/composables/accounts/blockchain/use-account-loading';
import { type AccountManageState, editBlockchainAccount } from '@/composables/accounts/blockchain/use-account-manage';
import { useAddressBookForm } from '@/composables/address-book/form';
import { useSupportedChains } from '@/composables/info/chains';
import { TableId, useRememberTableSorting } from '@/modules/table/use-remember-table-sorting';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useStatusStore } from '@/store/status';
import { useTaskStore } from '@/store/tasks';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { sum } from '@/utils/balances';
import { getAccountAddress, getAccountId, getChain, getGroupId } from '@/utils/blockchain/accounts/utils';

type DataRow = T & { id: string };

defineOptions({
  inheritAttrs: false,
});

const chainFilter = defineModel<Record<string, string[]>>('chainFilter', { default: {}, required: false });

const pagination = defineModel<TablePaginationData>('pagination', { required: true });

const sort = defineModel<DataTableSortData<T>>('sort', { required: true });

const expandedIds = defineModel<string[]>('expandedIds', { required: true });

const props = withDefaults(defineProps<{
  accounts: Collection<T>;
  group?: 'evm' | 'xpub';
  category: string;
}>(), {
  group: undefined,
});

const emit = defineEmits<{
  (e: 'edit', account: AccountManageState): void;
  (e: 'refresh'): void;
}>();

const { category } = toRefs(props);

const { t } = useI18n({ useScope: 'global' });

const collapsed = ref<DataRow[]>([]) as Ref<DataRow[]>;

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const { useIsTaskRunning } = useTaskStore();
const { isLoading } = useStatusStore();
const { supportsTransactions } = useSupportedChains();
const { showConfirmation } = useAccountDelete();

const { isSectionLoading } = useBlockchainAccountLoading(category);

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
    return get(rows).filter(row => get(expandedIds).includes(row.id) && row.expansion);
  },
  set(value: DataRow[]) {
    set(expandedIds, get(value).map(row => row.id));
  },
}));

const cols = computed<DataTableColumn<DataRow>[]>(() => {
  const currency = { symbol: get(currencySymbol) };
  const group = props.group;
  const headers: DataTableColumn<T>[] = [
    ...(get(anyExpansion)
      ? [{
          cellClass: '!py-0 !pr-0 !pl-3',
          class: '!py-0 !pr-0 !pl-3',
          key: 'expand',
          label: '',
          sortable: false,
        }]
      : []),
    ...(group
      ? [{
          cellClass: 'py-0 !px-3',
          class: '!px-3',
          key: 'label',
          label: t('common.account'),
          sortable: true,
        }]
      : []),
    ...(group !== 'xpub'
      ? [{
          cellClass: 'py-0 !pr-0',
          class: '!pr-0',
          key: 'chain',
          label: t('common.chain'),
          sortable: false,
        }]
      : []),
    ...(group === 'evm'
      ? [{
          cellClass: 'py-0',
          key: 'tags',
          label: t('common.tags'),
          sortable: false,
        }]
      : []),
    {
      align: 'end',
      cellClass: 'py-0 !pr-0 !pl-2',
      class: '!pr-0 !pl-2',
      key: 'assets',
      label: t('common.assets'),
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
      cellClass: '!p-0',
      key: 'actions',
      label: t('common.actions_text'),
    },
  ];

  return headers;
});

useRememberTableSorting<DataRow>(TableId.ACCOUNT_BALANCES, sort, cols);

const accountOperation = logicOr(
  useIsTaskRunning(TaskType.ADD_ACCOUNT),
  useIsTaskRunning(TaskType.REMOVE_ACCOUNT),
  isSectionLoading,
);

const isAnyLoading = logicOr(accountOperation, isSectionLoading);

function isRowLoading(row: DataRow) {
  if (row.type === 'account')
    return get(isLoading(Section.BLOCKCHAIN, row.chain));
  else
    return row.chains.some(chain => get(isLoading(Section.BLOCKCHAIN, chain)));
}

function getId(row: DataRow): string {
  return row.type === 'group' ? getGroupId(row) : getAccountId(row);
}

function isExpanded(row: DataRow) {
  const rowId = getId(row);
  return get(expanded).some(item => item.id === rowId);
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
    data: item,
    type: 'account',
  }, () => {
    emit('refresh');
  });
}

const { showGlobalDialog } = useAddressBookForm();

function edit(group: string, row: DataRow) {
  if (group === 'evm') {
    emit('edit', editBlockchainAccount(row));
  }
  else if (group === 'xpub') {
    const blockchain = getChain(row);
    if (blockchain) {
      showGlobalDialog({
        address: getAccountAddress(row),
        blockchain,
      });
    }
  }
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

function isVirtual(row: DataRow): boolean {
  return !!(('virtual' in row) && row.virtual);
}

function isOnlyShowingLoopringChain(row: DataRow): boolean {
  return ('chains' in row) && (row.chains.length === 1 && row.chains[0] === 'loopring');
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
        :row="row"
        :loading="isRowLoading(row)"
      />
    </template>
    <template #item.usdValue="{ row }">
      <div class="flex flex-col items-end justify-end">
        <div
          v-if="row.includedUsdValue && !isRowLoading(row)"
          class="text-xs"
        >
          <AmountDisplay
            v-if="row.includedUsdValue"
            fiat-currency="USD"
            :value="row.includedUsdValue"
            show-currency="symbol"
          />
          /
        </div>
        <AmountDisplay
          data-cy="usd-value"
          class="font-medium"
          fiat-currency="USD"
          :value="row.usdValue"
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
          :loading="isSectionLoading"
          :chain="row.type === 'group' ? row.chains[0] : row.chain"
        />
        <RowActions
          v-if="!isVirtual(row) && !isOnlyShowingLoopringChain(row)"
          class="account-balance-table__actions"
          :edit-tooltip="t('account_balances.edit_tooltip')"
          :disabled="accountOperation"
          @edit-click="edit(group, row)"
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
        :label-colspan="group && group === 'evm' ? 4 : 2"
        :is-mobile="false"
        class-name="[&>td]:p-4 text-sm"
      >
        <template #custom-columns>
          <td class="text-end">
            <AmountDisplay
              :loading="isSectionLoading"
              fiat-currency="USD"
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
            <RuiIcon :name="isOpen ? 'lu-chevron-up' : 'lu-chevron-down' " />
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
          fiat-currency="USD"
          :value="getCategoryTotal(header.group.category)"
          show-currency="symbol"
          :loading="isSectionLoading"
        />
      </td>
      <td />
    </template>
  </RuiDataTable>
</template>

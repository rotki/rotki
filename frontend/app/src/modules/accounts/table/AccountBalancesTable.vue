<script setup lang="ts" generic="T extends BlockchainAccountBalance">
import type { DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { AccountManageState } from '@/composables/accounts/blockchain/use-account-manage';
import type { BlockchainAccountBalance } from '@/types/blockchain/accounts';
import type { Collection } from '@/types/collection';
import AccountChains from '@/components/accounts/AccountChains.vue';
import AccountTopTokens from '@/components/accounts/AccountTopTokens.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import LabeledAddressDisplay from '@/components/display/LabeledAddressDisplay.vue';
import RowAppend from '@/components/helper/RowAppend.vue';
import TagDisplay from '@/components/tags/TagDisplay.vue';
import AccountTableGroupHeader from './components/AccountTableGroupHeader.vue';
import AccountActions from './components/table/AccountActions.vue';
import AccountBalanceValue from './components/table/AccountBalanceValue.vue';
import { useAccountLoadingStates } from './composables/use-account-loading-states';
import { useAccountOperations } from './composables/use-account-operations';
import { useAccountTableConfig } from './composables/use-account-table-config';
import { useAccountTableData } from './composables/use-account-table-data';

defineOptions({
  inheritAttrs: false,
});

const chainFilter = defineModel<Record<string, string[]>>('chainFilter', { default: {}, required: false });

const pagination = defineModel<TablePaginationData>('pagination', { required: true });

const sort = defineModel<DataTableSortData<T>>('sort', { required: true });

const expandedIds = defineModel<string[]>('expandedIds', { required: true });

const props = withDefaults(defineProps<{
  accounts: Collection<T>;
  category: string;
  group?: 'evm' | 'xpub';
}>(), {
  group: undefined,
});

const emit = defineEmits<{
  edit: [account: AccountManageState];
  refresh: [];
}>();

const { category } = toRefs(props);
const accounts = toRef(props, 'accounts');

const { t } = useI18n({ useScope: 'global' });

// Use composables
const { createColumns, initializeTableSorting } = useAccountTableConfig<T>();
const {
  anyExpansion,
  collapsed,
  expand,
  expanded,
  getCategoryTotal,
  getChains,
  isExpanded,
  isOnlyShowingLoopringChain,
  isVirtual,
  rows,
  totalValue,
} = useAccountTableData<T>(accounts, expandedIds, chainFilter);

const { accountOperation, isAnyLoading, isRowLoading, isSectionLoading } = useAccountLoadingStates<T>(category);

const { confirmDelete, edit } = useAccountOperations<T>({
  onEdit: account => emit('edit', account),
  onRefresh: () => emit('refresh'),
});

// Create columns
const cols = computed(() => createColumns(props.group, get(anyExpansion)));

// Initialize table sorting
initializeTableSorting(sort, cols);

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
        class="my-2"
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
    <template #item.value="{ row }">
      <AccountBalanceValue
        :included-value="row.includedValue"
        :value="row.value"
        :loading="isRowLoading(row)"
      />
    </template>
    <template #item.actions="{ row }">
      <AccountActions
        :row="row"
        :group="group"
        :account-operation="accountOperation"
        :is-section-loading="isSectionLoading"
        :is-virtual="isVirtual(row)"
        :is-only-showing-loopring-chain="isOnlyShowingLoopringChain(row)"
        @edit="edit(group, row)"
        @delete="confirmDelete($event)"
      />
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
              force-currency
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
      <AccountTableGroupHeader
        :category="header.group.category || ''"
        :category-total="getCategoryTotal(header.group.category || '')"
        :colspan="colspan"
        :is-open="isOpen"
        :is-section-loading="isSectionLoading"
        @toggle="toggle()"
      />
    </template>
  </RuiDataTable>
</template>

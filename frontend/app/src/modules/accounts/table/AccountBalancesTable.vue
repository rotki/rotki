<script setup lang="ts" generic="T extends BlockchainAccountBalance">
import type { DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { AccountDataRow } from './types';
import type { BlockchainAccountBalance } from '@/modules/accounts/blockchain-accounts';
import type { AccountManageState } from '@/modules/accounts/blockchain/use-account-manage';
import type { Collection } from '@/modules/core/common/collection';
import { getAccountAddress, getAccountLabel } from '@/modules/accounts/account-utils';
import AccountChains from '@/modules/accounts/AccountChains.vue';
import AccountTopTokens from '@/modules/accounts/AccountTopTokens.vue';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import { useTableEmptyState, useTableFetchError } from '@/modules/core/table/use-table-empty-state';
import LabeledAddressDisplay from '@/modules/shell/components/display/LabeledAddressDisplay.vue';
import RowAppend from '@/modules/shell/components/RowAppend.vue';
import TagDisplay from '@/modules/tags/TagDisplay.vue';
import AccountTableGroupHeader from './components/AccountTableGroupHeader.vue';
import AccountActions from './components/table/AccountActions.vue';
import AccountBalanceValue from './components/table/AccountBalanceValue.vue';
import { useAccountLoadingStates } from './use-account-loading-states';
import { useAccountOperations } from './use-account-operations';
import { useAccountTableConfig } from './use-account-table-config';
import { useAccountTableData } from './use-account-table-data';

defineOptions({
  inheritAttrs: false,
});

const chainFilter = defineModel<Record<string, string[]>>('chainFilter', { default: () => ({}), required: false });

const pagination = defineModel<TablePaginationData>('pagination', { required: true });

const sort = defineModel<DataTableSortData<T>>('sort', { required: true });

const expandedIds = defineModel<string[]>('expandedIds', { default: () => [], required: false });

const { accounts, category, detailsInDrawer = false, fetching = false, framed = false, group } = defineProps<{
  accounts: Collection<T>;
  category: string;
  group?: 'evm' | 'xpub';
  /** Sits in a TableFrame, which draws the border, so the table leaves its own outline off. */
  framed?: boolean;
  /** The page is still being fetched: with no rows yet, the table shows loading rather than its empty state. */
  fetching?: boolean;
  /** Every row opens its details elsewhere (`open-details`) instead of expanding in place. */
  detailsInDrawer?: boolean;
}>();

const emit = defineEmits<{
  'edit': [account: AccountManageState];
  'refresh': [];
  'open-details': [row: T];
}>();

const slots = defineSlots<{
  /** Inline expansion content; unused when `detailsInDrawer` is set. */
  details?: (props: { row: T }) => any;
  /** Replaces the generic empty text, unless the fetch failed: that shows its own message. */
  empty?: () => any;
}>();

const { t } = useI18n({ useScope: 'global' });

const emptyState = useTableEmptyState();
const fetchError = useTableFetchError();
/** A failed fetch is not something adding an account or clearing filters would fix. */
const showEmptySlot = computed<boolean>(() => !!slots.empty && !(fetchError && get(fetchError)));

const { createColumns, initializeTableSorting } = useAccountTableConfig<T>();
const {
  anyExpansion,
  collapsed,
  expand,
  expanded,
  getCategoryTotal,
  getChains,
  isExpanded,
  rows,
  totalValue,
} = useAccountTableData<T>(() => accounts, expandedIds, chainFilter);

const { accountOperation, isInitialLoading, isRowLoading, isSectionLoading } = useAccountLoadingStates<T>(() => category);

const { confirmDelete, deleteAccount, edit } = useAccountOperations<T>({
  onEdit: account => emit('edit', account),
  onRefresh: () => emit('refresh'),
});

const expandsInline = computed<boolean>(() => !detailsInDrawer && get(anyExpansion));

/** The first column holds the expander inline, or the open-details button for every row. */
const hasLeadColumn = computed<boolean>(() => detailsInDrawer || get(anyExpansion));

const cols = computed(() => createColumns(group, get(hasLeadColumn)));

initializeTableSorting(sort, cols);

/** The category a table group header stands for; only group rows carry one. */
function headerCategory(group: Partial<AccountDataRow<T>>): string {
  return 'category' in group && typeof group.category === 'string' ? group.category : '';
}

defineExpose({
  confirmDelete,
});
</script>

<template>
  <RuiDataTable
    v-bind="$attrs"
    v-model:sort.external="sort"
    v-model:pagination.external="pagination"
    v-model:collapsed="collapsed"
    :expanded="expandsInline ? expanded : undefined"
    :cols="cols"
    :rows="rows"
    :loading="(group && isInitialLoading) || (fetching && accounts.data.length === 0)"
    row-attr="id"
    :empty="emptyState"
    :loading-text="t('account_balances.data_table.loading')"
    data-testid="account-table"
    single-expand
    :outlined="!framed"
    sticky-header
    dense
    @update:expanded="expanded = $event ?? []"
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
        :address="getAccountAddress(row)"
        :row="row"
      />
    </template>
    <template #item.tags="{ row }">
      <TagDisplay
        :tags="row.tags"
        class="mt-0!"
        small
      />
    </template>
    <template #item.assets="{ row }">
      <AccountTopTokens
        :chains="getChains(row)"
        :row="row"
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
        @edit="edit(group, row)"
        @delete="deleteAccount($event)"
      />
    </template>
    <template
      v-if="totalValue && accounts.data.length > 0"
      #body.append
    >
      <RowAppend
        :label="t('common.total')"
        :left-patch-colspan="hasLeadColumn ? 1 : 0"
        :label-colspan="group && group === 'evm' ? 4 : 2"
        :is-mobile="false"
        variant="fixed"
      >
        <template #custom-columns>
          <td class="text-end">
            <FiatDisplay
              :value="totalValue"
              :loading="isSectionLoading"
            />
          </td>
        </template>
      </RowAppend>
    </template>
    <template
      v-if="expandsInline"
      #expanded-item="{ row }"
    >
      <slot
        name="details"
        :row="row"
      />
    </template>
    <template #item.expand="{ row }">
      <RuiButton
        v-if="detailsInDrawer"
        variant="text"
        icon
        size="sm"
        data-id="expand-button"
        data-testid="account-open-details"
        data-account-details-opener
        :aria-label="t('account_balances.open_details', { account: getAccountLabel(row) })"
        @click="emit('open-details', row)"
      >
        <RuiIcon
          name="lu-chevron-right"
          size="18"
        />
      </RuiButton>
      <RuiTableRowExpander
        v-else-if="row.expansion"
        :expanded="isExpanded(row)"
        @click="expand(row)"
      />
    </template>
    <template #group.header="{ header, isOpen, toggle, colspan }">
      <AccountTableGroupHeader
        :category="headerCategory(header.group)"
        :category-total="getCategoryTotal(headerCategory(header.group))"
        :colspan="colspan"
        :is-open="isOpen"
        :is-section-loading="isSectionLoading"
        @toggle="toggle()"
      />
    </template>
    <template
      v-if="showEmptySlot"
      #no-data
    >
      <slot name="empty" />
    </template>
  </RuiDataTable>
</template>

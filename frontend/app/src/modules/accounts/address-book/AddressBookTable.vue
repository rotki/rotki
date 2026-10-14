<script setup lang="ts">
import type { DataTableColumn, DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { AddressBookEntry, AddressBookLocation } from '@/modules/accounts/address-book/eth-names';
import type { Collection } from '@/modules/core/common/collection';
import { useAddressBookDeletion } from '@/modules/accounts/address-book/use-address-book-deletion';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import { type TableEmptyState, useTableEmptyState } from '@/modules/core/table/use-table-empty-state';
import AccountDisplay from '@/modules/shell/components/display/AccountDisplay.vue';
import RowActions from '@/modules/shell/components/RowActions.vue';

const paginationModel = defineModel<TablePaginationData>('pagination', { required: true });

const sortModel = defineModel<DataTableSortData<AddressBookEntry>>('sort', { required: true });

const { collection, filtered = false, location, loading } = defineProps<{
  collection: Collection<AddressBookEntry>;
  /** Whether a filter or chain narrows the rows, so an empty table means no match rather than no entries. */
  filtered?: boolean;
  location: AddressBookLocation;
  loading: boolean;
}>();

const emit = defineEmits<{
  edit: [item: AddressBookEntry];
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });

// says why there are no rows: nothing matches the filter, or the private book has nothing in it yet
const emptyState = useTableEmptyState({
  fallback: (): TableEmptyState => {
    if (filtered)
      return { description: t('address_book.empty.filtered_description'), label: t('address_book.empty.filtered') };
    if (location === 'private')
      return { description: t('address_book.empty.private_description'), label: t('address_book.empty.private') };
    return { description: t('data_table.no_data') };
  },
});

// whole addresses where they fit; shortened on a phone, where they push the name out of view
const { isMdAndUp } = useBreakpoint();

const cols = computed<DataTableColumn<AddressBookEntry>[]>(() => [
  {
    key: 'address',
    label: t('common.address'),
    sortable: true,
  },
  {
    key: 'name',
    label: t('common.name'),
    sortable: true,
  },
  {
    align: 'end',
    key: 'actions',
    label: '',
  },
]);

useRememberTableSorting<AddressBookEntry>(TableId.ADDRESS_BOOK, sortModel, cols);

function refresh() {
  emit('refresh');
}

function edit(item: AddressBookEntry) {
  emit('edit', item);
}

// a getter, as the one table now switches between the books and must delete from the one in view
const { showDeleteConfirmation } = useAddressBookDeletion(toRef(() => location), refresh);
</script>

<template>
  <RuiDataTable
    v-model:pagination.external="paginationModel"
    v-model:sort.external="sortModel"
    :rows="collection.data"
    :cols="cols"
    :empty="emptyState"
    :loading="loading"
    row-attr="address"
    dense
    data-testid="address-book-table"
  >
    <template #item.address="{ row }">
      <AccountDisplay
        :account="{
          address: row.address,
          chain: row.blockchain ?? 'ALL',
        }"
        :use-alias-name="false"
        :no-truncate="isMdAndUp"
      />
    </template>
    <template #item.name="{ row }">
      <span
        v-if="row.name"
        class="text-rui-text"
      >
        {{ row.name }}
      </span>
      <span
        v-else
        class="text-rui-text-disabled"
      >
        {{ t('address_book.no_name') }}
      </span>
    </template>
    <template #item.actions="{ row }">
      <RowActions
        align="end"
        :disabled="loading"
        :delete-tooltip="t('address_book.actions.delete.tooltip')"
        :edit-tooltip="t('address_book.actions.edit.tooltip')"
        @delete-click="showDeleteConfirmation(row)"
        @edit-click="edit(row)"
      />
    </template>
  </RuiDataTable>
</template>

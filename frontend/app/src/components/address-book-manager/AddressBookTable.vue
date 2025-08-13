<script setup lang="ts">
import type { DataTableColumn, DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { Collection } from '@/types/collection';
import type { AddressBookEntry, AddressBookLocation } from '@/types/eth-names';
import AccountDisplay from '@/components/display/AccountDisplay.vue';
import CollectionHandler from '@/components/helper/CollectionHandler.vue';
import RowActions from '@/components/helper/RowActions.vue';
import { useAddressBookDeletion } from '@/composables/address-book/use-address-book-deletion';
import { TableId, useRememberTableSorting } from '@/modules/table/use-remember-table-sorting';

const paginationModel = defineModel<TablePaginationData>('pagination', { required: true });

const sortModel = defineModel<DataTableSortData<AddressBookEntry>>('sort', { required: true });

const props = defineProps<{
  collection: Collection<AddressBookEntry>;
  location: AddressBookLocation;
  loading: boolean;
}>();

const emit = defineEmits<{
  (e: 'edit', item: AddressBookEntry): void;
  (e: 'refresh'): void;
}>();

const { location } = toRefs(props);

const { t } = useI18n({ useScope: 'global' });

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

function setPage(page: number) {
  set(paginationModel, {
    ...get(paginationModel),
    page,
  });
}

const { showDeleteConfirmation } = useAddressBookDeletion(location, refresh);
</script>

<template>
  <div>
    <CollectionHandler
      :collection="collection"
      @set-page="setPage($event)"
    >
      <template #default="{ data }">
        <RuiDataTable
          v-model:pagination.external="paginationModel"
          v-model:sort.external="sortModel"
          :rows="data"
          :cols="cols"
          :loading="loading"
          row-attr="address"
          outlined
          dense
        >
          <template #item.address="{ row }">
            <AccountDisplay
              :account="{
                address: row.address,
                chain: row.blockchain ?? 'ALL',
              }"
              :use-alias-name="false"
              :truncate="false"
            />
          </template>
          <template #item.actions="{ row }">
            <RowActions
              :disabled="loading"
              :delete-tooltip="t('address_book.actions.delete.tooltip')"
              :edit-tooltip="t('address_book.actions.edit.tooltip')"
              @delete-click="showDeleteConfirmation(row)"
              @edit-click="edit(row)"
            />
          </template>
        </RuiDataTable>
      </template>
    </CollectionHandler>
  </div>
</template>

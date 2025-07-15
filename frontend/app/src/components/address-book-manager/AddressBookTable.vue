<script setup lang="ts">
import type { DataTableColumn, DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { Collection } from '@/types/collection';
import type { AddressBookEntry, AddressBookLocation } from '@/types/eth-names';
import { NotificationCategory, type NotificationPayload, Severity } from '@rotki/common';
import AccountDisplay from '@/components/display/AccountDisplay.vue';
import CollectionHandler from '@/components/helper/CollectionHandler.vue';
import RowActions from '@/components/helper/RowActions.vue';
import { TableId, useRememberTableSorting } from '@/modules/table/use-remember-table-sorting';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';
import { useConfirmStore } from '@/store/confirm';
import { useNotificationsStore } from '@/store/notifications';

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

function addressBookDeletion(location: Ref<AddressBookLocation>) {
  const { show } = useConfirmStore();
  const { notify } = useNotificationsStore();
  const { deleteAddressBook: deleteAddressBookCaller } = useAddressesNamesStore();

  const deleteAddressBook = async (address: string, blockchain: string | null) => {
    try {
      await deleteAddressBookCaller(get(location), [{ address, blockchain }]);
      refresh();
    }
    catch (error: any) {
      const notification: NotificationPayload = {
        category: NotificationCategory.DEFAULT,
        display: true,
        message: t('address_book.actions.delete.error.description', {
          address,
          chain: blockchain || t('common.multi_chain'),
          message: error.message,
        }),
        severity: Severity.ERROR,
        title: t('address_book.actions.delete.error.title'),
      };
      notify(notification);
    }
  };

  const showDeleteConfirmation = (item: AddressBookEntry) => {
    show(
      {
        message: t('address_book.actions.delete.dialog.message', {
          address: item.address,
          chain: item.blockchain || t('common.multi_chain'),
        }),
        title: t('address_book.actions.delete.dialog.title'),
      },
      () => deleteAddressBook(item.address, item.blockchain),
    );
  };

  return {
    showDeleteConfirmation,
  };
}

const { showDeleteConfirmation } = addressBookDeletion(location);
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

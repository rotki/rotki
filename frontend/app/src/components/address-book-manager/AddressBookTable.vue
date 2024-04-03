<script setup lang="ts">
import {
  NotificationCategory,
  type NotificationPayload,
  Severity,
} from '@rotki/common/lib/messages';
import type {
  DataTableColumn,
  DataTableOptions,
} from '@rotki/ui-library-compat';
import type {
  AddressBookEntry,
  AddressBookLocation,
} from '@/types/eth-names';
import type { Collection } from '@/types/collection';
import type { TablePagination } from '@/types/pagination';

const props = defineProps<{
  collection: Collection<AddressBookEntry>;
  location: AddressBookLocation;
  loading: boolean;
  options: TablePagination<AddressBookEntry>;
}>();

const emit = defineEmits<{
  (e: 'edit', item: AddressBookEntry): void;
  (e: 'update:page', page: number): void;
  (e: 'update:options', pagination: DataTableOptions): void;
  (e: 'refresh'): void;
}>();

const { t } = useI18n();

function setPage(page: number) {
  emit('update:page', page);
}

function updatePagination(pagination: DataTableOptions) {
  return emit('update:options', pagination);
}

function refresh() {
  emit('refresh');
}

function addressBookDeletion(location: Ref<AddressBookLocation>) {
  const { show } = useConfirmStore();
  const { notify } = useNotificationsStore();
  const { deleteAddressBook: deleteAddressBookCaller } = useAddressesNamesStore();

  const deleteAddressBook = async (
    address: string,
    blockchain: string | null,
  ) => {
    try {
      await deleteAddressBookCaller(get(location), [{ address, blockchain }]);
      refresh();
    }
    catch (error: any) {
      const notification: NotificationPayload = {
        title: t('address_book.actions.delete.error.title'),
        message: t('address_book.actions.delete.error.description', {
          chain: blockchain || t('common.multi_chain'),
          address,
          message: error.message,
        }).toString(),
        category: NotificationCategory.DEFAULT,
        display: true,
        severity: Severity.ERROR,
      };
      notify(notification);
    }
  };

  const showDeleteConfirmation = (item: AddressBookEntry) => {
    show(
      {
        title: t('address_book.actions.delete.dialog.title'),
        message: t('address_book.actions.delete.dialog.message', {
          chain: item.blockchain || t('common.multi_chain'),
          address: item.address,
        }),
      },
      () => deleteAddressBook(item.address, item.blockchain),
    );
  };

  return {
    showDeleteConfirmation,
  };
}

const { location } = toRefs(props);

function edit(item: AddressBookEntry) {
  emit('edit', item);
}

const tableHeaders = computed<DataTableColumn[]>(() => [
  {
    label: t('common.address').toString(),
    key: 'address',
    sortable: false,
  },
  {
    label: t('common.name').toString(),
    key: 'name',
    sortable: false,
  },
  {
    label: '',
    key: 'actions',
    sortable: false,
  },
]);

const { showDeleteConfirmation } = addressBookDeletion(location);
</script>

<template>
  <div>
    <CollectionHandler
      :collection="collection"
      @set-page="setPage($event)"
    >
      <template #default="{ data, itemLength }">
        <RuiDataTable
          :rows="data"
          :cols="tableHeaders"
          :loading="loading"
          :options="options"
          :pagination="{
            limit: options.itemsPerPage,
            page: options.page,
            total: itemLength,
          }"
          :pagination-modifiers="{ external: true }"
          row-attr=""
          outlined
          :server-items-length="itemLength"
          @update:options="updatePagination($event)"
        >
          <template #item.address="{ row }">
            <AccountDisplay
              :account="{
                address: row.address,
                chain: row.blockchain,
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

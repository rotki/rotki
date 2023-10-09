<script setup lang="ts">
import {
  NotificationCategory,
  type NotificationPayload,
  Severity
} from '@rotki/common/lib/messages';
import { type Ref } from 'vue';
import { type Blockchain } from '@rotki/common/lib/blockchain';
import { type DataTableHeader } from '@/types/vuetify';
import {
  type AddressBookEntry,
  type AddressBookLocation,
  type AddressBookRequestPayload
} from '@/types/eth-names';
import { type Collection } from '@/types/collection';
import { type TablePagination } from '@/types/pagination';

const props = defineProps<{
  collection: Collection<AddressBookEntry>;
  location: AddressBookLocation;
  loading: boolean;
  options: TablePagination<AddressBookEntry>;
}>();

const emit = defineEmits<{
  (e: 'edit', item: AddressBookEntry): void;
  (e: 'update:page', page: number): void;
  (e: 'update:options', pagination: AddressBookRequestPayload): void;
  (e: 'refresh'): void;
}>();

const { t } = useI18n();

const setPage = (page: number) => {
  emit('update:page', page);
};

const updatePagination = (pagination: AddressBookRequestPayload) =>
  emit('update:options', pagination);

const refresh = () => {
  emit('refresh');
};

const addressBookDeletion = (location: Ref<AddressBookLocation>) => {
  const { show } = useConfirmStore();
  const { notify } = useNotificationsStore();
  const { deleteAddressBook: deleteAddressBookCaller } =
    useAddressesNamesStore();

  const deleteAddressBook = async (
    address: string,
    blockchain: Blockchain | null
  ) => {
    try {
      await deleteAddressBookCaller(get(location), [{ address, blockchain }]);
      refresh();
    } catch (e: any) {
      const notification: NotificationPayload = {
        title: t('address_book.actions.delete.error.title'),
        message: t('address_book.actions.delete.error.description', {
          chain: blockchain || t('common.multi_chain'),
          address,
          message: e.message
        }).toString(),
        category: NotificationCategory.DEFAULT,
        display: true,
        severity: Severity.ERROR
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
          address: item.address
        })
      },
      () => deleteAddressBook(item.address, item.blockchain)
    );
  };

  return {
    showDeleteConfirmation
  };
};

const { location } = toRefs(props);

const edit = (item: AddressBookEntry) => {
  emit('edit', item);
};

const tableHeaders = computed<DataTableHeader[]>(() => [
  {
    text: t('common.address').toString(),
    value: 'address'
  },
  {
    text: t('common.name').toString(),
    value: 'name'
  },
  {
    text: '',
    value: 'actions',
    sortable: false
  }
]);

const { showDeleteConfirmation } = addressBookDeletion(location);
</script>

<template>
  <div>
    <CollectionHandler :collection="collection" @set-page="setPage($event)">
      <template #default="{ data, itemLength }">
        <DataTable
          :items="data"
          :headers="tableHeaders"
          :loading="loading"
          :options="options"
          :server-items-length="itemLength"
          @update:options="updatePagination($event)"
        >
          <template #item.address="{ item }">
            <AccountDisplay
              :account="{
                address: item.address,
                chain: item.blockchain
              }"
              :use-alias-name="false"
              :truncate="false"
            />
          </template>
          <template #item.actions="{ item }">
            <RowActions
              :disabled="loading"
              :delete-tooltip="t('address_book.actions.delete.tooltip')"
              :edit-tooltip="t('address_book.actions.edit.tooltip')"
              @delete-click="showDeleteConfirmation(item)"
              @edit-click="edit(item)"
            />
          </template>
        </DataTable>
      </template>
    </CollectionHandler>
  </div>
</template>

<script setup lang="ts">
import { type NotificationPayload, Severity } from '@rotki/common/lib/messages';
import { type PropType, type Ref } from 'vue';
import { type DataTableHeader } from 'vuetify';
import RowActions from '@/components/helper/RowActions.vue';
import { useEthNamesStore } from '@/store/balances/ethereum-names';
import { useNotificationsStore } from '@/store/notifications';
import {
  type EthAddressBookLocation,
  type EthNamesEntries,
  type EthNamesEntry
} from '@/types/eth-names';
import { useConfirmStore } from '@/store/confirm';

const addressBookDeletion = (location: Ref<EthAddressBookLocation>) => {
  const { show } = useConfirmStore();

  const { tc } = useI18n();
  const { notify } = useNotificationsStore();
  const { deleteEthAddressBook } = useEthNamesStore();

  const deleteAddressBook = async (address: string) => {
    try {
      await deleteEthAddressBook(get(location), [address]);
    } catch (e: any) {
      const notification: NotificationPayload = {
        title: tc('eth_address_book.actions.delete.error.title'),
        message: tc('eth_address_book.actions.delete.error.description', 0, {
          message: e.message
        }).toString(),
        display: true,
        severity: Severity.ERROR
      };
      notify(notification);
    }
  };

  const showDeleteConfirmation = (item: EthNamesEntry) => {
    show(
      {
        title: tc('eth_address_book.actions.delete.dialog.title'),
        message: tc('eth_address_book.actions.delete.dialog.message')
      },
      () => deleteAddressBook(item.address)
    );
  };

  return {
    showDeleteConfirmation
  };
};

const props = defineProps({
  location: {
    required: true,
    type: String as PropType<EthAddressBookLocation>
  },
  search: { required: false, type: String, default: '' }
});

const emit = defineEmits<{
  (e: 'edit', item: EthNamesEntry): void;
}>();

const { location, search } = toRefs(props);
const ethNamesStore = useEthNamesStore();
const { fetchEthAddressBook } = ethNamesStore;
const { ethAddressBook } = toRefs(ethNamesStore);
const loading = ref<boolean>(false);

const { t, tc } = useI18n();

const data = computed<EthNamesEntries>(() => {
  return get(ethAddressBook)[get(location)];
});

const filteredData = computed<EthNamesEntries>(() => {
  if (!get(search)) return get(data);
  const keyword = get(search).toLowerCase();
  return get(data).filter(
    item =>
      item.address.includes(keyword) ||
      item.name.toLowerCase().includes(keyword)
  );
});

const edit = (item: EthNamesEntry) => {
  emit('edit', item);
};

onBeforeMount(async () => {
  set(loading, true);
  await fetchEthAddressBook(get(location));
  set(loading, false);
});

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
    <data-table
      :items="filteredData"
      :headers="tableHeaders"
      :loading="loading"
    >
      <template #item.actions="{ item }">
        <row-actions
          :disabled="loading"
          :delete-tooltip="tc('eth_address_book.actions.delete.tooltip')"
          :edit-tooltip="tc('eth_address_book.actions.edit.tooltip')"
          @delete-click="showDeleteConfirmation(item)"
          @edit-click="edit(item)"
        />
      </template>
    </data-table>
  </div>
</template>

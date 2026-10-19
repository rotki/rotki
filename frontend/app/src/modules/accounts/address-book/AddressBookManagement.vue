<script setup lang="ts">
import type {
  AddressBookEntry,
  AddressBookLocation,
  AddressBookPayload,
  AddressBookRequestPayload,
} from '@/modules/accounts/address-book/eth-names';
import AddressBookFormDialog from '@/modules/accounts/address-book/AddressBookFormDialog.vue';
import AddressBookManagementMore from '@/modules/accounts/address-book/AddressBookManagementMore.vue';
import AddressBookTable from '@/modules/accounts/address-book/AddressBookTable.vue';
import EthNamesHint from '@/modules/accounts/address-book/EthNamesHint.vue';
import { useAddressBookFields } from '@/modules/accounts/address-book/use-address-book-fields';
import { addressBookChainParams, type Filters } from '@/modules/accounts/address-book/use-address-book-filter';
import { useAddressBookOperations } from '@/modules/accounts/address-book/use-address-book-operations';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import { useCommonTableProps } from '@/modules/core/table/use-common-table-props';
import { useServerTable } from '@/modules/core/table/use-server-table';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

/** The book in view; the page keeps it in the route. */
const location = defineModel<AddressBookLocation>('location', { default: 'global', required: false });

const { t } = useI18n({ useScope: 'global' });

const selectedChain = ref<string>();
const strictBlockchain = ref<boolean>(false);

const locations: AddressBookLocation[] = ['global', 'private'];

const { editableItem, openDialog } = useCommonTableProps<AddressBookPayload>();

const { getAddressBook } = useAddressBookOperations();

const fields = useAddressBookFields();
const pillLabels = usePillBarLabels();

const { pillParams, source: chainSource } = addressBookChainParams(selectedChain, strictBlockchain);

const {
  collection: state,
  filter: filters,
  isLoading,
  pagination,
  refetch: fetchData,
  sort,
} = useServerTable<
  AddressBookEntry,
  AddressBookRequestPayload,
  Filters
>({
  fetch: filter => getAddressBook(get(location), get(filter)),
  fields,
  params: [chainSource],
  sort: {
    default: [{
      column: 'name',
      direction: 'asc',
    }],
  },
  urlState: { mode: 'route' },
});

/** Whether a filled pill or a chain narrows the rows; a pill still waiting for its value does not. */
const filtered = computed<boolean>(() => !!get(selectedChain)
  || Object.values(get(filters)).some(value => (Array.isArray(value) ? value.length > 0 : !!value)));

function add(): void {
  set(editableItem, null);
  set(openDialog, true);
}

function edit(item: AddressBookEntry): void {
  set(editableItem, {
    ...item,
    location: get(location),
  });
  set(openDialog, true);
}

watchImmediate(location, async () => {
  await fetchData();
});
</script>

<template>
  <TablePageLayout :title="[t('navigation_menu.manage_address_book')]">
    <template #buttons>
      <AddressBookManagementMore @refresh="fetchData()" />
      <RuiButton
        color="primary"
        data-testid="address-book-add"
        @click="add()"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('address_book.dialog.add_title') }}
      </RuiButton>
    </template>

    <TableFrame>
      <template #toolbar>
        <RuiTabs
          v-model="location"
          variant="segmented"
          color="primary"
          data-testid="address-book-scope-tabs"
        >
          <RuiTab
            v-for="loc in locations"
            :key="loc"
            :value="loc"
            class="capitalize"
            data-testid="address-book-scope-tab"
            :data-key="loc"
          >
            {{ loc }}
          </RuiTab>
        </RuiTabs>
        <EthNamesHint />
        <PillFilterBar
          v-model:matches="filters"
          v-model:params="pillParams"
          class="flex-1 min-w-48 md:min-w-96"
          :fields="fields"
          :labels="pillLabels"
        />
      </template>

      <AddressBookTable
        v-model:sort="sort"
        v-model:pagination="pagination"
        :collection="state"
        :filtered="filtered"
        :location="location"
        :loading="isLoading"
        @edit="edit($event)"
        @refresh="fetchData()"
      />
    </TableFrame>

    <AddressBookFormDialog
      v-model:open="openDialog"
      v-model:location="location"
      :editable-item="editableItem"
      :edit-mode="!!editableItem"
      :selected-chain="selectedChain"
      @refresh="fetchData()"
    />
  </TablePageLayout>
</template>

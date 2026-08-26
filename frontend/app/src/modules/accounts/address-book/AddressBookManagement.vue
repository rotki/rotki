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
import { useCommonTableProps } from '@/modules/core/table/use-common-table-props';
import { useServerTable } from '@/modules/core/table/use-server-table';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

const { t } = useI18n({ useScope: 'global' });

const selectedChain = ref<string>();
const strictBlockchain = ref<boolean>(false);
const tab = ref<number>(0);

const locations: AddressBookLocation[] = ['global', 'private'];

const location = computed<AddressBookLocation>(() => locations[get(tab)]);

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
  <TablePageLayout
    class="p-4"
    :title="[t('navigation_menu.manage_address_book')]"
  >
    <template #buttons>
      <RuiButton
        color="primary"
        size="lg"
        data-testid="address-book-add"
        @click="add()"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('address_book.dialog.add_title') }}
      </RuiButton>
      <AddressBookManagementMore @refresh="fetchData()" />
    </template>

    <RuiCard>
      <!-- The tabs are the scope the bar filters within, so they come first and share its row: the
           bar used to sit above them, which read as filtering the tab strip itself. -->
      <div class="flex flex-wrap items-center gap-4 mb-3">
        <div class="flex items-center gap-2">
          <RuiTabs
            v-model="tab"
            color="primary"
            class="border border-default rounded bg-white dark:bg-rui-grey-900 flex max-w-min"
            data-testid="address-book-scope-tabs"
          >
            <RuiTab
              v-for="loc in locations"
              :key="loc"
              class="capitalize"
              data-testid="address-book-scope-tab"
              :data-key="loc"
            >
              {{ loc }}
            </RuiTab>
          </RuiTabs>
          <EthNamesHint with-header />
        </div>

        <PillFilterBar
          v-model:matches="filters"
          v-model:params="pillParams"
          class="flex-1"
          :fields="fields"
          :labels="pillLabels"
        />
      </div>

      <RuiTabItems v-model="tab">
        <RuiTabItem
          v-for="loc in locations"
          :key="loc"
        >
          <template #default>
            <AddressBookTable
              v-model:sort="sort"
              v-model:pagination="pagination"
              :collection="state"
              :location="loc"
              :loading="isLoading"
              :blockchain="selectedChain"
              @edit="edit($event)"
              @refresh="fetchData()"
            />
          </template>
        </RuiTabItem>
      </RuiTabItems>
    </RuiCard>

    <AddressBookFormDialog
      v-model:open="openDialog"
      :editable-item="editableItem"
      :edit-mode="!!editableItem"
      :selected-chain="selectedChain"
      :location="location"
      @update-tab="tab = $event"
      @refresh="fetchData()"
    />
  </TablePageLayout>
</template>

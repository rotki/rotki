<script setup lang="ts">
import type {
  AddressBookEntry,
  AddressBookLocation,
  AddressBookPayload,
  AddressBookRequestPayload,
} from '@/types/eth-names';
import ChainSelect from '@/components/accounts/blockchain/ChainSelect.vue';
import AddressBookFormDialog from '@/components/address-book-manager/AddressBookFormDialog.vue';
import AddressBookManagementMore from '@/components/address-book-manager/AddressBookManagementMore.vue';
import AddressBookTable from '@/components/address-book-manager/AddressBookTable.vue';
import EthNamesHint from '@/components/EthNamesHint.vue';
import TableStatusFilter from '@/components/helper/TableStatusFilter.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import TableFilter from '@/components/table-filter/TableFilter.vue';
import { type Filters, type Matcher, useAddressBookFilter } from '@/composables/filters/address-book';
import { usePaginationFilters } from '@/composables/use-pagination-filter';
import { useCommonTableProps } from '@/modules/table/use-common-table-props';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';

const { t } = useI18n({ useScope: 'global' });

const selectedChain = ref<string>();
const strictBlockchain = ref<boolean>(true);
const tab = ref<number>(0);

const locations: AddressBookLocation[] = ['global', 'private'];

const location = computed<AddressBookLocation>(() => locations[get(tab)]);

const { editableItem, openDialog } = useCommonTableProps<AddressBookPayload>();

const { getAddressBook } = useAddressesNamesStore();

const {
  fetchData,
  filters,
  isLoading,
  matchers,
  pagination,
  sort,
  state,
} = usePaginationFilters<
  AddressBookEntry,
  AddressBookRequestPayload,
  Filters,
  Matcher
>(filter => getAddressBook(get(location), filter), {
  defaultSortBy: [{
    column: 'name',
    direction: 'asc',
  }],
  extraParams: computed(() => ({
    blockchain: get(selectedChain),
    strictBlockchain: get(strictBlockchain),
  })),
  filterSchema: useAddressBookFilter,
  history: 'router',
});

function add() {
  set(editableItem, null);
  set(openDialog, true);
}

function edit(item: AddressBookEntry) {
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
      <div class="flex flex-col md:flex-row items-stretch md:items-center justify-end gap-3">
        <div class="flex gap-3 w-full lg:w-[24rem]">
          <TableStatusFilter>
            <div class="p-1 max-w-[20rem] pb-4">
              <RuiCheckbox
                v-model="strictBlockchain"
                color="primary"
                class="px-3 mt-0"
                :label="t('address_book.strict_blockchain_filter.label')"
                :hint="t('address_book.strict_blockchain_filter.hint')"
              />
            </div>
          </TableStatusFilter>

          <ChainSelect
            v-model="selectedChain"
            hide-details
            clearable
            dense
            exclude-eth-staking
          />
        </div>

        <div class="w-full lg:w-[26rem]">
          <TableFilter
            v-model:matches="filters"
            :matchers="matchers"
          />
        </div>
      </div>

      <div class="flex flex-row items-center gap-2 my-3">
        <RuiTabs
          v-model="tab"
          color="primary"
          class="border border-default rounded bg-white dark:bg-rui-grey-900 flex max-w-min"
        >
          <RuiTab
            v-for="loc in locations"
            :key="loc"
            class="capitalize"
          >
            {{ loc }}
          </RuiTab>
        </RuiTabs>
        <EthNamesHint with-header />
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
      :selected-chain="selectedChain"
      :location="location"
      @update-tab="tab = $event"
      @refresh="fetchData()"
    />
  </TablePageLayout>
</template>

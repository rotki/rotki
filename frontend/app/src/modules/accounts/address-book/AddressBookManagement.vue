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
import { useAddressBookOperations } from '@/modules/accounts/address-book/use-address-book-operations';
import ChainSelect from '@/modules/accounts/blockchain/ChainSelect.vue';
import { type Filters, type Matcher, useAddressBookFilter } from '@/modules/core/table/filters/use-address-book-filter';
import TableFilter from '@/modules/core/table/TableFilter.vue';
import TableStatusFilter from '@/modules/core/table/TableStatusFilter.vue';
import { useCommonTableProps } from '@/modules/core/table/use-common-table-props';
import { usePaginationFilters } from '@/modules/core/table/use-pagination-filter';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

const { t } = useI18n({ useScope: 'global' });

const selectedChain = ref<string>();
const strictBlockchain = ref<boolean>(false);
const tab = ref<number>(0);

const locations: AddressBookLocation[] = ['global', 'private'];

const location = computed<AddressBookLocation>(() => locations[get(tab)]);

const { editableItem, openDialog } = useCommonTableProps<AddressBookPayload>();

const { getAddressBook } = useAddressBookOperations();

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
>(filter => getAddressBook(get(location), get(filter)), {
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

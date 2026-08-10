<script setup lang="ts">
import type {
  AddressBookEntry,
  AddressBookLocation,
  AddressBookPayload,
  AddressBookRequestPayload,
} from '@/modules/accounts/address-book/eth-names';
import type { Filters } from '@/modules/accounts/address-book/use-address-book-filter';
import AddressBookFormDialog from '@/modules/accounts/address-book/AddressBookFormDialog.vue';
import AddressBookManagementMore from '@/modules/accounts/address-book/AddressBookManagementMore.vue';
import AddressBookTable from '@/modules/accounts/address-book/AddressBookTable.vue';
import EthNamesHint from '@/modules/accounts/address-book/EthNamesHint.vue';
import { useAddressBookFields } from '@/modules/accounts/address-book/use-address-book-fields';
import { useAddressBookOperations } from '@/modules/accounts/address-book/use-address-book-operations';
import { arrayify } from '@/modules/core/common/data/array';
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
  params: [{
    to: 'both',
    values: computed<Record<string, unknown>>(() => ({
      blockchain: get(selectedChain),
      strictBlockchain: get(strictBlockchain),
    })),
  }],
  sort: {
    default: [{
      column: 'name',
      direction: 'asc',
    }],
  },
  urlState: { mode: 'route' },
});

// The chain and strict-chain pills are param-bound, so the bar's param bag is bridged to the refs
// backing them — the same refs the standalone selector and checkbox used to write, and the ones the
// request/url param source reads. An absent param clears its ref: removing the pill is how the
// filter is turned off.
const pillParams = computed<Record<string, string | string[] | boolean>>({
  get(): Record<string, string | string[] | boolean> {
    const chain = get(selectedChain);
    return {
      ...(chain ? { blockchain: chain } : {}),
      ...(get(strictBlockchain) ? { strictBlockchain: true } : {}),
    };
  },
  set(value: Record<string, string | string[] | boolean>): void {
    const chain = value.blockchain;
    set(selectedChain, typeof chain === 'boolean' ? undefined : arrayify(chain ?? []).at(0));
    set(strictBlockchain, value.strictBlockchain === true);
  },
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
      <PillFilterBar
        v-model:matches="filters"
        v-model:params="pillParams"
        :fields="fields"
        :labels="pillLabels"
      />

      <div class="flex items-center gap-2 my-3">
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
            :data-testid="`address-book-scope-${loc}`"
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
      :edit-mode="!!editableItem"
      :selected-chain="selectedChain"
      :location="location"
      @update-tab="tab = $event"
      @refresh="fetchData()"
    />
  </TablePageLayout>
</template>

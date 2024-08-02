<script setup lang="ts">
import type {
  AddressBookEntry,
  AddressBookLocation,
  AddressBookPayload,
  AddressBookRequestPayload,
} from '@/types/eth-names';
import type { Collection } from '@/types/collection';
import type { Filters, Matcher } from '@/composables/filters/address-book';

const selectedChain = ref<string>();
const enableForAllChains = ref<boolean>(false);

const tab = ref<number>(0);
const locations: AddressBookLocation[] = ['global', 'private'];
const { t } = useI18n();

const location = computed<AddressBookLocation>(() => locations[get(tab)]);

const emptyForm: () => Partial<AddressBookPayload> = () => ({
  location: get(location),
  blockchain: get(selectedChain) ?? null,
});

const { setOpenDialog, setPostSubmitFunc } = useAddressBookForm();

const editMode = ref<boolean>(false);
const formPayload = ref<Partial<AddressBookPayload>>(emptyForm());

const { getAddressBook } = useAddressesNamesStore();

const { filters, matchers, state, isLoading, fetchData, sort, pagination } = usePaginationFilters<
  AddressBookEntry,
  AddressBookRequestPayload,
  AddressBookEntry,
  Collection<AddressBookEntry>,
  Filters,
  Matcher
>(null, true, useAddressBookFilter, filter => getAddressBook(get(location), filter), {
  extraParams: computed(() => ({
    blockchain: get(selectedChain),
  })),
  defaultSortBy: {
    key: ['name'],
    ascending: [true],
  },
});

function openForm(item: AddressBookEntry | null = null) {
  set(editMode, !!item);
  if (item) {
    set(formPayload, {
      ...item,
      location: get(location),
    });
    set(enableForAllChains, !item.blockchain);
  }
  else {
    set(formPayload, emptyForm());
  }
  setOpenDialog(true);
}

onMounted(async () => {
  await fetchData();
});

watchImmediate(location, async () => {
  await fetchData();
});

setPostSubmitFunc(fetchData);
</script>

<template>
  <TablePageLayout
    class="p-4"
    :title="[t('navigation_menu.manage_address_book')]"
  >
    <template #buttons>
      <RuiButton
        color="primary"
        @click="openForm()"
      >
        <template #prepend>
          <RuiIcon name="add-line" />
        </template>
        {{ t('address_book.dialog.add_title') }}
      </RuiButton>
    </template>

    <RuiCard>
      <div class="flex flex-row flex-wrap items-center justify-end gap-2">
        <ChainSelect
          :model-value="selectedChain"
          hide-details
          class="flex-1 max-w-full md:max-w-[18rem]"
          clearable
          dense
          exclude-eth-staking
          @update:model-value="selectedChain = $event"
        />

        <div class="w-[20rem] max-w-[30rem]">
          <TableFilter
            v-model:matches="filters"
            :matchers="matchers"
          />
        </div>
      </div>

      <div class="flex flex-row items-center gap-2 mb-3">
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
              @edit="openForm($event)"
              @refresh="fetchData()"
            />
          </template>
        </RuiTabItem>
      </RuiTabItems>
    </RuiCard>

    <AddressBookFormDialog
      v-model:enable-for-all-chains="enableForAllChains"
      :payload="formPayload"
      :edit-mode="editMode"
      @update-tab="tab = $event"
    />
  </TablePageLayout>
</template>

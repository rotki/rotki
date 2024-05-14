<script setup lang="ts">
import { ApiValidationError } from '@/types/api/errors';
import type {
  AddressBookEntry,
  AddressBookLocation,
  AddressBookPayload,
  AddressBookRequestPayload,
} from '@/types/eth-names';
import type { Collection } from '@/types/collection';
import type { Filters, Matcher } from '@/composables/filters/address-book';

const selectedChain: Ref<string | null> = ref(null);
const enableForAllChains: Ref<boolean> = ref(false);

const tab = ref<number>(0);
const locations: AddressBookLocation[] = ['global', 'private'];
const { t } = useI18n();

const location = computed<AddressBookLocation>(() => locations[get(tab)]);

const emptyForm: () => AddressBookPayload = () => ({
  location: get(location),
  blockchain: get(selectedChain),
  address: '',
  name: '',
});

const { setSubmitFunc, setOpenDialog, closeDialog } = useAddressBookForm();

const editMode = ref<boolean>(false);
const formPayload = ref<AddressBookPayload>(emptyForm());
const errorMessages = ref<{ address?: string[]; name?: string[] }>({});

const { getAddressBook, addAddressBook, updateAddressBook } = useAddressesNamesStore();
const { setMessage } = useMessageStore();

const {
  filters,
  matchers,
  state,
  isLoading,
  fetchData,
  setFilter,
  sort,
  pagination,
} = usePaginationFilters<
  AddressBookEntry,
  AddressBookRequestPayload,
  AddressBookEntry,
  Collection<AddressBookEntry>,
  Filters,
  Matcher
>(
  null,
  true,
  useAddressBookFilter,
  filter => getAddressBook(get(location), filter),
  {
    extraParams: computed(() => ({
      blockchain: get(selectedChain),
    })),
    defaultSortBy: {
      key: 'name',
      ascending: [true],
    },
  },
);

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
    const newForm = emptyForm();
    set(formPayload, {
      ...newForm,
    });
  }
  setOpenDialog(true);
}

const resetForm = function () {
  closeDialog();
  set(formPayload, emptyForm());
  set(enableForAllChains, false);
  set(errorMessages, {});
};

async function save() {
  try {
    const { blockchain, address, name, location } = get(formPayload);
    const payload = {
      address: address.trim(),
      name: name.trim(),
      blockchain: get(enableForAllChains) ? null : blockchain,
    };
    if (get(editMode))
      await updateAddressBook(location, [payload]);
    else
      await addAddressBook(location, [payload]);

    set(tab, location === 'global' ? 0 : 1);

    closeDialog();
    await fetchData();
    return true;
  }
  catch (error: any) {
    let errors = error.message;

    if (error instanceof ApiValidationError)
      errors = error.getValidationErrors(get(formPayload));

    if (typeof errors === 'string') {
      const values = { message: error.message };
      const title = get(editMode)
        ? t('address_book.actions.edit.error.title')
        : t('address_book.actions.add.error.title');
      const description = get(editMode)
        ? t('address_book.actions.edit.error.description', values)
        : t('address_book.actions.add.error.description', values);
      setMessage({
        title,
        description,
        success: false,
      });
    }
    else {
      set(errorMessages, errors);
    }
    return false;
  }
}

setSubmitFunc(save);

onMounted(async () => {
  await fetchData();
});

watch(location, async () => {
  await fetchData();
});

watch(formPayload, ({ blockchain }, { blockchain: oldBlockchain }) => {
  if (blockchain !== oldBlockchain)
    set(errorMessages, {});
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
          class="flex-1 max-w-full md:max-w-[15rem]"
          clearable
          dense
          exclude-eth-staking
          @update:model-value="selectedChain = $event"
        />

        <div class="max-w-[25rem]">
          <TableFilter
            :matchers="matchers"
            :matches="filters"
            @update:matches="setFilter($event)"
          />
        </div>
      </div>

      <div class="flex flex-row items-end gap-2 mb-4">
        <RuiTabs
          v-model="tab"
          color="primary"
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
              :collection="state"
              :location="loc"
              :loading="isLoading"
              :sort.sync="sort"
              :pagination.sync="pagination"
              :blockchain="selectedChain"
              @edit="openForm($event)"
              @refresh="fetchData()"
            />
          </template>
        </RuiTabItem>
      </RuiTabItems>
    </RuiCard>

    <AddressBookFormDialog
      v-model="formPayload"
      :enable-for-all-chains.sync="enableForAllChains"
      :edit-mode="editMode"
      :error-messages="errorMessages"
      @reset="resetForm()"
    />
  </TablePageLayout>
</template>

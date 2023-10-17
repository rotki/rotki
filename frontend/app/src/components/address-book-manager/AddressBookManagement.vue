<script setup lang="ts">
import { type Blockchain } from '@rotki/common/lib/blockchain';
import { type Ref } from 'vue';
import {
  type AddressBookEntry,
  type AddressBookLocation,
  type AddressBookPayload,
  type AddressBookRequestPayload
} from '@/types/eth-names';
import { type Collection } from '@/types/collection';
import { type Filters, type Matcher } from '@/composables/filters/address-book';

const selectedChain: Ref<Blockchain | null> = ref(null);
const enableForAllChains: Ref<boolean> = ref(false);

const tab = ref<number>(0);
const locations: AddressBookLocation[] = ['global', 'private'];
const { t } = useI18n();

const location = computed<AddressBookLocation>(() => locations[get(tab)]);

const emptyForm: () => AddressBookPayload = () => ({
  location: get(location),
  blockchain: get(selectedChain),
  address: '',
  name: ''
});

const { setSubmitFunc, setOpenDialog, closeDialog } = useAddressBookForm();

const openForm = (item: AddressBookEntry | null = null) => {
  set(editMode, !!item);
  if (item) {
    set(formPayload, {
      ...item,
      location: get(location)
    });
    set(enableForAllChains, !item.blockchain);
  } else {
    const newForm = emptyForm();
    set(formPayload, {
      ...newForm
    });
  }
  setOpenDialog(true);
};

const resetForm = function () {
  closeDialog();
  set(formPayload, emptyForm());
  set(enableForAllChains, false);
};

const editMode = ref<boolean>(false);
const formPayload = ref<AddressBookPayload>(emptyForm());

const { getAddressBook, addAddressBook, updateAddressBook } =
  useAddressesNamesStore();
const { setMessage } = useMessageStore();

const save = async () => {
  try {
    const formVal = get(formPayload);
    const enableForAllChainsVal = get(enableForAllChains);
    const payload = {
      address: formVal.address.trim(),
      name: formVal.name,
      blockchain: enableForAllChainsVal ? null : formVal.blockchain
    };
    const location = formVal.location;
    if (get(editMode)) {
      await updateAddressBook(location, [payload]);
    } else {
      await addAddressBook(location, [payload]);
    }

    set(tab, location === 'global' ? 0 : 1);
    if (!enableForAllChainsVal) {
      set(selectedChain, formVal.blockchain);
    }

    closeDialog();
    await fetchData();
    return true;
  } catch (e: any) {
    const values = { message: e.message };
    const title = get(editMode)
      ? t('address_book.actions.edit.error.title')
      : t('address_book.actions.add.error.title');
    const description = get(editMode)
      ? t('address_book.actions.edit.error.description', values)
      : t('address_book.actions.add.error.description', values);
    setMessage({
      title,
      description,
      success: false
    });
    return false;
  }
};

setSubmitFunc(save);

const {
  filters,
  matchers,
  state,
  isLoading,
  options,
  fetchData,
  setOptions,
  setFilter,
  setPage
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
      blockchain: get(selectedChain)
    }))
  }
);

onMounted(async () => {
  await fetchData();
});

watch(location, async () => {
  await fetchData();
});
</script>

<template>
  <TablePageLayout
    class="p-4"
    :title="[t('navigation_menu.manage_address_book')]"
  >
    <template #buttons>
      <RuiButton color="primary" @click="openForm()">
        <template #prepend>
          <RuiIcon name="add-line" />
        </template>
        {{ t('address_book.dialog.add_title') }}
      </RuiButton>
    </template>

    <RuiCard>
      <div class="flex flex-row flex-wrap items-center justify-end gap-2">
        <ChainSelect
          evm-only
          :model-value="selectedChain"
          hide-details
          class="flex-1 max-w-full md:max-w-[15rem]"
          dense
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

      <div class="flex flex-row items-end gap-2">
        <RuiTabs v-model="tab" color="primary">
          <RuiTab v-for="loc in locations" :key="loc" class="capitalize">
            {{ loc }}
          </RuiTab>
        </RuiTabs>
        <EthNamesHint with-header />
      </div>

      <RuiTabItems v-model="tab">
        <RuiTabItem v-for="loc in locations" :key="loc">
          <template #default>
            <AddressBookTable
              :collection="state"
              :location="loc"
              :loading="isLoading"
              :options="options"
              :blockchain="selectedChain"
              @edit="openForm($event)"
              @update:page="setPage($event)"
              @update:options="setOptions($event)"
              @refresh="fetchData()"
            />
          </template>
        </RuiTabItem>
      </RuiTabItems>
    </RuiCard>

    <AddressBookFormDialog
      v-model="formPayload"
      :enable-for-all-chains="enableForAllChains"
      :edit-mode="editMode"
      @update:enable-for-all-chains="enableForAllChains = $event"
      @reset="resetForm()"
    />
  </TablePageLayout>
</template>

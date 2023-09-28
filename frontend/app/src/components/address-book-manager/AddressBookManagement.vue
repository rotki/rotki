<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { type Ref } from 'vue';
import {
  type AddressBookEntry,
  type AddressBookLocation,
  type AddressBookPayload
} from '@/types/eth-names';

const search: Ref<string> = ref('');
const pendingSearch: Ref<string> = ref('');
const selectedChain: Ref<Blockchain> = ref(Blockchain.ETH);
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

const {
  isPending: isTimeoutPending,
  start,
  stop
} = useTimeoutFn(
  () => {
    set(search, get(pendingSearch));
  },
  600,
  { immediate: false }
);

const onSearchTermChange = (term: string | null) => {
  set(pendingSearch, term || '');
  if (get(isTimeoutPending)) {
    stop();
  }
  start();
};

const { addAddressBook, updateAddressBook } = useAddressesNamesStore();
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
</script>

<template>
  <TablePageLayout class="p-4">
    <template #title>
      {{ t('navigation_menu.manage_address_book') }}
    </template>
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
          class="flex-1 max-w-full md:max-w-[22rem]"
          dense
          @update:model-value="selectedChain = $event"
        />
        <RuiTextField
          :value="pendingSearch"
          hide-details
          prepend-icon
          class="flex-1 max-w-full md:max-w-[22rem]"
          dense
          :label="t('common.actions.filter')"
          variant="outlined"
          @input="onSearchTermChange($event)"
        >
          <template v-if="isTimeoutPending" #append>
            <div class="flex flex-row items-center">
              <RuiProgress
                variant="indeterminate"
                circular
                size="20"
                thickness="3"
                color="primary"
              />
            </div>
          </template>
        </RuiTextField>
      </div>

      <div class="flex flex-row gap-2">
        <RuiTabs v-model="tab" color="primary">
          <RuiTab v-for="loc in locations" :key="loc" class="capitalize">
            {{ loc }}
          </RuiTab>
        </RuiTabs>
        <EthNamesHint with-header />
      </div>

      <RuiTabItems v-model="tab">
        <RuiTabItem v-for="loc in locations" :key="loc">
          <AddressBookTable
            :location="loc"
            :blockchain="selectedChain"
            :search="search"
            @edit="openForm($event)"
          >
            {{ loc }}
          </AddressBookTable>
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

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
  <VContainer>
    <VRow justify="space-between" align="center" no-gutters>
      <VCol>
        <CardTitle>{{ t('address_book.title') }}</CardTitle>
      </VCol>
    </VRow>
    <Card class="mt-8">
      <template #title>
        {{ t('address_book.table.title') }}
      </template>
      <template #subtitle>
        {{ t('address_book.table.subtitle') }}
      </template>

      <template #search>
        <VRow class="pt-2 pb-6" justify="end">
          <VCol cols="12" sm="4" md="3">
            <ChainSelect
              evm-only
              :model-value="selectedChain"
              hide-details
              dense
              @update:model-value="selectedChain = $event"
            />
          </VCol>
          <VCol cols="12" sm="8" md="6" lg="4">
            <VTextField
              :value="pendingSearch"
              input-class=""
              hide-details
              prepend-inner-icon="mdi-magnify"
              :label="t('common.actions.filter')"
              outlined
              dense
              clearable
              @input="onSearchTermChange($event)"
            >
              <template v-if="isTimeoutPending" #append>
                <VProgressCircular
                  indeterminate
                  color="primary"
                  width="2"
                  size="24"
                />
              </template>
            </VTextField>
          </VCol>
        </VRow>
      </template>

      <VRow align="center">
        <VCol cols="auto">
          <VTabs v-model="tab">
            <VTab v-for="loc in locations" :key="loc">
              {{ loc }}
            </VTab>
          </VTabs>
        </VCol>
        <VCol class="pl-0">
          <EthNamesHint with-header />
        </VCol>
        <VCol />
        <VCol cols="auto">
          <VBtn
            class="mr-2"
            small
            depressed
            fab
            color="primary"
            @click="openForm()"
          >
            <VIcon>mdi-plus</VIcon>
          </VBtn>
        </VCol>
      </VRow>

      <VTabsItems v-model="tab">
        <VTabItem v-for="loc in locations" :key="loc">
          <AddressBookTable
            :location="loc"
            :blockchain="selectedChain"
            :search="search"
            @edit="openForm($event)"
          >
            {{ loc }}
          </AddressBookTable>
        </VTabItem>
      </VTabsItems>
    </Card>

    <AddressBookFormDialog
      v-model="formPayload"
      :enable-for-all-chains="enableForAllChains"
      :edit-mode="editMode"
      @update:enable-for-all-chains="enableForAllChains = $event"
      @reset="resetForm()"
    />
  </VContainer>
</template>

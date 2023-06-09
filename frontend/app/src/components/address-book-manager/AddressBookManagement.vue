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
  <v-container>
    <v-row justify="space-between" align="center" no-gutters>
      <v-col>
        <card-title>{{ t('address_book.title') }}</card-title>
      </v-col>
    </v-row>
    <card outlined-body class="mt-8">
      <template #title>
        {{ t('address_book.table.title') }}
      </template>
      <template #subtitle>
        {{ t('address_book.table.subtitle') }}
      </template>

      <template #search>
        <v-row class="pt-2 pb-6" justify="end">
          <v-col cols="12" sm="4" md="3">
            <chain-select
              evm-only
              :model-value="selectedChain"
              hide-details
              dense
              @update:model-value="selectedChain = $event"
            />
          </v-col>
          <v-col cols="12" sm="8" md="6" lg="4">
            <v-text-field
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
                <v-progress-circular
                  indeterminate
                  color="primary"
                  width="2"
                  size="24"
                />
              </template>
            </v-text-field>
          </v-col>
        </v-row>
      </template>

      <v-row align="center">
        <v-col cols="auto">
          <v-tabs v-model="tab">
            <v-tab v-for="loc in locations" :key="loc">
              {{ loc }}
            </v-tab>
          </v-tabs>
        </v-col>
        <v-col class="pl-0">
          <eth-names-hint with-header />
        </v-col>
        <v-col />
        <v-col cols="auto">
          <v-btn
            class="mr-2"
            small
            depressed
            fab
            color="primary"
            @click="openForm()"
          >
            <v-icon>mdi-plus</v-icon>
          </v-btn>
        </v-col>
      </v-row>

      <v-tabs-items v-model="tab">
        <v-tab-item v-for="loc in locations" :key="loc">
          <address-book-table
            :location="loc"
            :blockchain="selectedChain"
            :search="search"
            @edit="openForm($event)"
          >
            {{ loc }}
          </address-book-table>
        </v-tab-item>
      </v-tabs-items>
    </card>

    <address-book-form-dialog
      v-model="formPayload"
      :enable-for-all-chains="enableForAllChains"
      :edit-mode="editMode"
      @update:enable-for-all-chains="enableForAllChains = $event"
      @reset="resetForm()"
    />
  </v-container>
</template>

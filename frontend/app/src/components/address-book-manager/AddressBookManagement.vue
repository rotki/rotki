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
  set(showForm, true);
};

const hideForm = function () {
  set(showForm, false);
  set(formPayload, emptyForm());
  set(enableForAllChains, false);
};

const valid = ref<boolean>(false);
const showForm = ref(false);
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
  if (!get(valid)) {
    return;
  }
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
    set(showForm, false);
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
  }
};

const css = useCssModule();
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
        <v-row class="pt-2 pb-6">
          <v-col cols="12" sm="4" md="3">
            <chain-select
              evm-only
              :model-value="selectedChain"
              dense
              hide-details
              @update:model-value="selectedChain = $event"
            />
          </v-col>
          <v-col cols="12" sm="8" md="6" lg="4">
            <v-text-field
              :value="pendingSearch"
              input-class=""
              dense
              :class="css.filter"
              hide-details
              prepend-inner-icon="mdi-magnify"
              :label="t('common.actions.filter')"
              outlined
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

    <big-dialog
      :display="showForm"
      :title="
        editMode
          ? t('address_book.dialog.edit_title')
          : t('address_book.dialog.add_title')
      "
      :action-disabled="!valid"
      @confirm="save()"
      @cancel="hideForm()"
    >
      <address-book-form
        v-model="formPayload"
        :edit="editMode"
        :enable-for-all-chains="enableForAllChains"
        @valid="valid = $event"
        @update:enable-for-all-chains="enableForAllChains = $event"
      />
    </big-dialog>
  </v-container>
</template>

<style lang="scss" module>
.filter {
  :global {
    .v-input {
      &__slot {
        height: 46px !important;
        padding-top: 2px !important;
      }
    }
  }
}
</style>

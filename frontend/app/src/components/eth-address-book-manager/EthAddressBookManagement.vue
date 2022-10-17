<template>
  <v-container>
    <v-row justify="space-between" align="center" no-gutters>
      <v-col>
        <card-title>{{ tc('eth_address_book.title') }}</card-title>
      </v-col>
    </v-row>
    <card outlined-body class="mt-8">
      <template #title>
        {{ tc('eth_address_book.table.title') }}
      </template>
      <template #subtitle>
        {{ tc('eth_address_book.table.subtitle') }}
      </template>

      <template #search>
        <v-row justify="end" no-gutters>
          <v-col cols="12" sm="4">
            <v-text-field
              :value="pendingSearch"
              dense
              prepend-inner-icon="mdi-magnify"
              :label="tc('common.actions.filter')"
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
          <eth-address-book-table
            :location="loc"
            :search="search"
            @edit="openForm($event)"
          >
            {{ loc }}
          </eth-address-book-table>
        </v-tab-item>
      </v-tabs-items>
    </card>

    <big-dialog
      :display="showForm"
      :title="
        editMode
          ? tc('eth_address_book.dialog.edit_title')
          : tc('eth_address_book.dialog.add_title')
      "
      :action-disabled="!valid"
      @confirm="save"
      @cancel="hideForm()"
    >
      <eth-address-book-form
        v-model="form"
        :edit="editMode"
        @valid="valid = $event"
      />
    </big-dialog>
  </v-container>
</template>
<script setup lang="ts">
import BigDialog from '@/components/dialogs/BigDialog.vue';
import EthAddressBookForm from '@/components/eth-address-book-manager/EthAddressBookForm.vue';
import EthAddressBookTable from '@/components/eth-address-book-manager/EthAddressBookTable.vue';
import EthNamesHint from '@/components/EthNamesHint.vue';
import { useEthNamesStore } from '@/store/balances/ethereum-names';
import { useMessageStore } from '@/store/message';
import {
  EthAddressBookLocation,
  EthNamesEntry,
  EthNamesPayload
} from '@/types/eth-names';

const search = ref<string>('');
const pendingSearch = ref<string>('');

const tab = ref<number>(0);
const locations: EthAddressBookLocation[] = ['global', 'private'];
const { tc } = useI18n();

const location = computed<EthAddressBookLocation>(() => {
  return locations[get(tab)];
});

const emptyForm: () => EthNamesPayload = () => ({
  location: get(location),
  address: '',
  name: ''
});

const openForm = (item: EthNamesEntry | null = null) => {
  set(editMode, !!item);
  if (item) {
    set(form, {
      ...item,
      location: get(location)
    });
  } else {
    const newForm = emptyForm();
    set(form, {
      ...newForm
    });
  }
  set(showForm, true);
};

const hideForm = function () {
  set(showForm, false);
  set(form, emptyForm());
};

const valid = ref<boolean>(false);
const showForm = ref(false);
const editMode = ref<boolean>(false);
const form = ref<EthNamesPayload>(emptyForm());

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

const onSearchTermChange = (term: string) => {
  set(pendingSearch, term);
  if (get(isTimeoutPending)) {
    stop();
  }
  start();
};

const { addEthAddressBook, updateEthAddressBook } = useEthNamesStore();
const { setMessage } = useMessageStore();

const save = async () => {
  if (!get(valid)) return;
  try {
    const formVal = get(form);
    const payload = {
      address: formVal.address.trim(),
      name: formVal.name
    };
    const location = formVal.location;
    if (get(editMode)) {
      await updateEthAddressBook(location, [payload]);
    } else {
      await addEthAddressBook(location, [payload]);
    }

    set(tab, location === 'global' ? 0 : 1);
    set(showForm, false);
  } catch (e: any) {
    const values = { message: e.message };
    const title = get(editMode)
      ? tc('eth_address_book.actions.edit.error.title')
      : tc('eth_address_book.actions.add.error.title');
    const description = get(editMode)
      ? tc('eth_address_book.actions.edit.error.description', 0, values)
      : tc('eth_address_book.actions.add.error.description', 0, values);
    setMessage({
      title,
      description,
      success: false
    });
  }
};
</script>

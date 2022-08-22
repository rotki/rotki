<template>
  <v-container>
    <v-row justify="space-between" align="center" no-gutters>
      <v-col>
        <card-title>{{ $t('eth_address_book.title') }}</card-title>
      </v-col>
    </v-row>
    <card outlined-body class="mt-8">
      <template #title>
        {{ $t('eth_address_book.table.title') }}
      </template>
      <template #subtitle>
        {{ $t('eth_address_book.table.subtitle') }}
      </template>

      <template #search>
        <v-row justify="end" no-gutters>
          <v-col cols="12" sm="4">
            <v-text-field
              :value="pendingSearch"
              dense
              prepend-inner-icon="mdi-magnify"
              :label="$t('common.actions.filter')"
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
            <v-tab v-for="location in locations" :key="location">
              {{ location }}
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
        <v-tab-item v-for="location in locations" :key="location">
          <eth-address-book-table
            :location="location"
            :search="search"
            @edit="openForm($event)"
          >
            {{ location }}
          </eth-address-book-table>
        </v-tab-item>
      </v-tabs-items>
    </card>

    <big-dialog
      :display="showForm"
      :title="
        editMode
          ? $t('eth_address_book.dialog.edit_title')
          : $t('eth_address_book.dialog.add_title')
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
<script lang="ts">
import { get, set, useTimeoutFn } from '@vueuse/core';
import { computed, defineComponent, ref } from 'vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import EthAddressBookForm from '@/components/eth-address-book-manager/EthAddressBookForm.vue';
import EthAddressBookTable from '@/components/eth-address-book-manager/EthAddressBookTable.vue';
import EthNamesHint from '@/components/EthNamesHint.vue';
import i18n from '@/i18n';
import { useEthNamesStore } from '@/store/balances/ethereum-names';
import {
  EthAddressBookLocation,
  EthNamesEntry,
  EthNamesPayload
} from '@/store/balances/types';
import { useMainStore } from '@/store/main';

export default defineComponent({
  name: 'EthAddressBookManagement',
  components: {
    EthNamesHint,
    EthAddressBookForm,
    EthAddressBookTable,
    BigDialog
  },
  setup() {
    const search = ref<string>('');
    const pendingSearch = ref<string>('');

    const tab = ref<number>(0);
    const locations: EthAddressBookLocation[] = ['global', 'private'];

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
    const { setMessage } = useMainStore();

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

        set(showForm, false);
      } catch (e: any) {
        const values = { message: e.message };
        const title = editMode
          ? i18n.t('eth_address_book.actions.edit.error.title')
          : i18n.t('eth_address_book.actions.add.error.title');
        const description = editMode
          ? i18n.t('eth_address_book.actions.edit.error.description', values)
          : i18n.t('eth_address_book.actions.add.error.description', values);
        setMessage({
          title: title.toString(),
          description: description.toString(),
          success: false
        });
      }
    };

    return {
      form,
      tab,
      locations,
      search,
      pendingSearch,
      showForm,
      editMode,
      valid,
      isTimeoutPending,
      openForm,
      hideForm,
      onSearchTermChange,
      save
    };
  }
});
</script>

<template>
  <v-form v-model="valid">
    <div class="mt-2">
      <div>
        <v-select
          :value="value.location"
          outlined
          :label="$t('common.location')"
          :items="locations"
          :disabled="edit"
          @input="input({ location: $event })"
        >
          <template #item="{ item }"> {{ toSentenceCase(item) }} </template>
          <template #selection="{ item }">
            {{ toSentenceCase(item) }}
          </template>
        </v-select>
      </div>
      <div>
        <v-combobox
          :value="value.address"
          outlined
          :label="$t('eth_address_book.form.labels.address')"
          :items="addressSuggestions"
          :no-data-text="$t('eth_address_book.form.no_suggestions_available')"
          :disabled="edit"
          :rules="addressRules"
          :search-input.sync="search"
          @input="input({ address: $event })"
        />
      </div>
      <div>
        <v-text-field
          :value="value.name"
          outlined
          :label="$t('common.name')"
          :rules="nameRules"
          @input="input({ name: $event })"
        />
      </div>
    </div>
  </v-form>
</template>

<script lang="ts">
import {
  computed,
  ref,
  toRefs,
  watch,
  defineComponent,
  PropType
} from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import i18n from '@/i18n';
import { useEthNamesStore } from '@/store/balances';
import {
  EthAddressBookLocation,
  EthNamesPayload
} from '@/store/balances/types';
import { sanitizeAddress, toSentenceCase } from '@/utils/text';

export default defineComponent({
  name: 'EthAddressBookForm',
  props: {
    value: {
      required: true,
      type: Object as PropType<EthNamesPayload>
    },
    edit: {
      required: true,
      type: Boolean
    }
  },
  emits: ['input', 'valid'],
  setup(props, { emit }) {
    const { value } = toRefs(props);
    const valid = ref(false);

    const search = ref<string | null>('');

    const ethNamesStore = useEthNamesStore();
    const { ensAddresses, ethAddressBook } = toRefs(ethNamesStore);

    const addressBookList = computed<string[]>(() => {
      const items = get(ethAddressBook)[get(value).location];
      return items.map(item => item.address);
    });

    const addressSuggestions = computed<string[]>(() => {
      return get(ensAddresses).filter(
        (address: string) => !get(addressBookList).includes(address)
      );
    });

    watch(valid, value => emit('valid', value));

    const input = (payload: Partial<EthNamesPayload>) => {
      emit('input', { ...get(value), ...payload });
    };

    watch(search, address => {
      if (address === null) address = '';
      input({ address });
    });

    watch(value, ({ address }) => {
      const sanitizedAddress = sanitizeAddress(get(address));
      if (get(address) !== sanitizedAddress) {
        set(search, sanitizedAddress);
      }
    });

    const locations: EthAddressBookLocation[] = ['global', 'private'];

    const addressRules = [
      (v: string) =>
        !!v || i18n.t('eth_address_book.form.validation.address').toString()
    ];

    const nameRules = [
      (v: string) =>
        !!v || i18n.t('eth_address_book.form.validation.name').toString()
    ];

    return {
      search,
      locations,
      valid,
      addressSuggestions,
      addressRules,
      nameRules,
      input,
      toSentenceCase
    };
  }
});
</script>

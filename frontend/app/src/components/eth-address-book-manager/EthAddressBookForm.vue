<template>
  <v-form v-model="valid">
    <div class="mt-2">
      <div>
        <v-select
          :value="value.location"
          outlined
          :label="t('common.location')"
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
          :label="t('eth_address_book.form.labels.address')"
          :items="addressSuggestions"
          :no-data-text="t('eth_address_book.form.no_suggestions_available')"
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
          :label="t('common.name')"
          :rules="nameRules"
          @input="input({ name: $event })"
        />
      </div>
    </div>
  </v-form>
</template>

<script setup lang="ts">
import { get, set } from '@vueuse/core';
import { computed, PropType, ref, toRefs, watch } from 'vue';
import { useI18n } from 'vue-i18n-composable';
import { useEthNamesStore } from '@/store/balances/ethereum-names';
import { EthAddressBookLocation, EthNamesPayload } from '@/types/eth-names';
import { sanitizeAddress, toSentenceCase } from '@/utils/text';

const props = defineProps({
  value: {
    required: true,
    type: Object as PropType<EthNamesPayload>
  },
  edit: {
    required: true,
    type: Boolean
  }
});

const emit = defineEmits(['input', 'valid']);
const { t } = useI18n();
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
  (v: string) => !!v || t('eth_address_book.form.validation.address').toString()
];

const nameRules = [
  (v: string) => !!v || t('eth_address_book.form.validation.name').toString()
];
</script>

<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import {
  type AddressBookLocation,
  type AddressBookPayload
} from '@/types/eth-names';
import {
  isValidEthAddress,
  sanitizeAddress,
  toSentenceCase
} from '@/utils/text';
import ChainSelect from '@/components/accounts/blockchain/ChainSelect.vue';

const props = withDefaults(
  defineProps<{
    value: AddressBookPayload;
    edit: boolean;
    enableForAllChains?: boolean;
  }>(),
  {
    enableForAllChains: false
  }
);

const emit = defineEmits<{
  (e: 'input', value: AddressBookPayload): void;
  (e: 'valid', valid: boolean): void;
  (e: 'update:enable-for-all-chains', enable: boolean): void;
}>();

const { t } = useI18n();
const { value, enableForAllChains } = toRefs(props);

const search = ref<string | null>('');

const addressesNamesStore = useAddressesNamesStore();
const { getFetchedAddressesList } = addressesNamesStore;

const addressSuggestions = computed<string[]>(() => {
  return get(getFetchedAddressesList(get(value).blockchain));
});

const input = (payload: Partial<AddressBookPayload>) => {
  emit('input', { ...get(value), ...payload });
};

watch(search, address => {
  if (address === null) {
    address = '';
  }
  input({ address });
});

watch(value, ({ address }) => {
  const sanitizedAddress = sanitizeAddress(get(address));
  if (get(address) !== sanitizedAddress) {
    set(search, sanitizedAddress);
  }
});

const locations: AddressBookLocation[] = ['global', 'private'];

const rules = {
  address: {
    required: helpers.withMessage(
      t('address_book.form.validation.address').toString(),
      required
    ),
    isValidEthAddress: helpers.withMessage(
      t('address_book.form.validation.valid').toString(),
      isValidEthAddress
    )
  },
  name: {
    required: helpers.withMessage(
      t('address_book.form.validation.name').toString(),
      required
    )
  }
};

const v$ = useVuelidate(
  rules,
  {
    address: computed(() => get(value).address),
    name: computed(() => get(value).name)
  },
  { $autoDirty: true }
);

watch(v$, ({ $invalid }) => {
  emit('valid', !$invalid);
});

const updateAllChainsState = (enable: boolean) => {
  emit('update:enable-for-all-chains', enable);
};

const { getBlockie } = useBlockie();
</script>

<template>
  <v-form :value="!v$.$invalid">
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
        <chain-select
          evm-only
          :model-value="value.blockchain"
          :disabled="edit || enableForAllChains"
          @update:model-value="input({ blockchain: $event })"
        />
        <v-checkbox
          :disabled="edit"
          class="mt-0"
          :input-value="enableForAllChains"
          :label="t('address_book.form.labels.for_all_chain')"
          @change="updateAllChainsState"
        />
      </div>
      <div>
        <v-combobox
          :value="value.address"
          outlined
          :label="t('address_book.form.labels.address')"
          :items="addressSuggestions"
          :no-data-text="t('address_book.form.no_suggestions_available')"
          :disabled="edit"
          :error-messages="v$.address.$errors.map(e => e.$message)"
          :search-input.sync="search"
          @input="input({ address: $event })"
        >
          <template #prepend-inner>
            <span>
              <v-avatar size="24" class="mr-2" color="grey">
                <v-img
                  v-if="value.address && isValidEthAddress(value.address)"
                  :src="getBlockie(value.address)"
                />
              </v-avatar>
            </span>
          </template>
          <template #item="{ item }">
            <span v-if="item">
              <v-avatar size="24" class="mr-2">
                <v-img :src="getBlockie(item)" />
              </v-avatar>
            </span>
            {{ item }}
          </template>
        </v-combobox>
      </div>
      <div>
        <v-text-field
          :value="value.name"
          outlined
          :label="t('common.name')"
          :error-messages="v$.name.$errors.map(e => e.$message)"
          @input="input({ name: $event })"
        />
      </div>
    </div>
  </v-form>
</template>

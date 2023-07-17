<script setup lang="ts">
import { helpers, required } from '@vuelidate/validators';
import { type ComputedRef } from 'vue';
import {
  type AddressBookLocation,
  type AddressBookPayload
} from '@/types/eth-names';
import { isValidEthAddress, toSentenceCase } from '@/utils/text';
import { toMessages } from '@/utils/validation';

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

const addressesNamesStore = useAddressesNamesStore();
const { getFetchedAddressesList } = addressesNamesStore;

const addressSuggestions: ComputedRef<string[]> = computed(() =>
  get(getFetchedAddressesList(get(value).blockchain))
);

const input = (payload: Partial<AddressBookPayload>) => {
  emit('input', { ...get(value), ...payload });
};

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

const { valid, setValidation } = useAddressBookForm();

const v$ = setValidation(
  rules,
  {
    address: computed(() => get(value).address),
    name: computed(() => get(value).name)
  },
  { $autoDirty: true }
);

const updateAllChainsState = (enable: boolean) => {
  emit('update:enable-for-all-chains', enable);
};

const { getBlockie } = useBlockie();
</script>

<template>
  <VForm :value="valid">
    <div class="mt-2">
      <div>
        <VSelect
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
        </VSelect>
      </div>
      <div>
        <ChainSelect
          evm-only
          :model-value="value.blockchain"
          :disabled="edit || enableForAllChains"
          @update:model-value="input({ blockchain: $event })"
        />
        <VCheckbox
          :disabled="edit"
          class="mt-0"
          :input-value="enableForAllChains"
          :label="t('address_book.form.labels.for_all_chain')"
          @change="updateAllChainsState($event)"
        />
      </div>
      <div>
        <ComboboxWithCustomInput
          :value="value.address || ''"
          outlined
          :label="t('address_book.form.labels.address')"
          :items="addressSuggestions"
          :no-data-text="t('address_book.form.no_suggestions_available')"
          :disabled="edit"
          :error-messages="toMessages(v$.address)"
          auto-select-first
          @input="input({ address: $event })"
        >
          <template #prepend-inner>
            <span>
              <VAvatar size="24" class="mr-2" color="grey">
                <VImg
                  v-if="value.address && isValidEthAddress(value.address)"
                  :src="getBlockie(value.address)"
                />
              </VAvatar>
            </span>
          </template>
          <template #item="{ item }">
            <span v-if="item">
              <VAvatar size="24" class="mr-2">
                <VImg :src="getBlockie(item)" />
              </VAvatar>
            </span>
            {{ item }}
          </template>
        </ComboboxWithCustomInput>
      </div>
      <div>
        <VTextField
          :value="value.name"
          outlined
          :label="t('common.name')"
          :error-messages="toMessages(v$.name)"
          @input="input({ name: $event })"
        />
      </div>
    </div>
  </VForm>
</template>

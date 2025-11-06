<script setup lang="ts">
import type { ValidationErrors } from '@/types/api/errors';
import type { SelectOptions } from '@/types/common';
import type { AddressBookLocation, AddressBookPayload } from '@/types/eth-names';
import { Blockchain } from '@rotki/common';
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import { each } from 'es-toolkit/compat';
import ChainSelect from '@/components/accounts/blockchain/ChainSelect.vue';
import AppImage from '@/components/common/AppImage.vue';
import AutoCompleteWithSearchSync from '@/components/inputs/AutoCompleteWithSearchSync.vue';
import { useBlockie } from '@/composables/accounts/blockie';
import { useFormStateWatcher } from '@/composables/form';
import { useSupportedChains } from '@/composables/info/chains';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';
import { nullDefined, useRefPropVModel } from '@/utils/model';
import { toMessages } from '@/utils/validation';

const modelValue = defineModel<AddressBookPayload>({ required: true });
const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

withDefaults(
  defineProps<{
    editMode?: boolean;
  }>(),
  {
    editMode: false,
  },
);

const { t } = useI18n({ useScope: 'global' });

const { supportedChains } = useSupportedChains();

const name = useRefPropVModel(modelValue, 'name');
const location = useRefPropVModel(modelValue, 'location');
const address = useRefPropVModel(modelValue, 'address');
const blockchain = useRefPropVModel(modelValue, 'blockchain');
const blockchainModel = nullDefined(blockchain);
const { addresses } = useAccountAddresses();
const addressesNamesStore = useAddressesNamesStore();
const { addressNameSelector, getAddressesWithoutNames } = addressesNamesStore;

const addressSuggestions = getAddressesWithoutNames(blockchain);
const locations = computed<SelectOptions<AddressBookLocation>>(() => [
  { key: 'global', label: t('address_book.hint.global') },
  { key: 'private', label: t('address_book.hint.private') },
]);

const rules = {
  address: {
    required: helpers.withMessage(t('address_book.form.validation.address'), required),
  },
  blockchain: {
    required: helpers.withMessage(t('address_book.form.validation.chain'), required),
  },
  name: {
    required: helpers.withMessage(t('address_book.form.validation.name'), required),
  },
};

const states = {
  address,
  blockchain,
  name,
};

const v$ = useVuelidate(
  rules,
  states,
  { $autoDirty: true, $externalResults: errors },
);

useFormStateWatcher(states, stateUpdated);

const { getBlockie } = useBlockie();

function fetchNames() {
  const addressMap = get(addresses);

  each(Blockchain, (chain) => {
    addressMap[chain]?.forEach(address => get(addressNameSelector(address, chain)));
  });
}

const chainOptions = computed(() => [
  'evm',
  ...get(supportedChains).map(item => item.id).filter(item => item !== Blockchain.ETH2),
]);

/**
 * if new suggestions does not include last suggested and selected address, reset address
 */
watch(addressSuggestions, (suggestions, oldSuggestions) => {
  const chainAddress = get(address);
  if (get(blockchain) && oldSuggestions.includes(chainAddress) && !suggestions.includes(chainAddress))
    set(address, '');
});

watchEffect(fetchNames);
onMounted(fetchNames);

defineExpose({
  validate: () => get(v$).$validate(),
});
</script>

<template>
  <form class="flex flex-col gap-4">
    <RuiMenuSelect
      v-model="location"
      :label="t('common.location')"
      :options="locations"
      :disabled="editMode"
      key-attr="key"
      text-attr="label"
      variant="outlined"
    />
    <ChainSelect
      v-model="blockchainModel"
      :disabled="editMode"
      :items="chainOptions"
      :error-messages="toMessages(v$.blockchain)"
    />
    <div class="flex gap-2">
      <div class="m-3 rounded-full overflow-hidden w-8 h-8 bg-rui-grey-300 dark:bg-rui-grey-600">
        <AppImage
          v-if="modelValue.address"
          :src="getBlockie(modelValue.address)"
          size="2rem"
        />
      </div>
      <AutoCompleteWithSearchSync
        v-model.trim="address"
        class="flex-1"
        :label="t('address_book.form.labels.address')"
        :items="addressSuggestions"
        :no-data-text="t('address_book.form.no_suggestions_available')"
        :disabled="editMode"
        :error-messages="toMessages(v$.address)"
        clearable
      >
        <template #item.prepend="{ item }">
          <div
            v-if="item"
            class="mr-2 rounded-full overflow-hidden w-6 h-6 bg-rui-grey-300 dark:bg-rui-grey-600"
          >
            <AppImage
              v-if="item"
              :src="getBlockie(item)"
              size="1.5rem"
            />
          </div>
        </template>
      </AutoCompleteWithSearchSync>
    </div>
    <RuiTextField
      v-model="name"
      class="mt-2"
      variant="outlined"
      color="primary"
      :label="t('common.name')"
      :error-messages="toMessages(v$.name)"
    />
  </form>
</template>

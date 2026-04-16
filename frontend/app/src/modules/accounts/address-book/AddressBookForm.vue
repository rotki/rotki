<script setup lang="ts">
import type { AddressBookLocation, AddressBookPayload } from '@/modules/accounts/address-book/eth-names';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import type { SelectOptions } from '@/modules/core/common/common-types';
import { Blockchain } from '@rotki/common';
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import { each } from 'es-toolkit/compat';
import { useAddressNameResolution } from '@/modules/accounts/address-book/use-address-name-resolution';
import ChainSelect from '@/modules/accounts/blockchain/ChainSelect.vue';
import { useBlockie } from '@/modules/accounts/use-blockie';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { useFormStateWatcher } from '@/modules/core/common/use-form';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { nullDefined, useRefPropVModel } from '@/modules/core/common/validation/model';
import { toMessages } from '@/modules/core/common/validation/validation';
import AppImage from '@/modules/shell/components/AppImage.vue';
import AutoCompleteWithSearchSync from '@/modules/shell/components/inputs/AutoCompleteWithSearchSync.vue';

const modelValue = defineModel<AddressBookPayload>({ required: true });
const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const { editMode = false } = defineProps<{
  editMode?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const { supportedChains } = useSupportedChains();

const name = useRefPropVModel(modelValue, 'name');
const location = useRefPropVModel(modelValue, 'location');
const address = useRefPropVModel(modelValue, 'address');
const blockchain = useRefPropVModel(modelValue, 'blockchain');
const blockchainModel = nullDefined(blockchain);
const { addresses } = useAccountAddresses();
const addressNameResolution = useAddressNameResolution();
const { getAddressName, useAddressesWithoutNames } = addressNameResolution;

const addressSuggestions = useAddressesWithoutNames(blockchain);
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
    addressMap[chain]?.forEach(address => getAddressName(address, chain));
  });
}

const chainOptions = computed<string[]>(() => [
  'all',
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
  <div class="flex flex-col gap-4">
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
  </div>
</template>

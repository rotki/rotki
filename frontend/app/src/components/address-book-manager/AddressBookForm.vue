<script setup lang="ts">
import { each } from 'lodash-es';
import { Blockchain } from '@rotki/common';
import { helpers, required, requiredIf } from '@vuelidate/validators';
import { toMessages } from '@/utils/validation';
import type { SelectOptions } from '@/types/common';
import type { AddressBookLocation, AddressBookPayload } from '@/types/eth-names';

const props = defineProps<{
  modelValue: AddressBookPayload;
  edit: boolean;
  errorMessages: { address?: string[]; name?: string[] };
}>();

const emit = defineEmits<{
  (e: 'update:model-value', value: AddressBookPayload): void;
  (e: 'valid', valid: boolean): void;
}>();

const { t } = useI18n();
const { errorMessages } = toRefs(props);

const name = useSimplePropVModel(props, 'name', emit);
const address = useSimplePropVModel(props, 'address', emit);
const location = useSimplePropVModel(props, 'location', emit);
const chain = useSimplePropVModel(props, 'blockchain', emit);
const blockchain = nullDefined(chain);
const enabledForAllChains = defineModel<boolean>('enableForAllChains', { required: true, default: false });

const { addresses } = useBlockchainStore();
const addressesNamesStore = useAddressesNamesStore();
const { getAddressesWithoutNames, addressNameSelector } = addressesNamesStore;

const addressSuggestions = getAddressesWithoutNames(chain);
const locations = computed<SelectOptions<AddressBookLocation>>(() => [
  { label: t('address_book.hint.global'), key: 'global' },
  { label: t('address_book.hint.private'), key: 'private' },
]);

const rules = {
  blockchain: {
    required: helpers.withMessage(t('address_book.form.validation.chain'), requiredIf(logicNot(enabledForAllChains))),
  },
  address: {
    required: helpers.withMessage(t('address_book.form.validation.address'), required),
  },
  name: {
    required: helpers.withMessage(t('address_book.form.validation.name'), required),
  },
};

const { setValidation } = useAddressBookForm();

const v$ = setValidation(
  rules,
  {
    blockchain,
    address,
    name,
  },
  { $autoDirty: true, $externalResults: errorMessages },
);

const { getBlockie } = useBlockie();

function fetchNames() {
  const addressMap = get(addresses);

  each(Blockchain, (chain) => {
    addressMap[chain]?.forEach(address => get(addressNameSelector(address, chain)));
  });
}

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
</script>

<template>
  <form class="flex flex-col gap-4">
    <RuiMenuSelect
      v-model="location"
      :label="t('common.location')"
      :options="locations"
      :disabled="edit"
      key-attr="key"
      text-attr="label"
      variant="outlined"
    />
    <RuiSwitch
      v-model="enabledForAllChains"
      :disabled="edit"
      color="primary"
      :label="t('address_book.form.labels.for_all_chain')"
    />
    <ChainSelect
      v-model="blockchain"
      :disabled="edit || enabledForAllChains"
      exclude-eth-staking
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
        :disabled="edit"
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

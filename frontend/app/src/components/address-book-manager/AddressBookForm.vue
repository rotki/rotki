<script setup lang="ts">
import { helpers, required } from '@vuelidate/validators';
import { isValidEthAddress, toSentenceCase } from '@/utils/text';
import { toMessages } from '@/utils/validation';
import type {
  AddressBookLocation,
  AddressBookPayload,
} from '@/types/eth-names';

const props = withDefaults(
  defineProps<{
    value: AddressBookPayload;
    edit: boolean;
    enableForAllChains?: boolean;
  }>(),
  {
    enableForAllChains: false,
  },
);

const emit = defineEmits<{
  (e: 'input', value: AddressBookPayload): void;
  (e: 'valid', valid: boolean): void;
  (e: 'update:enable-for-all-chains', enable: boolean): void;
}>();

const { t } = useI18n();

const name = useSimplePropVModel(props, 'name', emit);
const address = useSimplePropVModel(props, 'address', emit);
const location = useSimplePropVModel(props, 'location', emit);
const blockchain = useSimplePropVModel(props, 'blockchain', emit);
const enabledForAllChains = useKebabVModel(props, 'enableForAllChains', emit);

const addressesNamesStore = useAddressesNamesStore();
const { getAddressesWithoutNames } = addressesNamesStore;

const addressSuggestions = getAddressesWithoutNames();
const locations: AddressBookLocation[] = ['global', 'private'];

const rules = {
  address: {
    required: helpers.withMessage(
      t('address_book.form.validation.address'),
      required,
    ),
    isValidEthAddress: helpers.withMessage(
      t('address_book.form.validation.valid'),
      isValidEthAddress,
    ),
  },
  name: {
    required: helpers.withMessage(
      t('address_book.form.validation.name'),
      required,
    ),
  },
};

const { setValidation } = useAddressBookForm();

const v$ = setValidation(
  rules,
  {
    address,
    name,
  },
  { $autoDirty: true },
);

const { getBlockie } = useBlockie();
</script>

<template>
  <form>
    <VSelect
      v-model="location"
      outlined
      :label="t('common.location')"
      :items="locations"
      :disabled="edit"
    >
      <template #item="{ item }">
        {{ toSentenceCase(item) }}
      </template>
      <template #selection="{ item }">
        {{ toSentenceCase(item) }}
      </template>
    </VSelect>
    <ChainSelect
      evm-only
      :model-value="blockchain"
      :disabled="edit || enableForAllChains"
      @update:model-value="blockchain = $event"
    />
    <RuiCheckbox
      v-model="enabledForAllChains"
      :disabled="edit"
      color="primary"
      class="-my-2"
      :label="t('address_book.form.labels.for_all_chain')"
    />
    <ComboboxWithCustomInput
      v-model="address"
      outlined
      :label="t('address_book.form.labels.address')"
      :items="addressSuggestions"
      :no-data-text="t('address_book.form.no_suggestions_available')"
      :disabled="edit"
      :error-messages="toMessages(v$.address)"
      auto-select-first
    >
      <template #prepend-inner>
        <span>
          <VAvatar
            size="24"
            class="mr-2"
            color="grey"
          >
            <AppImage
              v-if="value.address && isValidEthAddress(value.address)"
              :src="getBlockie(value.address)"
              size="1.5rem"
            />
          </VAvatar>
        </span>
      </template>
      <template #item="{ item }">
        <span v-if="item">
          <VAvatar
            size="24"
            class="mr-2"
          >
            <AppImage
              :src="getBlockie(item)"
              size="1.5rem"
            />
          </VAvatar>
        </span>
        {{ item }}
      </template>
    </ComboboxWithCustomInput>
    <RuiTextField
      v-model="name"
      variant="outlined"
      color="primary"
      :label="t('common.name')"
      :error-messages="toMessages(v$.name)"
    />
  </form>
</template>

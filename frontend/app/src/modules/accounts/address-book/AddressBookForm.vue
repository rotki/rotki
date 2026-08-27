<script setup lang="ts">
import type { ZodType } from 'zod';
import type { AddressBookLocation, AddressBookPayload } from '@/modules/accounts/address-book/eth-names';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import type { SelectOptions } from '@/modules/core/common/common-types';
import { Blockchain } from '@rotki/common';
import { addressBookEntrySchema } from '@/modules/accounts/address-book/address-book-form';
import { useAddressSuggestions } from '@/modules/accounts/address-book/use-address-suggestions';
import ChainSelect from '@/modules/accounts/blockchain/ChainSelect.vue';
import { useBlockie } from '@/modules/accounts/use-blockie';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useModelForm } from '@/modules/core/form/use-model-form';
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

const locations = computed<SelectOptions<AddressBookLocation>>(() => [
  { key: 'global', label: t('address_book.hint.global') },
  { key: 'private', label: t('address_book.hint.private') },
]);

const schema = computed<ZodType>(() => addressBookEntrySchema({
  address: t('address_book.form.validation.address'),
  chain: t('address_book.form.validation.chain'),
  name: t('address_book.form.validation.name'),
}));

const { errors: fieldErrors, state, touch, validate } = useModelForm<AddressBookPayload>({
  model: modelValue,
  schema,
  serverErrors: errors,
  stateUpdated,
  transientKeys: ['location'],
});

const addressSuggestions = useAddressSuggestions(() => state.blockchain, {
  clear: (): void => {
    state.address = '';
  },
  selected: () => state.address,
});

const { getBlockie } = useBlockie();

const chainOptions = computed<string[]>(() => [
  'all',
  ...get(supportedChains).map(item => item.id).filter(item => item !== Blockchain.ETH2),
]);

/** `ChainSelect` has no null in its model, while the payload uses it for "every chain". */
const blockchainModel = computed<string | undefined>({
  get() {
    return state.blockchain ?? undefined;
  },
  set(value?: string) {
    state.blockchain = value ?? null;
    touch('blockchain');
  },
});

defineExpose({
  validate,
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <RuiMenuSelect
      v-model="state.location"
      :label="t('common.location')"
      :options="locations"
      :disabled="editMode"
      key-attr="key"
      text-attr="label"
      variant="outlined"
      data-testid="address-book-form-location"
    />
    <ChainSelect
      v-model="blockchainModel"
      :disabled="editMode"
      :items="chainOptions"
      :error-messages="fieldErrors('blockchain')"
      data-testid="address-book-form-chain"
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
        v-model.trim="state.address"
        class="flex-1"
        :label="t('address_book.form.labels.address')"
        :items="addressSuggestions"
        :no-data-text="t('address_book.form.no_suggestions_available')"
        :disabled="editMode"
        :error-messages="fieldErrors('address')"
        clearable
        data-testid="address-book-form-address"
        @update:model-value="touch('address')"
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
      v-model="state.name"
      class="mt-2"
      variant="outlined"
      color="primary"
      :label="t('common.name')"
      :error-messages="fieldErrors('name')"
      data-testid="address-book-form-name"
      @update:model-value="touch('name')"
    />
  </div>
</template>

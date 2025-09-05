<script setup lang="ts">
import type LatestPriceForm from '@/components/price-manager/latest/LatestPriceForm.vue';
import type { AddressBookPayload } from '@/types/eth-names';
import { useTemplateRef } from 'vue';
import AddressBookForm from '@/components/address-book-manager/AddressBookForm.vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';
import { useMessageStore } from '@/store/message';
import { ApiValidationError } from '@/types/api/errors';

const open = defineModel<boolean>('open', { required: true });

const props = withDefaults(
  defineProps<{
    editableItem?: AddressBookPayload | null;
    editMode?: boolean;
    selectedChain?: string;
    location?: 'global' | 'private';
    root?: boolean;
  }>(),
  {
    editableItem: null,
    editMode: undefined,
    root: false,
  },
);

const emit = defineEmits<{
  (e: 'update:tab', tab: number): void;
  (e: 'refresh'): void;
}>();

const { editableItem, editMode, location, selectedChain } = toRefs(props);

const { t } = useI18n({ useScope: 'global' });

const modelValue = ref<AddressBookPayload>();
const loading = ref(false);
const errorMessages = ref<Record<string, string[]>>({});
const form = useTemplateRef<InstanceType<typeof LatestPriceForm>>('form');
const stateUpdated = ref(false);
const forAllChains = ref<boolean>(false);

const emptyForm: () => AddressBookPayload = () => ({
  address: '',
  blockchain: get(selectedChain) ?? null,
  location: get(location) || 'private',
  name: '',
});

const { addAddressBook, updateAddressBook } = useAddressesNamesStore();
const { setMessage } = useMessageStore();

async function save() {
  if (!isDefined(modelValue))
    return false;

  const formRef = get(form);
  const valid = await formRef?.validate();
  if (!valid)
    return false;

  const { address, blockchain, location, name } = get(modelValue);
  let success;
  const isEdit = get(editMode) ?? !!get(editableItem);
  const payload = {
    address: address.trim(),
    blockchain: get(forAllChains) ? null : blockchain,
    name: name.trim(),
  };

  set(loading, true);
  try {
    if (get(isEdit))
      success = await updateAddressBook(location, [payload]);
    else success = await addAddressBook(location, [payload], props.root);
  }
  catch (error: any) {
    success = false;
    let errors = error.message;

    if (error instanceof ApiValidationError)
      errors = error.getValidationErrors(get(modelValue));

    if (typeof errors === 'string') {
      const values = { message: error.message };
      const title = get(isEdit)
        ? t('address_book.actions.edit.error.title')
        : t('address_book.actions.add.error.title');
      const description = get(isEdit)
        ? t('address_book.actions.edit.error.description', values)
        : t('address_book.actions.add.error.description', values);
      setMessage({
        description,
        success: false,
        title,
      });
    }
    else {
      set(errorMessages, errors);
    }
  }

  set(loading, false);
  if (success) {
    set(modelValue, undefined);
    emit('update:tab', location === 'global' ? 0 : 1);
    emit('refresh');
  }
  return success;
}

const dialogTitle = computed<string>(() =>
  get(editableItem)
    ? t('address_book.dialog.edit_title')
    : t('address_book.dialog.add_title'),
);

watch(modelValue, (oldValue, currValue) => {
  if (currValue?.blockchain !== oldValue?.blockchain)
    set(errorMessages, {});
});

watchImmediate([open, editableItem], ([open, editableItem]) => {
  if (!open) {
    set(modelValue, undefined);
  }
  else {
    if (editableItem) {
      set(modelValue, editableItem);
    }
    else {
      set(modelValue, emptyForm());
    }
  }
});
</script>

<template>
  <BigDialog
    :display="!!modelValue"
    :title="dialogTitle"
    :primary-action="t('common.actions.save')"
    :loading="loading"
    :prompt-on-close="stateUpdated"
    @confirm="save()"
    @cancel="open = false"
  >
    <AddressBookForm
      v-if="modelValue"
      ref="form"
      v-model="modelValue"
      v-model:error-messages="errorMessages"
      v-model:state-updated="stateUpdated"
      v-model:for-all-chains="forAllChains"
      :edit-mode="editMode ?? !!editableItem"
    />
  </BigDialog>
</template>

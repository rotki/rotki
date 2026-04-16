<script setup lang="ts">
import type LatestPriceForm from '@/components/price-manager/latest/LatestPriceForm.vue';
import type { AddressBookPayload } from '@/modules/address-names/eth-names';
import { useTemplateRef } from 'vue';
import AddressBookForm from '@/components/address-book-manager/AddressBookForm.vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import { useAddressBookOperations } from '@/modules/address-names/use-address-book-operations';
import { ApiValidationError, type ValidationErrors } from '@/modules/api/types/errors';
import { getErrorMessage } from '@/modules/common/logging/error-handling';
import { useMessageStore } from '@/store/message';

const open = defineModel<boolean>('open', { required: true });

const {
  editableItem = null,
  editMode,
  location,
  root = false,
  selectedChain,
} = defineProps<{
  editableItem?: AddressBookPayload | null;
  editMode?: boolean;
  selectedChain?: string;
  location?: 'global' | 'private';
  root?: boolean;
}>();

const emit = defineEmits<{
  'update:tab': [tab: number];
  'refresh': [];
}>();

const { t } = useI18n({ useScope: 'global' });

const modelValue = ref<AddressBookPayload>();
const loading = ref(false);
const errorMessages = ref<Record<string, string[]>>({});
const form = useTemplateRef<InstanceType<typeof LatestPriceForm>>('form');
const stateUpdated = ref(false);

const emptyForm: () => AddressBookPayload = () => ({
  address: '',
  blockchain: selectedChain ?? 'all',
  location: location || 'private',
  name: '',
});

const { addAddressBook, updateAddressBook } = useAddressBookOperations();
const { setMessage } = useMessageStore();

function handleSaveError(error: unknown, isEdit: boolean, payload: AddressBookPayload): void {
  const message = getErrorMessage(error);
  let errors: string | ValidationErrors = message;

  if (error instanceof ApiValidationError)
    errors = error.getValidationErrors(payload);

  if (typeof errors === 'string') {
    const key = isEdit ? 'edit' : 'add';
    setMessage({
      description: t(`address_book.actions.${key}.error.description`, { message }),
      success: false,
      title: t(`address_book.actions.${key}.error.title`),
    });
  }
  else {
    set(errorMessages, errors);
  }
}

async function save(): Promise<boolean> {
  if (!isDefined(modelValue))
    return false;

  const formRef = get(form);
  const valid = await formRef?.validate();
  if (!valid)
    return false;

  const formValue = get(modelValue);
  const { address, blockchain, location, name } = formValue;
  const isEdit = editMode ?? !!editableItem;
  const payload = {
    address: address.trim(),
    blockchain: blockchain === 'all' ? null : blockchain,
    name: name.trim(),
  };

  set(loading, true);
  let success;
  try {
    success = isEdit
      ? await updateAddressBook(location, [payload])
      : await addAddressBook(location, [payload], root);
  }
  catch (error: unknown) {
    success = false;
    handleSaveError(error, isEdit, formValue);
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
  editableItem
    ? t('address_book.dialog.edit_title')
    : t('address_book.dialog.add_title'),
);

watch(modelValue, (oldValue, currValue) => {
  if (currValue?.blockchain !== oldValue?.blockchain)
    set(errorMessages, {});
});

watchImmediate([open, () => editableItem], ([open, editableItem]) => {
  if (!open) {
    set(modelValue, undefined);
  }
  else {
    if (editableItem) {
      set(modelValue, {
        ...editableItem,
        blockchain: editableItem.blockchain || 'all',
      });
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
      :edit-mode="editMode ?? !!editableItem"
    />
  </BigDialog>
</template>

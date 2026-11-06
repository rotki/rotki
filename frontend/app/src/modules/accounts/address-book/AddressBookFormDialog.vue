<script setup lang="ts">
import type { AddressBookPayload } from '@/modules/accounts/address-book/eth-names';
import { useTemplateRef } from 'vue';
import { type MessageKey, msg } from '@/message-key';
import AddressBookForm from '@/modules/accounts/address-book/AddressBookForm.vue';
import { useAddressBookOperations } from '@/modules/accounts/address-book/use-address-book-operations';
import { useSaveFailure } from '@/modules/core/form/use-save-failure';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';

const open = defineModel<boolean>('open', { required: true });

const {
  editableItem = null,
  editMode = false,
  location,
  root = false,
  selectedChain,
} = defineProps<{
  /** The entry the form starts from, which an addition may also have: see `editMode`. */
  editableItem?: AddressBookPayload | null;
  /**
   * Whether the entry is being updated rather than added.
   *
   * @remarks
   * Not derived from `editableItem`: the messages dialog seeds the form with the address the
   * backend asked the user to name, and that is still an addition.
   */
  editMode?: boolean;
  selectedChain?: string;
  /** The book a new entry starts in; after a save, the dialog reports the book it went into. */
  location?: 'global' | 'private';
  root?: boolean;
}>();

const emit = defineEmits<{
  'update:location': [location: 'global' | 'private'];
  'refresh': [];
}>();

const { t } = useI18n({ useScope: 'global' });

const modelValue = ref<AddressBookPayload>();
const loading = ref(false);
const form = useTemplateRef<InstanceType<typeof AddressBookForm>>('form');
const stateUpdated = ref(false);

const emptyForm: () => AddressBookPayload = () => ({
  address: '',
  blockchain: selectedChain ?? 'all',
  location: location || 'private',
  name: '',
});

const { addAddressBook, updateAddressBook } = useAddressBookOperations();
const { capture, clear, failure, modelFieldErrors } = useSaveFailure();

/**
 * The title of a failed save, one entry per operation.
 *
 * @remarks
 * Spelled out rather than interpolated. An inline template literal in `t()` makes the unused-key
 * lint rule treat its static prefix as used, which would exempt all of `address_book.actions.*`,
 * including the delete, fetch and tooltip keys this lookup never touches.
 */
const SAVE_ERROR_TITLES: Record<'add' | 'edit', MessageKey> = {
  add: msg.$t('address_book.actions.add.error.title'),
  edit: msg.$t('address_book.actions.edit.error.title'),
};

const failureTitle = computed<string>(() => t(SAVE_ERROR_TITLES[editMode ? 'edit' : 'add']));

async function save(): Promise<boolean> {
  if (!isDefined(modelValue))
    return false;

  const formRef = get(form);
  const valid = await formRef?.validate();
  if (!valid)
    return false;

  const formValue = get(modelValue);
  const { address, blockchain, location, name } = formValue;
  const payload = {
    address: address.trim(),
    blockchain: blockchain === 'all' ? null : blockchain,
    name: name.trim(),
  };

  set(loading, true);
  clear();
  let success;
  try {
    success = editMode
      ? await updateAddressBook(location, [payload])
      : await addAddressBook(location, [payload], root);
  }
  catch (error: unknown) {
    success = false;
    capture(error, formValue);
  }

  set(loading, false);
  if (success) {
    set(modelValue, undefined);
    set(open, false);
    emit('update:location', location);
    emit('refresh');
  }
  return success;
}

const dialogTitle = computed<string>(() =>
  editMode
    ? t('address_book.dialog.edit_title')
    : t('address_book.dialog.add_title'),
);

watch(modelValue, (oldValue, currValue) => {
  if (currValue?.blockchain !== oldValue?.blockchain)
    set(modelFieldErrors, {});
});

watchImmediate([open, () => editableItem], ([open, editableItem]) => {
  clear();
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
    :action="{ primary: t('common.actions.save') }"
    :layout="{ autoHeight: true, divide: true, maxWidth: '640px' }"
    :loading="loading"
    :prompt-on-close="stateUpdated"
    :failure="failure"
    :failure-title="failureTitle"
    @confirm="save()"
    @cancel="open = false"
  >
    <AddressBookForm
      v-if="modelValue"
      ref="form"
      v-model="modelValue"
      v-model:error-messages="modelFieldErrors"
      v-model:state-updated="stateUpdated"
      :edit-mode="editMode"
    />
  </BigDialog>
</template>

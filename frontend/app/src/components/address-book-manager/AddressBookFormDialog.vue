<script setup lang="ts">
import { ApiValidationError } from '@/types/api/errors';
import { useMessageStore } from '@/store/message';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';
import { useAddressBookForm } from '@/composables/address-book/form';
import type { AddressBookPayload } from '@/types/eth-names';

const enableForAllChains = defineModel<boolean>('enableForAllChains', { default: false, required: false });

const props = withDefaults(
  defineProps<{
    editMode?: boolean;
    payload: Partial<AddressBookPayload>;
    root?: boolean;
  }>(),
  {
    editMode: false,
    root: false,
  },
);

const emit = defineEmits<{
  (e: 'update:tab', tab: number): void;
}>();

const { editMode, payload: passedPayload } = toRefs(props);

const { openDialog, stateUpdated, submitting, trySubmit } = useAddressBookForm();

const { t } = useI18n();

const emptyForm: () => AddressBookPayload = () => ({
  address: '',
  blockchain: null,
  location: 'private',
  name: '',
});

const formPayload = ref<AddressBookPayload>(emptyForm());
const errorMessages = ref<{ address?: string[]; name?: string[] }>({});

const { closeDialog, setSubmitFunc } = useAddressBookForm();
const { addAddressBook, updateAddressBook } = useAddressesNamesStore();
const { setMessage } = useMessageStore();

const resetForm = function () {
  closeDialog();
  set(formPayload, emptyForm());
  set(enableForAllChains, false);
  set(errorMessages, {});
};

async function save() {
  try {
    const { address, blockchain, location, name } = get(formPayload);
    const payload = {
      address: address.trim(),
      blockchain: get(enableForAllChains) ? null : blockchain,
      name: name.trim(),
    };
    if (get(editMode))
      await updateAddressBook(location, [payload]);
    else await addAddressBook(location, [payload]);

    emit('update:tab', location === 'global' ? 0 : 1);

    closeDialog();
    return true;
  }
  catch (error: any) {
    let errors = error.message;

    if (error instanceof ApiValidationError)
      errors = error.getValidationErrors(get(formPayload));

    if (typeof errors === 'string') {
      const values = { message: error.message };
      const title = get(editMode)
        ? t('address_book.actions.edit.error.title')
        : t('address_book.actions.add.error.title');
      const description = get(editMode)
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
    return false;
  }
}

setSubmitFunc(save);

watchImmediate(passedPayload, () => {
  set(formPayload, {
    ...get(formPayload),
    ...get(passedPayload),
  });
  setSubmitFunc(save);
});

watch(formPayload, ({ blockchain }, { blockchain: oldBlockchain }) => {
  if (blockchain !== oldBlockchain)
    set(errorMessages, {});
});
</script>

<template>
  <BigDialog
    :display="openDialog"
    :title="editMode ? t('address_book.dialog.edit_title') : t('address_book.dialog.add_title')"
    :loading="submitting"
    :prompt-on-close="stateUpdated"
    @confirm="trySubmit()"
    @cancel="resetForm()"
  >
    <AddressBookForm
      v-model="formPayload"
      v-model:enable-for-all-chains="enableForAllChains"
      :edit="editMode"
      :error-messages="errorMessages"
    />
  </BigDialog>
</template>

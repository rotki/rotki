<script setup lang="ts">
import { type AddressBookPayload } from '@/types/eth-names';

defineProps<{
  value: AddressBookPayload;
  enableForAllChains: boolean;
  editMode: boolean;
}>();

const emit = defineEmits<{
  (e: 'input', value: AddressBookPayload): void;
  (e: 'update:enable-for-all-chains', enable: boolean): void;
  (e: 'reset'): void;
}>();

const { openDialog, submitting, trySubmit } = useAddressBookForm();

const resetForm = () => {
  emit('reset');
};

const { t } = useI18n();
</script>

<template>
  <BigDialog
    :display="openDialog"
    :title="
      editMode
        ? t('address_book.dialog.edit_title')
        : t('address_book.dialog.add_title')
    "
    :loading="submitting"
    @confirm="trySubmit()"
    @cancel="resetForm()"
  >
    <AddressBookForm
      :value="value"
      :edit="editMode"
      :enable-for-all-chains="enableForAllChains"
      @input="emit('input', $event)"
      @update:enable-for-all-chains="
        emit('update:enable-for-all-chains', $event)
      "
    />
  </BigDialog>
</template>

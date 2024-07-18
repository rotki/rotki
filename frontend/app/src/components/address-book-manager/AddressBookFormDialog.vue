<script setup lang="ts">
import type { AddressBookPayload } from '@/types/eth-names';

defineProps<{
  editMode: boolean;
  errorMessages: { address?: string[]; name?: string[] };
}>();

const emit = defineEmits<{
  (e: 'reset'): void;
}>();

const { openDialog, submitting, trySubmit } = useAddressBookForm();

const model = defineModel<AddressBookPayload>({ required: true });

const enabledForAllChains = defineModel<boolean>('enableForAllChains', { required: true });

function resetForm() {
  emit('reset');
}

const { t } = useI18n();
</script>

<template>
  <BigDialog
    :display="openDialog"
    :title="editMode ? t('address_book.dialog.edit_title') : t('address_book.dialog.add_title')"
    :loading="submitting"
    @confirm="trySubmit()"
    @cancel="resetForm()"
  >
    <AddressBookForm
      v-model="model"
      v-model:enable-for-all-chains="enabledForAllChains"
      :edit="editMode"
      :error-messages="errorMessages"
    />
  </BigDialog>
</template>

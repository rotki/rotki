<script setup lang="ts">
import type { AddressBookPayload } from '@/types/eth-names';

const props = defineProps<{
  modelValue: AddressBookPayload;
  enableForAllChains: boolean;
  editMode: boolean;
  errorMessages: { address?: string[]; name?: string[] };
}>();

const emit = defineEmits<{
  (e: 'update:model-value', value: AddressBookPayload): void;
  (e: 'update:enable-for-all-chains', enable: boolean): void;
  (e: 'reset'): void;
}>();

const { openDialog, submitting, trySubmit } = useAddressBookForm();

const model = useSimpleVModel(props, emit);
const enabledForAllChains = useKebabVModel(props, 'enableForAllChains', emit);

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

<script setup lang="ts">
import { type ExchangePayload } from '@/types/exchanges';

defineProps<{
  editMode: boolean;
  value: ExchangePayload;
}>();

const emit = defineEmits<{
  (e: 'input', value: ExchangePayload): void;
  (e: 'reset'): void;
}>();

const { t } = useI18n();

const { openDialog, submitting, trySubmit } = useExchangeApiKeysForm();

const resetForm = () => {
  emit('reset');
};
</script>

<template>
  <BigDialog
    :display="openDialog"
    :title="
      editMode
        ? t('exchange_settings.dialog.edit.title')
        : t('exchange_settings.dialog.add.title')
    "
    :primary-action="t('common.actions.save')"
    :secondary-action="t('common.actions.cancel')"
    :loading="submitting"
    @confirm="trySubmit()"
    @cancel="resetForm()"
  >
    <ExchangeKeysForm
      :exchange="value"
      :edit-mode="editMode"
      @input="emit('input', $event)"
    />
  </BigDialog>
</template>

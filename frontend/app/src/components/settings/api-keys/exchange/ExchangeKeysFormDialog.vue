<script setup lang="ts">
import type { ExchangePayload } from '@/types/exchanges';

const props = defineProps<{
  editMode: boolean;
  modelValue: ExchangePayload;
}>();

const emit = defineEmits<{
  (e: 'update:model-value', value: ExchangePayload): void;
  (e: 'reset'): void;
}>();

const { t } = useI18n();

const model = useSimpleVModel(props, emit);

const { openDialog, submitting, trySubmit } = useExchangeApiKeysForm();

function resetForm() {
  emit('reset');
}
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
      v-model="model"
      :edit-mode="editMode"
    />
  </BigDialog>
</template>

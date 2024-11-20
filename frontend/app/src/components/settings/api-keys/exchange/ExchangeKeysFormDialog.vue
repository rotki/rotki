<script setup lang="ts">
import type { ExchangePayload } from '@/types/exchanges';

const model = defineModel<ExchangePayload>({ required: true });

defineProps<{
  editMode: boolean;
}>();

const emit = defineEmits<{
  (e: 'reset'): void;
}>();

const { t } = useI18n();

const { openDialog, submitting, trySubmit, stateUpdated } = useExchangeApiKeysForm();

function resetForm() {
  emit('reset');
}
</script>

<template>
  <BigDialog
    :display="openDialog"
    :title="editMode ? t('exchange_settings.dialog.edit.title') : t('exchange_settings.dialog.add.title')"
    :primary-action="t('common.actions.save')"
    :secondary-action="t('common.actions.cancel')"
    :loading="submitting"
    :prompt-on-close="stateUpdated"
    @confirm="trySubmit()"
    @cancel="resetForm()"
  >
    <ExchangeKeysForm
      v-model="model"
      :edit-mode="editMode"
    />
  </BigDialog>
</template>

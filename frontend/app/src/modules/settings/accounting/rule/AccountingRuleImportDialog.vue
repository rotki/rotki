<script setup lang="ts">
import { useMessageStore } from '@/modules/core/common/use-message-store';
import { useAccountingSettings } from '@/modules/settings/accounting/use-accounting-settings';

const model = defineModel<boolean>({ required: true });

defineProps<{
  loading: boolean;
}>();

const emit = defineEmits<{
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const importFile = ref<File>();

const { importJSON } = useAccountingSettings();
const { setMessage } = useMessageStore();

async function importData() {
  const file = get(importFile);
  if (!file)
    return;

  const response = await importJSON(file);

  if (response === null)
    return;

  const { success } = response;

  setMessage({
    description: success
      ? t('actions.accounting_rules.import.message.success')
      : t('actions.accounting_rules.import.message.failure', { description: response.message }),
    success,
    title: t('actions.accounting_rules.import.title'),
  });

  if (success) {
    set(model, false);
    set(importFile, undefined);
    emit('refresh');
  }
}
</script>

<template>
  <RuiDialog
    v-model="model"
    max-width="600"
  >
    <RuiCard>
      <template #header>
        {{ t('accounting_settings.rule.import') }}
      </template>
      <RuiFileUpload
        v-model="importFile"
        accept=".json"
        :upload-text="t('file_upload.dropzone.prefix')"
        :click-to-upload-text="t('file_upload.dropzone.choose')"
        :replace-text="t('file_upload.dropzone.replace')"
      />
      <template #footer>
        <div class="grow" />
        <RuiButton
          variant="text"
          color="primary"
          data-testid="accounting-rule-import-cancel"
          @click="model = false"
        >
          {{ t('common.actions.cancel') }}
        </RuiButton>
        <RuiButton
          color="primary"
          :disabled="!importFile"
          :loading="loading"
          data-testid="accounting-rule-import-confirm"
          @click="importData()"
        >
          {{ t('common.actions.import') }}
        </RuiButton>
      </template>
    </RuiCard>
  </RuiDialog>
</template>

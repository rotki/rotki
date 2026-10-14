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
const importError = ref<string>('');

const { importJSON } = useAccountingSettings();
const { setMessage } = useMessageStore();

/** A new pick clears the last attempt's error, so it never sits next to a different file. */
function onFileChange(): void {
  set(importError, '');
}

/**
 * Imports the chosen file. A failure stays on the field with the file kept, so it can be fixed and
 * retried; a success closes the dialog and reloads the rules.
 */
async function importData(): Promise<void> {
  const file = get(importFile);
  if (!file)
    return;

  const response = await importJSON(file);

  if (response === null)
    return;

  if (!response.success) {
    set(importError, t('actions.accounting_rules.import.message.failure', { description: response.message }));
    return;
  }

  setMessage({
    description: t('actions.accounting_rules.import.message.success'),
    success: true,
    title: t('actions.accounting_rules.import.title'),
  });
  set(model, false);
  set(importFile, undefined);
  emit('refresh');
}
</script>

<template>
  <RuiDialog
    v-model="model"
    max-width="560"
  >
    <RuiCard>
      <template #header>
        {{ t('accounting_settings.rule.import') }}
      </template>
      <RuiFileUpload
        v-model="importFile"
        accept=".json"
        :disabled="loading"
        :error-messages="importError ? [importError] : []"
        :hint="t('accounting_settings.rule.import_hint')"
        :upload-text="t('file_upload.dropzone.prefix')"
        :click-to-upload-text="t('file_upload.dropzone.choose')"
        :replace-text="t('file_upload.dropzone.replace')"
        data-testid="accounting-rule-import-file"
        @update:model-value="onFileChange()"
        @error="importError = $event"
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

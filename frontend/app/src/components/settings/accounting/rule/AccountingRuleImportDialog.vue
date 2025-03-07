<script setup lang="ts">
import FileUpload from '@/components/import/FileUpload.vue';
import { useAccountingSettings } from '@/composables/settings/accounting';
import { useMessageStore } from '@/store/message';

const model = defineModel<boolean>({ required: true });

defineProps<{
  loading: boolean;
}>();

const emit = defineEmits<{
  (e: 'refresh'): void;
}>();

const { t } = useI18n();

const importFileUploader = ref<InstanceType<typeof FileUpload>>();
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
    get(importFileUploader)?.removeFile();
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
      <FileUpload
        ref="importFileUploader"
        v-model="importFile"
        source="json"
        file-filter=".json"
      />
      <template #footer>
        <div class="grow" />
        <RuiButton
          variant="text"
          color="primary"
          @click="model = false"
        >
          {{ t('common.actions.cancel') }}
        </RuiButton>
        <RuiButton
          color="primary"
          :disabled="!importFile"
          :loading="loading"
          @click="importData()"
        >
          {{ t('common.actions.import') }}
        </RuiButton>
      </template>
    </RuiCard>
  </RuiDialog>
</template>

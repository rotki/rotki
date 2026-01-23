<script setup lang="ts">
import { assert, Severity } from '@rotki/common';
import FileUpload from '@/components/import/FileUpload.vue';
import SettingsItem from '@/components/settings/controls/SettingsItem.vue';
import { useAssets } from '@/composables/assets';
import { useNotificationsStore } from '@/store/notifications';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';

const zip = ref<File>();
const importError = ref<string>('');
const uploading = ref<boolean>(false);
const uploaded = ref<boolean>(false);

const { t } = useI18n({ useScope: 'global' });
const { notify } = useNotificationsStore();
const { useIsTaskRunning } = useTaskStore();
const { exportCustomAssets, importCustomAssets } = useAssets();

const importDisabled = computed<boolean>(() => !get(zip));
const exporting = useIsTaskRunning(TaskType.EXPORT_ASSET);

async function importZip(): Promise<void> {
  const file = get(zip);
  assert(file);
  set(uploading, true);
  const result = await importCustomAssets(file);
  if (result.success)
    set(uploaded, true);
  else set(importError, result.message);

  set(uploading, false);
  set(zip, undefined);
}

async function exportZip(): Promise<void> {
  if (get(exporting))
    return;

  const result = await exportCustomAssets();

  // Only show notification for errors or when running in Electron (directory provided)
  // In web case, user sees the browser download prompt
  if ('success' in result && !result.success) {
    notify({
      display: true,
      message: t('manage_user_assets.export.error', { message: result.message }),
      severity: Severity.ERROR,
      title: t('manage_user_assets.export.title'),
    });
  }
  else if ('filePath' in result && result.directory) {
    notify({
      display: true,
      message: t('manage_user_assets.export.success', { filePath: result.filePath }),
      severity: Severity.INFO,
      title: t('manage_user_assets.export.title'),
    });
  }
}
</script>

<template>
  <RuiAlert
    type="info"
    class="mt-4"
  >
    {{ t('manage_user_assets.warning') }}
  </RuiAlert>

  <SettingsItem>
    <template #title>
      {{ t('manage_user_assets.export.title') }}
    </template>
    <template #subtitle>
      {{ t('manage_user_assets.export.subtitle') }}
    </template>
    <div class="flex flex-col gap-4 items-end">
      <RuiButton
        color="primary"
        :loading="exporting"
        @click="exportZip()"
      >
        {{ t('manage_user_assets.export.button') }}
      </RuiButton>
    </div>
  </SettingsItem>
  <SettingsItem>
    <template #title>
      {{ t('common.actions.import') }}
    </template>
    <template #subtitle>
      {{ t('manage_user_assets.import.subtitle') }}
    </template>
    <FileUpload
      v-model="zip"
      source="zip"
      file-filter=".zip"
      class="bg-white dark:bg-transparent"
      :uploaded="uploaded"
      :error-message="importError"
      @update:uploaded="uploaded = $event"
      @update:error-message="importError = $event"
    />
    <div class="flex justify-end">
      <RuiButton
        color="primary"
        class="mt-4"
        :disabled="importDisabled"
        :loading="uploading"
        @click="importZip()"
      >
        {{ t('common.actions.import') }}
      </RuiButton>
    </div>
  </SettingsItem>
</template>

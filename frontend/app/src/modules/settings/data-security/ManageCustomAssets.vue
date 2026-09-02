<script setup lang="ts">
import { assert, Severity } from '@rotki/common';
import { useAssets } from '@/modules/assets/use-assets';
import { useNotificationDispatcher } from '@/modules/core/notifications/use-notification-dispatcher';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import { ActivityPart } from '@/modules/task-center/core/types';
import { ActivityKind, useTaskCenter } from '@/modules/task-center/use-task-center';
import FileUpload from '@/modules/user-data/FileUpload.vue';

const zip = ref<File>();
const importError = ref<string>('');
const uploading = ref<boolean>(false);
const uploaded = ref<boolean>(false);

const { t } = useI18n({ useScope: 'global' });
const { notify } = useNotificationDispatcher();
const { useIsActive } = useTaskCenter();
const { exportCustomAssets, importCustomAssets } = useAssets();

const importDisabled = computed<boolean>(() => !get(zip));
const exporting = useIsActive(ActivityKind.ASSETS, ActivityPart.EXPORT);

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

/**
 * The notification an export result deserves, if any.
 *
 * @remarks
 * A success in the web build earns none. The browser shows its own download prompt, and a second
 * confirmation from the app would only repeat it. A desktop export picks a directory first, so its
 * path is worth reporting, because nothing else tells the user where the file went.
 *
 * @param result - what the export returned, which names either a failure or a written file
 * @returns the payload to notify with, or `undefined` when the export should pass silently
 */
function exportNotification(result: Awaited<ReturnType<typeof exportCustomAssets>>): Parameters<typeof notify>[0] | undefined {
  const title = t('manage_user_assets.export.title');

  if ('success' in result && !result.success) {
    return {
      display: true,
      message: t('manage_user_assets.export.error', { message: result.message }),
      severity: Severity.ERROR,
      title,
    };
  }

  if ('filePath' in result && result.directory) {
    return {
      display: true,
      message: t('manage_user_assets.export.success', { filePath: result.filePath }),
      severity: Severity.INFO,
      title,
    };
  }

  return undefined;
}

async function exportZip(): Promise<void> {
  if (get(exporting))
    return;

  const notification = exportNotification(await exportCustomAssets());
  if (notification)
    notify(notification);
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

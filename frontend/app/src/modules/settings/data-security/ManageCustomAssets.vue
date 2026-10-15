<script setup lang="ts">
import { assert, Priority, Severity } from '@rotki/common';
import { RuiFileUpload } from '@rotki/ui-library';
import { useAssets } from '@/modules/assets/use-assets';
import { useNotificationDispatcher } from '@/modules/core/notifications/use-notification-dispatcher';
import { isActionable } from '@/modules/core/tasks/task-result';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import { ActivityPart } from '@/modules/task-center/core/types';
import { ActivityKind, useTaskCenter } from '@/modules/task-center/use-task-center';

const uploader = useTemplateRef<InstanceType<typeof RuiFileUpload>>('uploader');
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

/**
 * Drops the last import's outcome once another file is picked, so it is never shown beside a
 * file it was not about.
 *
 * @param file - the uploader's new value, empty when the file was removed rather than picked
 */
function onFileChange(file: File | File[] | undefined): void {
  if (!file)
    return;

  set(importError, '');
  set(uploaded, false);
}

/**
 * Imports the picked archive, then empties the uploader whatever the outcome. The uploader's own
 * `removeFile` resets the hidden input too, so picking the same archive again still registers.
 */
async function importZip(): Promise<void> {
  const file = get(zip);
  assert(file);
  set(uploading, true);
  const result = await importCustomAssets(file);
  if (result.success)
    set(uploaded, true);
  else set(importError, result.message);

  set(uploading, false);
  get(uploader)?.removeFile();
}

/**
 * The notification an export result deserves, if any.
 *
 * @remarks
 * A success in the web build earns none. The browser shows its own download prompt, and a second
 * confirmation from the app would only repeat it. A desktop export picks a directory first, so its
 * path is worth reporting, because nothing else tells the user where the file went. A cancelled
 * export earns none either.
 *
 * @param outcome - what the export returned, which names either a failure or a written file
 * @returns the payload to notify with, or `undefined` when the export should pass silently
 */
function exportNotification(outcome: Awaited<ReturnType<typeof exportCustomAssets>>): Parameters<typeof notify>[0] | undefined {
  const title = t('manage_user_assets.export.title');

  if (!outcome.ok) {
    return isActionable(outcome.error)
      ? { message: t('manage_user_assets.export.error', { message: outcome.error.message }), severity: Severity.ERROR, title }
      : undefined;
  }

  const { directory, filePath } = outcome.value;
  return directory
    ? { message: t('manage_user_assets.export.success', { filePath }), severity: Severity.INFO, title }
    : undefined;
}

async function exportZip(): Promise<void> {
  if (get(exporting))
    return;

  const notification = exportNotification(await exportCustomAssets());
  if (notification)
    notify({ ...notification, priority: Priority.HIGH });
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
    <RuiFileUpload
      ref="uploader"
      v-model="zip"
      accept=".zip"
      class="bg-white dark:bg-transparent"
      :uploaded="uploaded"
      :error-messages="importError"
      :hint="uploaded ? t('file_upload.import_complete') : undefined"
      :upload-text="t('file_upload.dropzone.prefix')"
      :click-to-upload-text="t('file_upload.dropzone.choose')"
      :replace-text="t('file_upload.dropzone.replace')"
      @update:model-value="onFileChange($event)"
    />
    <div class="flex justify-end">
      <RuiButton
        color="primary"
        class="mt-4"
        :disabled="importDisabled"
        :loading="uploading"
        data-testid="user-assets-import"
        @click="importZip()"
      >
        {{ t('common.actions.import') }}
      </RuiButton>
    </div>
  </SettingsItem>
</template>

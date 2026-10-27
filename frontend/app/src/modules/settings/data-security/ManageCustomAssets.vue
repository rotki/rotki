<script setup lang="ts">
import { assert, NotificationKind, Severity } from '@rotki/common';
import { RuiFileUpload } from '@rotki/ui-library';
import { assetExportActivity } from '@/modules/assets/assets.activity';
import { useAssets } from '@/modules/assets/use-assets';
import { useFailureMessage } from '@/modules/core/api/use-failure-message';
import { useNotificationDispatcher } from '@/modules/core/notifications/use-notification-dispatcher';
import { isActionable } from '@/modules/core/tasks/task-result';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

const uploader = useTemplateRef<InstanceType<typeof RuiFileUpload>>('uploader');
const zip = ref<File>();
const importError = ref<string>('');
const uploading = ref<boolean>(false);
const uploaded = ref<boolean>(false);
/** Why the last export failed; the dock row reports it too, this keeps it beside the button. */
const exportError = shallowRef<unknown>();

const { t } = useI18n({ useScope: 'global' });
const { notify } = useNotificationDispatcher();
const failureMessage = useFailureMessage();
const { useIsActive } = useTaskCenter();
const { exportCustomAssets, importCustomAssets } = useAssets();

const importDisabled = computed<boolean>(() => !get(zip));
const exporting = useIsActive(assetExportActivity.kind, ...assetExportActivity.partsOf());

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
 * Exports the custom assets and reports where the file went.
 *
 * @remarks
 * A failure is named beside the button. A success in the web build earns no notification: the
 * browser shows its own download prompt, and a second confirmation would only repeat it. A desktop
 * export picks a directory first, so its path is worth reporting, because nothing else tells the
 * user where the file went. A cancelled export, such as a closed directory picker, reports nothing.
 */
async function exportZip(): Promise<void> {
  if (get(exporting))
    return;

  set(exportError, undefined);
  const outcome = await exportCustomAssets();
  if (!outcome.ok) {
    if (isActionable(outcome.error))
      set(exportError, outcome.error);
    return;
  }

  const { directory, filePath } = outcome.value;
  if (directory) {
    notify({
      kind: NotificationKind.RESULT,
      message: t('manage_user_assets.export.success', { filePath }),
      severity: Severity.INFO,
      title: t('manage_user_assets.export.title'),
    });
  }
}
</script>

<template>
  <SettingsItem>
    <template #title>
      {{ t('manage_user_assets.export.title') }}
    </template>
    <template #subtitle>
      {{ t('manage_user_assets.export.subtitle') }}
    </template>
    <RuiButton
      variant="outlined"
      color="primary"
      :loading="exporting"
      data-testid="user-assets-export"
      @click="exportZip()"
    >
      <template #prepend>
        <RuiIcon
          name="lu-download"
          size="16"
        />
      </template>
      {{ t('manage_user_assets.export.button') }}
    </RuiButton>
    <FailureStrip
      v-if="exportError"
      :retryable="false"
      class="mt-3"
      :title="t('manage_user_assets.export.failed')"
      :message="failureMessage(exportError)"
      data-testid="user-assets-export-error"
    />
  </SettingsItem>
  <SettingsItem>
    <template #title>
      {{ t('common.actions.import') }}
    </template>
    <template #subtitle>
      {{ t('manage_user_assets.import.subtitle') }}
    </template>
    <div class="flex flex-col gap-3">
      <RuiFileUpload
        ref="uploader"
        v-model="zip"
        accept=".zip"
        :loading="uploading"
        :uploaded="uploaded"
        :error-messages="importError ? [importError] : []"
        :hint="uploaded ? t('file_upload.import_complete') : t('manage_user_assets.warning')"
        :upload-text="t('file_upload.dropzone.prefix')"
        :click-to-upload-text="t('file_upload.dropzone.choose')"
        :replace-text="t('file_upload.dropzone.replace')"
        data-testid="user-assets-import-file"
        @update:model-value="onFileChange($event)"
        @error="importError = $event"
      />
      <RuiButton
        color="primary"
        class="self-start"
        :disabled="importDisabled"
        :loading="uploading"
        data-testid="user-assets-import"
        @click="importZip()"
      >
        <template #prepend>
          <RuiIcon
            name="lu-upload"
            size="16"
          />
        </template>
        {{ t('common.actions.import') }}
      </RuiButton>
    </div>
  </SettingsItem>
</template>

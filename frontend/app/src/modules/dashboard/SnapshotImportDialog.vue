<script lang="ts" setup>
const model = defineModel<boolean>({ required: true });

const balanceFile = defineModel<File>('balanceFile');

const locationFile = defineModel<File>('locationFile');

const { loading = false, persistent = false } = defineProps<{
  loading?: boolean;
  persistent?: boolean;
}>();

const emit = defineEmits<{
  import: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const complete = logicAnd(balanceFile, locationFile);
</script>

<template>
  <RuiDialog
    v-model="model"
    max-width="560"
    :persistent="persistent"
  >
    <template #activator="{ attrs }">
      <RuiButton
        color="primary"
        variant="outlined"
        v-bind="attrs"
      >
        <template #prepend>
          <RuiIcon name="lu-folder-input" />
        </template>
        {{ t('common.actions.import') }}
      </RuiButton>
    </template>

    <RuiCard data-testid="snapshot-import-dialog">
      <template #header>
        {{ t('snapshot_import_dialog.title') }}
      </template>
      <template #subheader>
        {{ t('snapshot_import_dialog.description') }}
      </template>

      <div class="flex flex-col gap-4">
        <div class="flex flex-col gap-2">
          <div class="text-sm font-medium text-rui-text">
            {{ t('snapshot_import_dialog.balance_snapshot_file') }}
          </div>
          <RuiFileUpload
            v-model="balanceFile"
            accept=".csv"
            :disabled="loading"
            :upload-text="t('file_upload.dropzone.prefix')"
            :click-to-upload-text="t('file_upload.dropzone.choose')"
            :replace-text="t('file_upload.dropzone.replace')"
            :hint="t('snapshot_import_dialog.balance_snapshot_file_suggested')"
            data-testid="snapshot-import-balance-file"
          />
        </div>
        <div class="flex flex-col gap-2">
          <div class="text-sm font-medium text-rui-text">
            {{ t('snapshot_import_dialog.location_data_snapshot_file') }}
          </div>
          <RuiFileUpload
            v-model="locationFile"
            accept=".csv"
            :disabled="loading"
            :upload-text="t('file_upload.dropzone.prefix')"
            :click-to-upload-text="t('file_upload.dropzone.choose')"
            :replace-text="t('file_upload.dropzone.replace')"
            :hint="t('snapshot_import_dialog.location_data_snapshot_suggested')"
            data-testid="snapshot-import-location-file"
          />
        </div>
      </div>

      <template #footer>
        <div class="w-full" />
        <RuiButton
          color="primary"
          variant="text"
          @click="model = false"
        >
          {{ t('common.actions.cancel') }}
        </RuiButton>
        <RuiButton
          color="primary"
          :disabled="!complete"
          :loading="loading"
          data-testid="snapshot-import-submit"
          @click="emit('import')"
        >
          {{ t('common.actions.import') }}
        </RuiButton>
      </template>
    </RuiCard>
  </RuiDialog>
</template>

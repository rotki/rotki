<script lang="ts" setup>
import FileUpload from '@/modules/user-data/FileUpload.vue';

const model = defineModel<boolean>({ required: true });

const balanceFile = defineModel<File>('balanceFile', {
  default: undefined,
});

const locationFile = defineModel<File>('locationFile', {
  default: undefined,
});

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
    max-width="650"
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

      <div class="grid grid-cols-2 gap-2">
        <div>
          <div class="font-bold">
            {{ t('snapshot_import_dialog.balance_snapshot_file') }}
          </div>
          <div
            class="py-2"
            data-testid="snapshot-import-balance-file"
          >
            <FileUpload
              v-model="balanceFile"
              source="csv"
            />
          </div>
          <div class="text-caption">
            {{ t('snapshot_import_dialog.balance_snapshot_file_suggested') }}
          </div>
        </div>
        <div>
          <div class="font-bold">
            {{ t('snapshot_import_dialog.location_data_snapshot_file') }}
          </div>
          <div
            class="py-2"
            data-testid="snapshot-import-location-file"
          >
            <FileUpload
              v-model="locationFile"
              source="csv"
            />
          </div>
          <div class="text-caption">
            {{ t('snapshot_import_dialog.location_data_snapshot_suggested') }}
          </div>
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

<script lang="ts" setup>
const props = withDefaults(
  defineProps<{
    value: boolean;
    balanceFile: File | null;
    locationFile: File | null;
    loading?: boolean;
    persistent?: boolean;
  }>(),
  {
    loading: false,
    persistent: false
  }
);

const emit = defineEmits<{
  (e: 'input', value: boolean): void;
  (e: 'import'): boolean;
  (e: 'update:balance-file', file: File | null): void;
  (e: 'update:location-file', file: File | null): void;
}>();

const { t } = useI18n();
const visible = useVModel(props, 'value', emit, { eventName: 'input' });

const balanceFile = computed<File | null>({
  get() {
    return props.balanceFile;
  },
  set(value) {
    emit('update:balance-file', value);
  }
});

const locationFile = computed<File | null>({
  get() {
    return props.locationFile;
  },
  set(value) {
    emit('update:location-file', value);
  }
});

const complete = logicOr(balanceFile, locationFile);
</script>

<template>
  <VDialog v-model="visible" max-width="600" :persistent="persistent">
    <template #activator="{ on }">
      <RuiButton color="primary" variant="outlined" v-on="on">
        <template #prepend>
          <RuiIcon name="folder-received-line" />
        </template>
        {{ t('common.actions.import') }}
      </RuiButton>
    </template>

    <RuiCard>
      <template #header>
        {{ t('snapshot_import_dialog.title') }}
      </template>

      <div class="pt-2 flex flex-row gap-2">
        <div>
          <div class="font-bold">
            {{ t('snapshot_import_dialog.balance_snapshot_file') }}
          </div>
          <div class="py-2">
            <FileUpload v-model="balanceFile" source="csv" />
          </div>
          <div class="text-caption">
            {{ t('snapshot_import_dialog.balance_snapshot_file_suggested') }}
          </div>
        </div>
        <div>
          <div class="font-bold">
            {{ t('snapshot_import_dialog.location_data_snapshot_file') }}
          </div>
          <div class="py-2">
            <FileUpload v-model="locationFile" source="csv" />
          </div>
          <div class="text-caption">
            {{ t('snapshot_import_dialog.location_data_snapshot_suggested') }}
          </div>
        </div>
      </div>

      <template #footer>
        <div class="w-full" />
        <RuiButton color="primary" variant="text" @click="visible = false">
          {{ t('common.actions.cancel') }}
        </RuiButton>
        <RuiButton
          color="primary"
          variant="outlined"
          :disabled="!complete"
          :loading="loading"
          @click="emit('import')"
        >
          {{ t('common.actions.import') }}
        </RuiButton>
      </template>
    </RuiCard>
  </VDialog>
</template>

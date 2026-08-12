<script setup lang="ts">
import type { BackendOptions } from '@shared/ipc';
import type { AdvancedBackendField } from '@/modules/settings/backend/backend-options-form';
import SettingResetButton from '@/modules/settings/SettingResetButton.vue';

const maxLogSize = defineModel<string>('maxLogSize', { required: true });
const maxLogFiles = defineModel<string>('maxLogFiles', { required: true });
const sqliteInstructions = defineModel<string>('sqliteInstructions', { required: true });
const logFromOtherModules = defineModel<boolean>('logFromOtherModules', { required: true });

const {
  atDefaults,
  fileConfig,
  loading = false,
  maxLogFilesErrors = [],
  maxLogSizeErrors = [],
  sqliteInstructionsErrors = [],
} = defineProps<{
  atDefaults: { maxLogFiles: boolean; maxLogSize: boolean; sqliteInstructions: boolean };
  fileConfig: Partial<BackendOptions>;
  loading?: boolean;
  maxLogFilesErrors?: string[];
  maxLogSizeErrors?: string[];
  sqliteInstructionsErrors?: string[];
}>();

const emit = defineEmits<{
  reset: [field: AdvancedBackendField];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="py-2">
    <RuiTextField
      v-model="maxLogSize"
      data-testid="max-log-size-input"
      class="mb-4"
      variant="outlined"
      color="primary"
      :hint="
        !!fileConfig.maxSizeInMbAllLogs
          ? t('backend_settings.config_file_disabled')
          : t('backend_settings.max_log_size.hint')
      "
      :label="t('backend_settings.max_log_size.label')"
      :disabled="!!fileConfig.maxSizeInMbAllLogs"
      :loading="loading"
      :error-messages="maxLogSizeErrors"
      type="number"
    >
      <template #append>
        <SettingResetButton
          v-if="!atDefaults.maxLogSize"
          data-testid="reset-max-log-size"
          @click="emit('reset', 'size')"
        />
      </template>
    </RuiTextField>
    <RuiTextField
      v-model="maxLogFiles"
      data-testid="max-log-files-input"
      variant="outlined"
      color="primary"
      class="mb-4"
      :hint="t('backend_settings.max_log_files.hint')"
      :label="
        !!fileConfig.maxLogfilesNum
          ? t('backend_settings.config_file_disabled')
          : t('backend_settings.max_log_files.label')
      "
      :disabled="!!fileConfig.maxLogfilesNum"
      :loading="loading"
      :error-messages="maxLogFilesErrors"
      type="number"
    >
      <template #append>
        <SettingResetButton
          v-if="!atDefaults.maxLogFiles"
          data-testid="reset-max-log-files"
          @click="emit('reset', 'files')"
        />
      </template>
    </RuiTextField>

    <RuiTextField
      v-model="sqliteInstructions"
      data-testid="sqlite-instructions-input"
      variant="outlined"
      color="primary"
      class="mb-4"
      :hint="
        !!fileConfig.sqliteInstructions
          ? t('backend_settings.config_file_disabled')
          : t('backend_settings.sqlite_instructions.hint')
      "
      :label="t('backend_settings.sqlite_instructions.label')"
      :disabled="!!fileConfig.sqliteInstructions"
      :loading="loading"
      :error-messages="sqliteInstructionsErrors"
      type="number"
    >
      <template #append>
        <SettingResetButton
          v-if="!atDefaults.sqliteInstructions"
          data-testid="reset-sqlite-instructions"
          @click="emit('reset', 'instructions')"
        />
      </template>
    </RuiTextField>

    <RuiCheckbox
      v-model="logFromOtherModules"
      color="primary"
      data-testid="log-from-other-modules-checkbox"
      :label="t('backend_settings.log_from_other_modules.label')"
      :disabled="fileConfig.logFromOtherModules"
      :hint="
        fileConfig.logFromOtherModules
          ? t('backend_settings.config_file_disabled')
          : t('backend_settings.log_from_other_modules.hint')
      "
    >
      {{ t('backend_settings.log_from_other_modules.label') }}
    </RuiCheckbox>
  </div>
</template>

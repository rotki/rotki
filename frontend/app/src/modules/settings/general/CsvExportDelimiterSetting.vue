<script setup lang="ts">
import { Defaults } from '@/modules/core/common/defaults';
import SettingText from '@/modules/settings/controls/SettingText.vue';

const { t } = useI18n({ useScope: 'global' });

function successMessage(delimiter: string): string {
  return t('general_settings.validation.csv_delimiter.success', { delimiter });
}
</script>

<template>
  <SettingText
    setting="csvExportDelimiter"
    maxlength="1"
    required
    :debounce="0"
    :max-length="1"
    :default="Defaults.DEFAULT_CSV_EXPORT_DELIMITER"
    :label="t('general_settings.labels.csv_delimiter')"
    :error-message="t('general_settings.validation.csv_delimiter.error')"
    :success-message="successMessage"
  />
</template>

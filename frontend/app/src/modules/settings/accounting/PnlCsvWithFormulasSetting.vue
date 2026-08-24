<script setup lang="ts">
import SettingSwitch from '@/modules/settings/controls/SettingSwitch.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingSwitch
    setting="pnlCsvWithFormulas"
    :debounce="1500"
    :label="t('account_settings.csv_export_settings.labels.export_csv_formulas')"
    :error-message="t('account_settings.messages.export_csv_formulas')"
  />
</template>

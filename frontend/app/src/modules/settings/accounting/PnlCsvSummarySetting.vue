<script setup lang="ts">
import SettingSwitch from '@/modules/settings/controls/SettingSwitch.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingSwitch
    setting="pnlCsvHaveSummary"
    class="csv_export_settings__haveCSVSummary"
    :debounce="1500"
    :label="t('account_settings.csv_export_settings.labels.have_csv_summary')"
    :error-message="t('account_settings.messages.have_csv_summary')"
  />
</template>

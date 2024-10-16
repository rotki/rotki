<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('account_settings.csv_export_settings.title') }}
    </template>
    <SettingsItem>
      <template #title>
        {{ t('account_settings.csv_export_settings.export_options') }}
      </template>
      <PnlCsvWithFormulasSetting />
      <PnlCsvSummarySetting />
    </SettingsItem>
  </SettingCategory>
</template>

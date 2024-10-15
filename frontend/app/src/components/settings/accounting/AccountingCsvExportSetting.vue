<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('account_settings.csv_export_settings.title') }}
    </template>

    <PnlCsvWithFormulasSetting />
    <PnlCsvSummarySetting />
    <CsvExportDelimiterSetting />
  </SettingCategory>
</template>

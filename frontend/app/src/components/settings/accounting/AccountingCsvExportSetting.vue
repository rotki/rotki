<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <SettingsItem>
    <template #title>
      {{ t('account_settings.csv_export_settings.title') }}
    </template>
    <template #default>
      <div class="pl-4 md:pl-8 lg:pl-12">
        <PnlCsvWithFormulasSetting />
        <PnlCsvSummarySetting />
      </div>
    </template>
  </SettingsItem>
</template>

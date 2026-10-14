<script setup lang="ts">
import PnlCsvSummarySetting from '@/modules/settings/accounting/PnlCsvSummarySetting.vue';
import PnlCsvWithFormulasSetting from '@/modules/settings/accounting/PnlCsvWithFormulasSetting.vue';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import SettingCategory from '@/modules/settings/SettingCategory.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('account_settings.csv_export_settings.title') }}
    </template>
    <SettingsItem setting-key="pnlCsvWithFormulas">
      <template #subtitle>
        {{ t('account_settings.csv_export_settings.descriptions.export_csv_formulas') }}
      </template>
      <PnlCsvWithFormulasSetting />
    </SettingsItem>
    <SettingsItem setting-key="pnlCsvHaveSummary">
      <template #subtitle>
        {{ t('account_settings.csv_export_settings.descriptions.have_csv_summary') }}
      </template>
      <PnlCsvSummarySetting />
    </SettingsItem>
  </SettingCategory>
</template>

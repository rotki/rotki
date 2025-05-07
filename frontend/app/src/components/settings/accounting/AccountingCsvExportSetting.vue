<script setup lang="ts">
import PnlCsvSummarySetting from '@/components/settings/accounting/PnlCsvSummarySetting.vue';
import PnlCsvWithFormulasSetting from '@/components/settings/accounting/PnlCsvWithFormulasSetting.vue';
import SettingsItem from '@/components/settings/controls/SettingsItem.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingsItem>
    <template #title>
      {{ t('account_settings.csv_export_settings.title') }}
    </template>
    <div class="pl-4 md:pl-8 lg:pl-12">
      <PnlCsvWithFormulasSetting />
      <PnlCsvSummarySetting />
    </div>
  </SettingsItem>
</template>

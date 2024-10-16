<script setup lang="ts">
import { NoteLocation } from '@/types/notes';

definePage({
  meta: {
    noteLocation: NoteLocation.SETTINGS_ACCOUNTING,
  },
});

enum Category {
  TRADE_SETTINGS = 'trade-settings',
  CSV_EXPORT = 'csv-export',
}

const { t } = useI18n();

const navigation = [
  { id: Category.TRADE_SETTINGS, label: t('accounting_settings.trade.title') },
  { id: Category.CSV_EXPORT, label: t('account_settings.csv_export_settings.title') },
];
</script>

<template>
  <div>
    <div class="py-4 border-b border-default flex flex-wrap gap-4 items-center justify-between">
      <SettingCategoryHeader>
        <template #title>
          {{ t('accounting_settings.rule.title') }}
        </template>
      </SettingCategoryHeader>
    </div>
    <div class="py-4">
      <AccountingRuleSetting />
    </div>
  </div>

  <SettingsPage :navigation="navigation">
    <AccountingTradeSettings :id="Category.TRADE_SETTINGS" />
    <AccountingCsvExportSetting :id="Category.CSV_EXPORT" />
  </SettingsPage>
</template>

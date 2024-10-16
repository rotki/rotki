<script setup lang="ts">
import { NoteLocation } from '@/types/notes';

definePage({
  meta: {
    canNavigateBack: true,
    noteLocation: NoteLocation.SETTINGS_ACCOUNTING,
  },
});

enum Category {
  ACCOUNTING_RULE = 'accounting-rule',
  TRADE_SETTINGS = 'trade-settings',
  CSV_EXPORT = 'csv-export',
}

const { t } = useI18n();

const navigation = [
  { id: Category.ACCOUNTING_RULE, label: t('accounting_settings.rule.title') },
  { id: Category.TRADE_SETTINGS, label: t('accounting_settings.trade.title') },
  { id: Category.CSV_EXPORT, label: t('account_settings.csv_export_settings.title') },
];
</script>

<template>
  <SettingsPage :navigation="navigation">
    <AccountingRuleSetting :id="Category.ACCOUNTING_RULE" />
    <AccountingTradeSettings :id="Category.TRADE_SETTINGS" />
    <AccountingCsvExportSetting :id="Category.CSV_EXPORT" />
  </SettingsPage>
</template>

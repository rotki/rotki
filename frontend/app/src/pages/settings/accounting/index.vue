<script setup lang="ts">
import { msg } from '@/message-key';
import { NoteLocation } from '@/modules/core/common/notes';
import CostBasisSettingsCategory from '@/modules/settings/accounting/CostBasisSettingsCategory.vue';
import PnlCsvSettingsCategory from '@/modules/settings/accounting/PnlCsvSettingsCategory.vue';
import AccountingRuleSetting from '@/modules/settings/accounting/rule/AccountingRuleSetting.vue';
import TaxSettingsCategory from '@/modules/settings/accounting/TaxSettingsCategory.vue';
import SettingsPage from '@/modules/settings/controls/SettingsPage.vue';
import { SettingsCategoryIds } from '@/modules/settings/setting-highlight-ids';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.settings_sub.accounting'), icon: 'lu-file-spreadsheet', parent: '/settings' },
    canNavigateBack: true,
    noteLocation: NoteLocation.SETTINGS_ACCOUNTING,
  },
});

const { t } = useI18n({ useScope: 'global' });

const navigation = computed<{ id: string; label: string }[]>(() => [
  { id: SettingsCategoryIds.ACCOUNTING_RULES, label: t('accounting_settings.rule.title') },
  { id: SettingsCategoryIds.COST_BASIS, label: t('accounting_settings.cost_basis.title') },
  { id: SettingsCategoryIds.TAXES, label: t('accounting_settings.taxes.title') },
  { id: SettingsCategoryIds.PNL_CSV, label: t('account_settings.csv_export_settings.title') },
]);
</script>

<template>
  <SettingsPage :navigation="navigation">
    <div :id="SettingsCategoryIds.ACCOUNTING_RULES">
      <AccountingRuleSetting />
    </div>
    <CostBasisSettingsCategory :id="SettingsCategoryIds.COST_BASIS" />
    <TaxSettingsCategory :id="SettingsCategoryIds.TAXES" />
    <PnlCsvSettingsCategory :id="SettingsCategoryIds.PNL_CSV" />
  </SettingsPage>
</template>

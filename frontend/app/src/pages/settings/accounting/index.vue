<script setup lang="ts">
import { NoteLocation } from '@/types/notes';
import AccountingCsvExportSetting from '@/components/settings/accounting/AccountingCsvExportSetting.vue';
import AccountingTradeSettings from '@/components/settings/accounting/AccountingTradeSettings.vue';
import AccountingRuleSetting from '@/components/settings/accounting/rule/AccountingRuleSetting.vue';
import SettingsPage from '@/components/settings/controls/SettingsPage.vue';

definePage({
  meta: {
    canNavigateBack: true,
    noteLocation: NoteLocation.SETTINGS_ACCOUNTING,
  },
});
</script>

<template>
  <SettingsPage>
    <div>
      <AccountingRuleSetting />
      <AccountingTradeSettings />
      <AccountingCsvExportSetting />
    </div>
  </SettingsPage>
</template>

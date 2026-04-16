<script setup lang="ts">
import { NoteLocation } from '@/modules/core/common/notes';
import AccountingCsvExportSetting from '@/modules/settings/accounting/AccountingCsvExportSetting.vue';
import AccountingTradeSettings from '@/modules/settings/accounting/AccountingTradeSettings.vue';
import AccountingRuleSetting from '@/modules/settings/accounting/rule/AccountingRuleSetting.vue';
import SettingsPage from '@/modules/settings/controls/SettingsPage.vue';

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

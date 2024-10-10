<script setup lang="ts">
import { NoteLocation } from '@/types/notes';

definePage({
  meta: {
    canNavigateBack: true,
    noteLocation: NoteLocation.SETTINGS_ACCOUNTING,
  },
});
</script>

<template>
  <SettingsPage class="accounting-settings">
    <AccountingRuleSetting />
    <AccountingTradeSettings />
    <AccountingCsvExportSetting />
  </SettingsPage>
</template>

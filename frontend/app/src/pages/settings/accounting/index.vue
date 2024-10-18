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
  <div class="accounting-settings flex flex-col">
    <AccountingRuleSetting />
    <AccountingTradeSettings />
    <AccountingCsvExportSetting />
  </div>
</template>

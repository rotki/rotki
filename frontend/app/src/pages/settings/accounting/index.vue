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
  <AccountingRuleSetting />
  <AccountingTradeSettings />
  <AccountingCsvExportSetting />
</template>

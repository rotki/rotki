<script setup lang="ts">
import { NoteLocation } from '@/types/notes';

definePage({
  meta: {
    noteLocation: NoteLocation.SETTINGS_ORACLE,
  },
});
</script>

<template>
  <SettingsPage>
    <PriceOracleSettings />
    <OracleCacheManagement />
  </SettingsPage>
</template>

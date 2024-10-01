<script setup lang="ts">
import { NoteLocation } from '@/types/notes';

definePage({
  meta: {
    noteLocation: NoteLocation.SETTINGS_DATABASE,
  },
});
</script>

<template>
  <SettingsPage>
    <AssetUpdate />
    <BackupManager />
    <DataManagement />
    <ManageCustomAssets />
    <RestoreAssetsDatabase />
  </SettingsPage>
</template>

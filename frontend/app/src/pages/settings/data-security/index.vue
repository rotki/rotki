<script setup lang="ts">
import { NoteLocation } from '@/types/notes';

definePage({
  meta: {
    noteLocation: NoteLocation.SETTINGS_DATA_SECURITY,
  },
});
</script>

<template>
  <div class="flex flex-col gap-8">
    <ChangePassword />
    <AssetUpdate />
    <BackupManager />
    <DataManagement />
    <OracleCacheManagement />
    <ManageCustomAssets />
    <RestoreAssetsDatabase />
  </div>
</template>

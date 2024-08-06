<script setup lang="ts">
import { NoteLocation } from '@/types/notes';

definePage({
  meta: {
    noteLocation: NoteLocation.SETTINGS_DATA_SECURITY,
  },
});
</script>

<template>
  <div>
    <ChangePassword />
    <AssetUpdate />
    <BackupManager class="mt-8" />
    <DataManagement />
    <OracleCacheManagement class="mt-8" />
    <ManageCustomAssets class="mt-8" />
    <RestoreAssetsDatabase />
  </div>
</template>

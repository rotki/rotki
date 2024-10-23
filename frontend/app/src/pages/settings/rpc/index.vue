<script setup lang="ts">
import { NoteLocation } from '@/types/notes';

definePage({
  meta: {
    noteLocation: NoteLocation.SETTINGS_RPC,
  },
});
</script>

<template>
  <SettingsPage>
    <RpcSettings />
  </SettingsPage>
</template>

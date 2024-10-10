<script setup lang="ts">
import { NoteLocation } from '@/types/notes';

definePage({
  meta: {
    noteLocation: NoteLocation.SETTINGS_INTERFACE,
  },
});
</script>

<template>
  <SettingsPage>
    <FrontendSettings />
  </SettingsPage>
</template>

<script setup lang="ts">
import SettingsPage from '@/components/settings/controls/SettingsPage.vue';
import RpcSettings from '@/components/settings/general/rpc/RpcSettings.vue';
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

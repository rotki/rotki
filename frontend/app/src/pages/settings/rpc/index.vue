<script setup lang="ts">
import { NoteLocation } from '@/types/notes';
import RpcSettings from '@/components/settings/general/rpc/RpcSettings.vue';
import SettingsPage from '@/components/settings/controls/SettingsPage.vue';

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

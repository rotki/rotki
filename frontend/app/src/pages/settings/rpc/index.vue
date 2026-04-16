<script setup lang="ts">
import { NoteLocation } from '@/modules/core/common/notes';
import SettingsPage from '@/modules/settings/controls/SettingsPage.vue';
import RpcSettings from '@/modules/settings/general/rpc/RpcSettings.vue';

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

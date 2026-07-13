<script setup lang="ts">
import { msg } from '@/message-key';
import { NoteLocation } from '@/modules/core/common/notes';
import SettingsPage from '@/modules/settings/controls/SettingsPage.vue';
import RpcSettings from '@/modules/settings/general/rpc/RpcSettings.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.settings_sub.rpc_nodes'), icon: 'lu-wifi', parent: '/settings' },
    noteLocation: NoteLocation.SETTINGS_RPC,
  },
});
</script>

<template>
  <SettingsPage>
    <RpcSettings />
  </SettingsPage>
</template>

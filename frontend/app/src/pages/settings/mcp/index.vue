<script setup lang="ts">
import { msg } from '@/message-key';
import { NoteLocation } from '@/modules/core/common/notes';
import McpServerSetting from '@/modules/settings/backend/McpServerSetting.vue';
import SettingsPage from '@/modules/settings/controls/SettingsPage.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.settings_sub.mcp'), icon: 'lu-bot', parent: '/settings' },
    noteLocation: NoteLocation.SETTINGS_MCP,
  },
});
</script>

<template>
  <SettingsPage>
    <McpServerSetting />
  </SettingsPage>
</template>

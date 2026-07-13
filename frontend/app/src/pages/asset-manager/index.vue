<script setup lang="ts">
import { msg } from '@/message-key';
import { NoteLocation } from '@/modules/core/common/notes';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.manage_assets'), icon: 'lu-manage-assets', section: 2, order: 20, drawer: 'asset-manager', addAction: { labelKey: msg.$t('asset_management.add_title') } },
    noteLocation: NoteLocation.ASSETS,
  },
  redirect: '/asset-manager/managed',
});
</script>

<template>
  <RouterView />
</template>

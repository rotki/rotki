<script setup lang="ts">
import { NoteLocation } from '@/modules/core/common/notes';

definePage({
  meta: {
    nav: { labelKey: 'navigation_menu.manage_assets', icon: 'lu-manage-assets', section: 2, order: 20, drawer: 'asset-manager', addAction: { labelKey: 'asset_management.add_title' } },
    noteLocation: NoteLocation.ASSETS,
  },
  redirect: '/asset-manager/managed',
});
</script>

<template>
  <RouterView />
</template>

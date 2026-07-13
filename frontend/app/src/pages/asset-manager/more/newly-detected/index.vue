<script setup lang="ts">
import { msg } from '@/message-key';
import NewlyDetectedAssetTable from '@/modules/assets/detection/NewlyDetectedAssetTable.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.manage_assets_sub.newly_detected'), icon: 'lu-list-collapse', parent: '/asset-manager/' },
  },
});
</script>

<template>
  <NewlyDetectedAssetTable />
</template>

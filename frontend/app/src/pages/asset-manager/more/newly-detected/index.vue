<script setup lang="ts">
import { msg } from '@/message-key';
import AssetManagerMoreTitle from '@/modules/assets/admin/AssetManagerMoreTitle.vue';
import NewlyDetectedAssetTable from '@/modules/assets/detection/NewlyDetectedAssetTable.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.manage_assets_sub.newly_detected'), icon: 'lu-list-collapse', parent: '/asset-manager/' },
  },
});
</script>

<template>
  <TablePageLayout child>
    <template #title>
      <AssetManagerMoreTitle />
    </template>
    <NewlyDetectedAssetTable />
  </TablePageLayout>
</template>

<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <TablePageLayout
    :title="[
      t('navigation_menu.manage_assets'),
      t('navigation_menu.manage_assets_sub.newly_detected')
    ]"
  >
    <NewlyDetectedAssetTable />
  </TablePageLayout>
</template>

<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <TablePageLayout>
    <template #title>
      <span class="text-rui-text-secondary">
        {{ t('navigation_menu.manage_assets') }} /
      </span>
      {{ t('navigation_menu.manage_assets_sub.newly_detected') }}
    </template>

    <NewlyDetectedAssetTable />
  </TablePageLayout>
</template>

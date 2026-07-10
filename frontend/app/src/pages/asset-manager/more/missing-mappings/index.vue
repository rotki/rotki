<script setup lang="ts">
import AssetMissingMappings from '@/modules/assets/admin/missing-mappings/AssetMissingMappings.vue';

definePage({
  meta: {
    nav: { labelKey: 'navigation_menu.manage_assets_sub.missing_mappings', icon: 'lu-scroll', parent: '/asset-manager/' },
  },
});
</script>

<template>
  <AssetMissingMappings />
</template>

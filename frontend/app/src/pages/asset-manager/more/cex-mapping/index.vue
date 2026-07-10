<script setup lang="ts">
import ManageCexMappingContent from '@/modules/assets/admin/cex-mapping/ManageCexMappingContent.vue';

definePage({
  meta: {
    nav: { labelKey: 'navigation_menu.manage_assets_sub.cex_mapping', icon: 'lu-scroll-text', parent: '/asset-manager/', addAction: { labelKey: 'asset_management.cex_mapping.add_title' } },
  },
});
</script>

<template>
  <ManageCexMappingContent />
</template>

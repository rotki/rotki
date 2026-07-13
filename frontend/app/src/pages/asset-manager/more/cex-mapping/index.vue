<script setup lang="ts">
import { msg } from '@/message-key';
import ManageCexMappingContent from '@/modules/assets/admin/cex-mapping/ManageCexMappingContent.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.manage_assets_sub.cex_mapping'), icon: 'lu-scroll-text', parent: '/asset-manager/', addAction: { labelKey: msg.$t('asset_management.cex_mapping.add_title') } },
  },
});
</script>

<template>
  <ManageCexMappingContent />
</template>

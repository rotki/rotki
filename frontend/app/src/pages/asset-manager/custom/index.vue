<script setup lang="ts">
import CustomAssetContent from '@/modules/assets/admin/custom/CustomAssetContent.vue';

definePage({
  meta: {
    nav: { labelKey: 'navigation_menu.manage_assets_sub.custom_assets', icon: 'lu-custom-assets', parent: '/asset-manager/', order: 20, drawer: 'asset-manager-custom' },
  },
  props: to => ({
    identifier: to.query.id ?? null,
  }),
});

const { identifier = null } = defineProps<{
  identifier?: string | null;
}>();
</script>

<template>
  <CustomAssetContent
    main-page
    :identifier="identifier"
  />
</template>

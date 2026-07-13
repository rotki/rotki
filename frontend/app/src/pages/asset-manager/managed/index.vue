<script setup lang="ts">
import { msg } from '@/message-key';
import ManagedAssetContent from '@/modules/assets/admin/managed/ManagedAssetContent.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.manage_assets_sub.assets'), icon: 'lu-manage-assets', parent: '/asset-manager/', order: 10, drawer: 'asset-manager-managed' },
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
  <ManagedAssetContent
    main-page
    :identifier="identifier"
  />
</template>

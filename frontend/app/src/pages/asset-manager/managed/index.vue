<script setup lang="ts">
import ManagedAssetContent from '@/modules/assets/admin/managed/ManagedAssetContent.vue';

definePage({
  name: 'asset-manager-managed',
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

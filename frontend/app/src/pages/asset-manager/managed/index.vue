<script setup lang="ts">
import ManagedAssetContent from '@/components/asset-manager/managed/ManagedAssetContent.vue';

definePage({
  name: 'asset-manager-managed',
  props: to => ({
    identifier: to.query.id ?? null,
  }),
});

const props = withDefaults(
  defineProps<{
    identifier?: string | null;
  }>(),
  { identifier: null },
);

const { identifier } = toRefs(props);
</script>

<template>
  <ManagedAssetContent
    main-page
    :identifier="identifier"
  />
</template>

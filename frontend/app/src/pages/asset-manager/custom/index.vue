<script setup lang="ts">
import CustomAssetContent from '@/components/asset-manager/custom/CustomAssetContent.vue';

definePage({
  name: 'asset-manager-custom',
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
  <CustomAssetContent
    main-page
    :identifier="identifier"
  />
</template>

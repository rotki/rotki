<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    identifier?: string | null;
  }>(),
  { identifier: null },
);

definePage({
  name: 'asset-manager-custom',
  props: to => ({
    identifier: to.query.id ?? null,
  }),
});

const { identifier } = toRefs(props);
</script>

<template>
  <CustomAssetContent
    main-page
    :identifier="identifier"
  />
</template>

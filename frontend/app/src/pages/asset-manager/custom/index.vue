<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    identifier?: string | null;
  }>(),
  { identifier: null }
);

const { identifier } = toRefs(props);
</script>

<template>
  <CustomAssetContent main-page :identifier="identifier" />
</template>

<script setup lang="ts">
import CustomAssetContent from '@/modules/assets/admin/custom/CustomAssetContent.vue';

definePage({
  name: 'asset-manager-custom',
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

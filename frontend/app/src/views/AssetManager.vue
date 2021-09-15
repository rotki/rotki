<template>
  <asset-management :identifier="identifier" />
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import AssetManagement from '@/components/asset-manager/AssetManagement.vue';

export default defineComponent({
  name: 'AssetManager',
  components: { AssetManagement },
  props: {
    identifier: { required: false, type: String, default: null }
  }
});
</script>

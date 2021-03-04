<template>
  <asset-management />
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import AssetManagement from '@/components/asset-manager/AssetManagement.vue';

@Component({
  components: { AssetManagement }
})
export default class AssetManager extends Vue {}
</script>

<style scoped lang="scss"></style>

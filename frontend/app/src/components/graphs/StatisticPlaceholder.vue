<script setup lang="ts">
import AppImage from '@/components/common/AppImage.vue';
import GetPremiumPlaceholder from '@/components/graphs/GetPremiumPlaceholder.vue';

const { t } = useI18n();
const { isMdAndDown } = useBreakpoint();

function getFullPath(fileName: string) {
  return `./assets/images/placeholder/${fileName}`;
}
</script>

<template>
  <div class="relative">
    <GetPremiumPlaceholder
      class="absolute z-1 pt-40 top-0 left-1/2 transform -translate-x-1/2"
      :title="t('premium_settings.chart_limit.statistic')"
    />
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-2">
      <AppImage
        class="lg:col-span-2"
        :src="isMdAndDown ? getFullPath('net_value_graph_placeholder_small.png') : getFullPath('net_value_graph_placeholder.png')"
      />
      <AppImage
        class="lg:col-span-2"
        :src="isMdAndDown ? getFullPath('asset_amount_and_value_graph_small.png') : getFullPath('asset_amount_and_value_graph.png')"
      />
      <AppImage :src="getFullPath('asset_distribution_by_location.png')" />
      <AppImage :src="getFullPath('asset_distribution_by_asset.png')" />
    </div>
  </div>
</template>

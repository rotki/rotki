<script setup lang="ts">
import AppImage from '@/components/common/AppImage.vue';
import GetPremiumPlaceholder from '@/components/common/GetPremiumPlaceholder.vue';

const { t } = useI18n({ useScope: 'global' });
const { isMdAndDown } = useBreakpoint();

function getFullPath(fileName: string) {
  return `./assets/images/placeholder/${fileName}`;
}
</script>

<template>
  <div class="relative">
    <div
      class="grid grid-cols-1 lg:grid-cols-2 gap-2 dark:invert-[0.9] dark:hue-rotate-[180deg]"
    >
      <AppImage
        class="lg:col-span-2 -m-4"
        :src="isMdAndDown ? getFullPath('net_value_graph_placeholder_small.png') : getFullPath('net_value_graph_placeholder.png')"
      />
      <AppImage
        class="lg:col-span-2 -m-4"
        :src="isMdAndDown ? getFullPath('asset_amount_and_value_graph_small.png') : getFullPath('asset_amount_and_value_graph.png')"
      />
      <AppImage
        class="-m-4"
        :src="getFullPath('asset_distribution_by_location.png')"
      />
      <AppImage
        class="-m-4"
        :src="getFullPath('asset_distribution_by_asset.png')"
      />
    </div>

    <GetPremiumPlaceholder
      class="absolute z-1 pt-40 top-0 left-1/2 transform -translate-x-1/2"
      :title="t('premium_settings.chart_limit.statistic')"
    />
  </div>
</template>

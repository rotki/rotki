<script setup lang="ts">
import { getPublicPlaceholderImagePath as getFullPath } from '@/modules/core/common/file/file';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import AppImage from '@/modules/shell/components/AppImage.vue';
import GetPremiumPlaceholder from '@/modules/shell/components/GetPremiumPlaceholder.vue';

const { t } = useI18n({ useScope: 'global' });
const { isMdAndDown } = useBreakpoint();

const { minimumTier } = useFeatureAccess(PremiumFeature.GRAPHS_VIEW);
</script>

<template>
  <div class="relative">
    <div
      class="grid grid-cols-1 lg:grid-cols-2 gap-2 dark:invert-[0.9] dark:hue-rotate-180"
    >
      <AppImage
        class="lg:col-span-2 -m-4"
        :src="isMdAndDown ? getFullPath('net_value_graph_placeholder_small.webp') : getFullPath('net_value_graph_placeholder.webp')"
      />
      <AppImage
        class="lg:col-span-2 -m-4"
        :src="isMdAndDown ? getFullPath('asset_amount_and_value_graph_small.webp') : getFullPath('asset_amount_and_value_graph.webp')"
      />
      <AppImage
        class="-m-4"
        :src="getFullPath('asset_distribution_by_location.webp')"
      />
      <AppImage
        class="-m-4"
        :src="getFullPath('asset_distribution_by_asset.webp')"
      />
    </div>

    <GetPremiumPlaceholder
      class="absolute z-1 pt-40 top-0 left-1/2 transform -translate-x-1/2"
      :title="t('premium_settings.chart_limit.statistic')"
      :minimum-tier="minimumTier"
    />
  </div>
</template>

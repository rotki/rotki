<script setup lang="ts">
import { getPublicPlaceholderImagePath } from '@/modules/core/common/file/file';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import AppImage from '@/modules/shell/components/AppImage.vue';
import GetPremiumPlaceholder from '@/modules/shell/components/GetPremiumPlaceholder.vue';

const { t } = useI18n({ useScope: 'global' });

const { minimumTier } = useFeatureAccess(PremiumFeature.GRAPHS_VIEW);
</script>

<template>
  <RuiCard content-class="-mx-3 !pt-0">
    <template #header>
      <div class="pt-2">
        {{ t('premium_components.statistics.asset_amount_and_value_over_time') }}
      </div>
    </template>
    <div class="relative">
      <AppImage
        class="dark:invert-[0.88] dark:hue-rotate-[180deg] -m-2"
        :src="getPublicPlaceholderImagePath('asset_amount_and_value_partial.png')"
      />

      <GetPremiumPlaceholder
        :title="t('premium_settings.chart_limit.title')"
        :minimum-tier="minimumTier"
        class="absolute z-1 pt-20 top-0 left-1/2 transform -translate-x-1/2 flex flex-col items-center justify-center text-center"
      />
    </div>
  </RuiCard>
</template>

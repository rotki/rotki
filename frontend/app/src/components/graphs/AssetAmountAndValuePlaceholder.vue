<script setup lang="ts">
import AppImage from '@/components/common/AppImage.vue';
import GetPremiumPlaceholder from '@/components/common/GetPremiumPlaceholder.vue';
import { getPublicPlaceholderImagePath } from '@/utils/file';

const { t } = useI18n({ useScope: 'global' });
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
        class="absolute z-1 pt-20 top-0 left-1/2 transform -translate-x-1/2 flex flex-col items-center justify-center text-center"
      />
    </div>
  </RuiCard>
</template>

<script setup lang="ts">
import AppImage from '@/components/common/AppImage.vue';
import GetPremiumPlaceholder from '@/components/graphs/GetPremiumPlaceholder.vue';

const { t } = useI18n();
</script>

<template>
  <RuiCard content-class="-mx-3">
    <template #header>
      <div class="pt-2">
        {{ t('premium_components.statistics.asset_amount_and_value_over_time') }}
      </div>
    </template>
    <div class="relative">
      <AppImage
        class="dark:invert-[0.88] dark:hue-rotate-[180deg]"
        src="./assets/images/placeholder/asset_amount_and_value_partial.png"
      />

      <GetPremiumPlaceholder
        :title="t('premium_settings.chart_limit.title')"
        class="absolute z-1 pt-20 top-0 left-1/2 transform -translate-x-1/2 flex flex-col items-center justify-center text-center"
      />
    </div>
  </RuiCard>
</template>

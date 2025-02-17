<script setup lang="ts">
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
    <GetPremiumPlaceholder
      :title="t('premium_settings.chart_limit.title')"
      class="flex flex-col items-center justify-center text-center bg-contain bg-no-repeat bg-center aspect-[25/9]"
      :style="{
        backgroundImage: `url('./assets/images/placeholder/asset_amount_and_value_partial.png')`,
      }"
    />
  </RuiCard>
</template>

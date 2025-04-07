<script setup lang="ts">
import AppImage from '@/components/common/AppImage.vue';
import GetPremiumPlaceholder from '@/components/common/GetPremiumPlaceholder.vue';

const { t } = useI18n();
const { isMdAndDown } = useBreakpoint();

function getFullPath(fileName: string) {
  return `./assets/images/placeholder/${fileName}`;
}
</script>

<template>
  <div class="relative">
    <div
      class="grid grid-cols-1 lg:grid-cols-5 gap-4 dark:invert-[0.9] dark:hue-rotate-[180deg]"
    >
      <AppImage
        class="lg:col-span-2 -m-4"
        :src="getFullPath('eth_staking_overview.png')"
      />
      <AppImage
        class="lg:col-span-3 -m-4"
        :src="isMdAndDown ? getFullPath('eth_staking_per_validator_small.png') : getFullPath('eth_staking_per_validator.png')"
      />
    </div>

    <GetPremiumPlaceholder
      class="absolute z-1 pt-40 top-0 left-1/2 transform -translate-x-1/2"
      :title="t('eth2_page.no_premium')"
    />
  </div>
</template>

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
      class="grid lg:grid-cols-2 gap-4 dark:invert-[0.9] dark:hue-rotate-[180deg]"
    >
      <AppImage
        class="-m-4"
        :src="getFullPath('liquity_staking_deposits.png')"
      />
      <AppImage
        class="-m-4"
        :src="getFullPath('liquity_staking_stake.png')"
      />
      <AppImage
        class="lg:col-span-2 -m-4"
        :src="isMdAndDown ? getFullPath('liquity_staking_statistics_mobile.png') : getFullPath('liquity_staking_statistics.png')"
      />
    </div>

    <GetPremiumPlaceholder
      class="absolute z-1 pt-40 top-0 left-1/2 transform -translate-x-1/2"
      :title="t('eth2_page.no_premium')"
    />
  </div>
</template>

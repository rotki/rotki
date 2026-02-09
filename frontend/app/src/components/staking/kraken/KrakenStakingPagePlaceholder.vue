<script setup lang="ts">
import AppImage from '@/components/common/AppImage.vue';
import GetPremiumPlaceholder from '@/components/common/GetPremiumPlaceholder.vue';
import { getPublicPlaceholderImagePath } from '@/utils/file';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="relative">
    <AppImage
      class="-m-2 -mt-4 dark:invert-[0.9] dark:hue-rotate-[180deg] [&>img]:w-full"
      :src="getPublicPlaceholderImagePath('kraken_staking.png')"
    />

    <GetPremiumPlaceholder
      class="absolute z-1 pt-40 top-0 left-1/2 transform -translate-x-1/2"
      :title="t('kraken_page.no_premium')"
    />
  </div>
</template>

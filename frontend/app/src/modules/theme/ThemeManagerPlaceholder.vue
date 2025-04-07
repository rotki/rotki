<script setup lang="ts">
import AppImage from '@/components/common/AppImage.vue';
import GetPremiumPlaceholder from '@/components/common/GetPremiumPlaceholder.vue';

const { t } = useI18n();
</script>

<template>
  <div class="relative">
    <div class="grid lg:grid-cols-2 gap-4 dark:invert-[0.95] dark:hue-rotate-[180deg]">
      <AppImage
        src="./assets/images/placeholder/theme_manager.png"
        class="-m-2"
      />
      <AppImage
        src="./assets/images/placeholder/theme_manager.png"
        class="-m-2"
      />
    </div>

    <GetPremiumPlaceholder
      class="absolute z-1 pt-20 top-0 left-1/2 transform -translate-x-1/2"
      :title="t('theme_manager_lock')"
    />
  </div>
</template>

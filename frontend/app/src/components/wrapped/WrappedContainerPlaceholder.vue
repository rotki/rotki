<script setup lang="ts">
import AppImage from '@/components/common/AppImage.vue';
import RotkiLogo from '@/components/common/RotkiLogo.vue';
import GetPremiumPlaceholder from '@/components/graphs/GetPremiumPlaceholder.vue';

const { t } = useI18n();
</script>

<template>
  <div class="flex flex-col gap-6 py-4 px-2 relative">
    <div class="py-8 w-full rounded-lg flex flex-col items-center bg-gradient-to-b from-transparent to-rui-primary/[0.05]">
      <RotkiLogo
        :size="3"
        class="mb-4"
      />
      <h2 class="text-4xl font-bold mb-2">
        {{ t('wrapped.title') }}
      </h2>
      <p class="text-xl text-rui-text-secondary">
        {{ t('wrapped.year_subtitle') }}
      </p>
    </div>

    <div class="relative">
      <AppImage
        class="dark:invert-[0.89] dark:hue-rotate-[180deg]"
        src="./assets/images/placeholder/history_events_wrapped.png"
      />

      <GetPremiumPlaceholder
        class="absolute w-full pt-20 z-1 top-0 left-1/2 transform -translate-x-1/2"
        :title="t('wrapped.free_limit')"
      />
    </div>
  </div>
</template>

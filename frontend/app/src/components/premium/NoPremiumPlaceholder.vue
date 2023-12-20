<script setup lang="ts">
import { externalLinks } from '@/data/external-links';

defineProps<{ text: string }>();

const { t } = useI18n();
</script>

<template>
  <FullSizeContent class="gap-4">
    <div class="flex items-center justify-center">
      <div
        class="w-[8rem] h-[8rem] md:w-[16rem] md:h-[16rem] bg-rui-grey-200 p-8 md:p-16 rounded-full mb-8"
      >
        <slot name="logo">
          <RotkiLogo class="h-full w-full" :url="externalLinks.logo.noData" />
        </slot>
      </div>
    </div>
    <div class="text-h5">
      {{ t('no_premium_placeholder.no_premium') }}
    </div>
    <div class="text-subtitle-2 text-rui-text-secondary">
      {{ t('no_premium_placeholder.premium_only', { text }) }}
    </div>
    <i18n
      path="no_premium_placeholder.get_premium"
      class="text-rui-text-secondary"
    >
      <ExternalLink :text="t('common.website')" color="primary" premium />
    </i18n>
  </FullSizeContent>
</template>

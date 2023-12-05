<script setup lang="ts">
defineProps<{ text: string }>();

const { t } = useI18n();

const { premiumURL } = useInterop();
const remoteEmptyScreenLogo =
  'https://raw.githubusercontent.com/rotki/data/main/assets/icons/empty_screen_logo.png';
</script>

<template>
  <FullSizeContent class="gap-4">
    <div class="flex items-center justify-center">
      <div
        class="w-[8rem] h-[8rem] md:w-[16rem] md:h-[16rem] bg-rui-grey-200 p-8 md:p-16 rounded-full mb-8"
      >
        <slot name="logo">
          <RotkiLogo class="h-full w-full" :url="remoteEmptyScreenLogo" />
        </slot>
      </div>
    </div>
    <div class="text-h5">
      {{ t('no_premium_placeholder.no_premium') }}
    </div>
    <div class="text-subtitle-2 text--secondary">
      {{ t('no_premium_placeholder.premium_only', { text }) }}
    </div>
    <i18n
      path="no_premium_placeholder.get_premium"
      tag="p"
      class="text-rui-text-secondary"
    >
      <BaseExternalLink
        text="website."
        :href="premiumURL"
        class="font-medium"
      />
    </i18n>
  </FullSizeContent>
</template>

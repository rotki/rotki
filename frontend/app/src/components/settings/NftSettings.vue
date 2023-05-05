<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <setting-category>
    <template #title>
      {{ t('general_settings.nft_setting.title') }}
    </template>

    <div>
      <div class="text-h6">
        {{ t('general_settings.nft_setting.subtitle.include_nfts') }}
      </div>
      <nfts-in-net-value-setting />
    </div>

    <div class="mt-8">
      <nft-image-rendering-setting />
    </div>
  </setting-category>
</template>

<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('general_settings.nft_setting.title') }}
    </template>

    <div>
      <div class="text-h6">
        {{ t('general_settings.nft_setting.subtitle.include_nfts') }}
      </div>
      <NftsInNetValueSetting />
    </div>

    <div class="mt-8">
      <NftImageRenderingSetting />
    </div>
  </SettingCategory>
</template>

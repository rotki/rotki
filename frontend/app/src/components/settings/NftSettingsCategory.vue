<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('general_settings.nft_setting.title') }}
    </template>
    <template #subtitle>
      {{ t('general_settings.nft_setting.subtitle.include_nfts') }}
    </template>

    <SettingsItem>
      <template #title>
        {{ t('general_settings.nft_setting.label.include_nfts_subtitle') }}
      </template>
      <template #subtitle>
        {{ t('general_settings.nft_setting.label.include_nfts_hint') }}
      </template>
      <NftsInNetValueSetting />
    </SettingsItem>

    <SettingsItem>
      <template #title>
        {{ t('general_settings.nft_setting.subtitle.nft_images_rendering_setting') }}
      </template>
      <template #subtitle>
        <i18n-t
          tag="div"
          keypath="general_settings.nft_setting.subtitle.nft_images_rendering_setting_hint"
        >
          <template #link>
            <ExternalLink
              color="primary"
              :url="externalLinks.nftWarning"
            >
              {{ t('common.here') }}
            </ExternalLink>
          </template>
        </i18n-t>
      </template>
      <NftImageRenderingSetting />
    </SettingsItem>
  </SettingCategory>
</template>

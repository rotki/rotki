<script setup lang="ts">
import { externalLinks } from '@shared/external-links';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import NftImageRenderingSetting from '@/modules/settings/general/nft/NftImageRenderingSetting.vue';
import NftsInNetValueSetting from '@/modules/settings/general/nft/NftsInNetValueSetting.vue';
import { SettingsHighlightIds } from '@/modules/settings/setting-highlight-ids';
import SettingCategory from '@/modules/settings/SettingCategory.vue';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('general_settings.nft_setting.title') }}
    </template>
    <template #subtitle>
      {{ t('general_settings.nft_setting.subtitle.include_nfts') }}
    </template>

    <SettingsItem :id="SettingsHighlightIds.NFT_IN_NET_VALUE">
      <template #title>
        {{ t('general_settings.nft_setting.label.include_nfts_subtitle') }}
      </template>
      <template #subtitle>
        {{ t('general_settings.nft_setting.label.include_nfts_hint') }}
      </template>
      <NftsInNetValueSetting />
    </SettingsItem>

    <SettingsItem :id="SettingsHighlightIds.NFT_IMAGE_RENDERING">
      <template #title>
        {{ t('general_settings.nft_setting.subtitle.nft_images_rendering_setting') }}
      </template>
      <template #subtitle>
        <i18n-t
          scope="global"
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

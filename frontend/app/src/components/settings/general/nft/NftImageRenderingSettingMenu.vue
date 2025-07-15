<script setup lang="ts">
import { externalLinks } from '@shared/external-links';
import ExternalLink from '@/components/helper/ExternalLink.vue';
import NftImageRenderingSetting from '@/components/settings/general/nft/NftImageRenderingSetting.vue';

const { t } = useI18n({ useScope: 'global' });

const dialogOpen = ref(false);
</script>

<template>
  <RuiMenu
    menu-class="max-w-[32rem] !z-[1]"
    :popper="{ placement: 'bottom-end' }"
    :persistent="dialogOpen"
  >
    <template #activator="{ attrs }">
      <RuiButton
        variant="text"
        icon
        class="!p-2"
        v-bind="attrs"
      >
        <RuiIcon name="lu-file-cog" />
      </RuiButton>
    </template>
    <div class="p-4">
      <i18n-t
        scope="global"
        tag="div"
        class="mb-3 text-body-2 text-rui-text-secondary"
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
      <NftImageRenderingSetting @dialog-open="dialogOpen = $event" />
    </div>
  </RuiMenu>
</template>

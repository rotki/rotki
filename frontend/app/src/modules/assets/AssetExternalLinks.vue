<script setup lang="ts">
import { externalLinks } from '@shared/external-links';
import { getPublicServiceImagePath } from '@/modules/core/common/file/file';
import AppImage from '@/modules/shell/components/AppImage.vue';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

const { coingecko, cryptocompare } = defineProps<{
  coingecko?: string;
  cryptocompare?: string;
}>();

const { t } = useI18n({ useScope: 'global' });

const { coingeckoAsset, cryptocompareAsset } = externalLinks;
</script>

<template>
  <ExternalLink
    v-if="coingecko"
    custom
    :url="coingeckoAsset.replace('$symbol', coingecko)"
  >
    <RuiButton
      variant="text"
      icon
      size="sm"
      :aria-label="t('external_services.coingecko.title')"
    >
      <AppImage
        size="16px"
        :src="getPublicServiceImagePath('coingecko.svg')"
      />
    </RuiButton>
  </ExternalLink>
  <ExternalLink
    v-if="cryptocompare"
    custom
    :url="cryptocompareAsset.replace('$symbol', cryptocompare)"
  >
    <RuiButton
      variant="text"
      icon
      size="sm"
      :aria-label="t('external_services.cryptocompare.title')"
    >
      <AppImage
        size="16px"
        :src="getPublicServiceImagePath('cryptocompare.svg')"
      />
    </RuiButton>
  </ExternalLink>
</template>

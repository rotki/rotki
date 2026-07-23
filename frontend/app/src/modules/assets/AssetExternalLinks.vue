<script setup lang="ts">
import { externalLinks } from '@shared/external-links';
import { getPublicServiceImagePath } from '@/modules/core/common/file/file';
import AppImage from '@/modules/shell/components/AppImage.vue';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

const { coingecko, cryptocompare } = defineProps<{
  coingecko?: string;
  cryptocompare?: string;
}>();

const { coingeckoAsset, cryptocompareAsset } = externalLinks;
</script>

<template>
  <ExternalLink
    v-if="coingecko"
    custom
    :url="coingeckoAsset.replace('$symbol', coingecko)"
  >
    <RuiButton
      size="sm"
      icon
    >
      <template #prepend>
        <AppImage
          size="30px"
          :src="getPublicServiceImagePath('coingecko.svg')"
        />
      </template>
    </RuiButton>
  </ExternalLink>
  <ExternalLink
    v-if="cryptocompare"
    custom
    :url="cryptocompareAsset.replace('$symbol', cryptocompare)"
  >
    <RuiButton
      size="sm"
      icon
    >
      <template #prepend>
        <AppImage
          size="30px"
          :src="getPublicServiceImagePath('cryptocompare.svg')"
        />
      </template>
    </RuiButton>
  </ExternalLink>
</template>

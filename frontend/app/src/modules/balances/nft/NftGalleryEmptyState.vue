<script setup lang="ts">
import InternalLink from '@/modules/shell/components/InternalLink.vue';
import NoDataScreen from '@/modules/shell/components/NoDataScreen.vue';

const { error } = defineProps<{
  error: string;
  nftLimited: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <NoDataScreen
    :icon="error ? 'lu-image-off' : 'lu-image'"
    data-testid="nft-gallery-empty"
  >
    <template #title>
      {{ error ? t('nft_gallery.error_title') : t('nft_gallery.empty_title') }}
    </template>
    <i18n-t
      v-if="nftLimited"
      scope="global"
      keypath="nft_gallery.fill_api_key"
    >
      <template #link>
        <InternalLink
          :to="{
            name: '/api-keys/external/',
            query: { service: 'opensea' },
          }"
        >
          {{ t('nft_gallery.open_sea') }}
        </InternalLink>
      </template>
    </i18n-t>
    <template v-else>
      {{ error ? error : t('nft_gallery.empty_subtitle') }}
    </template>
  </NoDataScreen>
</template>

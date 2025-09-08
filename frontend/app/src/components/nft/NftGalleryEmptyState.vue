<script setup lang="ts">
import NoDataScreen from '@/components/common/NoDataScreen.vue';
import InternalLink from '@/components/helper/InternalLink.vue';
import { Routes } from '@/router/routes';

interface Props {
  error: string;
  nftLimited: boolean;
}

defineProps<Props>();

const emit = defineEmits<{
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <NoDataScreen full>
    <template #title>
      {{ error ? t('nft_gallery.error_title') : t('nft_gallery.empty_title') }}
    </template>
    <div v-if="nftLimited">
      <i18n-t
        scope="global"
        keypath="nft_gallery.fill_api_key"
      >
        <template #link>
          <InternalLink
            :to="{
              path: Routes.API_KEYS_EXTERNAL_SERVICES.toString(),
              query: { service: 'opensea' },
            }"
          >
            {{ t('nft_gallery.open_sea') }}
          </InternalLink>
        </template>
      </i18n-t>
    </div>
    <div v-else>
      {{ error ? error : t('nft_gallery.empty_subtitle') }}
    </div>
    <RuiButton
      color="primary"
      class="mx-auto mt-8"
      @click="emit('refresh')"
    >
      <template #prepend>
        <RuiIcon
          name="lu-refresh-ccw"
          size="20"
        />
      </template>
      {{ t('common.refresh') }}
    </RuiButton>
  </NoDataScreen>
</template>

<script setup lang="ts">
import { useAirdropsMetadata } from '@/modules/airdrops/use-airdrops-metadata';
import { getPublicProtocolImagePath } from '@/modules/core/common/file/file';
import AppImage from '@/modules/shell/components/AppImage.vue';

const { source, iconUrl, icon } = defineProps<{
  source: string;
  iconUrl?: string;
  icon?: string;
}>();

const { getAirdropImageUrl, getAirdropName, loading } = useAirdropsMetadata();

const name = getAirdropName(() => source);
const image = getAirdropImageUrl(() => source);

const imageFromIconName = computed<string | undefined>(() => {
  if (!icon)
    return undefined;

  return getPublicProtocolImagePath(icon);
});
</script>

<template>
  <div class="flex items-center gap-4">
    <AppImage
      class="icon-bg"
      size="1.5rem"
      :src="iconUrl || imageFromIconName || image"
      contain
      :loading="loading"
    />
    <div>{{ name }}</div>
  </div>
</template>

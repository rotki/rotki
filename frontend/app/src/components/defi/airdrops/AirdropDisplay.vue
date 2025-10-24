<script setup lang="ts">
import AppImage from '@/components/common/AppImage.vue';
import { useAirdropsMetadata } from '@/composables/defi/airdrops/metadata';
import { getPublicProtocolImagePath } from '@/utils/file';

const props = defineProps<{
  source: string;
  iconUrl?: string;
  icon?: string;
}>();

const { getAirdropImageUrl, getAirdropName, loading } = useAirdropsMetadata();

const { icon, source } = toRefs(props);

const name = getAirdropName(source);
const image = getAirdropImageUrl(source);
const imageFromIconName = computed(() => {
  const iconVal = get(icon);
  if (!iconVal)
    return undefined;

  return getPublicProtocolImagePath(iconVal);
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

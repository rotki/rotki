<script setup lang="ts">
import AppImage from '@/components/common/AppImage.vue';
import AdaptiveWrapper from '@/components/display/AdaptiveWrapper.vue';
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
    <AdaptiveWrapper>
      <AppImage
        :src="iconUrl || imageFromIconName || image"
        width="1.5rem"
        height="1.5rem"
        contain
        :loading="loading"
        max-height="2rem"
        max-width="2rem"
      />
    </AdaptiveWrapper>
    <div>{{ name }}</div>
  </div>
</template>

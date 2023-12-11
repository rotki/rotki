<script setup lang="ts">
const props = defineProps<{
  source: string;
}>();

const { getAirdropName, getAirdropImageUrl } = useAirdropsMetadata();

const { source } = toRefs(props);

const name = getAirdropName(source);
const image = getAirdropImageUrl(source);
</script>

<template>
  <div class="flex items-center gap-4">
    <AdaptiveWrapper>
      <AppImage
        :src="image"
        width="1.5rem"
        height="1.5rem"
        contain
        max-height="2rem"
        max-width="2rem"
      />
    </AdaptiveWrapper>
    <div>{{ name }}</div>
  </div>
</template>

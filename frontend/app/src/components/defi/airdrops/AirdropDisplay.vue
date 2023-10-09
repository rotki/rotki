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
      <VImg
        width="24px"
        height="24px"
        contain
        position="left"
        max-height="32px"
        max-width="32px"
        :src="image"
      />
    </AdaptiveWrapper>
    <div>{{ name }}</div>
  </div>
</template>

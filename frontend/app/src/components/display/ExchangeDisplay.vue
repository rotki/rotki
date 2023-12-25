<script setup lang="ts">
const props = defineProps<{
  exchange: string;
}>();

const { exchange } = toRefs(props);
const { locationData } = useLocations();

const location = locationData(exchange);
const name = useRefMap(location, location => location?.name);
const image = useRefMap(location, location => location?.image ?? undefined);
</script>

<template>
  <div class="flex flex-row items-center shrink">
    <AdaptiveWrapper>
      <AppImage width="24px" height="24px" contain :src="image" />
    </AdaptiveWrapper>
    <div class="ml-2" v-text="name" />
  </div>
</template>

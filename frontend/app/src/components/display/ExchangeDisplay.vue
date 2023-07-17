<script setup lang="ts">
import { type SupportedExchange } from '@/types/exchanges';

const props = defineProps<{
  exchange: SupportedExchange;
}>();

const { exchange } = toRefs(props);
const { locationData } = useLocations();

const location = locationData(exchange);
const name = useRefMap(location, location => location?.name);
const image = useRefMap(location, location => location?.image);
</script>

<template>
  <div class="d-flex flex-row align-center shrink">
    <AdaptiveWrapper>
      <VImg width="24px" height="24px" contain :src="image" />
    </AdaptiveWrapper>
    <div class="ml-2" v-text="name" />
  </div>
</template>

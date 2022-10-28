<template>
  <div class="d-flex flex-row align-center shrink">
    <adaptive-wrapper>
      <v-img width="24px" height="24px" contain :src="icon" />
    </adaptive-wrapper>
    <div class="ml-2" v-text="name" />
  </div>
</template>

<script setup lang="ts">
import { PropType } from 'vue';
import AdaptiveWrapper from '@/components/display/AdaptiveWrapper.vue';
import { SupportedExchange } from '@/types/exchanges';
import { TradeLocationData, tradeLocations } from '@/types/trades';
import { toSentenceCase } from '@/utils/text';

const props = defineProps({
  exchange: { required: true, type: String as PropType<SupportedExchange> }
});

const { exchange } = toRefs(props);
const locations = tradeLocations;

const location = computed<TradeLocationData | undefined>(() => {
  return locations.find(({ identifier }) => identifier === get(exchange));
});

const name = computed<string>(() => {
  return get(location)?.name ?? toSentenceCase(get(exchange));
});

const icon = computed<string>(() => {
  return get(location)?.icon ?? '';
});
</script>

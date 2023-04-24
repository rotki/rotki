<script setup lang="ts">
import { type ComputedRef } from 'vue';
import { type SupportedExchange } from '@/types/exchanges';
import { type TradeLocationData } from '@/types/history/trade/location';

const props = defineProps<{
  exchange: SupportedExchange;
}>();

const { exchange } = toRefs(props);
const { getLocation } = useLocations();

const location: ComputedRef<TradeLocationData | undefined> = computed(() =>
  getLocation(exchange)
);

const name = computed<string>(
  () => get(location)?.name ?? toSentenceCase(get(exchange))
);

const image = computed<string>(() => get(location)?.image ?? '');
</script>

<template>
  <div class="d-flex flex-row align-center shrink">
    <adaptive-wrapper>
      <v-img width="24px" height="24px" contain :src="image" />
    </adaptive-wrapper>
    <div class="ml-2" v-text="name" />
  </div>
</template>

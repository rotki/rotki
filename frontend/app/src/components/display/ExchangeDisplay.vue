<script setup lang="ts">
import { type PropType } from 'vue';
import { type SupportedExchange } from '@/types/exchanges';
import { toSentenceCase } from '@/utils/text';
import { type TradeLocationData } from '@/types/history/trade/location';

const props = defineProps({
  exchange: { required: true, type: String as PropType<SupportedExchange> }
});

const { exchange } = toRefs(props);
const { tradeLocations } = useTradeLocations();

const location = computed<TradeLocationData | undefined>(() =>
  get(tradeLocations).find(({ identifier }) => identifier === get(exchange))
);

const name = computed<string>(
  () => get(location)?.name ?? toSentenceCase(get(exchange))
);

const icon = computed<string>(() => get(location)?.icon ?? '');
</script>

<template>
  <div class="d-flex flex-row align-center shrink">
    <adaptive-wrapper>
      <v-img width="24px" height="24px" contain :src="icon" />
    </adaptive-wrapper>
    <div class="ml-2" v-text="name" />
  </div>
</template>

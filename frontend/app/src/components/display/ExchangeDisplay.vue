<template>
  <div class="d-flex flex-row align-center shrink">
    <adaptive-wrapper>
      <v-img width="24px" height="24px" contain :src="icon" />
    </adaptive-wrapper>
    <div class="ml-2" v-text="name" />
  </div>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  PropType,
  toRefs
} from '@vue/composition-api';
import { get } from '@vueuse/core';
import AdaptiveWrapper from '@/components/display/AdaptiveWrapper.vue';
import { tradeLocations } from '@/components/history/consts';
import { TradeLocationData } from '@/components/history/type';
import { SupportedExchange } from '@/types/exchanges';
import { toSentenceCase } from '@/utils/text';

export default defineComponent({
  name: 'ExchangeDisplay',
  components: { AdaptiveWrapper },
  props: {
    exchange: { required: true, type: String as PropType<SupportedExchange> }
  },
  setup(props) {
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

    return {
      icon,
      name
    };
  }
});
</script>

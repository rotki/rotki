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
import AdaptiveWrapper from '@/components/display/AdaptiveWrapper.vue';
import { tradeLocations } from '@/components/history/consts';
import { TradeLocationData } from '@/components/history/type';
import { capitalize } from '@/filters';
import { SupportedExchange } from '@/types/exchanges';

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
      return locations.find(({ identifier }) => identifier === exchange.value);
    });

    const name = computed<string>(() => {
      return location.value?.name ?? capitalize(exchange.value);
    });

    const icon = computed<string>(() => {
      return location.value?.icon ?? '';
    });

    return {
      icon,
      name
    };
  }
});
</script>

<template>
  <v-row align="center">
    <v-col cols="auto">
      <adaptive-wrapper>
        <v-img
          :width="size"
          contain
          position="left"
          :max-height="size"
          :src="icon"
        />
      </adaptive-wrapper>
    </v-col>
    <v-col v-if="identifier == PriceOracle.UNISWAP3" cols="auto">
      {{ t('oracles.uniswap_v3') }}
    </v-col>
    <v-col v-else-if="identifier == PriceOracle.UNISWAP2" cols="auto">
      {{ t('oracles.uniswap_v2') }}
    </v-col>
    <v-col v-else-if="identifier == PriceOracle.MANUALCURRENT" cols="auto">
      {{ t('oracles.manual_latest') }}
    </v-col>
    <v-col v-else cols="auto">
      {{ toSentenceCase(identifier) }}
    </v-col>
  </v-row>
</template>

<script setup lang="ts">
import AdaptiveWrapper from '@/components/display/AdaptiveWrapper.vue';
import { PriceOracle } from '@/types/price-oracle';
import { toSentenceCase } from '@/utils/text';

const props = defineProps({
  identifier: { required: true, type: String }
});

const { t } = useI18n();

const { identifier } = toRefs(props);

const size = computed<string>(() => {
  if (get(identifier) === PriceOracle.MANUAL) {
    return '40px';
  }
  return '48px';
});

const icon = computed<string>(() => {
  if (get(identifier) === PriceOracle.CRYPTOCOMPARE) {
    return '/assets/images/oracles/cryptocompare.png';
  } else if (get(identifier) === PriceOracle.COINGECKO) {
    return '/assets/images/oracles/coingecko.svg';
  } else if (get(identifier) === PriceOracle.MANUAL) {
    return '/assets/images/oracles/book.svg';
  } else if (get(identifier) === PriceOracle.MANUALCURRENT) {
    return '/assets/images/oracles/book.svg';
  } else if (identifier.value === PriceOracle.UNISWAP2) {
    return '/assets/images/defi/uniswap.svg';
  } else if (identifier.value === PriceOracle.UNISWAP3) {
    return '/assets/images/defi/uniswap.svg';
  } else if (identifier.value === PriceOracle.SADDLE) {
    return '/assets/images/airdrops/saddle-finance.svg';
  } else if (identifier.value === PriceOracle.DEFILLAMA) {
    return '/assets/images/oracles/defillama.svg';
  }
  return '';
});
</script>

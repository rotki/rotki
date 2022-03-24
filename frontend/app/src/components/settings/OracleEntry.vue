<template>
  <v-row align="center">
    <v-col cols="auto">
      <v-img
        :width="size"
        contain
        position="left"
        :max-height="size"
        :src="icon"
      />
    </v-col>
    <v-col v-if="identifier == 'uniswapv3'" cols="auto">
      {{ $t('oracles.uniswap_v3') }}
    </v-col>
    <v-col v-else-if="identifier == 'uniswapv2'" cols="auto">
      {{ $t('oracles.uniswap_v2') }}
    </v-col>
    <v-col v-else cols="auto">
      {{ toSentenceCase(identifier) }}
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { computed, defineComponent, toRefs } from '@vue/composition-api';
import { get } from '@vueuse/core';
import { toSentenceCase } from '@/utils/text';

export default defineComponent({
  name: 'OracleEntry',
  props: {
    identifier: { required: true, type: String }
  },
  setup(props) {
    const { identifier } = toRefs(props);

    const size = computed<string>(() => {
      if (get(identifier) === 'manual') {
        return '40px';
      }
      return '48px';
    });

    const icon = computed<string>(() => {
      if (get(identifier) === 'cryptocompare') {
        return '/assets/images/oracles/cryptocompare.png';
      } else if (get(identifier) === 'coingecko') {
        return '/assets/images/oracles/coingecko.svg';
      } else if (get(identifier) === 'manual') {
        return '/assets/images/oracles/book.svg';
      } else if (identifier.value === 'uniswapv2') {
        return '/assets/images/defi/uniswap.svg';
      } else if (identifier.value === 'uniswapv3') {
        return '/assets/images/defi/uniswap.svg';
      } else if (identifier.value === 'saddle') {
        return '/assets/images/airdrops/saddle-finance.svg';
      }
      return '';
    });

    return {
      size,
      icon,
      toSentenceCase
    };
  }
});
</script>

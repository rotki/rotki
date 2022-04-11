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
    <v-col cols="auto">
      {{ capitalize(identifier) }}
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { computed, defineComponent, toRefs } from '@vue/composition-api';
import { get } from '@vueuse/core';

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
        return require('@/assets/images/oracles/cryptocompare.png');
      } else if (get(identifier) === 'coingecko') {
        return require('@/assets/images/oracles/coingecko.svg');
      } else if (get(identifier) === 'manual') {
        return require('@/assets/images/oracles/book.svg');
      }
      return '';
    });

    const capitalize = (text: string) => {
      return text[0].toUpperCase() + text.slice(1);
    };

    return {
      size,
      icon,
      capitalize
    };
  }
});
</script>

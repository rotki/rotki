<template>
  <v-row align="center">
    <v-col cols="4">
      <v-img
        :width="size"
        contain
        position="left"
        :max-height="size"
        :src="icon"
      />
    </v-col>
    <v-col>
      {{ capitalize(identifier) }}
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { computed, defineComponent, toRefs } from '@vue/composition-api';

export default defineComponent({
  name: 'OracleEntry',
  props: {
    identifier: { required: true, type: String }
  },
  setup(props) {
    const { identifier } = toRefs(props);

    const size = computed<string>(() => {
      if (identifier.value === 'manual') {
        return '40px';
      }
      return '48px';
    });

    const icon = computed<string>(() => {
      if (identifier.value === 'cryptocompare') {
        return require('@/assets/images/oracles/cryptocompare.png');
      } else if (identifier.value === 'coingecko') {
        return require('@/assets/images/oracles/coingecko.svg');
      } else if (identifier.value === 'manual') {
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

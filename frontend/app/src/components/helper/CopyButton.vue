<template>
  <v-tooltip top open-delay="400">
    <template #activator="{ on, attrs }">
      <v-btn small v-bind="attrs" icon @click="copy" v-on="on">
        <v-icon small>mdi-content-copy</v-icon>
      </v-btn>
    </template>
    <span>{{ tooltip }}</span>
  </v-tooltip>
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import { toRefs, useClipboard } from '@vueuse/core';

export default defineComponent({
  name: 'CopyButton',
  props: {
    value: { required: true, type: String },
    tooltip: { required: true, type: String }
  },
  setup(props) {
    const { value } = toRefs(props);
    const { copy: copyText } = useClipboard({ source: value });

    const copy = () => copyText();

    return {
      copy
    };
  }
});
</script>

<template>
  <v-tooltip top open-delay="400">
    <template #activator="{ on, attrs }">
      <v-btn small v-bind="attrs" icon v-on="on" @click="copy">
        <v-icon small>mdi-content-copy</v-icon>
      </v-btn>
    </template>
    <span>{{ tooltip }}</span>
  </v-tooltip>
</template>

<script lang="ts">
import { defineComponent, toRefs } from '@vue/composition-api';

export default defineComponent({
  name: 'CopyButton',
  props: {
    value: { required: true, type: String },
    tooltip: { required: true, type: String }
  },
  setup(props) {
    const { value } = toRefs(props);
    const copy = () => {
      navigator.clipboard.writeText(value.value);
    };

    return {
      copy
    };
  }
});
</script>

<template>
  <span>
    <v-btn icon small @click="click">
      <v-icon v-if="expanded" small> mdi-chevron-up </v-icon>
      <v-icon v-else small> mdi-chevron-down </v-icon>
    </v-btn>
  </span>
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';

export default defineComponent({
  name: 'RowExpander',
  props: {
    expanded: { required: true, type: Boolean }
  },
  emits: ['click'],
  setup(_, { emit }) {
    const click = () => emit('click');

    return {
      click
    };
  }
});
</script>

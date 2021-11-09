<template>
  <v-tooltip top>
    <template #activator="{ on, attrs }">
      <v-btn
        fab
        text
        small
        depressed
        :disabled="loading"
        v-bind="attrs"
        @click="refresh"
        v-on="on"
      >
        <v-icon color="primary">mdi-refresh</v-icon>
      </v-btn>
    </template>
    <span>{{ tooltip }}</span>
  </v-tooltip>
</template>
<script lang="ts">
import { defineComponent } from '@vue/composition-api';

export default defineComponent({
  props: {
    loading: { required: true, type: Boolean },
    tooltip: { required: true, type: String }
  },
  emits: ['refresh'],
  setup(_, { emit }) {
    const refresh = () => {
      emit('refresh');
    };
    return {
      refresh
    };
  }
});
</script>

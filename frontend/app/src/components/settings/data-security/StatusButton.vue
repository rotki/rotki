<template>
  <v-row align="center">
    <v-col cols="auto">
      <v-tooltip top>
        <template #activator="{ on, attrs }">
          <v-btn
            color="primary"
            depressed
            v-bind="{ ...attrs, ...$attrs }"
            v-on="{ ...on, ...$listeners }"
          >
            <slot />
          </v-btn>
        </template>
        <span>{{ tooltip }}</span>
      </v-tooltip>
    </v-col>
    <v-col v-if="!!successMessage">
      <v-icon color="success">mdi-check-circle</v-icon>
      <span class="ml-2 success--text status-button__message--success">
        {{ successMessage }}
      </span>
    </v-col>
    <v-col v-else-if="!!errorMessage">
      <v-icon color="error">mdi-alert</v-icon>
      <span class="ml-2 error--text status-button__message--error">
        {{ errorMessage }}
      </span>
    </v-col>
  </v-row>
</template>
<script lang="ts">
import { defineComponent } from '@vue/composition-api';

export default defineComponent({
  name: 'StatusButton',
  props: {
    successMessage: { required: true, type: String },
    errorMessage: { required: true, type: String },
    tooltip: { required: false, type: String, default: '' }
  }
});
</script>

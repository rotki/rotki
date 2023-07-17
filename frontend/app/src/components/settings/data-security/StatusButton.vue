<script setup lang="ts">
import { useListeners } from 'vue';

defineProps({
  successMessage: { required: true, type: String },
  errorMessage: { required: true, type: String },
  tooltip: { required: false, type: String, default: '' }
});
const rootAttrs = useAttrs();
const rootListeners = useListeners();
</script>

<template>
  <VRow align="center">
    <VCol cols="auto">
      <VTooltip top>
        <template #activator="{ on, attrs }">
          <VBtn
            color="primary"
            depressed
            v-bind="{ ...attrs, ...rootAttrs }"
            v-on="{ ...on, ...rootListeners }"
          >
            <slot />
          </VBtn>
        </template>
        <span>{{ tooltip }}</span>
      </VTooltip>
    </VCol>
    <VCol v-if="!!successMessage">
      <VIcon color="success">mdi-check-circle</VIcon>
      <span class="ml-2 success--text status-button__message--success">
        {{ successMessage }}
      </span>
    </VCol>
    <VCol v-else-if="!!errorMessage">
      <VIcon color="error">mdi-alert</VIcon>
      <span class="ml-2 error--text status-button__message--error">
        {{ errorMessage }}
      </span>
    </VCol>
  </VRow>
</template>

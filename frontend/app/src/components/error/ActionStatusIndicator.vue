<template>
  <div
    v-if="status && (status.success || status.error)"
    class="action-status-indicator"
  >
    <v-alert
      class="mb-0"
      dense
      :color="status.success ? 'success' : 'error'"
      text
      outlined
      :icon="status.success ? 'mdi-check' : 'mdi-alert-circle-outline'"
    >
      {{ status.success || status.error }}
    </v-alert>
  </div>
</template>

<script setup lang="ts">
import { PropType } from 'vue';
import { BaseMessage } from '@/types/messages';

defineProps({
  status: {
    required: false,
    type: Object as PropType<BaseMessage | null>,
    default: null
  }
});
</script>

<style scoped lang="scss">
.action-status-indicator {
  height: 48px;
}
</style>

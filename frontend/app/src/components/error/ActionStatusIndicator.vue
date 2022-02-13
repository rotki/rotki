<template>
  <div class="action-status-indicator">
    <v-alert
      v-if="status"
      class="mb-0"
      dense
      :color="status.success ? 'success' : 'error'"
      text
      outlined
      :icon="status.success ? 'mdi-check' : 'mdi-alert-circle-outline'"
    >
      {{ status.message }}
    </v-alert>
  </div>
</template>

<script lang="ts">
import { defineComponent, PropType } from '@vue/composition-api';
import { ActionStatus } from '@/store/types';

export default defineComponent({
  name: 'ActionStatusIndicator',
  props: {
    status: {
      required: false,
      type: Object as PropType<ActionStatus | null>,
      default: null
    }
  }
});
</script>

<style scoped lang="scss">
.action-status-indicator {
  height: 48px;
  margin-bottom: 8px;
}
</style>

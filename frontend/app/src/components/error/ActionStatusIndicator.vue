<script setup lang="ts">
import type { BaseMessage } from '@/modules/messaging/base-message';

defineProps<{
  status: BaseMessage | null;
}>();
</script>

<template>
  <div
    v-if="status && (status.success || status.error)"
    class="action-status-indicator min-h-[3rem]"
  >
    <RuiAlert
      class="mb-0"
      :type="status.success ? 'success' : 'error'"
      variant="outlined"
    >
      {{ status.success || status.error }}
    </RuiAlert>
  </div>
</template>

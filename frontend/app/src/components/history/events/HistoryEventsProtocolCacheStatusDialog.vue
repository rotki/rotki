<script setup lang="ts">
import HistoryEventsProtocolCacheUpdateStatus from '@/components/history/events/HistoryEventsProtocolCacheUpdateStatus.vue';

interface Props {
  refreshing: boolean;
}

const modelValue = defineModel<boolean>({ required: true });

defineProps<Props>();

function closeDialog(): void {
  set(modelValue, false);
}
</script>

<template>
  <RuiDialog
    v-model="modelValue"
    max-width="600"
  >
    <HistoryEventsProtocolCacheUpdateStatus
      v-if="modelValue"
      :refreshing="refreshing"
    >
      <RuiButton
        variant="text"
        icon
        @click="closeDialog()"
      >
        <RuiIcon name="lu-x" />
      </RuiButton>
    </HistoryEventsProtocolCacheUpdateStatus>
  </RuiDialog>
</template>

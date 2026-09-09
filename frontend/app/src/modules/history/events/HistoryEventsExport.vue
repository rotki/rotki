<script setup lang="ts">
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import { useHistoryEventsExport } from '@/modules/history/events/use-history-events-export';

const { filters, matchExactEvents } = defineProps<{
  matchExactEvents: boolean;
  filters: HistoryEventRequestPayload;
}>();

const { t } = useI18n({ useScope: 'global' });

const { showConfirmation, taskRunning } = useHistoryEventsExport(
  () => filters,
  () => matchExactEvents,
);
</script>

<template>
  <RuiTooltip :open-delay="400">
    <template #activator>
      <RuiButton
        color="primary"
        variant="outlined"
        icon
        size="xl"
        class="!rounded"
        :disabled="taskRunning"
        @click="showConfirmation()"
      >
        <RuiIcon name="lu-file-down" />
      </RuiButton>
    </template>
    {{ t('common.actions.export_csv') }}
  </RuiTooltip>
</template>

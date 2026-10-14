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
        variant="text"
        icon
        :disabled="taskRunning"
        :aria-label="t('common.actions.export_csv')"
        data-testid="history-events-export"
        @click="showConfirmation()"
      >
        <RuiIcon
          name="lu-file-down"
          size="18"
        />
      </RuiButton>
    </template>
    {{ t('common.actions.export_csv') }}
  </RuiTooltip>
</template>

<script setup lang="ts">
import type { ContextColorsType, RuiIcons } from '@rotki/ui-library';
import { HistoryEventState } from '@/types/history/events/schemas';

interface EventStateConfig {
  icon: RuiIcons;
  color: ContextColorsType;
  label: string;
}

const props = defineProps<{
  state: HistoryEventState;
}>();

const { t } = useI18n({ useScope: 'global' });

const EVENT_STATE_CONFIG: Record<HistoryEventState, EventStateConfig> = {
  [HistoryEventState.AUTO_MATCHED]: {
    icon: 'lu-link',
    color: 'info',
    label: t('transactions.events.event_states.auto_matched'),
  },
  [HistoryEventState.CUSTOMIZED]: {
    icon: 'lu-square-pen',
    color: 'primary',
    label: t('transactions.events.event_states.customized'),
  },
  [HistoryEventState.IMPORTED_FROM_CSV]: {
    icon: 'lu-file-spreadsheet',
    color: 'success',
    label: t('transactions.events.event_states.imported_from_csv'),
  },
  [HistoryEventState.PROFIT_ADJUSTMENT]: {
    icon: 'lu-calculator',
    color: 'warning',
    label: t('transactions.events.event_states.profit_adjustment'),
  },
};

const config = computed<EventStateConfig>(() => EVENT_STATE_CONFIG[props.state]);
</script>

<template>
  <RuiChip
    size="sm"
    :color="config.color"
    class="px-1"
  >
    <div class="flex items-center gap-1 text-caption font-bold !text-xs">
      <RuiIcon
        :name="config.icon"
        size="14"
      />
      {{ config.label }}
    </div>
  </RuiChip>
</template>

import type { ContextColorsType, RuiIcons } from '@rotki/ui-library';
import { HistoryEventState } from '@/types/history/events/schemas';

export interface EventStateConfig {
  icon: RuiIcons;
  color: ContextColorsType;
  label: string;
}

const validStates: string[] = Object.values(HistoryEventState);

export function isValidHistoryEventState(s: string): s is HistoryEventState {
  return validStates.includes(s);
}

export const useHistoryEventStateMapping = createSharedComposable(() => {
  const { t } = useI18n({ useScope: 'global' });

  const stateConfigs: Record<HistoryEventState, EventStateConfig> = {
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

  return {
    stateConfigs,
  };
});
